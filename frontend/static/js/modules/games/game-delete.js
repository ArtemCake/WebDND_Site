// frontend/static/js/modules/games/game-delete.js

export function initGameDelete() {
	const root = document.querySelector('[data-game-delete]');

	if (!root || root.dataset.initialized === 'true') {
		return;
	}

	root.dataset.initialized = 'true';

	const button = root.querySelector('[data-game-delete-button]');
	const message = root.querySelector('[data-game-delete-message]');
	const settingsForm = document.querySelector('[data-game-settings]');

	let busy = false;
	let cleanupPending = false;
	let requestSent = false;

	button.addEventListener('click', async () => {
		if (busy) {
			return;
		}

		if (settingsForm?.dataset.saving === 'true') {
			message.textContent =
				'Дождитесь завершения сохранения настроек.';
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

		if (!cleanupPending && !window.confirm(
			'Удалить игру навсегда вместе с её картами, сессиями '
			+ 'и историей? Отменить это действие будет нельзя.'
		)) {
			return;
		}

		busy = true;
		button.disabled = true;
		root.setAttribute('aria-busy', 'true');
		message.textContent = cleanupPending
			? 'Повторная очистка файлов…'
			: 'Удаление игры…';

		if (settingsForm) {
			settingsForm.dataset.deleting = 'true';
			settingsForm.querySelectorAll(
				'input, textarea, select, button'
			).forEach((control) => {
				control.disabled = true;
			});
		}

		try {
			requestSent = true;

			const response = await fetch(root.dataset.deleteUrl, {
				method: 'DELETE',
				credentials: 'include',
				redirect: 'error',
				headers: {
					'Accept': 'application/json',
					'X-CSRF-Token': csrfToken
				}
			});

			const data = await response.json().catch(() => null);

			if (!response.ok || data?.deleted !== true) {
				message.textContent =
					typeof data?.detail === 'string'
						? data.detail
						: 'Удаление не подтверждено. Обновите список игр '
							+ 'перед дальнейшими действиями.';
				return;
			}

			cleanupPending = data.cleanup_complete !== true;

			if (cleanupPending) {
				message.textContent = data.detail;
				button.textContent = 'Повторить очистку файлов';
				return;
			}

			message.textContent = data.detail;
			window.location.assign(root.dataset.returnUrl);

		} catch {
			message.textContent =
				'Не удалось получить результат. Игра могла быть удалена. '
				+ 'Повторный запрос безопасен и проверит очистку.';
			button.textContent = 'Повторить запрос удаления';

		} finally {
			busy = false;
			button.disabled = false;
			root.setAttribute('aria-busy', 'false');

			// После отправленного удаления не разрешаем сохранять
			// настройки потенциально уже удалённой игры.
			if (!requestSent && settingsForm) {
				delete settingsForm.dataset.deleting;
			}
		}
	});
}