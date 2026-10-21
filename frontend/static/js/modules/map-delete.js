// frontend/static/js/modules/map-delete.js

function showDeleteMessage(text, isError = false) {
	const box = document.getElementById('maps-delete-message');
	if (!box) return;

	box.className = isError
		? 'alert alert-error'
		: 'alert alert-success';
	box.textContent = text;
}

async function deleteMap(button) {
	if (button.dataset.submitting === 'true') return;

	const title = button.dataset.mapTitle || 'Без названия';
	const confirmed = window.confirm(
		`Удалить карту «${title}»?\n\n`
		+ 'Будут удалены её слои, гексы, объекты, аудиозоны '
		+ 'и загруженный фон. Токены останутся без привязки '
		+ 'к этой карте. Отменить удаление нельзя.'
	);

	if (!confirmed) return;

	const csrfToken = document.querySelector(
		'meta[name="csrf-token"]'
	)?.content;

	if (!csrfToken) {
		showDeleteMessage(
			'Не найден защитный токен. Обновите страницу.',
			true
		);
		return;
	}

	const originalText = button.textContent;
	button.dataset.submitting = 'true';
	button.disabled = true;
	button.textContent = 'Удаление…';

	try {
		const response = await fetch(button.dataset.mapDelete, {
			method: 'DELETE',
			credentials: 'include',
			redirect: 'error',
			headers: {
				'Accept': 'application/json',
				'X-CSRF-Token': csrfToken
			}
		});

		if (response.status !== 204) {
			const data = await response.json().catch(() => null);
			const message = typeof data?.detail === 'string'
				? data.detail
				: 'Не удалось удалить карту. Обновите каталог '
					+ 'и проверьте её состояние.';

			showDeleteMessage(message, true);
			return;
		}

		button.dataset.deleted = 'true';
		button.textContent = 'Карта удалена';
		showDeleteMessage('Карта удалена.');

		window.location.assign(button.dataset.returnUrl);
	} catch {
		showDeleteMessage(
			'Не удалось получить ответ сервера. Обновите каталог '
			+ 'перед повторной попыткой: карта могла быть удалена.',
			true
		);
	} finally {
		if (button.dataset.deleted !== 'true') {
			delete button.dataset.submitting;
			button.disabled = false;
			button.textContent = originalText;
		}
	}
}

export function initMapDelete() {
	document.querySelectorAll('[data-map-delete]').forEach(button => {
		if (button.dataset.deleteInitialized === 'true') return;
		button.dataset.deleteInitialized = 'true';

		button.addEventListener('click', () => {
			deleteMap(button);
		});
	});
}