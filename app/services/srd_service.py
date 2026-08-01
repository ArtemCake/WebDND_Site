# app/services/srd_service.py

from app.repositories.srd_repository import SRDBaseRepository
from app.services.log_service import LogService
from app.enums.log_enums import LogAction, LogLevelEnum
from Config.imports import Type, List, Any,AsyncSession, Dict, selectinload, select
from app.database._models import  Spell


class SRDService:
	"""
	Facade-сервис для работы со всеми справочными данными.
	Не содержит SQL, делегирует работу в SRDBaseRepository.
	Здесь живет логика агрегации данных из разных источников.
	"""

	@staticmethod
	async def get_srd_data(
			db: AsyncSession,
			model: Type[Any],
			search_query: str = "",
			filters: dict = None,
			sort_by: str = "name"
	) -> List[Any]:
		"""
		Универсальный метод получения любых справочников.
		Служит единой точкой входа для Web_Routers и API_Routers.
		"""
		try:
			# Просто проксируем вызов в репозиторий
			data = await SRDBaseRepository.get_list(
				db=db,
				model=model,
				search_query=search_query,
				filters=filters,
				sort_by=sort_by
			)
			return data

		except Exception as error:
			# Логируем ошибку централизованно здесь
			entity_name = getattr(model, '__name__', 'Unknown')
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка загрузки справочника {entity_name}: {error}",
				log_level=LogLevelEnum.ERROR
			)
			raise

	# Пример сложного метода, где сервис НЕОБХОДИМ (агрегация)
	@staticmethod
	async def get_spells_with_classes(db: AsyncSession) -> List[Dict[str, Any]]:
		"""
		Получает список заклинаний вместе со списком классов для каждого.

		Это пример агрегирующего метода Сервиса.
		Репозиторий возвращает сырые объекты ORM, а Сервис собирает из них
		структуру данных (DTO), удобную для передачи во фронтенд/шаблонизатор.
		"""
		try:
			# Шаг 1: Получаем базовые данные и связанные классы одним JOIN-запросом.
			# Мы не используем здесь универсальный репозиторий, так как нужен специфический .options(selectinload)

			query = (
				select(Spell)
				.options(
					# ЭТО КЛЮЧЕВОЙ МОМЕНТ:
					# selectinload говорит SQLAlchemy: "Когда достаешь Spell,
					# сразу сделай дополнительный запрос, чтобы загрузить все related классы"
					# Это решает проблему N+1 запросов.
					selectinload(Spell.classes)
				)
				.order_by(Spell.name.asc())
			)

			result = await db.execute(query)
			spell_objects = result.unique().scalars().all()

			# Шаг 2: Трансформация (Mapping).
			# Преобразуем тяжелые объекты SQLAlchemy в легкие словари (JSON-совместимые).
			spells_data = []
			for spell in spell_objects:
				spells_data.append({
					"id": spell.id,
					"name": spell.name,
					"level": spell.level,
					"school": spell.school_of_magic,
					"description": spell.description,
					# Собираем названия связанных классов в простой список строк
					"classes": [char_class.name for char_class in spell.classes]
				})

			return spells_data

		except Exception as error:
			await LogService.create_log(
				username=None,
				action=LogAction.DATABASE_ERROR,
				description=f"Ошибка загрузки заклинаний с классами: {error}",
				log_level=LogLevelEnum.ERROR
			)
			raise