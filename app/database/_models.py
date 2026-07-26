"""
Единый интерфейс базы данных проекта WebDND_Site.
Гарантирует правильный порядок загрузки моделей во избежание Circular Import Errors.
"""

# --- 1. БАЗОВЫЕ СПРАВОЧНИКИ И СИСТЕМНЫЕ СУЩНОСТИ ---
# Сначала грузим всё, что ни от кого не зависит или имеет минимум связей.
from app.database.models.srd_models import (
	DamageType, Resistance, AbilityScore,
	CharacterAbilityValue
)
from app.database.models.lore_models import LoreArticle, LoreTag, ArticleTagLink
from app.database.models.spell_models import Spell, ClassSpellLink
from app.database.models.bestiary_models import Monster
from app.database.models.combat_models import Condition, ActiveEffect# ВАЖНО: Условия ДО боя

# --- 2. ПОЛЬЗОВАТЕЛИ И ОРГАНИЗАЦИЯ КАМПАНИЙ ---
# Теперь можно грузить пользователей (они ссылаются на SRD выше)
from app.database.models.user_models import User, UserLog, AppLog
from app.database.models.campaign_models import (Campaign, CampaignPlayerLink)
from app.database.models.combat_models import  Encounter

# --- 3. ГЕЙМПЛЕЙ (Сложные игровые зависимости) ---
# ТОЛЬКО ПОСЛЕ ТОГО, КАК ЗАГРУЖЕНЫ USER И CAMPAIGN
from app.database.models.core_game_models import (
	Character, Race, Class, Subclass, Background,
	CharacterClassLink)

# --- 4. ВИРТУАЛЬНЫЙ СТОЛ И БОЙ ---
# Карты, токены и бой зависят от Пользователей, Кампаний и Персонажей
from app.database.models.map_models import Location, Token, Wall, LightSource
from app.database.models.combat_models import CombatTracker, InitiativeRoll

# --- АГРЕГАЦИЯ МЕТАДАННЫХ ДЛЯ ALEMBIC ---
# Импортируем Base только после того, как ВСЕ классы объявлены выше
from .database import metadata

def get_sorted_table_names():
	"""
	Вспомогательная функция для получения отсортированного списка имен таблиц.
	Полезна для отладки зависимостей ForeignKey при создании БД вручную.
	"""
	return sorted([table.name for table in metadata.sorted_tables])