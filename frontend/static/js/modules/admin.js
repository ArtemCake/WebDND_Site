// frontend/static/js/modules/admin.js

/**
 * @fileoverview Админ-панель: модалка управления пользователем (роли, права,
 * удаление) и действия по жалобам. Без inline-JS — делегирование кликов
 * по data-атрибутам, согласно правилу 1.5 Инструкции.
 * @module modules/admin
 */

let currentUserId = null;

function getCsrfToken() {
	return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

function showAdminMessage(text, isError) {
	const box = document.getElementById('message-box-admin');
	if (box) box.innerHTML = `<div class="alert ${isError ? 'alert-danger' : 'alert-success'}">${text}</div>`;
}

function openManageModal(trigger) {
	currentUserId = trigger.dataset.userId;
	document.getElementById('admin-manage-nickname').textContent = trigger.dataset.userNickname;

	const roles = (trigger.dataset.userRoles || '').split(',').filter(Boolean);
	const permissions = (trigger.dataset.userPermissions || '').split(',').filter(Boolean);

	document.querySelectorAll('[data-role-checkbox]').forEach(cb => { cb.checked = roles.includes(cb.value); });
	document.querySelectorAll('[data-permission-checkbox]').forEach(cb => { cb.checked = permissions.includes(cb.value); });

	document.getElementById('admin-manage-modal')?.classList.remove('hidden');
}

function closeManageModal() {
	document.getElementById('admin-manage-modal')?.classList.add('hidden');
	currentUserId = null;
	const box = document.getElementById('message-box-admin');
	if (box) box.innerHTML = '';
}

async function saveRoles() {
	if (!currentUserId) return;
	const body = new URLSearchParams();
	document.querySelectorAll('[data-role-checkbox]:checked').forEach(cb => body.append('roles', cb.value));

	try {
		const resp = await fetch(`/admin/users/${currentUserId}/roles`, {
			method: 'PATCH', credentials: 'include',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRF-Token': getCsrfToken() },
			body
		});
		const data = await resp.json().catch(() => ({}));
		if (!resp.ok) { showAdminMessage(data.detail || 'Не удалось сохранить роли.', true); return; }
		showAdminMessage('Роли сохранены. Обновите страницу, чтобы увидеть изменения в таблице.', false);
	} catch (e) { showAdminMessage('Ошибка сети.', true); }
}

async function savePermissions() {
	if (!currentUserId) return;
	const body = new URLSearchParams();
	document.querySelectorAll('[data-permission-checkbox]:checked').forEach(cb => body.append('permissions', cb.value));

	try {
		const resp = await fetch(`/admin/users/${currentUserId}/permissions`, {
			method: 'PATCH', credentials: 'include',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRF-Token': getCsrfToken() },
			body
		});
		const data = await resp.json().catch(() => ({}));
		if (!resp.ok) { showAdminMessage(data.detail || 'Не удалось сохранить права.', true); return; }
		showAdminMessage('Права сохранены. Обновите страницу, чтобы увидеть изменения в таблице.', false);
	} catch (e) { showAdminMessage('Ошибка сети.', true); }
}

async function deleteUser(permanent) {
	if (!currentUserId) return;
	if (permanent && !window.confirm('Удалить пользователя навсегда? Это нельзя отменить.')) return;

	const body = new URLSearchParams();
	body.append('permanent', permanent);

	try {
		const resp = await fetch(`/admin/users/${currentUserId}/delete`, {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRF-Token': getCsrfToken() },
			body
		});
		const data = await resp.json().catch(() => ({}));
		if (!resp.ok) { showAdminMessage(data.detail || 'Не удалось выполнить действие.', true); return; }
		showAdminMessage(data.message, false);
	} catch (e) { showAdminMessage('Ошибка сети.', true); }
}

async function updateReport(reportId, newStatus) {
	const body = new URLSearchParams();
	body.append('new_status', newStatus);

	try {
		const resp = await fetch(`/admin/reports/${reportId}`, {
			method: 'PATCH', credentials: 'include',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRF-Token': getCsrfToken() },
			body
		});
		if (resp.ok) window.location.reload();
	} catch (e) { /* молча — пользователь увидит, что статус не изменился */ }
}

export function initAdminPanel() {
	document.body.addEventListener('click', (e) => {
		const manageTrigger = e.target.closest('[data-admin-action]');
		if (manageTrigger) {
			switch (manageTrigger.dataset.adminAction) {
				case 'manage': openManageModal(manageTrigger); break;
				case 'close': closeManageModal(); break;
				case 'save-roles': saveRoles(); break;
				case 'save-permissions': savePermissions(); break;
				case 'deactivate': deleteUser(false); break;
				case 'delete-permanent': deleteUser(true); break;
			}
			return;
		}

		const reportTrigger = e.target.closest('[data-report-action]');
		if (reportTrigger) {
			const status = reportTrigger.dataset.reportAction === 'resolve' ? 'resolved' : 'dismissed';
			updateReport(reportTrigger.dataset.reportId, status);
		}
	});
}