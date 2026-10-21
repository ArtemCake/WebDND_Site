// frontend/static/js/modules/map-edit.js

function showEditMessage(text, isError = false) {
	const box = document.getElementById('map-edit-message');
	if (!box) return;

	box.className = isError
		? 'alert alert-error'
		: 'alert alert-success';
	box.textContent = text;
}

function getEditError(data, status) {
	if (typeof data?.detail === 'string') {
		return data.detail;
	}

	if (Array.isArray(data?.detail)) {
		const messages = data.detail
			.map(item => item?.msg)
			.filter(message => typeof message === 'string');

		if (messages.length) return messages.join('; ');
	}

	return `Не удалось сохранить карту. Код ответа: ${status}.`;
}

function initEditPreview(form) {
	const input = form.querySelector('[name="background_image"]');
	const image = document.getElementById('map-edit-preview');
	const message = document.getElementById('map-edit-preview-message');

	if (!image || !message) return;

	let objectUrl = null;
	let selectedFilePreview = false;

	function clearPreview() {
		image.hidden = true;
		image.removeAttribute('src');

		if (objectUrl) {
			URL.revokeObjectURL(objectUrl);
			objectUrl = null;
		}

		selectedFilePreview = false;
	}

	function showCurrentBackground() {
		clearPreview();

		const backgroundUrl = form.dataset.backgroundUrl?.trim();

		if (!backgroundUrl) {
			message.textContent = 'У карты пока нет фонового изображения.';
			return;
		}

		try {
			const url = new URL(backgroundUrl, window.location.origin);

			if (
				!['http:', 'https:'].includes(url.protocol)
				|| url.origin !== window.location.origin
				|| url.username
				|| url.password
			) {
				throw new Error('Unsupported background URL');
			}

			message.textContent = 'Загрузка текущего фона…';
			image.src = url.href;
		} catch {
			message.textContent =
				'Текущий фон нельзя показать: нужен адрес на этом сайте. '
				+ 'Можно выбрать новое изображение.';
		}
	}

	image.addEventListener('load', () => {
		image.hidden = false;
		message.textContent = selectedFilePreview
			? 'Предпросмотр нового фона. Изменения ещё не сохранены.'
			: 'Текущий фон карты.';
	});

	image.addEventListener('error', () => {
		image.hidden = true;

		if (selectedFilePreview) {
			input?.setCustomValidity(
				'Не удалось прочитать изображение. Выберите другой файл.'
			);
			message.textContent =
				'Браузер не смог показать выбранное изображение.';
		} else {
			message.textContent =
				'Не удалось загрузить текущий фон. '
				+ 'Можно сохранить остальные поля или выбрать новый файл.';
		}
	});

	input?.addEventListener('change', () => {
		clearPreview();
		input.setCustomValidity('');

		const file = input.files?.[0];

		if (!file) {
			showCurrentBackground();
			return;
		}

		const allowedTypes = [
			'image/png',
			'image/jpeg',
			'image/webp'
		];
		const maxBytes = Number(input.dataset.maxBytes);

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
			message.textContent = input.validationMessage;
			input.reportValidity();
			return;
		}

		objectUrl = URL.createObjectURL(file);
		selectedFilePreview = true;
		message.textContent = 'Подготовка предпросмотра…';
		image.src = objectUrl;
	});

	window.addEventListener('pagehide', clearPreview);

	showCurrentBackground();
}

async function submitMapEdit(form) {
	if (
		form.dataset.submitting === 'true'
		|| form.dataset.saved === 'true'
	) return;

	const titleInput = form.querySelector('[name="title"]');
	titleInput.value = titleInput.value.trim();

	if (!form.reportValidity()) return;

	const csrfToken = document.querySelector(
		'meta[name="csrf-token"]'
	)?.content;

	if (!csrfToken) {
		showEditMessage(
			'Не найден защитный токен. Обновите страницу.',
			true
		);
		return;
	}

	const formData = new FormData(form);
	const fogInput = form.querySelector(
		'[name="fog_of_war_enabled"]'
	);
	const fileInput = form.querySelector('[name="background_image"]');

	formData.set(
		'fog_of_war_enabled',
		fogInput.checked ? 'true' : 'false'
	);

	if (!fileInput?.files?.length) {
		formData.delete('background_image');
	}

	const submitButton = form.querySelector('button[type="submit"]');
	const originalText = submitButton.textContent;

	form.dataset.submitting = 'true';
	submitButton.disabled = true;
	submitButton.textContent = 'Сохранение…';
	showEditMessage('Сохранение изменений…');

	try {
		const response = await fetch(form.action, {
			method: 'PATCH',
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
			showEditMessage(
				getEditError(data, response.status),
				true
			);
			return;
		}

		form.dataset.saved = 'true';
		submitButton.textContent = 'Изменения сохранены';
		showEditMessage('Изменения сохранены.');

		window.location.assign(form.dataset.returnUrl);
	} catch {
		showEditMessage(
			'Не удалось получить ответ сервера. Перед повторным '
			+ 'сохранением откройте просмотр карты и проверьте изменения: '
			+ 'они могли сохраниться.',
			true
		);
	} finally {
		if (form.dataset.saved !== 'true') {
			delete form.dataset.submitting;
			submitButton.disabled = false;
			submitButton.textContent = originalText;
		}
	}
}

export function initMapEdit() {
	const form = document.getElementById('map-edit-form');

	if (!form || form.dataset.editInitialized === 'true') return;
	form.dataset.editInitialized = 'true';

	initEditPreview(form);

	form.addEventListener('submit', event => {
		event.preventDefault();
		submitMapEdit(form);
	});
}