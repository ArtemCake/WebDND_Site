# backend/app/Services/Maps/map_image_service.py

from Config.imports import (BytesIO, Image, ImageOps, UnidentifiedImageError, PurePosixPath, re,
	Path, UUID, UploadFile, HTTPException, logging, run_in_threadpool, os, uuid4)
from Config.Config import settings


log = logging.getLogger(__name__)


def _storage_root() -> Path:
	base = Path(settings.BASE_DIR)

	private_maps = (
			base / "frontend" / "static" / "private" / "maps"
	).resolve()

	root = (
		Path(settings.MAP_IMAGES_DIR)
		if settings.MAP_IMAGES_DIR is not None
		else private_maps
	).resolve()

	public_root = (
			base / "frontend" / "static"
	).resolve()

	if (
			root.is_relative_to(public_root)
			and not root.is_relative_to(private_maps)
	):
		raise RuntimeError(
			"Внутри frontend/static карты можно хранить "
			"только в private/maps"
		)

	return root

def _image_path(map_id: UUID | str) -> Path:
	root = _storage_root()

	if isinstance(map_id, UUID):
		# Совместимость со старым хранилищем.
		return root / f"{map_id}.png"

	if not isinstance(map_id, str):
		raise ValueError("Некорректный адрес изображения карты")

	relative = PurePosixPath(map_id)

	if (
			relative.is_absolute()
			or "\\" in map_id
			or len(relative.parts) != 3
			or relative.as_posix() != map_id
	):
		raise ValueError("Некорректный адрес изображения карты")

	master_folder, game_folder, filename = relative.parts

	if (
			not master_folder.startswith("master-")
			or not game_folder.startswith("game-")
			or not re.fullmatch(r"[\w-]+", master_folder)
			or not re.fullmatch(r"[\w-]+", game_folder)
			or not re.fullmatch(r"map-[1-9][0-9]*\.png", filename)
	):
		raise ValueError("Некорректный адрес изображения карты")

	path = root.joinpath(*relative.parts).resolve()

	# Дополнительная защита от выхода за пределы хранилища,
	# в том числе через существующую символическую ссылку.
	if not path.is_relative_to(root):
		raise ValueError("Путь изображения вне хранилища карт")

	return path

def _normalize_image(contents: bytes) -> bytes:
	try:
		with Image.open(
				BytesIO(contents),
				formats=["JPEG", "PNG", "WEBP"],
		) as source:
			width, height = source.size

			if (
					width <= 0
					or height <= 0
					or width > settings.MAP_IMAGE_MAX_SIDE
					or height > settings.MAP_IMAGE_MAX_SIDE
					or width * height > settings.MAP_IMAGE_MAX_PIXELS
			):
				raise HTTPException(
					status_code=400,
					detail="Слишком большие размеры изображения",
				)

			if getattr(source, "n_frames", 1) != 1:
				raise HTTPException(
					status_code=400,
					detail="Выберите изображение без анимации",
				)

			source.load()
			oriented = ImageOps.exif_transpose(source)

			has_alpha = (
					"A" in oriented.getbands()
					or "transparency" in oriented.info
			)
			mode = "RGBA" if has_alpha else "RGB"

			# Новый объект не переносит исходные метаданные.
			with oriented.convert(mode) as converted:
				with Image.new(mode, converted.size) as clean:
					clean.paste(converted)
					output = BytesIO()
					clean.save(output, format="PNG")
					return output.getvalue()

	except HTTPException:
		raise
	except (
			UnidentifiedImageError,
			Image.DecompressionBombError,
			OSError,
			ValueError,
			SyntaxError,
	) as exc:
		raise HTTPException(
			status_code=400,
			detail="Не удалось прочитать изображение. Выберите PNG, JPEG или WebP",
		) from exc

async def prepare_background(upload: UploadFile) -> bytes:
	try:
		contents = await upload.read(settings.MAP_IMAGE_MAX_BYTES + 1)
	finally:
		await upload.close()

	if not contents:
		raise HTTPException(
			status_code=400,
			detail="Выбран пустой файл",
		)

	if len(contents) > settings.MAP_IMAGE_MAX_BYTES:
		raise HTTPException(
			status_code=413,
			detail="Изображение превышает допустимый размер",
		)

	return await run_in_threadpool(_normalize_image, contents)

def _write_background(map_id: UUID | str, contents: bytes) -> None:
	path = _image_path(map_id)
	path.parent.mkdir(parents=True, exist_ok=True)

	# Не перезаписываем существующий файл.
	with path.open("xb") as destination:
		try:
			destination.write(contents)
		except BaseException:
			path.unlink(missing_ok=True)
			raise

async def save_background(map_id: UUID | str, contents: bytes) -> None:
	try:
		await run_in_threadpool(_write_background, map_id, contents)
	except OSError as exc:
		log.exception("Не удалось сохранить фон карты %s", map_id)
		raise HTTPException(
			status_code=500,
			detail="Не удалось сохранить изображение карты",
		) from exc

async def read_background(map_id: UUID | str) -> bytes:
	try:
		return await run_in_threadpool(_image_path(map_id).read_bytes)
	except FileNotFoundError as exc:
		raise HTTPException(
			status_code=404,
			detail="Изображение карты не найдено",
		) from exc
	except OSError as exc:
		log.exception("Не удалось прочитать фон карты %s", map_id)
		raise HTTPException(
			status_code=500,
			detail="Не удалось прочитать изображение карты",
		) from exc

async def remove_background(map_id: UUID | str) -> None:
	try:
		await run_in_threadpool(
			_image_path(map_id).unlink,
			missing_ok=True,
		)
	except OSError:
		# Удаление файла не должно превращать уже выполненное
		# удаление записи из БД в ложную ошибку всей операции.
		log.exception(
			"Не удалось очистить файл фона карты %s",
			map_id,
		)

def _cleanup_temporary_background(path: Path | None) -> None:
	if path is None:
		return

	try:
		path.unlink(missing_ok=True)
	except OSError:
		log.exception(
			"Не удалось удалить временный файл изображения %s",
			path.name,
		)

def _replace_background(map_id: UUID | str, contents: bytes) -> Path | None:
	path = _image_path(map_id)
	path.parent.mkdir(parents=True, exist_ok=True)

	operation_id = uuid4()
	temporary_path = path.with_name(f"{path.stem}.{operation_id}.upload.tmp")
	backup_path = path.with_name(f"{path.stem}.{operation_id}.backup.tmp")

	backup_created = False

	try:
		# Сначала записываем новое изображение целиком.
		# Текущий фон на этом этапе не изменяется.
		with temporary_path.open("xb") as destination:
			destination.write(contents)
			destination.flush()
			os.fsync(destination.fileno())

		try:
			old_contents = path.read_bytes()
		except FileNotFoundError:
			old_contents = None

		if old_contents is not None:
			with backup_path.open("xb") as destination:
				destination.write(old_contents)
				destination.flush()
				os.fsync(destination.fileno())

			backup_created = True

		# Оба файла находятся в одной папке.
		# Читатель получает старый или новый файл, а не часть записи.
		os.replace(temporary_path, path)

	except BaseException:
		_cleanup_temporary_background(temporary_path)
		_cleanup_temporary_background(backup_path)
		raise

	return backup_path if backup_created else None

async def replace_background(map_id: UUID | str, contents: bytes) -> Path | None:
	try:
		return await run_in_threadpool(
			_replace_background,
			map_id,
			contents,
		)
	except OSError as exc:
		log.exception("Не удалось заменить фон карты %s", map_id)
		raise HTTPException(
			status_code=500,
			detail="Не удалось заменить изображение карты",
		) from exc

def _rollback_background(map_id: UUID | str, backup_path: Path | None) -> None:
	path = _image_path(map_id)

	if backup_path is None:
		# До операции управляемого файла не было.
		path.unlink(missing_ok=True)
	else:
		os.replace(backup_path, path)

async def rollback_background(map_id: UUID | str, backup_path: Path | None) -> None:
	try:
		await run_in_threadpool(
			_rollback_background,
			map_id,
			backup_path,
		)
	except OSError as exc:
		# При неудаче восстановления резервный файл не удаляем.
		log.exception(
			"Не удалось восстановить предыдущий фон карты %s; "
			"резервный файл: %s",
			map_id,
			backup_path,
		)
		raise HTTPException(
			status_code=500,
			detail=(
				"Не удалось восстановить предыдущий фон после "
				"ошибки сохранения. Требуется проверка хранилища"
			),
		) from exc

async def finish_background_replacement(backup_path: Path | None) -> None:
	await run_in_threadpool(_cleanup_temporary_background,backup_path,)