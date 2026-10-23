// frontend/static/js/modules/games/lobby.js

/**
 * @fileoverview Лобби игр: список своих игр, создание игры, приглашения.
 * Без inline-JS — делегирование кликов по data-атрибутам, согласно правилу 1.5 Инструкции.
 * Чистый fetch + построение DOM (в отличие от auth.js на HTMX): API лобби отдаёт JSON, а не HTML.
 * @module modules/lobby
 */

 import { initGameDetails } from './game-details.js';

let currentUserId = null;
let currentInviteGameId = null;

const STATUS_LABELS = { draft: 'Черновик', active: 'Идёт', archived: 'Архив' };
const PRIVACY_LABELS = {
	public: 'Публичная', friends_only: 'Только друзья',
	invite_only: 'По приглашению', private: 'Приватная'
};

function getCsrfToken() {
	return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

function showLobbyMessage(boxId, text, isError) {
	const box = document.getElementById(boxId);
	if (box) box.innerHTML = `<div class="alert ${isError ? 'alert-error' : 'alert-success'}">${text}</div>`;
}

function escapeHtml(str) {
	const div = document.createElement('div');
	div.textContent = str ?? '';
	return div.innerHTML;
}

async function fetchCurrentUserId() {
	try {
		const resp = await fetch('/profile/data', { credentials: 'include' });
		if (!resp.ok) return null;
		const data = await resp.json();
		return data.id || null;
	} catch (e) {
		return null;
	}
}

function renderGameCard(game) {
	const isMaster = currentUserId && game.master_id === currentUserId;
	const statusLabel = STATUS_LABELS[game.status] || game.status;
	const privacyLabel = PRIVACY_LABELS[game.privacy_level] || game.privacy_level;
	const detailsUrl = `/games/${encodeURIComponent(game.id)}/details`;
    const playUrl =	`/games/${encodeURIComponent(game.id)}/play`;

	return `
		<article class="lobby-card" data-game-id="${escapeHtml(game.id)}">
			<header class="lobby-card__header">
								<h3>
                					<a href="${escapeHtml(detailsUrl)}">
                						${escapeHtml(game.title)}
                					</a>
                				</h3>
				${isMaster ? '<span class="lobby-badge lobby-badge--master">Вы — ведущий</span>' : ''}
			</header>
			${game.description ? `<p class="lobby-card__description">${escapeHtml(game.description)}</p>` : ''}
			<div class="lobby-card__badges">
				<span class="lobby-badge">Статус: ${escapeHtml(statusLabel)}</span>
				<span class="lobby-badge">${escapeHtml(privacyLabel)}</span>
			</div>
			<div class="lobby-card__actions">
				<a class="btn btn-outline-primary" href="${escapeHtml(detailsUrl)}">
            		${isMaster ? 'Открыть и настроить' : 'Открыть игру'}
            	</a>
            	<a class="btn btn-outline-primary" href="${escapeHtml(playUrl)}">
            		К игровым сессиям
            	</a>
				${isMaster ? `<button type="button" class="btn btn-outline-primary" data-lobby-action="invite-open" data-game-id="${escapeHtml(game.id)}">Пригласить</button>` : ''}
				${!isMaster ? `<button type="button" class="btn btn-outline-primary" data-lobby-action="leave-game" data-game-id="${escapeHtml(game.id)}">Покинуть</button>` : ''}
			</div>
		</article>
	`;
}

function renderGames(games) {
	const list = document.getElementById('games-list');
	const empty = document.getElementById('games-empty');
	if (!list) return;

	list.querySelectorAll('.lobby-card').forEach(el => el.remove());

	if (!games.length) {
		empty?.classList.remove('hidden');
		return;
	}
	empty?.classList.add('hidden');

	const html = games.map(renderGameCard).join('');
	list.insertAdjacentHTML('beforeend', html);
}

async function loadGames() {
	try {
		const resp = await fetch('/games/list', { credentials: 'include' });
		if (!resp.ok) {
			showLobbyMessage('message-box-lobby', 'Не удалось загрузить список игр.', true);
			return;
		}
		const games = await resp.json();
		renderGames(games);
	} catch (e) {
		showLobbyMessage('message-box-lobby', 'Ошибка сети при загрузке игр.', true);
	}
}

function openCreateModal() {
	document.getElementById('lobby-create-modal')?.classList.remove('hidden');
}

function closeCreateModal() {
	document.getElementById('lobby-create-modal')?.classList.add('hidden');
	document.getElementById('lobby-create-form')?.reset();
	const box = document.getElementById('message-box-lobby-create');
	if (box) box.innerHTML = '';
}

async function submitCreateGame(form) {
	const formData = new FormData(form);
	const payload = {
		title: formData.get('title'),
		description: formData.get('description') || null,
		system_id: formData.get('system_id'),
		privacy_level: formData.get('privacy_level'),
		is_homebrew_allowed: formData.get('is_homebrew_allowed') === 'on'
	};

	try {
		const resp = await fetch('/games', {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
			body: JSON.stringify(payload)
		});
		const data = await resp.json().catch(() => ({}));
		if (!resp.ok) {
			showLobbyMessage('message-box-lobby-create', data.detail || 'Не удалось создать игру.', true);
			return;
		}
		closeCreateModal();
		showLobbyMessage('message-box-lobby', 'Игра создана.', false);
		await loadGames();
	} catch (e) {
		showLobbyMessage('message-box-lobby-create', 'Ошибка сети.', true);
	}
}

function openInviteModal(gameId) {
	currentInviteGameId = gameId;
	document.getElementById('lobby-invite-result')?.classList.add('hidden');
	document.getElementById('lobby-invite-modal')?.classList.remove('hidden');
}

function closeInviteModal() {
	document.getElementById('lobby-invite-modal')?.classList.add('hidden');
	document.getElementById('lobby-invite-form')?.reset();
	currentInviteGameId = null;
	const box = document.getElementById('message-box-lobby-invite');
	if (box) box.innerHTML = '';
}

async function submitCreateInvite(form) {
	if (!currentInviteGameId) return;
	const formData = new FormData(form);
	const expiresLocal = formData.get('expires_at');
	const usesLimit = formData.get('uses_limit');

	const payload = {
		expires_at: expiresLocal ? new Date(expiresLocal).toISOString() : null,
		uses_limit: usesLimit ? Number(usesLimit) : null,
		message: formData.get('message') || null
	};

	try {
		const resp = await fetch(`/games/${currentInviteGameId}/invites`, {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
			body: JSON.stringify(payload)
		});
		const data = await resp.json().catch(() => ({}));
		if (!resp.ok) {
			showLobbyMessage('message-box-lobby-invite', data.detail || 'Не удалось создать приглашение.', true);
			return;
		}
		const output = document.getElementById('lobby-invite-token-output');
		if (output) output.value = data.token;
		document.getElementById('lobby-invite-result')?.classList.remove('hidden');
		showLobbyMessage('message-box-lobby-invite', 'Приглашение создано.', false);
	} catch (e) {
		showLobbyMessage('message-box-lobby-invite', 'Ошибка сети.', true);
	}
}

async function copyInviteToken() {
	const output = document.getElementById('lobby-invite-token-output');
	if (!output || !output.value) return;
	try {
		await navigator.clipboard.writeText(output.value);
		showLobbyMessage('message-box-lobby-invite', 'Токен скопирован.', false);
	} catch (e) {
		showLobbyMessage('message-box-lobby-invite', 'Не удалось скопировать — выделите токен вручную.', true);
	}
}

async function claimInvite() {
	const input = document.getElementById('lobby-invite-token-input');
	const token = input?.value?.trim();
	if (!token) return;

	try {
		const resp = await fetch('/games/invites/claim', {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
			body: JSON.stringify({ token })
		});
		const data = await resp.json().catch(() => ({}));
		if (!resp.ok) {
			showLobbyMessage('message-box-lobby', data.detail || 'Не удалось присоединиться по этому токену.', true);
			return;
		}
		if (input) input.value = '';
		showLobbyMessage('message-box-lobby', 'Вы присоединились к игре.', false);
		await loadGames();
	} catch (e) {
		showLobbyMessage('message-box-lobby', 'Ошибка сети.', true);
	}
}

async function leaveGame(gameId) {
	if (!window.confirm('Покинуть эту игру?')) return;
	try {
		const resp = await fetch(`/games/${gameId}/leave`, {
			method: 'POST', credentials: 'include',
			headers: { 'X-CSRF-Token': getCsrfToken() }
		});
		if (!resp.ok) {
			showLobbyMessage('message-box-lobby', 'Не удалось покинуть игру.', true);
			return;
		}
		showLobbyMessage('message-box-lobby', 'Вы покинули игру.', false);
		await loadGames();
	} catch (e) {
		showLobbyMessage('message-box-lobby', 'Ошибка сети.', true);
	}
}

async function loadGameSystems() {
	const select = document.getElementById('lobby-system-select');
	if (!select) return;

	try {
		const resp = await fetch('/game-systems', { credentials: 'include' });
		if (!resp.ok) {
			select.innerHTML = '<option value="" disabled selected>Не удалось загрузить</option>';
			return;
		}
		const systems = await resp.json();
		if (!systems.length) {
			select.innerHTML = '<option value="" disabled selected>Нет доступных систем</option>';
			return;
		}
		select.innerHTML = systems
			.map(s => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.name)}</option>`)
			.join('');
	} catch (e) {
		select.innerHTML = '<option value="" disabled selected>Ошибка сети</option>';
	}
}

export async function initLobby() {
	initGameDetails();

	if (!document.getElementById('games-list')) return;

	currentUserId = await fetchCurrentUserId();
	await loadGames();
	await loadGameSystems();

	document.body.addEventListener('click', (e) => {
		const trigger = e.target.closest('[data-lobby-action]');
		if (!trigger) return;
		const action = trigger.dataset.lobbyAction;

		switch (action) {
			case 'create-game-open': openCreateModal(); break;
			case 'create-game-close': closeCreateModal(); break;
			case 'invite-open': openInviteModal(trigger.dataset.gameId); break;
			case 'invite-close': closeInviteModal(); break;
			case 'copy-invite': copyInviteToken(); break;
			case 'claim-invite': claimInvite(); break;
			case 'leave-game': leaveGame(trigger.dataset.gameId); break;
		}
	});

	document.getElementById('lobby-create-form')?.addEventListener('submit', (e) => {
		e.preventDefault();
		submitCreateGame(e.target);
	});

	document.getElementById('lobby-invite-form')?.addEventListener('submit', (e) => {
		e.preventDefault();
		submitCreateInvite(e.target);
	});
}