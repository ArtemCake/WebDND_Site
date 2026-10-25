// frontend/static/js/modules/mfa-setup.js

import {sessionClient, SessionRefreshError, isAuthenticationFailure} from './games/session-client.js';

/**
 * Отправляет форму через общий клиент cookie-сессии.
 *
 * Клиент добавляет CSRF-заголовок и при авторизационном отказе
 * выполняет refresh с однократным повтором исходного запроса.
 * JWT из JSON не читаются и в localStorage не сохраняются.
 */
async function postForm(path, formData) {
	try {
		const response = await sessionClient.sessionFetch(path, {
			method: 'POST',
			body: formData
		});

		if (isAuthenticationFailure(response)) {
			window.location.href =
				'/login?redirect=' +
				encodeURIComponent(
					window.location.pathname + window.location.search
				);

			return {
				ok: false,
				data: {
					error: 'Сессия завершена. Выполните вход снова.'
				}
			};
		}

		return {
			ok: response.ok,
			data: await response.json().catch(() => ({}))
		};
	} catch (error) {
		if (
			error instanceof SessionRefreshError &&
			error.status === 401
		) {
			window.location.href =
				'/login?redirect=' +
				encodeURIComponent(
					window.location.pathname + window.location.search
				);

			return {
				ok: false,
				data: {
					error: 'Сессия завершена. Выполните вход снова.'
				}
			};
		}

		return {
			ok: false,
			data: {
				error: error instanceof SessionRefreshError
					? error.message
					: 'Сетевая ошибка. Повторите действие позже.'
			}
		};
	}
}

function showStatus(el, type, text) {
	if (el) {
		el.innerHTML =
			`<div class="alert alert-${type}" role="alert">${text}</div>`;
	}
}

const initializedMfaRoots = new WeakSet();

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

	const root = startBtn || disableForm;

	if (initializedMfaRoots.has(root)) return;
	initializedMfaRoots.add(root);

	startBtn?.addEventListener('click', async () => {
		const { ok, data } = await postForm(
			'/profile/mfa/setup',
			new FormData()
		);

		if (!ok) {
			return showStatus(
				statusEl,
				'danger',
				data.error || 'Не удалось начать настройку.'
			);
		}

		setupBlock?.classList.remove('hidden');

		if (secretEl) {
			secretEl.textContent = data.secret;
		}

		if (window.QRCode && qrCanvas) {
			window.QRCode.toCanvas(
				qrCanvas,
				data.otpauth_uri,
				{ width: 220 }
			);
		}
	});

	confirmForm?.addEventListener('submit', async (e) => {
		e.preventDefault();

		const { ok, data } = await postForm(
			'/profile/mfa/confirm',
			new FormData(confirmForm)
		);

		if (!ok) {
			return showStatus(
				statusEl,
				'danger',
				data.error || 'Неверный код.'
			);
		}

		showStatus(
			statusEl,
			'success',
			data.message || 'Готово.'
		);

		if (Array.isArray(data.backup_codes) && backupList) {
			backupList.innerHTML = data.backup_codes
				.map(c => `<li><code>${c}</code></li>`)
				.join('');

			const wrapper = backupList.closest('.mfa-backup-wrapper');
			wrapper?.classList.remove('hidden');

			const downloadBtn =
				document.getElementById('mfa-backup-download');

			downloadBtn?.addEventListener('click', () => {
				downloadBackupCodes(data.backup_codes);
			});

			const ackBtn =
				document.getElementById('mfa-backup-ack');

			ackBtn?.addEventListener(
				'click',
				() => window.location.reload(),
				{ once: true }
			);
		}
	});

	function downloadBackupCodes(codes) {
		const text =
			'Резервные коды двухфакторной аутентификации WorldLoom\n\n' +
			codes.join('\n') +
			'\n\nКаждый код можно использовать только один раз. ' +
			'Храните файл в надёжном месте.';

		const blob = new Blob(
			[text],
			{ type: 'text/plain;charset=utf-8' }
		);

		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');

		a.href = url;
		a.download = 'worldloom-backup-codes.txt';
		a.click();

		URL.revokeObjectURL(url);
	}

	disableForm?.addEventListener('submit', async (e) => {
		e.preventDefault();

		const { ok, data } = await postForm(
			'/profile/mfa/disable',
			new FormData(disableForm)
		);

		showStatus(
			statusEl,
			ok ? 'success' : 'danger',
			data.message || data.error || ''
		);

		if (ok) {
			setTimeout(() => window.location.reload(), 1200);
		}
	});
}