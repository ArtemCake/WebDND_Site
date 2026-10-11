# backend/app/Services/legal_service.py

"""Рендер юридических документов (политика конфиденциальности, соглашение)
из markdown-файлов проекта в HTML для шаблонов."""

from Config.imports import (Path, markdown)


LEGAL_DOCS_DIR = Path(__file__).resolve().parents[3] / "frontend" / "static" / "docs"

def render_legal_markdown(filename: str) -> str:
	"""Читает .md-файл из frontend/static/docs и рендерит в HTML."""
	path = LEGAL_DOCS_DIR / filename
	text = path.read_text(encoding="utf-8")
	return markdown.markdown(text, extensions=["tables", "sane_lists"])
