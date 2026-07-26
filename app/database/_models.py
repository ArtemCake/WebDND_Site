"""
Единый интерфейс базы данных проекта WebDND_Site.
Гарантирует правильный порядок загрузки моделей во избежание Circular Import Errors.
"""

# --- 1. БАЗОВЫЕ СПРАВОЧНИКИ И СИСТЕМНЫЕ СУЩНОСТИ ---
from app.database.models.srd_models import (
	DamageType, Resistance, AbilityScore,
	CharacterAbilityValue, Trait, Skill
)
from app.database.models.lore_models import LoreArticle, LoreTag, ArticleTagLink
from app.database.models.spell_models import Spell, ClassSpellLink
from app.database.models.bestiary_models import Monster
from app.database.models.combat_models import Condition, ActiveEffect

# --- ПЕРЕНОСИМ ЗАВИСИМОСТИ USER СЮДА ---
# AssetLibraryEntry нужен для связи user.homebrew_assets
from app.database.models.assets_models import AssetLibraryEntry
# Token нужен для back_populates у AssetLibraryEntry
from app.database.models.map_models import Token

# --- 2. ПОЛЬЗОВАТЕЛИ И ОРГАНИЗАЦИЯ КАМПАНИЙ ---
# Теперь User может безопасно ссылаться на AssetLibraryEntry
from app.database.models.campaign_models import Lobby
from app.database.models.user_models import User, UserLog, AppLog
from app.database.models.campaign_models import Campaign, CampaignPlayerLink, Invitation, Session
from app.database.models.combat_models import Encounter, CombatTracker, InitiativeRoll

# --- 3. ГЕЙМПЛЕЙ ---
from app.database.models.core_game_models import (
	Race, Class, Subclass, Background,
	CharacterClassLink, CharacterSpell, Ruleset, HomebrewEntity
)

# --- 4. ВИРТУАЛЬНЫЙ СТОЛ ---
from app.database.models.map_models import Location, Wall, LightSource # Token уже импортирован выше
from app.database.models.inventory_models import Item, MagicItemProperty, InventoryItem, CurrencyPouch

# --- АГРЕГАЦИЯ МЕТАДАННЫХ ДЛЯ ALEMBIC ---
# Импортируем Base только после того, как ВСЕ классы объявлены выше
from .database import metadata

def get_sorted_table_names():
	"""
	Вспомогательная функция для получения отсортированного списка имен таблиц.
	Полезна для отладки зависимостей ForeignKey при создании БД вручную.
	"""
	return sorted([table.name for table in metadata.sorted_tables])