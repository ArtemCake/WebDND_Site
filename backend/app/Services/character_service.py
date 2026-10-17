# backend/app/Services/character_service.py

from Config.imports import (UUID, HTTPException, status, select, AsyncSession, selectinload)
from backend.app.database.models.gameplay.characters import (Character, CharacterSheet, CharacterSheetAbilityScore, CharacterInventory)
from backend.app.database.models.content.skills import Skill, SkillCharacteristicMap
from backend.app.schemas.character import (CharacterCreate, CharacterUpdate, CharacterSheetCreate, CharacterSheetUpdate)


# --- Расчётные хелперы (чистые функции, без обращения к БД) ---

def ability_modifier(value: int) -> int:
	return (value - 10) // 2

def proficiency_bonus_for_level(level: int) -> int:
	# Стандартная прогрессия 5e: +2 на 1–4 уровне, далее +1 каждые 4 уровня
	return 2 + (level - 1) // 4

async def resolve_skill_characteristic(
		session: AsyncSession, skill_id: UUID, game_id: UUID | None = None,
) -> UUID:
	"""
	Возвращает characteristic_id для навыка. Сначала проверяет homebrew-переопределение
	(SkillCharacteristicMap), и только если его нет — берёт характеристику по умолчанию
	у самого Skill.
	"""
	stmt = select(SkillCharacteristicMap).where(SkillCharacteristicMap.skill_id == skill_id)
	if game_id is not None:
		stmt = stmt.where(SkillCharacteristicMap.game_id == game_id)
	custom_link = (await session.execute(stmt)).scalar_one_or_none()
	if custom_link is not None:
		return custom_link.characteristic_id

	skill = await session.get(Skill, skill_id)
	if skill is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Навык не найден")
	return skill.ability_score_id

# --- CRUD Character (глобальный шаблон персонажа) ---

async def create_character(session: AsyncSession, owner_id: UUID, data: CharacterCreate) -> Character:
	character = Character(owner_id=owner_id, **data.model_dump())
	session.add(character)
	await session.commit()
	return character

async def get_character(session: AsyncSession, character_id: UUID, owner_id: UUID) -> Character:
	character = await session.get(Character, character_id)
	if character is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Персонаж не найден")
	if character.owner_id != owner_id:
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Это не ваш персонаж")
	return character

async def list_characters(session: AsyncSession, owner_id: UUID) -> list[Character]:
	stmt = select(Character).where(Character.owner_id == owner_id)
	return list((await session.execute(stmt)).scalars().all())

async def update_character(
		session: AsyncSession, character_id: UUID, owner_id: UUID, data: CharacterUpdate,
) -> Character:
	character = await get_character(session, character_id, owner_id)
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(character, field, value)
	await session.commit()
	return character

async def delete_character(session: AsyncSession, character_id: UUID, owner_id: UUID) -> None:
	character = await get_character(session, character_id, owner_id)
	await session.delete(character)
	await session.commit()

# --- CharacterSheet (лист в рамках конкретной игры) ---

async def create_character_sheet(
		session: AsyncSession, player_id: UUID, data: CharacterSheetCreate,
) -> CharacterSheet:
	# Если лист клонируется из шаблона — убеждаемся, что шаблон принадлежит игроку
	if data.base_character_id is not None:
		await get_character(session, data.base_character_id, player_id)

	sheet = CharacterSheet(
		player_id=player_id,
		game_id=data.game_id,
		base_character_id=data.base_character_id,
		party_id=data.party_id,
		version_note=data.version_note,
		stats_json=data.stats_json,
		saves_json=data.saves_json,
		skills_json=data.skills_json,
		hp_current=data.hp_current,
		hp_temp=data.hp_temp,
	)
	session.add(sheet)
	await session.flush()  # получаем sheet.id до коммита

	for score in data.ability_scores:
		session.add(CharacterSheetAbilityScore(
			character_sheet_id=sheet.id,
			characteristic_id=score.characteristic_id,
			value=score.value,
		))

	await session.commit()
	return await get_character_sheet(session, sheet.id, player_id)

async def get_character_sheet(session: AsyncSession, sheet_id: UUID, player_id: UUID) -> CharacterSheet:
	stmt = (
		select(CharacterSheet)
		.where(CharacterSheet.id == sheet_id)
		.options(
			selectinload(CharacterSheet.ability_scores),
			selectinload(CharacterSheet.inventory),
		)
	)
	sheet = (await session.execute(stmt)).scalar_one_or_none()
	if sheet is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Лист персонажа не найден")
	if sheet.player_id != player_id:
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Это не ваш лист персонажа")
	return sheet

async def update_character_sheet(
		session: AsyncSession, sheet_id: UUID, player_id: UUID, data: CharacterSheetUpdate,
) -> CharacterSheet:
	sheet = await get_character_sheet(session, sheet_id, player_id)
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(sheet, field, value)
	await session.commit()
	return sheet
