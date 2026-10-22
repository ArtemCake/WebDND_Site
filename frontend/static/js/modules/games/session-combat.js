// frontend/static/js/modules/games/session-combat.js

import { gameStateApi } from './game-state-api.js';

function renderState(root, state) {
	const status = root.querySelector('[data-combat-status]');
	const round = root.querySelector('[data-combat-round]');
	const list = root.querySelector('[data-combat-order]');

	list.replaceChildren();
	round.hidden = true;

	if (
		!state
		|| !Array.isArray(state.turn_order)
		|| typeof state.combat_active !== 'boolean'
		|| typeof state.session_active !== 'boolean'
		|| state.turn_order.some(
			(item) => !item || typeof item !== 'object'
				|| Array.isArray(item)
		)
	) {
		throw new Error('Сервер вернул некорректное состояние боя.');
	}

	const order = state.turn_order;

	if (!order.length) {
		if (!state.session_active) {
			status.textContent =
				'Игровая сессия завершена. Сохранённой очереди нет.';
		} else if (state.combat_active) {
			status.textContent = 'Бой активен, но очередь участников пуста.';
		} else {
			status.textContent = 'Бой не начат или уже завершён.';
		}
		return;
	}

	if (
		!Number.isInteger(state.current_index)
		|| state.current_index < 0
		|| state.current_index >= order.length
		|| !Number.isInteger(state.round_number)
		|| state.round_number < 1
	) {
		throw new Error('Сохранённые номер раунда или текущий ход некорректны.');
	}

	const currentTurnActive =
		state.session_active && state.combat_active;

	if (!state.session_active) {
		status.textContent =
			'Игровая сессия завершена. Показана сохранённая очередь.';
	} else if (!state.combat_active) {
		status.textContent =
			'Бой неактивен. Показана сохранённая очередь.';
	} else {
		status.textContent = 'Бой идёт.';
	}

	round.textContent = `Раунд: ${state.round_number}`;
	round.hidden = false;

	const fragment = document.createDocumentFragment();

	order.forEach((combatant, index) => {
		const item = document.createElement('li');
		const name = (
			typeof combatant.name === 'string'
			&& combatant.name.trim()
		)
			? combatant.name.trim()
			: `Участник ${index + 1}`;

		const initiative = (
			typeof combatant.initiative === 'number'
			&& Number.isFinite(combatant.initiative)
		)
			? combatant.initiative
			: 'не указана';

		item.textContent = `${name} — инициатива: ${initiative}`;

		if (index === state.current_index) {
			if (currentTurnActive) {
				item.setAttribute('aria-current', 'step');
				const marker = document.createElement('strong');
				marker.textContent = ' — текущий ход';
				item.append(marker);
			} else {
				item.append(' — сохранённая позиция');
			}
		}

		fragment.append(item);
	});

	list.append(fragment);
}

async function loadState(root) {
	if (root.dataset.loading === 'true') {
		return;
	}

	const button = root.querySelector('[data-combat-refresh]');
	const status = root.querySelector('[data-combat-status]');
	const round = root.querySelector('[data-combat-round]');
	const list = root.querySelector('[data-combat-order]');

	root.dataset.loading = 'true';
	root.setAttribute('aria-busy', 'true');
	button.disabled = true;

	// Не оставляем старую очередь на экране при ошибке обновления.
	list.replaceChildren();
	round.hidden = true;
	status.textContent = 'Загрузка состояния боя…';

	try {
		const state = await gameStateApi.getCombatState(
			root.dataset.sessionId
		);
		renderState(root, state);
	} catch (error) {
		list.replaceChildren();
		round.hidden = true;
		status.textContent = error instanceof Error
			? error.message
			: 'Не удалось загрузить состояние боя.';
	} finally {
		delete root.dataset.loading;
		root.setAttribute('aria-busy', 'false');
		button.disabled = false;
	}
}

export function initSessionCombat() {
	document.querySelectorAll('[data-session-combat]').forEach((root) => {
		if (root.dataset.initialized === 'true') {
			return;
		}

		root.dataset.initialized = 'true';

		root.querySelector('[data-combat-refresh]')
			.addEventListener('click', () => {
				void loadState(root);
			});

		void loadState(root);
	});
}