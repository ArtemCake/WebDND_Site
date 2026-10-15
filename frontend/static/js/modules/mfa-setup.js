// frontend/static/js/modules/mfa-setup.js

function getCsrfToken() {
	return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

async function postForm(path, formData) {
	const resp = await fetch(path, {
		method: 'POST',
		credentials: 'include',
		headers: { 'X-CSRF-Token': getCsrfToken() },
		body: formData
	});
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
			backupList.closest('.mfa-backup-wrapper')?.classList.remove('hidden');
		}
		setTimeout(() => window.location.reload(), 4000);
	});

	disableForm?.addEventListener('submit', async (e) => {
		e.preventDefault();
		const { ok, data } = await postForm('/profile/mfa/disable', new FormData(disableForm));
		showStatus(statusEl, ok ? 'success' : 'danger', data.message || data.error || '');
		if (ok) setTimeout(() => window.location.reload(), 1200);
	});
}