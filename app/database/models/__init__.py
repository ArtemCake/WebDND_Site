"""
Единый интерфейс базы данных проекта WebDND_Site.
Импортирует модули целиком для корректного порядка регистрации метаданных.
"""

from . import assets_models
from . import campaign_models
from . import combat_models
from . import Character_models
from . import lore_models
from . import map_models
from . import core_srd
from . import user_models

from app.database.database import metadata

def get_sorted_table_names():
	return sorted([table.name for table in metadata.sorted_tables])