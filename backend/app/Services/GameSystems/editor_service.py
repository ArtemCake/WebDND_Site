# backend/app/Services/GameSystems/editor_service.py

"""Согласованное сохранение системы и черновика.

Одна операция — одна транзакция:
commit после подготовки полного ответа, rollback при ошибке.

Использовать с сессией запроса без посторонних несохранённых
изменений. Не вызывать внутри внешнего session.begin().
"""

from Config.imports import (AsyncSession, HTTPException, IntegrityError, UUID, func, insert, or_, select, update)
from backend.app.Database._models import (GameSystem, RuleEngineVersion, GameSystemRulesDraft)
from backend.app.Schemas.content import (GameSystemAdminRead, GameSystemCreate)
from backend.app.Schemas.game_rules import (GameSystemRulesDraftRead, RulesProfile)
from backend.app.Schemas.game_system_editor import (GameSystemEditorCreate, GameSystemEditorUpdate, GameSystemEditorRead)
from backend.app.Schemas.game_system_origin import (GameSystemEngineEditorUpdate, GameSystemEngineOriginRead, GameSystemFromEngineCreate)
from backend.app.Services.GameSystems.system_rule_origin import (load_editor_engine_origin, load_saved_engine_version, load_engine_origin, require_standalone_draft)
from backend.app.Schemas.rule_engines import RuleEngineVersionRead


_SYSTEMS = GameSystem.__table__
_DRAFTS = GameSystemRulesDraft.__table__


def _conflict(detail: str) -> HTTPException:
	return HTTPException(status_code=409, detail=detail)

async def _check_unique(session: AsyncSession, data: GameSystemCreate, exclude_id: UUID | None = None) -> None:
	stmt = select(_SYSTEMS.c.id).where(
		or_(
			_SYSTEMS.c.name == data.name,
			_SYSTEMS.c.slug == data.slug,
			)
	)

	if exclude_id is not None:
		stmt = stmt.where(_SYSTEMS.c.id != exclude_id)

	result = await session.execute(stmt.limit(1))

	if result.scalar_one_or_none() is not None:
		raise _conflict(
			"Игровая система с таким названием "
			"или кодом уже существует."
		)

def _rules_payload(rules: RulesProfile) -> dict:
	# Создаём независимый проверенный снимок.
	return RulesProfile.model_validate(
		rules.model_dump(mode="json")
	).model_dump(mode="json")

def _response(system, draft) -> GameSystemEditorRead:
	return GameSystemEditorRead(
		system=GameSystemAdminRead.model_validate(dict(system)),
		draft=GameSystemRulesDraftRead.model_validate(dict(draft)),
	)

async def _insert_draft(session: AsyncSession, system_id: UUID, payload: dict, *, origin: dict | None = None):
	result = await session.execute(
		insert(_DRAFTS)
		.values(
			system_id=system_id,
			rules_json=payload,
			revision=1,
			**(origin or {}),
		)
		.returning(*_DRAFTS.c)
	)

	return result.mappings().one()

async def _rollback_integrity(session: AsyncSession, exc: IntegrityError) -> None:
	await session.rollback()

	sqlstate = (
			getattr(exc.orig, "sqlstate", None)
			or getattr(exc.orig, "pgcode", None)
	)

	if sqlstate == "23505":
		raise _conflict(
			"Возник конфликт уникальности данных. "
			"Проверьте название и код системы, "
			"а также актуальное состояние черновика."
		) from exc

async def create_system_with_draft(session: AsyncSession, data: GameSystemEditorCreate) -> GameSystemEditorRead:
	try:
		payload = _rules_payload(data.rules)

		await _check_unique(session, data.system)

		system_result = await session.execute(
			insert(_SYSTEMS)
			.values(**data.system.model_dump())
			.returning(*_SYSTEMS.c)
		)
		system = system_result.mappings().one()

		draft = await _insert_draft(
			session,
			system["id"],
			payload,
		)

		# Проверяем формат ответа до фиксации транзакции.
		response = _response(system, draft)

		await session.commit()
		return response

	except IntegrityError as exc:
		await _rollback_integrity(session, exc)
		raise

	except Exception:
		await session.rollback()
		raise

async def update_system_with_draft(session: AsyncSession, system_id: UUID, data: GameSystemEditorUpdate) -> GameSystemEditorRead:
	try:
		payload = _rules_payload(data.rules)

		# Тот же порядок блокировок, что в rules_service:
		# сначала система, затем её черновик.
		system_result = await session.execute(
			select(_SYSTEMS)
			.where(_SYSTEMS.c.id == system_id)
			.with_for_update()
		)
		system = system_result.mappings().one_or_none()

		if system is None:
			raise HTTPException(
				status_code=404,
				detail="Игровая система не найдена.",
			)

		draft_result = await session.execute(
			select(_DRAFTS)
			.where(_DRAFTS.c.system_id == system_id)
			.with_for_update()
		)
		draft = draft_result.mappings().one_or_none()

		if draft is None:
			if data.expected_revision is not None:
				raise _conflict(
					"Черновик отсутствует. "
					"Загрузите актуальное состояние системы."
				)
		elif data.expected_revision != draft["revision"]:
			raise _conflict(
				"Черновик уже изменён. Ваши изменения "
				"не сохранены. Загрузите актуальную ревизию "
				"перед повторным сохранением."
			)
		require_standalone_draft(draft)
		# Нельзя незаметно изменить движок уже существующей
		# системы через пользовательскую форму.
		if (
				data.system.rules_engine_version
				!= system["rules_engine_version"]
		):
			raise _conflict(
				"Изменение версии движка не поддерживается "
				"этой формой."
			)

		await _check_unique(
			session,
			data.system,
			exclude_id=system_id,
		)

		updated_system_result = await session.execute(
			update(_SYSTEMS)
			.where(_SYSTEMS.c.id == system_id)
			.values(
				**data.system.model_dump(),
				updated_at=func.now(),
			)
			.returning(*_SYSTEMS.c)
		)
		updated_system = updated_system_result.mappings().one()

		if draft is None:
			updated_draft = await _insert_draft(
				session,
				system_id,
				payload,
			)
		else:
			updated_draft_result = await session.execute(
				update(_DRAFTS)
				.where(
					_DRAFTS.c.id == draft["id"],
					_DRAFTS.c.revision == data.expected_revision,
					)
				.values(
					rules_json=payload,
					revision=_DRAFTS.c.revision + 1,
					updated_at=func.now(),
				)
				.returning(*_DRAFTS.c)
			)
			updated_draft = (
				updated_draft_result.mappings().one_or_none()
			)

			if updated_draft is None:
				raise _conflict(
					"Черновик изменился во время сохранения. "
					"Изменения системы и правил отменены."
				)

		response = _response(updated_system, updated_draft)

		await session.commit()
		return response

	except IntegrityError as exc:
		await _rollback_integrity(session, exc)
		raise

	except Exception:
		await session.rollback()
		raise

async def create_system_from_engine(session: AsyncSession, actor_id: UUID, data: GameSystemFromEngineCreate) -> GameSystemEditorRead:
	"""Создать карточку системы и связанный черновик атомарно.

	Право создавать игровые системы проверяет вызывающий слой.
	actor_id поступает из проверенной аутентификации.
	"""
	try:
		assembled = await load_engine_origin(
			session,
			data,
			actor_id,
			data.system.rules_engine_version,
		)

		await _check_unique(session, data.system)

		system_result = await session.execute(
			insert(_SYSTEMS)
			.values(**data.system.model_dump())
			.returning(*_SYSTEMS.c)
		)
		system = system_result.mappings().one()

		draft = await _insert_draft(
			session,
			system["id"],
			assembled["rules_json"],
			origin={
				"engine_version_id": assembled["engine_version_id"],
				"rules_overrides_json": assembled["rules_overrides_json"],
			},
		)

		response = _response(system, draft)

		await session.commit()
		return response

	except IntegrityError as exc:
		await _rollback_integrity(session, exc)
		raise

	except Exception:
		await session.rollback()
		raise

async def get_system_engine_origin(session: AsyncSession, system_id: UUID) -> GameSystemEngineOriginRead:
	"""Получить основу сохранённого черновика.

	Право доступа к системе проверяет вызывающий слой.
	"""
	result = await session.execute(
		select(_DRAFTS).where(
			_DRAFTS.c.system_id == system_id,
			)
	)
	draft = result.mappings().one_or_none()

	if draft is None:
		raise HTTPException(
			status_code=404,
			detail="Черновик игровой системы не найден.",
		)

	version = await load_saved_engine_version(
		session,
		draft,
	)

	return GameSystemEngineOriginRead(
		draft_revision=draft["revision"],
		engine_version=RuleEngineVersionRead.model_validate(
			dict(version),
		),
	)

async def update_system_from_engine(session: AsyncSession, system_id: UUID, actor_id: UUID, data: GameSystemEngineEditorUpdate) -> GameSystemEditorRead:
	"""Атомарно обновить карточку системы и связанные правила.

	Право управления системой проверяет вызывающий слой.

	Порядок блокировок:
		система -> черновик -> выбранный движок, если нужен.

	Одна операция:
		один commit либо rollback всех изменений.
	"""
	try:
		system_result = await session.execute(
			select(_SYSTEMS)
			.where(_SYSTEMS.c.id == system_id)
			.with_for_update()
		)
		system = system_result.mappings().one_or_none()

		if system is None:
			raise HTTPException(
				status_code=404,
				detail="Игровая система не найдена.",
			)

		draft_result = await session.execute(
			select(_DRAFTS)
			.where(_DRAFTS.c.system_id == system_id)
			.with_for_update()
		)
		draft = draft_result.mappings().one_or_none()

		if draft is None:
			if data.expected_revision is not None:
				raise _conflict(
					"Черновик отсутствует. "
					"Загрузите актуальное состояние системы."
				)
		elif draft["revision"] != data.expected_revision:
			raise _conflict(
				"Черновик уже изменён. "
				"Карточка и правила не сохранены. "
				"Загрузите актуальную ревизию."
			)

		if (
				data.system.rules_engine_version
				!= system["rules_engine_version"]
		):
			raise _conflict(
				"Изменение версии программного исполнителя "
				"не поддерживается этой формой."
			)

		assembled = await load_editor_engine_origin(
			session,
			data,
			actor_id,
			system["rules_engine_version"],
			draft,
		)

		await _check_unique(
			session,
			data.system,
			exclude_id=system_id,
		)

		updated_system_result = await session.execute(
			update(_SYSTEMS)
			.where(_SYSTEMS.c.id == system_id)
			.values(
				**data.system.model_dump(),
				updated_at=func.now(),
			)
			.returning(*_SYSTEMS.c)
		)
		updated_system = (
			updated_system_result.mappings().one()
		)

		if draft is None:
			saved_draft = await _insert_draft(
				session,
				system_id,
				assembled["rules_json"],
				origin={
					"engine_version_id": (
						assembled["engine_version_id"]
					),
					"rules_overrides_json": (
						assembled["rules_overrides_json"]
					),
				},
			)
		else:
			saved_draft_result = await session.execute(
				update(_DRAFTS)
				.where(
					_DRAFTS.c.id == draft["id"],
					_DRAFTS.c.revision == data.expected_revision,
					)
				.values(
					**assembled,
					revision=_DRAFTS.c.revision + 1,
					updated_at=func.now(),
				)
				.returning(*_DRAFTS.c)
			)
			saved_draft = (
				saved_draft_result.mappings().one_or_none()
			)

			if saved_draft is None:
				raise _conflict(
					"Черновик изменился во время сохранения. "
					"Изменения карточки и правил отменены."
				)

		response = _response(
			updated_system,
			saved_draft,
		)

		await session.commit()
		return response

	except IntegrityError as exc:
		await _rollback_integrity(session, exc)
		raise

	except Exception:
		await session.rollback()
		raise