// frontend/static/js/modules/mfa-setup.js

function getCsrfToken() {
	return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

/**
 * Тихое обновление пары токенов через /auth/refresh — та же схема,
 * что attemptTokenRefresh в auth.js, но без повторного htmx-запроса:
 * здесь просто обновляем токены в localStorage и сообщаем об успехе.
 */
async function refreshAccessToken() {
	try {
		const resp = await fetch('/auth/refresh', {
			method: 'POST',
			credentials: 'include'
		});
		if (!resp.ok) return false;

		const data = await resp.json();
		if (data.access_token) localStorage.setItem('accessToken', data.access_token);
		if (data.refresh_token) localStorage.setItem('refreshToken', data.refresh_token);
		return true;
	} catch (e) {
		console.warn('[MFA] Token refresh failed.', e);
		return false;
	}
}

/**
 * @param {boolean} isRetry - true, если это повтор запроса после обновления токена
 *     (чтобы не уйти в бесконечный цикл при повторном 401).
 */
async function postForm(path, formData, isRetry = false) {
	const resp = await fetch(path, {
		method: 'POST',
		credentials: 'include',
		headers: { 'X-CSRF-Token': getCsrfToken() },
		body: formData
	});

	if (resp.status === 401 && !isRetry) {
		const refreshed = await refreshAccessToken();
		if (refreshed) {
			return postForm(path, formData, true);
		}

		localStorage.removeItem('accessToken');
		localStorage.removeItem('refreshToken');
		window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
		return { ok: false, data: { error: 'Сессия истекла, выполните вход заново.' } };
	}

	const data = await resp.json().catch(() => ({}));
	return { ok: resp.ok, data };
}

function showStatus(el, type, text) {
	if (el) el.innerHTML = `<div class="alert alert-${type}" role="alert">${text}</div>`;
}

export function initMfaSetup() {
	const startBtn = document.getElementById('mfa-start-setup');
	const setupBlock = document.getElementById('mfa-setup-block');
	const qrCanvas = document.getElementById('mfa-qr-canvas');
	const secretEl = document.getElementById('mfa-manual-secret');
	const confirmForm = document.getElementById('mfa-confirm-form');
	const disableForm = document.getElementById('mfa-disable-form');
	const statusEl = document.getElementById('mfa-status');
	const backupList = document.getElementById('mfa-backup-codes');

	if (!startBtn && !disableForm) return;

	startBtn?.addEventListener('click', async () => {
		const { ok, data } = await postForm('/profile/mfa/setup', new FormData());
		if (!ok) return showStatus(statusEl, 'danger', data.error || 'Не удалось начать настройку.');

		setupBlock?.classList.remove('hidden');
		if (secretEl) secretEl.textContent = data.secret;
		if (window.QRCode && qrCanvas) window.QRCode.toCanvas(qrCanvas, data.otpauth_uri, { width: 220 });
	});

	confirmForm?.addEventListener('submit', async (e) => {
		e.preventDefault();
		const { ok, data } = await postForm('/profile/mfa/confirm', new FormData(confirmForm));
		if (!ok) return showStatus(statusEl, 'danger', data.error || 'Неверный код.');

		showStatus(statusEl, 'success', data.message || 'Готово.');

		if (Array.isArray(data.backup_codes) && backupList) {
			backupList.innerHTML = data.backup_codes.map(c => `<li><code>${c}</code></li>`).join('');
			const wrapper = backupList.closest('.mfa-backup-wrapper');
			wrapper?.classList.remove('hidden');

			const downloadBtn = document.getElementById('mfa-backup-download');
			downloadBtn?.addEventListener('click', () => downloadBackupCodes(data.backup_codes));

			const ackBtn = document.getElementById('mfa-backup-ack');
			ackBtn?.addEventListener('click', () => window.location.reload(), { once: true });
		}
	});

	function downloadBackupCodes(codes) {
		const text = 'Резервные коды двухфакторной аутентификации WorldLoom\n\n' + codes.join('\n') +
			'\n\nКаждый код можно использовать только один раз. Храните файл в надёжном месте.';
		const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'worldloom-backup-codes.txt';
		a.click();
		URL.revokeObjectURL(url);
	}

	disableForm?.addEventListener('submit', async (e) => {
		e.preventDefault();
		const { ok, data } = await postForm('/profile/mfa/disable', new FormData(disableForm));
		showStatus(statusEl, ok ? 'success' : 'danger', data.message || data.error || '');
		if (ok) setTimeout(() => window.location.reload(), 1200);
	});
}