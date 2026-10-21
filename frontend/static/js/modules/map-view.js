// frontend/static/js/modules/map-view.js

export function initMapView() {
	const root = document.getElementById('map-view-root');
	if (!root || root.dataset.initialized === 'true') return;

	const message = document.getElementById('map-view-message');
	const image = document.getElementById('map-view-background');

	if (!message || !image) return;
	root.dataset.initialized = 'true';

	const backgroundUrl = (root.dataset.backgroundUrl || '').trim();

	if (!backgroundUrl) {
		message.textContent =
			'Фоновое изображение для этой карты не задано.';
		return;
	}

	let parsedUrl;

	try {
				parsedUrl = new URL(backgroundUrl, window.location.origin);

		message.textContent =
        	'Не удалось показать фон: адрес изображения '
        	+ 'должен вести на этот сайт.';
        return;

	} catch {
		message.textContent =
			'Не удалось показать фон: нужен корректный HTTP- '
			+ 'или HTTPS-адрес без имени пользователя и пароля.';
		return;
	}

	image.addEventListener('load', () => {
		image.hidden = false;
		message.textContent = '';
		message.hidden = true;
	}, { once: true });

	image.addEventListener('error', () => {
		image.hidden = true;
		message.hidden = false;
		message.textContent =
			'Не удалось загрузить фон карты. Проверьте доступность '
			+ 'изображения и то, что ссылка ведёт непосредственно на него. '
			+ 'Карта при этом остаётся сохранённой.';
	}, { once: true });

	message.textContent = 'Загрузка фонового изображения…';
	image.src = parsedUrl.href;
}