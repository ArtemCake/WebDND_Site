# backend/app/Services/GameSystems/rule_engine_service.py

"""Хранение черновиков и публикация движков.

Изменяющие операции самостоятельно завершают транзакцию:
commit при успехе, rollback при ошибке.

Использовать с отдельной сессией запроса без посторонних
несохранённых изменений и без внешнего session.begin().

actor_id должен приходить от проверенной аутентификации,
а не из тела пользовательского запроса.

На этом этапе:
- изменять движок и читать черновик может только владелец;
- чужую публикацию можно читать у активного публичного движка;
- административный обход прав не предусмотрен;
- смена программного исполнителя не предусмотрена.
"""

from Config.imports import (AsyncSession, HTTPException, IntegrityError, UUID, ValidationError,
	asynccontextmanager, func, insert, select, update)
from backend.app.Database._models import (RuleEngine, RuleEngineDraft, RuleEngineVersion)
from backend.app.Schemas.game_rules import RulesProfile
from backend.app.Schemas.rule_engines import (RuleEngineCreate, RuleEngineDraftRead, RuleEngineDraftUpdate, RuleEngineEditorRead,
	RuleEnginePublish, RuleEngineRead, RuleEngineVersionRead)


_ENGINES = RuleEngine.__table__
_DRAFTS = RuleEngineDraft.__table__
_VERSIONS = RuleEngineVersion.__table__

def _error(code: int, detail: str) -> HTTPException:
	return HTTPException(status_code=code, detail=detail)

def _require_actor(actor_id: UUID) -> None:
	if not isinstance(actor_id, UUID):
		raise _error(401, "Требуется авторизованный пользователь.")

@asynccontextmanager
async def _write(session: AsyncSession):
	try:
		yield
		await session.commit()

	except IntegrityError as exc:
		await session.rollback()

		sqlstate = (
				getattr(exc.orig, "sqlstate", None)
				or getattr(exc.orig, "pgcode", None)
		)

		if sqlstate == "23505":
			raise _error(
				409,
				"Конфликт уникальности. Проверьте код движка "
				"и актуальное состояние его черновика.",
			) from exc

		raise

	except Exception:
		await session.rollback()
		raise

def _payload(raw: dict) -> dict:
	"""Проверить правила и получить независимый JSON-снимок."""
	return RulesProfile.model_validate(raw).model_dump(mode="json")

def _check_revision(actual: int, expected: int) -> None:
	if actual != expected:
		raise _error(
			409,
			"Черновик уже изменён. Загрузите актуальную "
			"ревизию перед сохранением или публикацией.",
		)

async def _find_engine(session: AsyncSession, engine_id: UUID, actor_id: UUID, *, owner_only: bool, for_update: bool = False):
	_require_actor(actor_id)

	statement = select(_ENGINES).where(
		_ENGINES.c.id == engine_id,
		)

	if for_update:
		statement = statement.with_for_update()

	result = await session.execute(statement)
	engine = result.mappings().one_or_none()

	if engine is None:
		raise _error(404, "Движок не найден.")

	is_owner = engine["owner_id"] == actor_id
	is_public = (
			engine["visibility"] == "public"
			and engine["is_active"]
	)

	if not is_owner and (owner_only or not is_public):
		# Не раскрываем существование чужого закрытого движка.
		raise _error(404, "Движок не найден.")

	return engine

async def _find_draft(session: AsyncSession, engine_id: UUID, *, for_update: bool = False):
	statement = select(_DRAFTS).where(
		_DRAFTS.c.engine_id == engine_id,
		)

	if for_update:
		statement = statement.with_for_update()

	result = await session.execute(statement)
	draft = result.mappings().one_or_none()

	if draft is None:
		raise _error(404, "Черновик движка не найден.")

	return draft

async def create_engine_with_draft(session: AsyncSession, actor_id: UUID, data: RuleEngineCreate) -> RuleEngineEditorRead:
	async with _write(session):
		_require_actor(actor_id)
		payload = _payload(data.rules.model_dump(mode="json"))

		engine_result = await session.execute(
			insert(_ENGINES)
			.values(
				owner_id=actor_id,
				name=data.name,
				slug=data.slug,
				description=data.description,
				visibility=data.visibility,
				is_active=True,
			)
			.returning(*_ENGINES.c)
		)
		engine = engine_result.mappings().one()

		draft_result = await session.execute(
			insert(_DRAFTS)
			.values(
				engine_id=engine["id"],
				rules_json=payload,
				rules_engine_version=data.rules_engine_version,
				revision=1,
			)
			.returning(*_DRAFTS.c)
		)
		draft = draft_result.mappings().one()

		response = RuleEngineEditorRead(
			engine=RuleEngineRead.model_validate(dict(engine)),
			draft=RuleEngineDraftRead.model_validate(dict(draft)),
		)

	return response

async def get_engine_draft(session: AsyncSession, engine_id: UUID, actor_id: UUID) -> RuleEngineDraftRead:
	await _find_engine(
		session,
		engine_id,
		actor_id,
		owner_only=True,
	)
	draft = await _find_draft(session, engine_id)

	return RuleEngineDraftRead.model_validate(dict(draft))

async def update_engine_draft(session: AsyncSession, engine_id: UUID, actor_id: UUID, data: RuleEngineDraftUpdate) -> RuleEngineDraftRead:
	async with _write(session):
		# Общий порядок блокировок:
		# сначала карточка движка, затем черновик.
		await _find_engine(
			session,
			engine_id,
			actor_id,
			owner_only=True,
			for_update=True,
		)
		draft = await _find_draft(
			session,
			engine_id,
			for_update=True,
		)

		_check_revision(draft["revision"], data.expected_revision)
		payload = _payload(data.rules.model_dump(mode="json"))

		result = await session.execute(
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
		updated = result.mappings().one_or_none()

		if updated is None:
			raise _error(
				409,
				"Черновик изменился во время сохранения. "
				"Сохранение отменено.",
			)

		response = RuleEngineDraftRead.model_validate(dict(updated))

	return response

async def publish_engine_version(session: AsyncSession, engine_id: UUID, actor_id: UUID, data: RuleEnginePublish) -> RuleEngineVersionRead:
	async with _write(session):
		engine = await _find_engine(
			session,
			engine_id,
			actor_id,
			owner_only=True,
			for_update=True,
		)

		if not engine["is_active"]:
			raise _error(
				409,
				"Перед публикацией активируйте движок.",
			)

		draft = await _find_draft(
			session,
			engine_id,
			for_update=True,
		)
		_check_revision(draft["revision"], data.expected_revision)

		# Берём только сохранённый черновик.
		# Запрос публикации не содержит новых правил.
		try:
			payload = _payload(draft["rules_json"])
		except ValidationError as exc:
			raise _error(
				409,
				"Сохранённый черновик не соответствует схеме "
				"правил. Исправьте его перед публикацией.",
			) from exc

		# Блокировка карточки сериализует публикации
		# одного движка через этот сервис.
		number_result = await session.execute(
			select(
				func.coalesce(
					func.max(_VERSIONS.c.version_number),
					0,
				) + 1
			)
			.where(_VERSIONS.c.engine_id == engine_id)
		)
		next_number = number_result.scalar_one()

		version_result = await session.execute(
			insert(_VERSIONS)
			.values(
				engine_id=engine_id,
				version_number=next_number,
				source_draft_revision=draft["revision"],
				rules_json=payload,
				rules_engine_version=draft["rules_engine_version"],
			)
			.returning(*_VERSIONS.c)
		)
		response = RuleEngineVersionRead.model_validate(
			dict(version_result.mappings().one()),
		)

		# Публикация потребляет ревизию:
		# повтор того же запроса не создаст второй снимок.
		revision_result = await session.execute(
			update(_DRAFTS)
			.where(
				_DRAFTS.c.id == draft["id"],
				_DRAFTS.c.revision == data.expected_revision,
				)
			.values(
				revision=_DRAFTS.c.revision + 1,
				updated_at=func.now(),
			)
			.returning(_DRAFTS.c.revision)
		)

		if revision_result.scalar_one_or_none() is None:
			raise _error(
				409,
				"Черновик изменился во время публикации. "
				"Публикация отменена.",
			)

	return response

async def get_engine_version(session: AsyncSession, engine_id: UUID, version_id: UUID, actor_id: UUID) -> RuleEngineVersionRead:
	await _find_engine(
		session,
		engine_id,
		actor_id,
		owner_only=False,
	)

	result = await session.execute(
		select(_VERSIONS)
		.where(
			_VERSIONS.c.id == version_id,
			_VERSIONS.c.engine_id == engine_id,
			)
	)
	version = result.mappings().one_or_none()

	if version is None:
		raise _error(404, "Публикация движка не найдена.")

	return RuleEngineVersionRead.model_validate(dict(version))