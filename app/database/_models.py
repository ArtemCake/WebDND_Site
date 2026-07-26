# app/database/_models.py

# --- ПЕРЕЭКСПОРТ МОДЕЛЕЙ ДЛЯ УДОБСТВА ИМПОРТА ---

# Блоки данных
from app.database.models.user_models import *
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