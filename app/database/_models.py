# app/database/_models.py

# --- ПЕРЕЭКСПОРТ МОДЕЛЕЙ ДЛЯ УДОБСТВА ИМПОРТА ---

# Блоки данных
from app.database.models.user import *
from app.database.models.core import *
from app.database.models.dnd import *
from app.database.models.character import *
from app.database.models.inventory import *
from app.database.models.world import *
from app.database.models.homebrew_entity import *
from app.database.models.combat import *
from app.database.models.references import *
from app.database.database import metadata

# --- КОНФИГУРАЦИЯ ALEMBIC ---

# Это критически важная часть для автоматических миграций.
# Мы собираем ВСЕ таблицы со всех Base-классов (если у вас их несколько)
# или просто используем metadata нашего единого Base.

def get_sorted_table_names():
	"""
	Вспомогательная функция для получения отсортированного списка имен таблиц.
	Полезна для отладки зависимостей ForeignKey при создании БД вручную.
	"""
	return sorted([table.name for table in metadata.sorted_tables])