# app/database/_models.py

# --- ПЕРЕЭКСПОРТ МОДЕЛЕЙ ДЛЯ УДОБСТВА ИМПОРТА ---

# Блоки данных
# app/database/models/__init__.py

"""
Публичный интерфейс базы данных проекта WebDND_Site.
Этот файл агрегирует все SQLAlchemy-модели для удобного импорта в роутеры и сервисы.
Использование:
    from app.database.models import User, Character, Encounter, Token
"""

# --- Базовые сущности ---
from app.database.models.user_models import (User, UserLog, AppLog)
from app.database.models.campaign_models import (Campaign, CampaignPlayerLink)
from app.database.models.srd_models import (DamageType, Resistance
, AbilityScore, CharacterAbilityValue, AbilityDefinition)

# --- Игровые сущности (Core) ---
from app.database.models.core_game_models import (Character, Race, Class, Subclass
, Background, CharacterClassLink)
from app.database.models.bestiary_models import (Monster)

# --- Лор и Контент ---
from app.database.models.lore_models import (LoreArticle, LoreTag, ArticleTagLink)
from app.database.models.assets_models import (AssetLibraryEntry)

# --- Боевая система ---
from app.database.models.combat_models import (CombatTracker, InitiativeRoll
, Condition, ActiveEffect,	Encounter)

# --- Предметы ---
from app.database.models.inventory_models import (Item, MagicItemProperty, InventoryItem, CurrencyPouch)

# --- Заклинания и Правила ---
from app.database.models.spell_models import (Spell, ClassSpellLink)

# --- Карты ---
from app.database.models.map_models import (Location, Token, Wall, LightSource)
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