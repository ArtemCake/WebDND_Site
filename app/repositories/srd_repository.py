# app/repositories/srd_repository.py

from Config.imports import Optional, selectinload, Type, List, Any, AsyncSession, and_, select, Dict
from app.database._models import Spell, Item, Monster, Class, ClassSpellLink, DamageType
from app.enums.log_enums import LogLevelEnum, LogAction
from app.schemas.item_schema import ItemCreate
from app.schemas.spell_schema import SpellCreate
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
	async def create_spell(db: AsyncSession, payload: SpellCreate) -> Spell:
		"""
		ПРИНИМАЕТ СХЕМУ (SpellCreate), создает МОДЕЛЬ ТАБЛИЦЫ (Spell) и сохраняет её.
		"""
		try:
			# 1. Подготавливаем данные для базовой модели
			spell_data = payload.model_dump(
				exclude={'class_ids', 'damage_type_ids', 'links'},
				exclude_unset=True
			)
			spell_db_obj = Spell(**spell_data)

			# 2. Обрабатываем связь "Классы" через связующую сущность ClassSpellLink
			if payload.class_ids:
				# Оптимизация: загружаем классы одним запросом вместо N+1
				classes_result = await db.execute(
					select(Class).where(Class.id.in_(payload.class_ids), Class.is_enabled == True)
				)
				found_classes_map = {cls.id: cls for cls in classes_result.scalars().unique()}

				# Проверка на несуществующие ID классов
				invalid_ids = set(payload.class_ids) - found_classes_map.keys()
				if invalid_ids:
					raise ValueError(f"Классы не найдены или отключены: {sorted(invalid_ids)}")

				for class_id in payload.class_ids:
					link = ClassSpellLink(
						base_class=found_classes_map[class_id],
						available_at_level=None # Можно добавить логику определения уровня доступа
					)
					spell_db_obj.class_links.append(link) # Используем каскадную связь

			# 3. Обрабатываем связь "Типы урона" напрямую через secondary-таблицу
			if payload.damage_type_ids:
				dmg_types_result = await db.execute(
					select(DamageType).where(DamageType.id.in_(payload.damage_type_ids), DamageType.is_enabled == True)
				)
				found_dmgs_map = {dt.id: dt for dt in dmg_types_result.scalars().unique()}

				invalid_dmg_ids = set(payload.damage_type_ids) - found_dmgs_map.keys()
				if invalid_dmg_ids:
					raise ValueError(f"Типы урона не найдены или отключены: {sorted(invalid_dmg_ids)}")

				# SQLAlchemy сама заполнит ассоциацию, если объекты загружены в сессию
				spell_db_obj.damage_types.extend(found_dmgs_map.values())

			if payload.links and payload.links.material_component_item_id:
				spell_db_obj.material_component_item_id = payload.links.material_component_item_id

			# 4. Единый коммит для всего графа объектов
			db.add(spell_db_obj)
			await db.commit()
			await db.refresh(spell_db_obj)

			return "Заклинание успешно создано", spell_db_obj

		except Exception as error:
			await db.rollback()
			return f"Системная ошибка: {error}", None

	@staticmethod
	async def create_item(db: AsyncSession, obj_in: ItemCreate) -> Item:
		"""
		ПРИНИМАЕТ СХЕМУ (ItemCreate), создает МОДЕЛЬ ТАБЛИЦЫ (Item) и сохраняет её.
		"""
		try:
			# Создаем экземпляр таблицы, распаковывая словарь из схемы Pydantic
			item_db_obj = Item(**obj_in.model_dump())

			db.add(item_db_obj)
			await db.commit()
			await db.refresh(item_db_obj) # Обязательно обновляем объект ID'ми после INSERT
			return item_db_obj

		except Exception as error:
			await db.rollback()
			raise error # Пробрасываем ошибку выше, чтобы Сервис залогировал её

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