// frontend/static/js/modules/delete-account.js

/**
 * @fileoverview Модальное окно удаления аккаунта (двухшаговое подтверждение).
 * Инициализируется на странице профиля через data-атрибуты,
 * без inline-обработчиков — согласно правилу 1.5 Инструкции.
 * @module modules/delete-account
 */

function showStep1() {
    document.getElementById('delete-modal-step1')?.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function showStep2() {
    document.getElementById('delete-modal-step1')?.classList.add('hidden');
    document.getElementById('delete-modal-step2')?.classList.remove('hidden');
}

function closeModals() {
    document.getElementById('delete-modal-step1')?.classList.add('hidden');
    document.getElementById('delete-modal-step2')?.classList.add('hidden');
    document.body.style.overflow = '';
    const box = document.getElementById('message-box-delete');
    if (box) box.innerHTML = '';
}

async function confirmDelete(permanent) {
    const passwordInput = document.getElementById('delete-password');
    const box = document.getElementById('message-box-delete');
    const password = passwordInput?.value;

    if (!password) {
        if (box) box.innerHTML = '<div class="alert alert-danger">Введите пароль.</div>';
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    try {
        const resp = await fetch('/auth/delete-account', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken || ''
            },
            body: JSON.stringify({ password, permanent })
        });

        const data = await resp.json().catch(() => ({}));

        if (!resp.ok) {
            if (box) box.innerHTML = `<div class="alert alert-danger">${data.detail || data.error || 'Не удалось удалить аккаунт.'}</div>`;
            return;
        }

        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';

    } catch (e) {
        if (box) box.innerHTML = '<div class="alert alert-danger">Ошибка сети. Попробуйте ещё раз.</div>';
    }
}

/**
 * Навешивает делегированный обработчик кликов на документ.
 * Вызывается один раз из main.js при инициализации приложения.
 */
export function initDeleteAccountModal() {
    document.body.addEventListener('click', (e) => {
        const action = e.target.closest('[data-delete-action]')?.dataset.deleteAction;
        if (!action) return;

        e.preventDefault();

        switch (action) {
            case 'open-step1':
                showStep1();
                break;
            case 'open-step2':
                showStep2();
                break;
            case 'close':
                closeModals();
                break;
            case 'confirm-soft':
                confirmDelete(false);
                break;
            case 'confirm-permanent':
                confirmDelete(true);
                break;
        }
    });
}