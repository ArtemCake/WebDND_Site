# app/repositories/srd_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from typing import Type, List, Any
from app.database._models import Spell, Item, Monster # Импортируем нужные модели здесь


class SRDBaseRepository:
	"""
	Базовый класс для всех справочников SRD.
	Содержит общие методы фильтрации и поиска.
	"""

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