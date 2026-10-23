// frontend/static/js/modules/games/game-details.js

function getErrorMessage(data) {
	if (typeof data?.detail === 'string') {
		return data.detail;
	}

	if (Array.isArray(data?.detail)) {
		return data.detail
			.map((item) => (
				typeof item?.msg === 'string' ? item.msg : ''
			))
			.filter(Boolean)
			.join('; ') || 'Проверьте значения полей.';
	}

	return 'Не удалось сохранить настройки игры.';
}

export function initGameDetails() {
	const form = document.querySelector('[data-game-settings]');

	if (!form || form.dataset.initialized === 'true') {
		return;
	}

	form.dataset.initialized = 'true';

	const message = form.querySelector('[data-game-settings-message]');
	const button = form.querySelector('button[type="submit"]');

	form.addEventListener('submit', async (event) => {
		event.preventDefault();

		if (form.dataset.saving === 'true') {
			return;
		}

		message.textContent = '';

		if (!form.reportValidity()) {
			return;
		}

		const fields = new FormData(form);
		const title = String(fields.get('title') || '').trim();

		if (!title) {
			message.textContent = 'Укажите название игры.';
			return;
		}

		const csrfToken = document.querySelector(
			'meta[name="csrf-token"]'
		)?.content;

		if (!csrfToken) {
			message.textContent =
				'Не найден защитный токен. Перезагрузите страницу.';
			return;
		}

		const payload = {
			title,
			description: String(fields.get('description') || '') || null,
			status: fields.get('status'),
			privacy_level: fields.get('privacy_level'),
			is_homebrew_allowed: fields.has('is_homebrew_allowed')
		};

		form.dataset.saving = 'true';
		form.setAttribute('aria-busy', 'true');
		button.disabled = true;

		try {
			const response = await fetch(form.action, {
				method: 'PATCH',
				credentials: 'include',
				redirect: 'error',
				headers: {
					'Accept': 'application/json',
					'Content-Type': 'application/json',
					'X-CSRF-Token': csrfToken
				},
				body: JSON.stringify(payload)
			});

			const data = await response.json().catch(() => null);

			if (!response.ok) {
				message.textContent = getErrorMessage(data);
				return;
			}

			message.textContent = 'Настройки сохранены.';

			// Обновляем сведения на странице с сервера.
			// Повторного PATCH при перезагрузке не будет.
			window.location.reload();
		} catch {
			message.textContent =
				'Не удалось подтвердить сохранение. Проверьте соединение '
				+ 'и обновите страницу перед повторной отправкой.';
		} finally {
			delete form.dataset.saving;
			form.setAttribute('aria-busy', 'false');
			button.disabled = false;
		}
	});
}