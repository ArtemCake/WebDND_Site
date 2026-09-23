// frontend/static/js/modules/auth.js

export function showMessage(formEl, type, text) {
    const box = formEl.querySelector('#message-box');
    if (box) {
        // Очистка старых классов Bootstrap alert-* перед добавлением новых
        box.innerHTML = `<div class="alert alert-${type}" role="alert">${text}</div>`;
    }
}

export function scrollToMessageBox() {
    const messageBox = document.getElementById('message-box');
    if (messageBox) {
        setTimeout(() => {
            messageBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
    }
}

export function setupAuthHandlers() {
    // Используем специфичный селектор вместо body, чтобы не ловить чужие запросы
    document.body.addEventListener('htmx:afterOnLoad', function (evt) {

        // Проверяем, был ли это POST-запрос к auth API
        const isAuthReq = evt.detail.pathInfo.startsWith('/auth/');
        if (!isAuthReq) return;

        const targetForm = evt.detail.requestConfig.elt;

        // Скрываем все вспомогательные блоки при любом ответе сервера
        document.getElementById('register-prompt')?.classList.remove('active'); // используем toggle/classlist
        document.getElementById('verify-prompt')?.classList.remove('active');

        let messageText = "";
        let isError = true;

        if (evt.detail.successful) {
            if (evt.detail.status === 201) {
                targetForm.reset();
                messageText = 'Аккаунт создан! Письмо отправлено.';

            } else if (evt.detail.status === 200) {
                // *** ЛОГИКА ВХОДА ***
                messageText = 'Добро пожаловать!';
                isError = false;

                // Сохранение токенов
                const data = JSON.parse(evt.detail.xhr.responseText);
                localStorage.setItem('accessToken', data.access_token);
                localStorage.setItem('refreshToken', data.refresh_token);

                // Перезагрузка страницы меню через htmx.trigger
                // Ждем чуть-чуть, чтобы анимация успева запуститься
                setTimeout(() => {
                    htmx.trigger(document.body, 'loadPage');
                }, 300);

                // Выходим досрочно, так как страница перезагрузится
                return;

            } else if (evt.detail.status === 403) {
                messageText = 'Необходимо подтвердить адрес электронной почты.';
                document.getElementById('verify-prompt')?.classList.add('active');
            }
        } else {
            // Обработка ошибок HTTP статуса
            const data = JSON.parse(evt.detail.xhr.responseText);

            if (evt.detail.status === 404) {
                messageText = 'Аккаунт не найден.';
                document.getElementById('register-prompt')?.classList.add('active');
            } else if (evt.detail.status === 401) {
                // Приоритет у поля error, а detail используем только как fallback после очистки
                let rawDetail = data.detail || '';
                // Удаляем всё, что похоже на JWT (длинные строки из букв, цифр, тире и подчеркиваний)
                const sanitizedDetail = rawDetail.replace(/[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+/g, '[токен скрыт]');
                messageText = data.error || sanitizedDetail || 'Неверный пароль.';
            } else {
                messageText = data.error || 'Ошибка сети или сервера.';
            }
        }

        // Отрисовка блока сообщений
        showMessage(targetForm, isError ? 'danger' : 'success', messageText);
        scrollToMessageBox();
    });
}