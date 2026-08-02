# app/repositories/srd_repository.py

from Config.imports import Optional, selectinload, Type, List, Any, AsyncSession, and_, select, Dict
from app.database._models import Spell, Item, Monster
from app.enums.log_enums import LogLevelEnum, LogAction
from app.services.log_service import LogService


class SRDRepository:
	"""
	Базовый класс для всех справочников SRD.
	Содержит общие методы фильтрации и поиска.
	"""
	# ==============================================================================
	# === УНИВЕРСАЛЬНЫЕ МЕТОДЫ ДЛЯ СПИСКОВ (GENERIC) ===============================
	# ==============================================================================

	@staticmethod
	async def get_list(
			db: AsyncSession,
			model: Type[Any],
			search_query: str = "",
			filters: dict = None,
			sort_by: str = "name"
	) -> List[Any]:
		"""
		Универсальный метод получения списка данных.

		:param db: Сессия БД
		:param model: Модель SQLAlchemy (например, Spell или Item)
		:param search_query: Строка поиска (ищет по полю 'name')
		:param filters: Словарь дополнительных фильтров {'level': 3, 'type': 'wand'}
		:param sort_by: Поле для сортировки
		"""
		query = select(model).order_by(getattr(model, sort_by).asc())

		# Поиск по названию (если у модели есть поле name)
		if search_query and hasattr(model, 'name'):
			query = query.where(model.name.ilike(f"%{search_query}%"))

		# Динамические фильтры
		if filters:
			conditions = []
			for key, value in filters.items():
				if hasattr(model, key) and value is not None and value != '':
					conditions.append(getattr(model, key) == value)
			if conditions:
				query = query.where(and_(*conditions))

		result = await db.execute(query)
		return result.scalars().all()

	# ==============================================================================
	# === ПОЛУЧЕНИЕ ОДНОГО ЭЛЕМЕНТА (DETAIL) =======================================
	# ==============================================================================

	@staticmethod
	async def get_spell_by_id(db: AsyncSession, spell_id: int) -> Optional[Spell]:
		"""Получает заклинание по ID вместе со списком классов."""
		try:
			query = (
				select(Spell)
				.options(selectinload(Spell.classes))
				.where(Spell.id == spell_id)
			)
			result = await db.execute(query)
			return result.scalars().first()

		except Exception as error:
			# Логиним любую ошибку БД при поиске детали
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка загрузки деталей заклинания ID={spell_id}: {str(error)}",
				log_level=LogLevelEnum.ERROR
			)
			return None

	@staticmethod
	async def get_item_by_id(db: AsyncSession, item_id: int) -> Optional[Item]:
		"""Получает предмет по ID."""
		try:
			query = select(Item).where(Item.id == item_id)
			result = await db.execute(query)
			return result.scalars().first()

		except Exception as error:
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка загрузки деталей предмета ID={item_id}: {str(error)}",
				log_level=LogLevelEnum.ERROR
			)
			return None

	@staticmethod
	async def get_monster_by_id(db: AsyncSession, monster_id: int) -> Optional[Monster]:
		"""Получает монстра по ID."""
		try:
			query = select(Monster).where(Monster.id == monster_id)
			result = await db.execute(query)
			return result.scalars().first()

		except Exception as error:
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка загрузки деталей монстра ID={monster_id}: {str(error)}",
				log_level=LogLevelEnum.ERROR
			)
			return None


	# ==============================================================================
	# === СОЗДАНИЕ (CREATE) ========================================================
	# ==============================================================================

	@staticmethod
	async def create_spell(db: AsyncSession, obj_in: Spell) -> Spell:
		"""Создает новое заклинание."""
		db.add(obj_in)
		try:
			await db.commit()
			await db.refresh(obj_in) # Обновляет объект ID'ми после INSERT
			return obj_in
		except Exception as error:
			await db.rollback()
			raise error # Пробрасываем ошибку выше, чтобы Сервис залогировал её

	@staticmethod
	async def create_item(db: AsyncSession, obj_in: Item) -> Item:
		"""Создает новый предмет."""
		db.add(obj_in)
		try:
			await db.commit()
			await db.refresh(obj_in)
			return obj_in
		except Exception as error:
			await db.rollback()
			raise error

	@staticmethod
	async def create_monster(db: AsyncSession, obj_in: Monster) -> Monster:
		"""Создает нового монстра."""
		db.add(obj_in)
		try:
			await db.commit()
			await db.refresh(obj_in)
			return obj_in
		except Exception as error:
			await db.rollback()
			raise error

	# ==============================================================================
	# === ОБНОВЛЕНИЕ (UPDATE) ======================================================
	# ==============================================================================

	# Вариант 1: Использование session.merge() (Проще, если приходит целый объект)
	@staticmethod
	async def update_spell(db: AsyncSession, db_obj: Spell, update_data: Dict) -> Spell:
		"""Обновляет поля существующего объекта через merge."""
		# Объединяем данные БД с новыми данными
		updated_data = {**db_obj.__dict__, **update_data}

		merged_obj = db.merge(Spell(**updated_data))
		try:
			await db.commit()
			await db.refresh(merged_obj)
			return merged_obj
		except Exception as error:
			await db.rollback()
			raise error

	@staticmethod
	async def update_item(db: AsyncSession, db_obj: Item, update_data: Dict) -> Item:
		updated_data = {**db_obj.__dict__, **update_data}
		merged_obj = db.merge(Item(**updated_data))
		try:
			await db.commit()
			await db.refresh(merged_obj)
			return merged_obj
		except Exception as error:
			await db.rollback()
			raise error

	@staticmethod
	async def update_monster(db: AsyncSession, db_obj: Monster, update_data: Dict) -> Monster:
		updated_data = {**db_obj.__dict__, **update_data}
		merged_obj = db.merge(Monster(**updated_data))
		try:
			await db.commit()
			await db.refresh(merged_obj)
			return merged_obj
		except Exception as error:
			await db.rollback()
			raise error

	# ==============================================================================
	# === УДАЛЕНИЕ (DELETE) ========================================================
	# ==============================================================================

	@staticmethod
	async def delete_spell(db: AsyncSession, db_obj: Spell):
		"""Удаляет заклинание."""
		await db.delete(db_obj)
		try:
			await db.commit()
		except Exception as error:
			await db.rollback()
			raise error

	@staticmethod
	async def delete_item(db: AsyncSession, db_obj: Item):
		"""Удаляет предмет."""
		await db.delete(db_obj)
		try:
			await db.commit()
		except Exception as error:
			await db.rollback()
			raise error

	@staticmethod
	async def delete_monster(db: AsyncSession, db_obj: Monster):
		"""Удаляет монстра."""
		await db.delete(db_obj)
		try:
			await db.commit()
		except Exception as error:
			await db.rollback()
			raise error