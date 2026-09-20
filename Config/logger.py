# Config/logger.py

from Config.imports import (Queue, Path, logging, sys, atexit,
                            TimedRotatingFileHandler, QueueHandler, QueueListener)
from Config.Config import settings


def setup_logging(app_name: str = "WebDND"):
	"""
	Настройка логгера с использованием Queue для работы в async среде (FastAPI + run_in_executor).
	Это предотвращает зависания при записи логов из разных потоков.

	Внимание: используется queue.Queue — это работает только в пределах одного процесса.
	При переходе на multiprocess-воркеры (gunicorn с несколькими процессами)
	потребуется multiprocessing.Queue вместо queue.Queue.
	"""

	# --- 1. Подготовка путей ---
	base_dir = Path(settings.BASE_DIR)
	log_dir = base_dir / "logs"
	log_dir.mkdir(exist_ok=True, parents=True)

	file_log_path = log_dir / f"{app_name.lower()}.log"
	error_log_path = log_dir / f"{app_name.lower()}_error.log"

	# --- 2. Создание ОБРАБОТЧИКОВ (Handlers) ---

	formatter = logging.Formatter(
		fmt='%(asctime)s.%(msecs)03d | %(levelname)-8s | [%(name)s:%(lineno)d] %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S'
	)

	console_handler = logging.StreamHandler(sys.stdout)
	console_handler.setLevel(logging.DEBUG)
	console_handler.setFormatter(formatter)

	file_handler = TimedRotatingFileHandler(
		filename=file_log_path,
		when="midnight",
		interval=1,
		backupCount=7,
		encoding="utf-8",
		delay=False
	)
	file_handler.setLevel(logging.INFO)
	file_handler.setFormatter(formatter)

	error_handler = TimedRotatingFileHandler(
		filename=error_log_path,
		when="midnight",
		interval=1,
		backupCount=30,
		encoding="utf-8"
	)
	error_handler.setLevel(logging.ERROR)
	error_handler.setFormatter(formatter)

	# --- 3. Создание ОЧЕРЕДИ и СЛУШАТЕЛЯ (Queue + Listener) ---
	_queue = Queue(-1)  # бесконечный размер очереди

	listener = QueueListener(
		_queue,
		console_handler,
		file_handler,
		error_handler,
		respect_handler_level=True
	)

	# --- 4. Создание ЛОГГЕРА приложения ---
	logger = logging.getLogger(app_name)

	# Если уже настроен — просто возвращаем существующий
	if getattr(logger, '_QUEUE_SETUP', False):
		return logger
	# Если был старый listener — останавливаем
	logger.handlers.clear()

	logger.setLevel(logging.DEBUG)

	# Вместо обычных хендлеров добавляем QUEUE_HANDLER
	qh = QueueHandler(_queue)
	logger.addHandler(qh)

	# Отключаем передачу вверх, чтобы root uvicorn не перехватывал наши логи дважды
	logger.propagate = False

	# Сохраняем ссылку на listener внутри логгера
	logger._listener = listener
	logger._QUEUE_SETUP = True

	# Запускаем слушатель в отдельном потоке
	listener.start()

	# Регистрируем остановку при штатном выходе процесса
	atexit.register(listener.stop)

	# Баннер только при первой инициализации
	logger.info("=====================================")
	logger.info("===   ЗАПУСК ПРИЛОЖЕНИЯ WEB-DND   ===")
	logger.info("=====================================")

	return logger