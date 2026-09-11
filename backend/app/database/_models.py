# backend/app/database/_models.py

from backend.app.database.database import Base

# Блок 0: Ядро
from backend.app.database.models.core.user import User, MFADevice, Friendship, OAuthProvider
from backend.app.database.models.core.auth import UserRole
# Блок 1: Лор
from backend.app.database.models.content.game_systems import GameSystem, HomebrewRule
from backend.app.database.models.content.worldbuilding import Language, LoreEntry

# Блок 2: Билдинг
from backend.app.database.models.content.character_building import Race, Origin, Background, Feat
from backend.app.database.models.content.character_building import CharacterClass, Subclass
from backend.app.database.models.content.skills import Skill, Characteristic, SkillCharacteristicMap

# Блок 3: Магия
from backend.app.database.models.content.magic import Spell, MagicSchool, Ability, Effect, DamageType, SpellSlot

# Блок 4: Предметы
from backend.app.database.models.content.equipment import (Equipment, ItemType, Rarity,	Weapon, WeaponType, WeaponClass,
	Armor, ArmorType, MagicalItem, Artifact, ArtifactProperty)

# Блок 5: Бестиарий
from backend.app.database.models.content.worldbuilding import Creature, CreatureSize, CreatureType, NPC, NPCTag

# Блок 6: Геймплей
from backend.app.database.models.gameplay.lobby import Game, Party, Invite, Session, InitiativeTracker, DiceRoll
from backend.app.database.models.gameplay.characters import Character, CharacterSheet, CharacterInventory, CharacterSheetAbilityScore
from backend.app.database.models.gameplay.communication import Chat, Message
from backend.app.database.models.gameplay.maps import CampaignMap, MapLayer, MapHex, MapObject, SpatialAudioZone, Token

# Блок 7: Система
from backend.app.database.models.medias.media import UploadedAsset, AIGenerationJob
from backend.app.database.models.systems.system import AuditLog, ContentReport, ActiveSessionCache, SystemEvent

__all__ = [
	# Блок 0
	'User', 'UserRole', 'MFADevice', 'Friendship', 'OAuthProvider',
	# Блок 1
	'GameSystem', 'HomebrewRule', 'Language', 'LoreEntry',
	# Блок 2
	'Race', 'Origin', 'Background', 'Feat', 'CharacterClass', 'Subclass',
	'Skill', 'Characteristic', 'SkillCharacteristicMap', 'CharacterSheetAbilityScore',
	# Блок 3
	'Spell', 'MagicSchool', 'Ability', 'Effect', 'DamageType', 'SpellSlot',
	# Блок 4
	'Equipment', 'ItemType', 'Rarity', 'Weapon', 'WeaponType', 'WeaponClass',
	'Armor', 'ArmorType', 'MagicalItem', 'Artifact', 'ArtifactProperty',
	# Блок 5
	'Creature', 'CreatureSize', 'CreatureType', 'NPC', 'NPCTag',
	# Блок 6
	'Game', 'Party', 'Invite', 'Session', 'InitiativeTracker', 'DiceRoll',
	'Character', 'CharacterSheet', 'CharacterInventory',
	# Блок 7
	'Chat', 'Message',
	# Блок 8
	'CampaignMap', 'MapLayer', 'MapHex', 'MapObject', 'SpatialAudioZone',
	'UploadedAsset', 'AIGenerationJob', 'Token',
	# Блок 9
	'AuditLog', 'ContentReport', 'ActiveSessionCache', 'SystemEvent'
]