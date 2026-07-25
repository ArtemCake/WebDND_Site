# app/database/models/associations.py

from Config.imports import (
	DateTime, func, SmallInteger, Integer, String, Boolean, Column,
	ForeignKey, Table, UniqueConstraint)
from app.database.database import Base


# --- СВЯЗИ МНОГИХ-КО-МНОГИМ ДЛЯ ПЕРСОНАЖА ---

character_classes = Table(
	'character_classes',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('class_id', Integer, ForeignKey('classes.id'), primary_key=True),
	Column('level', SmallInteger, nullable=False, default=1),
	Column('subclass_id', Integer, ForeignKey('subclasses.id'), nullable=True)
)

character_spells = Table(
	'character_spells',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('spell_id', Integer, ForeignKey('spells.id'), primary_key=True),
	Column('prepared', Boolean(), default=False)
)

character_items = Table(
	'character_items',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('item_id', Integer, ForeignKey('items.id'), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1),
	Column('equipped', Boolean(), default=False)
)

character_abilities_m2m = Table(
	'character_abilities_m2m',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ability_type_id', Integer, ForeignKey('ability_types.id'), primary_key=True),
	Column('score', SmallInteger, nullable=False, default=8),
	UniqueConstraint('character_id', 'ability_type_id', name='uq_character_ability_m2m')
)

skill_proficiencies_m2m = Table(
	'skill_proficiencies_m2m',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True),
	Column('is_expertise', Boolean(), default=False),
	Column('proficient', Boolean(), default=True),
	UniqueConstraint('character_id', 'skill_id', name='uq_character_skill_m2m')
)

character_feats = Table(
	'character_feats',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('feat_id', Integer, ForeignKey('feats.id'), primary_key=True),
	UniqueConstraint('character_id', 'feat_id', name='uq_character_feat')
)

character_languages = Table(
	'character_languages',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('language_id', Integer, ForeignKey('languages.id'), primary_key=True),
	UniqueConstraint('character_id', 'language_id', name='uq_character_language')
)

character_equipment = Table(
	'character_equipment',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('equipment_id', Integer, ForeignKey('equipment.id'), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1),
	Column('is_attuned', Boolean(), default=False),
	Column('attunement_slots_used', SmallInteger, default=0),
	Column('equipped', Boolean(), default=False),
	UniqueConstraint('character_id', 'equipment_id', name='uq_character_equipment')
)

character_allies = Table(
	'character_allies',
	Base.metadata,
	Column('owner_character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ally_character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('control_type', String(20), nullable=False, default='summon'),
	Column('is_permanent', Boolean(), default=False),
	UniqueConstraint('owner_character_id', 'ally_character_id', name='uq_owner_ally')
)

character_conditions = Table(
	'character_conditions',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('condition_id', Integer, ForeignKey('conditions.id'), primary_key=True),
	Column('source_character_id', Integer, ForeignKey('characters.id', ondelete="SET NULL"), nullable=True),
	Column('source_spell_id', Integer, ForeignKey('spells.id', ondelete="SET NULL"), nullable=True),
	Column('duration_type', String(20), default='instant'),
	Column('duration_value', Integer, nullable=True),
	Column('remaining_duration', Integer, nullable=True),
	Column('concentration_required', Boolean(), default=False),
	Column('is_active', Boolean(), default=True),
	Column('stackable', Boolean(), default=False),
	Column('applied_at', DateTime(timezone=True), server_default=func.now()),
	UniqueConstraint('character_id', 'condition_id', 'source_spell_id', name='uq_char_cond_source')
)

container_items = Table(
	'container_items',
	Base.metadata,
	Column('container_equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('item_equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1)
)

shop_inventory = Table(
	'shop_inventory',
	Base.metadata,
	Column('equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('price_cp', Integer, nullable=False)
)

# Дополнительные M2M-таблицы для связей с DamageType
spell_damage_types = Table(
	'spell_damage_types',
	Base.metadata,
	Column('spell_id', Integer, ForeignKey('spells.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True),
	UniqueConstraint('spell_id', 'damage_type_id', name='uq_spell_damage_type')
)

equipment_damage_types = Table(
	'equipment_damage_types',
	Base.metadata,
	Column('equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True),
	UniqueConstraint('equipment_id', 'damage_type_id', name='uq_equip_damage_type')
)

monster_damage_types = Table(
	'monster_damage_types',
	Base.metadata,
	Column('monster_action_id', Integer, ForeignKey('monster_actions.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True),
	UniqueConstraint('monster_action_id', 'damage_type_id', name='uq_monster_damage_type')
)

character_saving_throws = Table(
	'character_saving_throws',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ability_type_id', Integer, ForeignKey('ability_types.id', ondelete="CASCADE"), primary_key=True),
	Column('is_proficient', Boolean(), default=False),
	UniqueConstraint('character_id', 'ability_type_id', name='uq_char_saving_throw')
)