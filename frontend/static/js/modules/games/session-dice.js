// frontend/static/js/modules/games/session-dice.js

import { gameStateApi } from './game-state-api.js';

const initializedRoots = new WeakSet();

const MODE_LABELS = {
	advantage: 'Преимущество',
	disadvantage: 'Помеха'
};

function showMessage(box, text, type = 'info') {
	const message = document.createElement('div');
	message.className = `alert alert-${type}`;
	message.textContent = text;
	box.replaceChildren(message);
}

function readRollPayload(form) {
	const values = new FormData(form);
	const formula = String(values.get('formula') || '')
		.trim()
		.toLowerCase();

	const match = /^(\d+)d(\d+)([+-]\d+)?$/.exec(formula);

	if (!match) {
		throw new Error('Введите формулу вида 2d6+3 или 1d20-2.');
	}

	const count = Number(match[1]);
	const sides = Number(match[2]);
	const modifier = Number(match[3] || 0);

	if (
		!Number.isSafeInteger(count) ||
		!Number.isSafeInteger(sides) ||
		!Number.isSafeInteger(modifier) ||
		count < 1 ||
		sides < 1
	) {
		throw new Error(
			'Количество костей и граней должно быть положительным целым числом. ' +
			'Числа должны находиться в безопасном диапазоне.'
		);
	}

	const advantage = String(values.get('advantage') || '') || null;

	if (
		advantage !== null &&
		advantage !== 'advantage' &&
		advantage !== 'disadvantage'
	) {
		throw new Error('Выберите доступный режим броска.');
	}

	if (advantage !== null && (count !== 1 || sides !== 20)) {
		throw new Error(
			'Преимущество и помеха доступны только для 1d20 ' +
			'с необязательным модификатором.'
		);
	}

	return {
		formula,
		advantage,
		is_gm_hidden: false
	};
}

function describeRoll(roll) {
	const parts = [
		`Кости: ${roll.individual_results.join(', ')}`
	];

	if (roll.advantage) {
		parts.push(MODE_LABELS[roll.advantage] || roll.advantage);
	}

	if (roll.is_gm_hidden) {
		parts.push('Скрытый бросок');
	}

	const createdAt = new Date(roll.created_at);

	if (!Number.isNaN(createdAt.getTime())) {
		parts.push(createdAt.toLocaleString('ru-RU'));
	}

	return parts.join(' · ');
}

function renderRolls(list, empty, rolls) {
	const fragment = document.createDocumentFragment();

	for (const roll of rolls) {
		const item = document.createElement('li');
		item.className = 'session-dice__entry';

		const result = document.createElement('strong');
		result.textContent = `${roll.formula} → ${roll.result_total}`;

		const details = document.createElement('span');
		details.className = 'session-dice__hint';
		details.textContent = describeRoll(roll);

		item.append(result, details);
		fragment.append(item);
	}

	list.replaceChildren(fragment);
	empty.hidden = rolls.length > 0;
	empty.textContent = 'В этой сессии пока нет доступных вам бросков.';
}

function initPanel(root) {
	if (initializedRoots.has(root)) return;

	const form = root.querySelector('[data-session-dice-form]');
	const fieldset = form?.querySelector('fieldset');
	const refresh = root.querySelector('[data-session-dice-refresh]');
	const message = root.querySelector('[data-session-dice-message]');
	const list = root.querySelector('[data-session-dice-list]');
	const empty = root.querySelector('[data-session-dice-empty]');

	if (!form || !fieldset || !refresh || !message || !list || !empty) {
		return;
	}

	initializedRoots.add(root);

	const sessionId = root.dataset.sessionId?.trim();

	if (!sessionId) {
		fieldset.disabled = true;
		refresh.disabled = true;
		showMessage(
			message,
			'Страница не передала игровую сессию для панели кубиков.',
			'error'
		);
		return;
	}

	let busy = false;
	let rolls = [];

	function setBusy(value) {
		busy = value;
		fieldset.disabled = value;
		refresh.disabled = value;
		root.setAttribute('aria-busy', String(value));
	}

	async function loadHistory() {
		if (busy) return;
		setBusy(true);

		try {
			const data = await gameStateApi.listRolls(sessionId);

			if (!Array.isArray(data)) {
				throw new Error('Сервер вернул некорректный журнал бросков.');
			}

			rolls = data;
			renderRolls(list, empty, rolls);
			message.replaceChildren();
		} catch (error) {
			showMessage(
				message,
				error.message || 'Не удалось загрузить журнал.',
				'error'
			);
		} finally {
			setBusy(false);
		}
	}

	form.addEventListener('submit', async (event) => {
		event.preventDefault();
		if (busy) return;

		let payload;

		try {
			payload = readRollPayload(form);
		} catch (error) {
			showMessage(message, error.message, 'error');
			return;
		}

		setBusy(true);

		try {
			const roll = await gameStateApi.rollDice(sessionId, payload);

			// Добавляем подтверждённый сервером результат,
			// не выполняя повторного броска или локального расчёта.
			rolls = [
				roll,
				...rolls.filter((item) => item.id !== roll.id)
			];

			renderRolls(list, empty, rolls);
			showMessage(
				message,
				`${roll.formula}: результат ${roll.result_total}.`,
				'success'
			);
		} catch (error) {
			const uncertain = !error.status || error.status >= 500;
			const suffix = uncertain
				? ' Перед повтором обновите журнал: сервер мог успеть сохранить бросок.'
				: '';

			showMessage(
				message,
				(error.message || 'Не удалось выполнить бросок.') + suffix,
				'error'
			);
		} finally {
			setBusy(false);
		}
	});

	refresh.addEventListener('click', loadHistory);
	void loadHistory();
}

export function initSessionDice() {
	document.querySelectorAll('[data-session-dice]').forEach(initPanel);
}