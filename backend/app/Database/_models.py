# backend/app/Database/_models.py

from backend.app.Database.database import Base

# Блок 0: Ядро
from backend.app.Database.Models.Core.user import User, MFADevice, Friendship, OAuthProvider
# Блок 1: Лор
from backend.app.Database.Models.Content.game_systems import (GameSystem, HomebrewRule, GameSystemRulesDraft,
	GameSystemRulesVersion)
from backend.app.Database.Models.Content.worldbuilding import Language, LoreEntry

# Блок 2: Билдинг
from backend.app.Database.Models.Content.character_building import Race, Origin, Background, Feat
from backend.app.Database.Models.Content.character_building import CharacterClass, Subclass
from backend.app.Database.Models.Content.skills import Skill, Characteristic, SkillCharacteristicMap

# Блок 3: Магия
from backend.app.Database.Models.Content.magic import Spell, MagicSchool, Ability, Effect, DamageType, SpellSlot

# Блок 4: Предметы
from backend.app.Database.Models.Content.equipment import (Equipment, ItemType, Rarity, Weapon, WeaponType, WeaponClass,
                                                           Armor, ArmorType, MagicalItem, Artifact, ArtifactProperty)

# Блок 5: Бестиарий
from backend.app.Database.Models.Content.worldbuilding import Creature, CreatureSize, CreatureType, NPC, NPCTag

# Блок 6: Геймплей
from backend.app.Database.Models.Gameplay.lobby import Game, Party, Invite, Session, InitiativeTracker, DiceRoll
from backend.app.Database.Models.Gameplay.characters import Character, CharacterSheet, CharacterInventory, CharacterSheetAbilityScore
from backend.app.Database.Models.Gameplay.communication import Chat, Message
from backend.app.Database.Models.Gameplay.maps import CampaignMap, MapLayer, MapHex, MapObject, SpatialAudioZone, Token

# Блок 7: Система
from backend.app.Database.Models.Medias.media import UploadedAsset, AIGenerationJob
from backend.app.Database.Models.Systems.system import AuditLog, ContentReport, ActiveSessionCache, SystemEvent

__all__ = [
	# Блок 0
	'User', 'MFADevice', 'Friendship', 'OAuthProvider',
	# Блок 1
	'GameSystem', 'GameSystemRulesDraft', 'GameSystemRulesVersion', 'HomebrewRule', 'Language', 'LoreEntry',
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