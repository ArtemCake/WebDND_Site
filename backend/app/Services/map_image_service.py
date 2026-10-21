# backend/app/Services/map_image_service.py

from Config.imports import (
	BytesIO, Image, ImageOps, UnidentifiedImageError,
	Path, UUID, UploadFile, HTTPException,
	logging, run_in_threadpool,
)
from Config.Config import settings


log = logging.getLogger(__name__)


def _storage_root() -> Path:
	root = (Path(settings.MAP_IMAGES_DIR)
		if settings.MAP_IMAGES_DIR is not None
		else Path(settings.BASE_DIR) / "data" / "private" / "maps"
	).resolve()

	public_root = (Path(settings.BASE_DIR) / "frontend" / "static"
	).resolve()

	if root == public_root or root.is_relative_to(public_root):
		raise RuntimeError(	"Хранилище карт должно находиться вне публичной статики")

	return root


def _image_path(map_id: UUID) -> Path:
	return _storage_root() / f"{map_id}.png"


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


def _write_background(map_id: UUID, contents: bytes) -> None:
	path = _image_path(map_id)
	path.parent.mkdir(parents=True, exist_ok=True)

	# Не перезаписываем существующий файл.
	with path.open("xb") as destination:
		try:
			destination.write(contents)
		except BaseException:
			path.unlink(missing_ok=True)
			raise


async def save_background(map_id: UUID, contents: bytes) -> None:
	try:
		await run_in_threadpool(_write_background, map_id, contents)
	except OSError as exc:
		log.exception("Не удалось сохранить фон карты %s", map_id)
		raise HTTPException(
			status_code=500,
			detail="Не удалось сохранить изображение карты",
		) from exc


async def read_background(map_id: UUID) -> bytes:
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


async def remove_background(map_id: UUID) -> None:
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