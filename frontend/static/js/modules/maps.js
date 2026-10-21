// frontend/static/js/modules/maps.js

function showCreateMessage(text, isError = false) {
	const box = document.getElementById('maps-create-message');
	if (!box) return;

	const message = document.createElement('div');
	message.className = isError
		? 'alert alert-error'
		: 'alert alert-success';
	message.textContent = text;
	box.replaceChildren(message);
}

function getResponseError(data, status) {
	if (typeof data?.detail === 'string') return data.detail;

	if (Array.isArray(data?.detail)) {
		const messages = data.detail
			.map(item => item?.msg)
			.filter(message => typeof message === 'string');

		if (messages.length) return messages.join('; ');
	}

	return `Не удалось создать карту. Код ответа: ${status}.`;
}

function initBackgroundPreview(form) {
	const input = form.querySelector('[name="background_image"]');
	const preview = document.getElementById('maps-create-preview');
	if (!input || !preview) return;

	let previewUrl = null;

	function clearPreview() {
		preview.hidden = true;
		preview.removeAttribute('src');

		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
			previewUrl = null;
		}
	}

	input.addEventListener('change', () => {
		clearPreview();
		input.setCustomValidity('');

		const file = input.files?.[0];
		if (!file) return;

		const maxBytes = Number(input.dataset.maxBytes);
		const allowedTypes = [
			'image/png',
			'image/jpeg',
			'image/webp'
		];

		if (file.type && !allowedTypes.includes(file.type)) {
			input.setCustomValidity('Выберите PNG, JPEG или WebP.');
		} else if (!file.size) {
			input.setCustomValidity('Выбран пустой файл.');
		} else if (maxBytes > 0 && file.size > maxBytes) {
			input.setCustomValidity(
				'Изображение превышает допустимый размер.'
			);
		}

		if (!input.checkValidity()) {
			input.reportValidity();
			return;
		}

		previewUrl = URL.createObjectURL(file);
		preview.src = previewUrl;
	});

	preview.addEventListener('load', () => {
		preview.hidden = false;
	});

	preview.addEventListener('error', () => {
		clearPreview();
		input.setCustomValidity(
			'Браузер не смог прочитать изображение. Выберите другой файл.'
		);
		input.reportValidity();
	});

	window.addEventListener('pagehide', clearPreview);
}

async function submitCreateMap(form) {
	if (
		form.dataset.submitting === 'true'
		|| form.dataset.created === 'true'
	) return;

	if (!form.reportValidity()) return;

	const formData = new FormData(form);
	const title = String(formData.get('title') || '').trim();
	const gameId = String(formData.get('game_id') || '').trim();

	if (!title) {
		showCreateMessage('Укажите название карты.', true);
		return;
	}

	if (!gameId) {
		showCreateMessage(
			'Не выбрана игра. Вернитесь в каталог и выберите игру.',
			true
		);
		return;
	}

	const csrfToken = document.querySelector(
		'meta[name="csrf-token"]'
	)?.content;

	if (!csrfToken) {
		showCreateMessage(
			'Не найден защитный токен. Обновите страницу.',
			true
		);
		return;
	}

	formData.set('title', title);
	formData.set(
		'fog_of_war_enabled',
		form.querySelector('[name="fog_of_war_enabled"]').checked
			? 'true'
			: 'false'
	);

	const fileInput = form.querySelector('[name="background_image"]');
	if (!fileInput?.files?.length) {
		formData.delete('background_image');
	}

	const submitButton = form.querySelector('button[type="submit"]');
	const originalButtonText = submitButton?.textContent;

	form.dataset.submitting = 'true';

	if (submitButton) {
		submitButton.disabled = true;
		submitButton.textContent = 'Создание…';
	}

	showCreateMessage('Отправка данных карты…');

	try {
		const response = await fetch(form.action, {
			method: 'POST',
			credentials: 'include',
			redirect: 'error',
			headers: {
				'Accept': 'application/json',
				'X-CSRF-Token': csrfToken
			},
			body: formData
		});

		const data = await response.json().catch(() => null);

		if (!response.ok) {
			showCreateMessage(
				getResponseError(data, response.status),
				true
			);
			return;
		}

		form.dataset.created = 'true';

		if (submitButton) {
			submitButton.textContent = 'Карта создана';
		}

		const mapId = data?.id;
		const uuidPattern =
			/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

		if (typeof mapId !== 'string' || !uuidPattern.test(mapId)) {
			showCreateMessage(
				'Сервер подтвердил создание. Перейдите к списку карт '
				+ 'по ссылке выше; повторно отправлять форму не нужно.'
			);
			return;
		}

		showCreateMessage('Карта создана. Открываем просмотр.');
		window.location.assign(
			`/maps/${encodeURIComponent(mapId)}/view`
		);
	} catch {
		showCreateMessage(
			'Не удалось получить ответ сервера. Перед повторной '
			+ 'отправкой проверьте каталог: карта могла сохраниться.',
			true
		);
	} finally {
		if (form.dataset.created !== 'true') {
			delete form.dataset.submitting;

			if (submitButton) {
				submitButton.disabled = false;
				submitButton.textContent = originalButtonText;
			}
		}
	}
}

export function initMaps() {
	const form = document.getElementById('maps-create-form');

	if (!form || form.dataset.mapsInitialized === 'true') return;
	form.dataset.mapsInitialized = 'true';

	initBackgroundPreview(form);

	form.addEventListener('submit', event => {
		event.preventDefault();
		submitCreateMap(form);
	});
}