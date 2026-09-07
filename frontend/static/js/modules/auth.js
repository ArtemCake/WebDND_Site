// frontend/static/js/modules/auth.js

export function setupAuthHandlers() {
    document.body.addEventListener('htmx:afterRequest', function (evt) {
        const targetForm = evt.detail.requestConfig.elt;

        if (!targetForm.matches('form[ hx-post ]')) return;

        if (evt.detail.successful) {
            if (evt.detail.status === 201) {
                targetForm.reset();
                showMessage(targetForm, 'success', 'Аккаунт создан! Письмо отправлено.');
            } else {
                showMessage(targetForm, 'info', 'Добро пожаловать.');
            }
        } else {
            showMessage(targetForm, 'error', 'Ошибка сети или сервера.');
        }

        scrollToMessageBox();
    });
}

function showMessage(formEl, type, text) {
    const box = formEl.querySelector('#message-box');
    if (box) {
        box.innerHTML = `<div class="${type}">${text}</div>`;
    }
}

function scrollToMessageBox() {
    const messageBox = document.getElementById('message-box');
    if (messageBox) {
        setTimeout(() => {
            messageBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
    }
}