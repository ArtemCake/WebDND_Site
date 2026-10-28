# backend/app/Services/GameSystems/system_rule_origin.py

"""Загрузка основы и проверка происхождения правил.

Не фиксирует и не откатывает транзакцию.
Проверка права изменять игровую систему — обязанность
вызывающего слоя.
"""

from Config.imports import (AsyncSession, HTTPException, UUID, ValidationError, select)
from backend.app.Database._models import (RuleEngine, RuleEngineVersion)
from backend.app.Schemas.game_rules import RulesProfile
from backend.app.Schemas.game_system_origin import EngineRulesSource
from backend.app.Services.GameSystems.rules_composition import (compose_system_rules)


_ENGINES = RuleEngine.__table__
_VERSIONS = RuleEngineVersion.__table__


def _conflict(detail: str) -> HTTPException:
	return HTTPException(status_code=409, detail=detail)

def require_standalone_draft(draft) -> None:
	"""Не разрешать старой форме менять унаследованный профиль."""
	if draft is None:
		return

	if (
			draft.get("engine_version_id") is not None
			or draft.get("rules_overrides_json") is not None
	):
		raise _conflict(
			"Правила связаны с опубликованным движком. "
			"Сохраняйте их через выбор основы и переопределения, "
			"а не как самостоятельный профиль."
		)

def _assemble(version, overrides, executor_version, *, error_code):
	if version["rules_engine_version"] != executor_version:
		raise _conflict(
			"Версия программного исполнителя движка "
			"не совпадает с версией игровой системы."
		)

	try:
		base = RulesProfile.model_validate(version["rules_json"])
	except ValidationError as exc:
		raise _conflict(
			"Опубликованная основа не соответствует схеме правил."
		) from exc

	try:
		effective = compose_system_rules(base, overrides)
	except ValueError as exc:
		raise HTTPException(
			status_code=error_code,
			detail=f"Не удалось собрать правила: {exc}",
		) from exc

	payload = effective.model_dump(mode="json")

	# Храним переопределения в том же JSON-представлении,
	# что и соответствующие поля итогового профиля.
	normalized_overrides = {
		key: payload[key]
		for key in overrides
	}

	return {
		"engine_version_id": version["id"],
		"rules_overrides_json": normalized_overrides,
		"rules_json": payload,
	}

async def load_engine_origin(session: AsyncSession, source: EngineRulesSource, actor_id: UUID, executor_version: str) -> dict:
	"""Загрузить разрешённую публикацию для нового выбора основы."""
	if not isinstance(actor_id, UUID):
		raise HTTPException(
			status_code=401,
			detail="Требуется авторизованный пользователь.",
		)

	result = await session.execute(
		select(
			_VERSIONS.c.id,
			_VERSIONS.c.rules_json,
			_VERSIONS.c.rules_engine_version,
			_ENGINES.c.owner_id,
			_ENGINES.c.visibility,
			_ENGINES.c.is_active,
		)
		.select_from(
			_VERSIONS.join(
				_ENGINES,
				_ENGINES.c.id == _VERSIONS.c.engine_id,
				)
		)
		.where(
			_VERSIONS.c.id == source.engine_version_id,
			_VERSIONS.c.engine_id == source.engine_id,
			)
		# Пока выбираем основу, её карточку нельзя одновременно
		# деактивировать или изменить её видимость.
		.with_for_update(read=True, of=_ENGINES)
	)
	version = result.mappings().one_or_none()

	if version is None:
		raise HTTPException(
			status_code=404,
			detail="Доступная публикация движка не найдена.",
		)

	is_owner = version["owner_id"] == actor_id
	is_public = version["visibility"] == "public"

	if not version["is_active"] or not (is_owner or is_public):
		raise HTTPException(
			status_code=404,
			detail="Доступная публикация движка не найдена.",
		)

	return _assemble(
		version,
		source.rules_overrides,
		executor_version,
		error_code=422,
	)

async def origin_for_publication(session: AsyncSession, draft, executor_version: str, payload: dict) -> dict:
	"""Проверить сохранённое происхождение перед публикацией."""
	version_id = draft.get("engine_version_id")
	overrides = draft.get("rules_overrides_json")

	if version_id is None and overrides is None:
		# Не передаём JSONB-колонке Python None:
		# это может стать JSON null, а не SQL NULL.
		return {}

	if version_id is None or not isinstance(overrides, dict):
		raise _conflict(
			"В черновике нарушена согласованность происхождения правил."
		)

	result = await session.execute(
		select(_VERSIONS).where(_VERSIONS.c.id == version_id)
	)
	version = result.mappings().one_or_none()

	if version is None:
		raise _conflict("Исходная публикация движка не найдена.")

	# Для уже сохранённой основы не проверяем повторно публичность:
	# изменение видимости движка не переписывает существующие системы.
	assembled = _assemble(
		version,
		overrides,
		executor_version,
		error_code=409,
	)

	if assembled["rules_json"] != payload:
		raise _conflict(
			"Сохранённые правила не совпадают с основой "
			"и переопределениями. Публикация отменена."
		)

	return {
		"engine_version_id": assembled["engine_version_id"],
		"rules_overrides_json": assembled["rules_overrides_json"],
	}

async def load_saved_engine_version(session: AsyncSession, draft):
	"""Прочитать публикацию, уже связанную с черновиком системы.

	Право читать/изменять систему проверяет вызывающий слой.

	Видимость и активность исходного движка здесь не проверяются:
	ранее сохранённая связь не является новым выбором основы.
	"""
	version_id = draft.get("engine_version_id")
	overrides = draft.get("rules_overrides_json")

	if version_id is None and overrides is None:
		raise HTTPException(
			status_code=404,
			detail="Черновик использует самостоятельные правила.",
		)

	if version_id is None or not isinstance(overrides, dict):
		raise _conflict(
			"В черновике нарушена согласованность "
			"происхождения правил."
		)

	result = await session.execute(
		select(_VERSIONS).where(
			_VERSIONS.c.id == version_id,
			)
	)
	version = result.mappings().one_or_none()

	if version is None:
		raise _conflict(
			"Сохранённая публикация движка не найдена."
		)

	return version

async def load_editor_engine_origin(session: AsyncSession, source: EngineRulesSource, actor_id: UUID, executor_version: str, current_draft) -> dict:
	"""Собрать правила при обновлении единой формы.

	Та же публикация:
		используем сохранённую связь с системой.

	Другая публикация:
		заново проверяем доступность выбранной основы.
	"""
	if not isinstance(actor_id, UUID):
		raise HTTPException(
			status_code=401,
			detail="Требуется авторизованный пользователь.",
		)

	if current_draft is not None:
		saved_version_id = current_draft.get("engine_version_id")
		saved_overrides = current_draft.get("rules_overrides_json")

		if (
				(saved_version_id is None) != (saved_overrides is None)
				or (
				saved_version_id is not None
				and not isinstance(saved_overrides, dict)
		)
		):
			raise _conflict(
				"В черновике нарушена согласованность "
				"происхождения правил."
			)

		if saved_version_id == source.engine_version_id:
			version = await load_saved_engine_version(
				session,
				current_draft,
			)

			if version["engine_id"] != source.engine_id:
				raise HTTPException(
					status_code=404,
					detail="Публикация выбранного движка не найдена.",
				)

			return _assemble(
				version,
				source.rules_overrides,
				executor_version,
				error_code=422,
			)

	return await load_engine_origin(
		session,
		source,
		actor_id,
		executor_version,
	)