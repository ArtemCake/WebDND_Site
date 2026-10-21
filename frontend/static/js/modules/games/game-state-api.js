// frontend/static/js/modules/game-state-api.js

/**
 * API игрового состояния: токены, очередь ходов, броски кубиков.
 * Не управляет DOM, кроме обновления существующего CSRF meta-тега.
 * Данные форм и отображение результатов остаются в UI-модулях.
 */

export class GameStateApiError extends Error {
	constructor(message, status = 0, details = null) {
		super(message);
		this.name = 'GameStateApiError';
		this.status = status;
		this.details = details;
	}
}

function encodeId(value) {
	if (typeof value !== 'string' || !value.trim()) {
		throw new GameStateApiError('Не указан идентификатор объекта.');
	}

	return encodeURIComponent(value.trim());
}

function getErrorMessage(data, status) {
	if (typeof data?.detail === 'string') {
		return data.detail;
	}

	if (Array.isArray(data?.detail)) {
		const messages = data.detail.map((item) => {
			const location = Array.isArray(item.loc)
				? item.loc.filter((part) => part !== 'body').join('.')
				: '';

			const message = typeof item.msg === 'string'
				? item.msg
				: 'Некорректное значение';

			return location ? `${location}: ${message}` : message;
		});

		if (messages.length) {
			return messages.join('; ');
		}
	}

	switch (status) {
		case 401:
			return 'Сессия авторизации истекла. Войдите в аккаунт повторно.';
		case 403:
			return 'Недостаточно прав для выполнения действия.';
		case 404:
			return 'Запрошенный объект не найден.';
		case 409:
			return 'Состояние изменилось. Обновите данные перед повтором.';
		case 422:
			return 'Проверьте введённые данные.';
		default:
			return `Не удалось выполнить запрос (${status}).`;
	}
}

async function request(path, { method = 'GET', body } = {}) {
	const headers = new Headers({
		Accept: 'application/json'
	});

	if (body !== undefined) {
		headers.set('Content-Type', 'application/json');
	}

	if (method !== 'GET') {
		const csrfToken = document.querySelector(
			'meta[name="csrf-token"]'
		)?.content;

		if (!csrfToken) {
			throw new GameStateApiError(
				'Не найден защитный токен страницы. Обновите страницу.'
			);
		}

		headers.set('X-CSRF-Token', csrfToken);
	}

	let response;

	try {
		response = await fetch(path, {
			method,
			headers,
			credentials: 'include',
			body: body === undefined ? undefined : JSON.stringify(body)
		});
	} catch {
		throw new GameStateApiError(
			'Не удалось связаться с сервером. Проверьте соединение.'
		);
	}

	const freshCsrfToken = response.headers.get('X-CSRF-Token');

	if (freshCsrfToken) {
		document.querySelector('meta[name="csrf-token"]')
			?.setAttribute('content', freshCsrfToken);
	}

	if (response.status === 204) {
		return null;
	}

	const contentType = response.headers.get('Content-Type') || '';
	let data = null;

	if (contentType.includes('application/json')) {
		try {
			data = await response.json();
		} catch {
			throw new GameStateApiError(
				'Сервер вернул некорректный JSON.',
				response.status
			);
		}
	}

	if (!response.ok) {
		throw new GameStateApiError(
			getErrorMessage(data, response.status),
			response.status,
			data?.detail ?? null
		);
	}

	if (!contentType.includes('application/json')) {
		throw new GameStateApiError(
			'Вместо данных сервер вернул страницу. Проверьте авторизацию.',
			response.status
		);
	}

	return data;
}

export const gameStateApi = Object.freeze({
	listTokens(sessionId) {
		return request(`/sessions/${encodeId(sessionId)}/tokens`);
	},

	createToken(payload) {
		return request('/sessions/tokens', {
			method: 'POST',
			body: payload
		});
	},

	updateToken(tokenId, payload) {
		return request(`/sessions/tokens/${encodeId(tokenId)}`, {
			method: 'PATCH',
			body: payload
		});
	},

	moveToken(tokenId, payload) {
		return request(`/sessions/tokens/${encodeId(tokenId)}/move`, {
			method: 'POST',
			body: payload
		});
	},

	deleteToken(tokenId) {
		return request(`/sessions/tokens/${encodeId(tokenId)}`, {
			method: 'DELETE'
		});
	},

	startCombat(sessionId, combatants) {
		if (!Array.isArray(combatants)) {
			throw new GameStateApiError(
				'Участники боя должны передаваться списком.'
			);
		}

		return request(`/sessions/${encodeId(sessionId)}/combat/start`, {
			method: 'POST',
			body: combatants
		});
	},

	nextTurn(sessionId) {
		return request(`/sessions/${encodeId(sessionId)}/combat/next-turn`, {
			method: 'POST'
		});
	},

	endCombat(sessionId) {
		return request(`/sessions/${encodeId(sessionId)}/combat/end`, {
			method: 'POST'
		});
	},

	rollDice(sessionId, payload, partyId = null) {
		const query = new URLSearchParams();

		if (partyId !== null) {
			query.set('party_id', partyId);
		}

		const suffix = query.size ? `?${query.toString()}` : '';

		return request(`/sessions/${encodeId(sessionId)}/roll${suffix}`, {
			method: 'POST',
			body: payload
		});
	},

	listRolls(sessionId) {
		return request(`/sessions/${encodeId(sessionId)}/rolls`);
	}
});