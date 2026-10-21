// frontend/static/js/modules/maps/map-management.js

import { acquireMapOperation } from './map-operation-state.js';

function showManagementMessage(text, isError = false) {
	const box = document.getElementById('map-management-message');
	if (!box) return;

	box.className = isError
		? 'alert alert-error'
		: 'alert alert-success';
	box.textContent = text;
}

function getManagementError(data, status) {
	if (typeof data?.detail === 'string') return data.detail;

	if (Array.isArray(data?.detail)) {
		const messages = data.detail
			.map(item => item?.msg)
			.filter(message => typeof message === 'string');

		if (messages.length) return messages.join('; ');
	}

	return `Операция не выполнена. Код ответа: ${status}.`;
}

function confirmOperation(action, destinationTitle) {
	switch (action) {
		case 'activate':
			return window.confirm(
				'Активировать карту? Остальные карты этой игры '
				+ 'станут неактивными.'
			);
		case 'deactivate':
			return window.confirm(
				'Деактивировать карту? Другая карта '
				+ 'автоматически выбрана не будет.'
			);
		case 'copy':
			return window.confirm(
				`Создать копию карты в игре «${destinationTitle}»?\n\n`
				+ 'Будут скопированы фон, настройки, слои и сетка. '
				+ 'Токены, объекты, аудиозоны и исследованные области '
				+ 'не копируются. Оригинал останется на месте.'
			);
		case 'move':
			return window.confirm(
				`Перенести оригинал в игру «${destinationTitle}»?\n\n`
				+ 'Карта исчезнет из исходной игры, станет неактивной '
				+ 'и отвяжется от прежней сессии. Сетка и состояние '
				+ 'тумана сохранятся. При наличии токенов, объектов '
				+ 'или аудиозон сервер отклонит перенос.'
			);
		default:
			return false;
	}
}

async function performMapOperation(root, button) {
	const action = button.dataset.mapAction;

	if (!['activate', 'deactivate', 'copy', 'move'].includes(action)) {
		return;
	}

	const targetSelect = document.getElementById('map-destination-game');
	const needsTarget = action === 'copy' || action === 'move';
	const targetGameId = targetSelect?.value || '';

	if (needsTarget && !targetGameId) {
		showManagementMessage('Сначала выберите другую игру.', true);
		targetSelect?.focus();
		return;
	}

	const destinationTitle =
		targetSelect?.selectedOptions[0]?.textContent?.trim() || '';

	if (!confirmOperation(action, destinationTitle)) return;

	const csrfToken = document.querySelector(
		'meta[name="csrf-token"]'
	)?.content;

	if (!csrfToken) {
		showManagementMessage(
			'Не найден защитный токен. Обновите страницу.',
			true
		);
		return;
	}

	const release = acquireMapOperation();
	if (!release) return;

	const originalText = button.textContent;
	button.textContent = 'Выполнение…';

	// При потере ответа или серверной ошибке результат
	// может быть неопределённым. Автоматически не повторяем.
	let canRelease = false;

	try {
		const headers = {
			'Accept': 'application/json',
			'X-CSRF-Token': csrfToken
		};
		const options = {
			method: 'POST',
			credentials: 'include',
			redirect: 'error',
			headers
		};

		if (needsTarget) {
			headers['Content-Type'] = 'application/json';
			options.body = JSON.stringify({
				source_game_id: root.dataset.sourceGameId,
				target_game_id: targetGameId
			});
		}

		showManagementMessage('Запрос отправляется…');

		const response = await fetch(
			`/maps/${encodeURIComponent(root.dataset.mapId)}/${action}`,
			options
		);
		const data = await response.json().catch(() => null);

		if (!response.ok) {
			canRelease = response.status < 500;

			const warning = canRelease
				? ''
				: ' Перед повторением обновите каталог и проверьте '
					+ 'обе игры: операция могла завершиться.';

			showManagementMessage(
				getManagementError(data, response.status) + warning,
				true
			);
			return;
		}

		if (!needsTarget) {
			showManagementMessage('Статус карты изменён.');
			window.location.reload();
			return;
		}

		const mapId = data?.id;
		const uuidPattern =
			/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

		if (typeof mapId !== 'string' || !uuidPattern.test(mapId)) {
			showManagementMessage(
				'Сервер подтвердил выполнение. Проверьте каталог '
				+ 'целевой игры; повторять запрос не нужно.'
			);
			return;
		}

		showManagementMessage(
			action === 'copy'
				? 'Копия карты создана.'
				: 'Карта перенесена.'
		);
		window.location.assign(
			`/maps/${encodeURIComponent(mapId)}/view`
		);
	} catch {
		showManagementMessage(
			'Не удалось получить ответ сервера. Обновите каталог '
			+ 'и проверьте исходную и целевую игры перед повторением: '
			+ 'операция могла завершиться.',
			true
		);
	} finally {
		if (canRelease) {
			release();
			button.textContent = originalText;
		} else {
			button.textContent = 'Проверьте состояние карты';
		}
	}
}

export function initMapManagement() {
	const root = document.getElementById('map-management');

	if (!root || root.dataset.initialized === 'true') return;
	root.dataset.initialized = 'true';

	root.querySelectorAll('[data-map-action]').forEach(button => {
		button.addEventListener('click', () => {
			performMapOperation(root, button);
		});
	});
}