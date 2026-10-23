# backend/app/Services/Maps/map_cleanup_service.py

from Config.imports import Path, PurePosixPath, UUID, re, shutil
from backend.app.Services.Maps.map_image_service import _storage_root


def _checked_path(root: Path, parts: tuple[str, ...]) -> Path:
	path = root

	for part in parts:
		path = path / part

		is_junction = getattr(path, "is_junction", lambda: False)

		if path.is_symlink() or is_junction():
			raise ValueError(
				"Ссылки на каталоги и файлы в пути очистки запрещены"
			)

	if not path.resolve().is_relative_to(root):
		raise ValueError("Путь очистки выходит за пределы хранилища")

	return path

def _directory_parts(relative: str, master_id: UUID, game_id: UUID) -> tuple[str, str]:
	path = PurePosixPath(relative)

	if (
			path.is_absolute()
			or "\\" in relative
			or path.as_posix() != relative
			or len(path.parts) != 2
	):
		raise ValueError("Некорректный каталог карт игры")

	master_folder, game_folder = path.parts

	if (
			not re.fullmatch(r"master-[\w-]+", master_folder)
			or not re.fullmatch(r"game-[\w-]+", game_folder)
			or not master_folder.endswith(f"-{master_id}")
			or not game_folder.endswith(f"-{game_id}")
	):
		raise ValueError("Каталог не соответствует мастеру или игре")

	return master_folder, game_folder

def validate_plan(plan: dict) -> tuple[list[Path], list[Path]]:
	root = Path(plan["root"])

	if not root.is_absolute() or root.resolve() != root:
		raise ValueError("Корень хранилища изменился или содержит ссылки")

	master_id = UUID(plan["master_id"])
	game_id = UUID(plan["game_id"])

	directories = [
		_checked_path(
			root,
			_directory_parts(relative, master_id, game_id),
		)
		for relative in plan["directories"]
	]

	legacy_files = [
		_checked_path(root, (f"{UUID(value)}.png",))
		for value in plan["legacy_map_ids"]
	]

	return directories, legacy_files

def build_plan(game_id: UUID, master_id: UUID, master_folder: str | None,
		game_folder: str | None, maps) -> dict:
	directories = set()

	if game_folder:
		if not master_folder:
			raise ValueError("Не сохранён каталог мастера")

		directories.add(f"{master_folder}/{game_folder}")

	for item in maps:
		key = item.background_storage_path

		if not key:
			continue

		if not isinstance(key, str):
			raise ValueError("Некорректный путь фона карты")

		path = PurePosixPath(key)

		if (
				path.is_absolute()
				or "\\" in key
				or path.as_posix() != key
				or len(path.parts) != 3
				or not re.fullmatch(
			r"map-[1-9][0-9]*\.png",
			path.parts[-1],
		)
		):
			raise ValueError("Некорректный путь фона карты")

		directories.add(path.parent.as_posix())

	plan = {
		"root": str(_storage_root()),
		"game_id": str(game_id),
		"master_id": str(master_id),
		"directories": sorted(directories),
		# Проверяем старое UUID-хранение для каждой карты,
		# даже если у неё уже появился новый адрес фона.
		"legacy_map_ids": [str(item.id) for item in maps],
	}

	validate_plan(plan)
	return plan

def execute_plan(plan: dict) -> None:
	# Проверяем весь набор до первого удаления.
	directories, legacy_files = validate_plan(plan)

	for directory in directories:
		try:
			shutil.rmtree(directory)
		except FileNotFoundError:
			# Отсутствующий каталог уже очищен.
			# Ошибку отсутствующего вложенного файла не скрываем,
			# если сам каталог всё ещё существует.
			if directory.exists():
				raise

	for path in legacy_files:
		path.unlink(missing_ok=True)