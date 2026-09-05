# backend/app/database/models/_models.py

"""
Агрегатор всех SQLAlchemy моделей проекта.
Этот файл необходим для того, чтобы Alembic (инструмент миграций)
видел все таблицы при выполнении команды `alembic revision --autogenerate`.
"""
# ИСПРАВЛЕНИЕ: Используем полный путь от корня проекта "backend"
from backend.app.database.database import Base
from backend.app.database.models.core.user import User, MFADevice, Friendship, OAuthProvider
from backend.app.database.models.core.auth import Role, UserRole
from backend.app.database.models.content.game_systems import GameSystem, HomebrewRule
from backend.app.database.models.content.character_building import (
	Race, CharacterClass, Subclass, Background, Feat, Origin
)
from backend.app.database.models.content.skills import (
	Skill, Characteristic, SkillCharacteristicMap
)
from backend.app.database.models.content.equipment import (
	Equipment, ItemType, Rarity, Weapon, WeaponType, WeaponClass,
	Armor, ArmorType, MagicalItem, Artifact, ArtifactProperty
)
from backend.app.database.models.content.magic import (
	Spell, SpellSlot, MagicSchool, Ability, Effect, DamageType
)
from backend.app.database.models.content.worldbuilding import (
	Language, Creature, CreatureSize, CreatureType, NPC, NPCTag,
	LoreEntry
)
from backend.app.database.models.gameplay.lobby import Game, Party, Invite, Session, InitiativeTracker, DiceRoll
from backend.app.database.models.gameplay.characters import CharacterSheet, CharacterInventory
from backend.app.database.models.gameplay.communication import Chat, Message
from backend.app.database.models.gameplay.maps import (
	CampaignMap, MapLayer, MapHex, MapObject, SpatialAudioZone, Token
)
from backend.app.database.models.medias.media import UploadedAsset, AIGenerationJob
from backend.app.database.models.systems.system import AuditLog, ContentReport, ActiveSessionCache, SystemEvent


# Собираем список всех таблиц в строгом порядке зависимостей (ForeignKeys).
__all__ = [
	# Блок 1: Ядро и справочники прав
	'User', 'MFADevice', 'Friendship', 'OAuthProvider',
	'Role', 'UserRole',

	# Блок 2: Игровые системы и лор
	'GameSystem', 'HomebrewRule',
	'Language', 'LoreEntry',

	# Блок 3: Билдинг персонажа (Расы/Классы/Навыки)
	'Race', 'CharacterClass', 'Subclass', 'Background', 'Feat', 'Origin',
	'Skill', 'Characteristic', 'SkillCharacteristicMap',

	# Блок 4: Магия и эффекты
	'Spell', 'SpellSlot', 'MagicSchool', 'Ability', 'Effect', 'DamageType',

	# Блок 5: Снаряжение и предметы
	'Equipment', 'ItemType', 'Rarity',
	'Weapon', 'WeaponType', 'WeaponClass',
	'Armor', 'ArmorType',
	'MagicalItem', 'Artifact', 'ArtifactProperty',

	# Блок 6: Бестиарий
	'Creature', 'CreatureSize', 'CreatureType', 'NPC', 'NPCTag',

	# Блок 7: Игровой процесс (Лобби и сессии)
	'Game', 'Party', 'Invite', 'Session', 'InitiativeTracker', 'DiceRoll',
	'CharacterSheet', 'CharacterInventory',

	# Блок 8: Коммуникация
	'Chat', 'Message',

	# Блок 9: Карты и ассеты
	'CampaignMap', 'MapLayer', 'MapHex', 'MapObject', 'SpatialAudioZone',
	'UploadedAsset', 'AIGenerationJob', 'Token',

	# Блок 10: Администрирование и системные логи
	'AuditLog', 'ContentReport', 'ActiveSessionCache', 'SystemEvent'
]



