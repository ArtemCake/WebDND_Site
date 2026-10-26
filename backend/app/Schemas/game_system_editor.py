# backend/app/Schemas/game_system_editor.py

from Config.imports import Field
from backend.app.Schemas.content import (GameSystemCreate, GameSystemAdminRead)
from backend.app.Schemas.game_rules import (RulesModel, RulesProfile, GameSystemRulesDraftRead)


class GameSystemEditorCreate(RulesModel):
	system: GameSystemCreate
	rules: RulesProfile

class GameSystemEditorUpdate(RulesModel):
	# Единая форма отправляет полный набор основных сведений.
	system: GameSystemCreate
	rules: RulesProfile

	# Поле обязательно присутствует в запросе.
	# null означает: клиент ожидает, что черновика пока нет.
	expected_revision: int | None = Field(..., ge=1)

class GameSystemEditorRead(RulesModel):
	system: GameSystemAdminRead
	draft: GameSystemRulesDraftRead