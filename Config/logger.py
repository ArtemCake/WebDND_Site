# backend/app/Config/logger.py
from Config.Config import settings
from Config.imports import (logging, sys, Path)


def setup_logging(app_name: str = "WebDND"):
	"""
	Централизованная настройка логгера для FastAPI/Uvicorn.
	Создает папку logs/, пишет туда файлы с ротацией по времени
	и дублирует вывод в консоль.
	"""

	# Определяем пути
	base_dir = settings._base_dir
	log_dir = base_dir / "logs"
	log_dir.mkdir(exist_ok=True)

	file_log_path = log_dir / f"{app_name.lower()}.log"

	# Корневой логгер приложения
	logger = logging.getLogger(app_name)
	logger.setLevel(logging.DEBUG) # Ловим абсолютно всё, фильтрация будет на обработчиках

	# Чтобы не добавлять хендлеры повторно при автоперезагрузке uvicorn
	if not logger.handlers:

		# --- Форматтер ---
		formatter = logging.Formatter(
			fmt='%(asctime)s.%(msecs)03d | %(levelname)-8s | [%(name)s:%(lineno)d] %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
		)

		# --- Хендлер для Файла (INFO и выше) ---
		from logging.handlers import TimedRotatingFileHandler
		file_handler = TimedRotatingFileHandler(
			filename=file_log_path,
			when="midnight",      # Ротация каждый день
			interval=1,
			backupCount=7,       # Хранить логи за последние 7 дней
			encoding="utf-8",
			delay=False
		)
		file_handler.setLevel(logging.INFO)
		file_handler.setFormatter(formatter)

		# --- Хендлер для Ошибок (ERROR и CRITICAL в отдельный файл) ---
		error_handler = TimedRotatingFileHandler(
			filename=log_dir / f"{app_name.lower()}_error.log",
			when="midnight",
			interval=1,
			backupCount=30,
			encoding="utf-8"
		)
		error_handler.setLevel(logging.ERROR)
		error_handler.setFormatter(formatter)

		# --- Хендлер для Консоли (DEBUG и выше) ---
		console_handler = logging.StreamHandler(sys.stdout)
		console_handler.setLevel(logging.DEBUG)
		console_handler.setFormatter(formatter)

		# Добавляем обработчики
		logger.addHandler(file_handler)
		logger.addHandler(error_handler)
		logger.addHandler(console_handler)

		# Предотвращаем двойную запись логов из дочерних модулей
		logger.propagate = False

	return logger