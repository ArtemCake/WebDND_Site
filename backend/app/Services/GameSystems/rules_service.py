# backend/app/Services/GameSystems/rules_service.py

"""Хранение черновиков и публикация снимков правил.

Изменяющие операции самостоятельно завершают транзакцию:
commit при успехе, rollback при ошибке.

Использовать с сессией запроса без посторонних несохранённых
изменений. Не вызывать внутри внешнего session.begin().

Проверка прав пользователя выполняется вызывающим слоем.
"""

from Config.imports import (AsyncSession, HTTPException, UUID, ValidationError, asynccontextmanager, func,
	insert, select, status, update)
from backend.app.Database._models import (GameSystem, GameSystemRulesDraft, GameSystemRulesVersion)
from backend.app.Schemas.game_rules import (GameSystemRulesDraftCreate, GameSystemRulesDraftRead, GameSystemRulesDraftUpdate,
	GameSystemRulesPublish, GameSystemRulesVersionRead, RulesProfile)


_SYSTEMS = GameSystem.__table__
_DRAFTS = GameSystemRulesDraft.__table__
_VERSIONS = GameSystemRulesVersion.__table__


@asynccontextmanager
async def _rules_write(session: AsyncSession):
	"""Граница транзакции для одной изменяющей операции."""

	try:
		yield
		await session.commit()
	except Exception:
		await session.rollback()
		raise

async def _lock_system(session: AsyncSession, system_id: UUID):
	"""Общая блокировка для операций над правилами одной системы.

	Порядок блокировок:
	1. Игровая система.
	2. Её черновик.

	Блокируем строку системы даже при отсутствии черновика:
	иначе два запроса могли бы одновременно создавать его.
	"""

	result = await session.execute(
		select(
			_SYSTEMS.c.id,
			_SYSTEMS.c.rules_engine_version,
		)
		.where(_SYSTEMS.c.id == system_id)
		.with_for_update()
	)

	system = result.mappings().one_or_none()

	if system is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Игровая система не найдена",
		)

	return system

async def _find_draft(session: AsyncSession, system_id: UUID, *, for_update: bool = False):
	stmt = select(_DRAFTS).where(
		_DRAFTS.c.system_id == system_id,
		)

	if for_update:
		stmt = stmt.with_for_update()

	result = await session.execute(stmt)
	return result.mappings().one_or_none()

def _require_draft(draft):
	if draft is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Черновик правил не найден",
		)

	return draft

def _check_revision(actual_revision: int, expected_revision: int) -> None:
	if actual_revision != expected_revision:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=(
				"Черновик уже изменён. "
				"Загрузите актуальную ревизию перед сохранением "
				"или публикацией."
			),
		)

def _rules_payload(raw: dict) -> dict:
	"""Повторно проверяет профиль и создаёт отдельный JSON-снимок."""

	return RulesProfile.model_validate(raw).model_dump(
		mode="json",
	)

async def get_rules_draft(session: AsyncSession, system_id: UUID) -> GameSystemRulesDraftRead:
	draft = _require_draft(
		await _find_draft(session, system_id),
	)

	return GameSystemRulesDraftRead.model_validate(draft)

async def create_rules_draft(session: AsyncSession, system_id: UUID, data: GameSystemRulesDraftCreate) -> GameSystemRulesDraftRead:
	async with _rules_write(session):
		await _lock_system(session, system_id)

		existing = await _find_draft(
			session,
			system_id,
			for_update=True,
		)

		if existing is not None:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=(
					"Черновик правил уже существует. "
					"Используйте обновление с ожидаемой ревизией."
				),
			)

		payload = _rules_payload(
			data.rules.model_dump(mode="json"),
		)

		result = await session.execute(
			insert(_DRAFTS)
			.values(
				system_id=system_id,
				rules_json=payload,
				revision=1,
			)
			.returning(*_DRAFTS.c)
		)

		response = GameSystemRulesDraftRead.model_validate(
			result.mappings().one(),
		)

	return response

async def update_rules_draft(session: AsyncSession, system_id: UUID, data: GameSystemRulesDraftUpdate) -> GameSystemRulesDraftRead:
	async with _rules_write(session):
		await _lock_system(session, system_id)

		draft = _require_draft(
			await _find_draft(
				session,
				system_id,
				for_update=True,
			),
		)

		_check_revision(
			draft["revision"],
			data.expected_revision,
		)

		payload = _rules_payload(
			data.rules.model_dump(mode="json"),
		)

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
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=(
					"Черновик изменился во время сохранения. "
					"Загрузите актуальную ревизию."
				),
			)

		response = GameSystemRulesDraftRead.model_validate(
			updated,
		)

	return response

async def publish_rules_version(session: AsyncSession, system_id: UUID, data: GameSystemRulesPublish) -> GameSystemRulesVersionRead:
	async with _rules_write(session):
		system = await _lock_system(session, system_id)

		draft = _require_draft(
			await _find_draft(
				session,
				system_id,
				for_update=True,
			),
		)

		_check_revision(
			draft["revision"],
			data.expected_revision,
		)

		# Публикуем сохранённый черновик, а не конфигурацию
		# из тела запроса публикации.
		try:
			payload = _rules_payload(draft["rules_json"])
		except ValidationError as exc:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=(
					"Сохранённый черновик не соответствует "
					"поддерживаемой схеме правил. "
					"Исправьте его перед публикацией."
				),
			) from exc

		# Все публикации через этот сервис сначала блокируют
		# одну и ту же строку игровой системы.
		# Поэтому вычисление следующего номера сериализовано.
		number_result = await session.execute(
			select(
				func.coalesce(
					func.max(_VERSIONS.c.version_number),
					0,
				) + 1,
				)
			.where(_VERSIONS.c.system_id == system_id)
		)

		next_number = number_result.scalar_one()

		version_result = await session.execute(
			insert(_VERSIONS)
			.values(
				system_id=system_id,
				version_number=next_number,
				rules_json=payload,
				rules_engine_version=system["rules_engine_version"],
			)
			.returning(*_VERSIONS.c)
		)

		response = GameSystemRulesVersionRead.model_validate(
			version_result.mappings().one(),
		)

		# Публикация также потребляет ожидаемую ревизию.
		# Повторный запрос со старой ревизией получит конфликт,
		# а не создаст ещё одну публикацию.
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
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=(
					"Черновик изменился во время публикации. "
					"Публикация отменена."
				),
			)

	return response

async def get_rules_version(session: AsyncSession, system_id: UUID, version_id: UUID) -> GameSystemRulesVersionRead:
	result = await session.execute(
		select(_VERSIONS)
		.where(
			_VERSIONS.c.id == version_id,
			_VERSIONS.c.system_id == system_id,
			)
	)

	version = result.mappings().one_or_none()

	if version is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Опубликованная версия правил не найдена",
		)

	return GameSystemRulesVersionRead.model_validate(version)

async def get_latest_rules_version(session: AsyncSession, system_id: UUID) -> GameSystemRulesVersionRead | None:
	"""Последняя публикация по номеру версии.

	Проверка существования системы и прав доступа —
	ответственность вызывающего маршрута.
	Черновик эта функция не читает.
	"""

	result = await session.execute(
		select(_VERSIONS)
		.where(_VERSIONS.c.system_id == system_id)
		.order_by(_VERSIONS.c.version_number.desc())
		.limit(1)
	)

	version = result.mappings().one_or_none()

	if version is None:
		return None

	return GameSystemRulesVersionRead.model_validate(version)