# backend/app/Core/static_files.py

from Config.imports import StaticFiles, Path


class PublicStaticFiles(StaticFiles):
	"""Раздаёт статику, исключая каталог private."""

	def __init__(self, directory, **kwargs):
		super().__init__(directory=directory, **kwargs)
		self._private_root = (
				Path(directory) / "private"
		).resolve()

	def lookup_path(self, path: str):
		full_path, stat_result = super().lookup_path(path)

		if full_path:
			resolved = Path(full_path).resolve()

			if resolved.is_relative_to(self._private_root):
				return "", None

		return full_path, stat_result