# app/services/srd_service.py

from app.repositories.srd_repository import SRDRepository
from app.services.log_service import LogService
from app.enums.log_enums import LogAction, LogLevelEnum
from Config.imports import  List, AsyncSession, Optional
from app.database._models import  Spell, Item, Monster
from app.schemas.spell_schema import SpellCreate, SpellUpdate
from app.schemas.item_schema import ItemCreate, ItemUpdate
from app.schemas.monster_schema import MonsterCreate, MonsterUpdate


class SRDService:
	"""
	Бизнес-слой для работы со справочными данными (SRD).
	Не содержит SQL-кода, делегирует задачи в SRDRepository.
	Отвечает за подготовку данных и логирование операций изменения.
	"""

	# ==============================================================================
	# === 1. ЗАКЛИНАНИЯ (SPELLS) ===================================================
	# ==============================================================================

	@staticmethod
	async def get_spells_list(
			db: AsyncSession,
			search_query: str = "",
			level: int = None
	) -> List[Spell]:
		"""Получение списка заклинаний с фильтрами."""
		filters = {"level": level} if level is not None else None

		spells = await SRDRepository.get_list(
			db=db,
			model=Spell,
			search_query=search_query,
			filters=filters,
			sort_by="name"
		)
		return spells

	@staticmethod
	async def get_spell_by_id(db: AsyncSession, spell_id: int) -> Optional[Spell]:
		"""Получение одного заклинания по ID (для Detail страницы)."""
		return await SRDRepository.get_spell_by_id(db, spell_id)

	@staticmethod
	async def create_spell(db: AsyncSession, obj_in: SpellCreate):
		"""Создание нового заклинания."""
		try:
			obj = await SRDRepository.create_spell(db, obj_in)

			await LogService.create_log(
				username=None,
				action=LogAction.SPELL_CREATED,
				description=f"Создано заклинание '{obj.name}' (ID: {obj.id})",
				log_level=LogLevelEnum.INFO
			)
			return True, "Заклинание успешно создано", obj
		except Exception as error:
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка создания заклинания: {str(error)}",
				log_level=LogLevelEnum.ERROR
			)
			return False, f"Системная ошибка: {error}", None

	@staticmethod
	async def update_spell(db: AsyncSession, db_obj: Spell, obj_in: SpellUpdate):
		"""Обновление существующего заклинания."""
		try:
			updated_obj = await SRDRepository.update_spell(db, db_obj, obj_in)

			await LogService.create_log(
				username=None,
				action=LogAction.SPELL_UPDATED,
				description=f"Обновлено заклинание '{updated_obj.name}' (ID: {updated_obj.id})",
				log_level=LogLevelEnum.INFO
			)
			return True, "Изменения сохранены", updated_obj
		except Exception as error:
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка обновления заклинания: {str(error)}",
				log_level=LogLevelEnum.ERROR
			)
			return False, f"Системная ошибка: {error}", None

	@staticmethod
	async def delete_spell(db: AsyncSession, db_obj: Spell):
		"""Удаление заклинания."""
		try:
			name = db_obj.name
			await SRDRepository.delete_spell(db, db_obj)

			await LogService.create_log(
				username=None,
				action=LogAction.SPELL_DELETED,
				description=f"Удалено заклинание '{name}'",
				log_level=LogLevelEnum.WARNING
			)
			return True, "Объект удален"
		except Exception as error:
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка удаления заклинания: {str(error)}",
				log_level=LogLevelEnum.ERROR
			)
			return False, f"Системная ошибка: {error}"

	# ==============================================================================
	# === 2. ПРЕДМЕТЫ (ITEMS) ======================================================
	# ==============================================================================

	@staticmethod
	async def get_items_list(
			db: AsyncSession,
			search_query: str = "",
			item_type: str = None
	) -> List[Item]:
		"""Получение списка предметов."""
		filters = {"type": item_type} if item_type else None

		items = await SRDRepository.get_list(
			db=db,
			model=Item,
			search_query=search_query,
			filters=filters,
			sort_by="name"
		)
		return items

	@staticmethod
	async def get_item_by_id(db: AsyncSession, item_id: int) -> Optional[Item]:
		"""Получение предмета по ID."""
		return await SRDRepository.get_item_by_id(db, item_id)

	@staticmethod
	async def create_item(db: AsyncSession, obj_in: ItemCreate):
		"""Создание предмета."""
		try:
			obj = await SRDRepository.create_item(db, obj_in)
			await LogService.create_log(None, LogAction.ITEM_CREATED, f"Создан предмет '{obj.name}'", LogLevelEnum.INFO)
			return True, "Предмет создан", obj
		except Exception as error:
			await LogService.create_log(None, LogAction.DATABASE_ERROR, f"Ошибка создания предмета: {error}", LogLevelEnum.ERROR)
			return False, str(error), None

	@staticmethod
	async def update_item(db: AsyncSession, db_obj: Item, obj_in: ItemUpdate):
		"""Обновление предмета."""
		try:
			updated_obj = await SRDRepository.update_item(db, db_obj, obj_in)
			await LogService.create_log(None, LogAction.ITEM_UPDATED, f"Обновлен предмет '{updated_obj.name}'", LogLevelEnum.INFO)
			return True, "Сохранено", updated_obj
		except Exception as error:
			await LogService.create_log(None, LogAction.DATABASE_ERROR, f"Ошибка обновления предмета: {error}", LogLevelEnum.ERROR)
			return False, str(error), None

	@staticmethod
	async def delete_item(db: AsyncSession, db_obj: Item):
		"""Удаление предмета."""
		try:
			name = db_obj.name
			await SRDRepository.delete_item(db, db_obj)
			await LogService.create_log(None, LogAction.ITEM_DELETED, f"Удален предмет '{name}'", LogLevelEnum.WARNING)
			return True, "Удалено"
		except Exception as error:
			await LogService.create_log(None, LogAction.DATABASE_ERROR, f"Ошибка удаления предмета: {error}", LogLevelEnum.ERROR)
			return False, str(error)

	# ==============================================================================
	# === 3. БЕСТИАРИЙ (MONSTERS) ==================================================
	# ==============================================================================

	@staticmethod
	async def get_bestiary_list(
			db: AsyncSession,
			search_query: str = "",
			cr: str = None,
			creature_type: str = None
	) -> List[Monster]:
		"""Получение списка монстров."""
		filters = {}
		if cr: filters["cr"] = cr
		if creature_type: filters["creature_type"] = creature_type

		monsters = await SRDRepository.get_list(
			db=db,
			model=Monster,
			search_query=search_query,
			filters=filters or None,
			sort_by="name"
		)
		return monsters

	@staticmethod
	async def get_monster_by_id(db: AsyncSession, monster_id: int) -> Optional[Monster]:
		"""Получение монстра по ID."""
		return await SRDRepository.get_monster_by_id(db, monster_id)

	@staticmethod
	async def create_monster(db: AsyncSession, obj_in: MonsterCreate):
		"""Создание монстра."""
		try:
			obj = await SRDRepository.create_monster(db, obj_in)
			await LogService.create_log(None, LogAction.MONSTER_CREATED, f"Создан монстр '{obj.name}' (CR {obj.challenge_rating})", LogLevelEnum.INFO)
			return True, "Монстр создан", obj
		except Exception as error:
			await LogService.create_log(None, LogAction.DATABASE_ERROR, f"Ошибка создания монстра: {error}", LogLevelEnum.ERROR)
			return False, str(error), None

	@staticmethod
	async def update_monster(db: AsyncSession, db_obj: Monster, obj_in: MonsterUpdate):
		"""Обновление монстра."""
		try:
			updated_obj = await SRDRepository.update_monster(db, db_obj, obj_in)
			await LogService.create_log(None, LogAction.MONSTER_UPDATED, f"Обновлен монстр '{updated_obj.name}'", LogLevelEnum.INFO)
			return True, "Сохранено", updated_obj
		except Exception as error:
			await LogService.create_log(None, LogAction.DATABASE_ERROR, f"Ошибка обновления монстра: {error}", LogLevelEnum.ERROR)
			return False, str(error), None

	@staticmethod
	async def delete_monster(db: AsyncSession, db_obj: Monster):
		"""Удаление монстра."""
		try:
			name = db_obj.name
			await SRDRepository.delete_monster(db, db_obj)
			await LogService.create_log(None, LogAction.MONSTER_DELETED, f"Удален монстр '{name}'", LogLevelEnum.WARNING)
			return True, "Удалено"
		except Exception as error:
			await LogService.create_log(None, LogAction.DATABASE_ERROR, f"Ошибка удаления монстра: {error}", LogLevelEnum.ERROR)
			return False, str(error)