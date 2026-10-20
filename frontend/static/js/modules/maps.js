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
	if (typeof data?.detail === 'string') {
		return data.detail;
	}

	if (Array.isArray(data?.detail)) {
		const messages = data.detail
			.map(item => item?.msg)
			.filter(message => typeof message === 'string');

		if (messages.length) {
			return messages.join('; ');
		}
	}

	return `Не удалось создать карту. Код ответа: ${status}.`;
}

async function submitCreateMap(form) {
	if (form.dataset.submitting === 'true') return;
	if (!form.reportValidity()) return;

	const formData = new FormData(form);
	const title = String(formData.get('title') || '').trim();
	const gameId = String(formData.get('game_id') || '').trim();
	const backgroundUrl = String(
		formData.get('background_image_url') || ''
	).trim();

	if (!title) {
		showCreateMessage('Укажите название карты.', true);
		return;
	}

	if (!gameId) {
		showCreateMessage(
			'Не выбрана игра. Обновите страницу и выберите игру.',
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

	const payload = {
		game_id: gameId,
		title,
		map_type: 'image_upload',
		background_image_url: backgroundUrl || null,
		grid_settings_json: {},
		fog_of_war_enabled: formData.has('fog_of_war_enabled'),
		lighting_model: 'basic'
	};

	const submitButton = form.querySelector('button[type="submit"]');
	const originalButtonText = submitButton?.textContent;

	form.dataset.submitting = 'true';

	if (submitButton) {
		submitButton.disabled = true;
		submitButton.textContent = 'Создание…';
	}

	showCreateMessage('Отправка запроса на создание карты…');

	try {
		const response = await fetch(form.action, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				'Accept': 'application/json',
				'X-CSRF-Token': csrfToken
			},
			body: JSON.stringify(payload)
		});

		if (response.redirected) {
			showCreateMessage(
				'Сервер перенаправил запрос. Проверьте вход в аккаунт '
				+ 'и обновите страницу перед повторной отправкой.',
				true
			);
			return;
		}

		const data = await response.json().catch(() => null);

		if (!response.ok) {
			showCreateMessage(
				getResponseError(data, response.status),
				true
			);
			return;
		}

		showCreateMessage('Карта создана. Обновляем список.');

		const pageUrl = new URL('/maps', window.location.origin);
		pageUrl.searchParams.set('game_id', gameId);
		window.location.assign(pageUrl.href);
	} catch (error) {
		showCreateMessage(
			'Не удалось получить ответ сервера. Перед повторной '
			+ 'отправкой обновите список: карта могла сохраниться.',
			true
		);
	} finally {
		delete form.dataset.submitting;

		if (submitButton) {
			submitButton.disabled = false;
			submitButton.textContent = originalButtonText;
		}
	}
}

export function initMaps() {
	const form = document.getElementById('maps-create-form');

	if (!form || form.dataset.mapsInitialized === 'true') return;
	form.dataset.mapsInitialized = 'true';

	form.addEventListener('submit', event => {
		event.preventDefault();
		submitCreateMap(form);
	});
}