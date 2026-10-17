# backend/app/Services/character_service.py

from Config.imports import (UUID, HTTPException, status, select, AsyncSession, selectinload)
from backend.app.Database.Models.Gameplay.characters import (Character, CharacterSheet, CharacterSheetAbilityScore, CharacterInventory)
from backend.app.Database.Models.Content.skills import Skill, SkillCharacteristicMap
from backend.app.Schemas.character import (CharacterCreate, CharacterUpdate, CharacterSheetCreate, CharacterSheetUpdate)
from backend.app.Database.Models.Gameplay.lobby import Party


# --- Расчётные хелперы (чистые функции, без обращения к БД) ---

def ability_modifier(value: int) -> int:
	return (value - 10) // 2

def proficiency_bonus_for_level(level: int) -> int:
	# Стандартная прогрессия 5e: +2 на 1–4 уровне, далее +1 каждые 4 уровня
	return 2 + (level - 1) // 4

async def resolve_skill_characteristic(session: AsyncSession, skill_id: UUID) -> UUID:
	"""
	Возвращает characteristic_id для навыка: сначала homebrew-переопределение
	(SkillCharacteristicMap, уникально на skill_id во всей системе),
	иначе — характеристика по умолчанию из Skill.ability_score_id.
	"""
	stmt = select(SkillCharacteristicMap).where(
		SkillCharacteristicMap.skill_id == skill_id,
		SkillCharacteristicMap.is_active.is_(True),
		)
	custom_link = (await session.execute(stmt)).scalar_one_or_none()
	if custom_link is not None:
		return custom_link.characteristic_id

	skill = await session.get(Skill, skill_id)
	if skill is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Навык не найден")
	return skill.ability_score_id

async def _ensure_active_party_member(session: AsyncSession, game_id: UUID, user_id: UUID) -> None:
	stmt = select(Party).where(
		Party.game_id == game_id,
		Party.user_id == user_id,
		)
	party = (await session.execute(stmt)).scalar_one_or_none()
	if party is None or not party.is_active or party.role_in_game == "banned":
		raise HTTPException(
			status.HTTP_403_FORBIDDEN,
			"Вы не являетесь активным участником этой игры",
		)

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

async def create_character_sheet(session, user_id: UUID, data: CharacterSheetCreate) -> CharacterSheet:
	await _ensure_active_party_member(session, data.game_id, user_id)

	if data.party_id is not None:
		party = await session.get(Party, data.party_id)
		if party is None or party.game_id != data.game_id:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="party_id не относится к указанной игре")

	sheet = CharacterSheet(
		game_id=data.game_id,
		base_character_id=data.character_id,   # маппинг: схема → модель
		**data.model_dump(exclude={"game_id", "character_id"}),
	)
	session.add(sheet)
	await session.commit()
	await session.refresh(sheet)
	return sheet

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
