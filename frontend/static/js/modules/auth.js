// frontend/static/js/modules/auth.js

/**
 * Отображение сообщения пользователю над формой.
 * @param {HTMLElement} formEl - Элемент формы (для контекста).
 * @param {'success'|'danger'} type - Тип сообщения.
 * @param {string} text - Текст сообщения.
 */
export function showMessage(formEl, type, text) {
    // Ищем общий контейнер страницы (согласно ТЗ он вынесен отдельно)
    const box = document.getElementById('message-box');
    if (box) {
        // Используем .innerHTML с осторожностью, так как текст контролируется нами,
        // либо можно использовать textContent + классы Bootstrap.
        box.innerHTML = `<div class="alert alert-${type}" role="alert">${text}</div>`;
    }
}

/**
 * Плавная прокрутка к сообщению об ошибке/успехе.
 */
export function scrollToMessageBox() {
    const messageBox = document.getElementById('message-box');
    if (messageBox) {
        setTimeout(() => {
            messageBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
    }
}

/**
 * Проверяет валидность Access Token без обращения к серверу.
 * Возвращает true, если токен существует и не истек.
 */
export function checkAuthValidity() {
    const accessToken = localStorage.getItem('accessToken');
    if (!accessToken) return false;

    try {
        const payloadB64 = accessToken.split('.')[1];
        const decoded = JSON.parse(atob(payloadB64));

        // Проверяем назначение токена (если оно есть)
        if (decoded.purpose && decoded.purpose !== 'access') {
            console.warn('[AUTH] Invalid token purpose in client storage.');
            return false;
        }

        // Проверка срока действия (exp в секундах)
        const now = Math.floor(Date.now() / 1000);
        if (decoded.exp && decoded.exp < now) {
            console.warn('[AUTH] Access Token expired on client side.');
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            return false;
        }
        return true;
    } catch (e) {
        console.error('[AUTH] Failed to parse stored token:', e);
        localStorage.removeItem('accessToken');
        return false;
    }
}

/**
 * Глобальная настройка обработчиков форм авторизации.
 * Фикс безопасности: Добавлен интерсептор для отправки CSRF-токена.
 */
export function setupAuthHandlers() {

    // === БЛОК CSRF ЗАЩИТЫ ===
    // Автоматически добавляем заголовок X-CSRF-Token во все запросы модификации данных
    document.body.addEventListener('htmx:configRequest', (event) => {
        if (['post', 'put', 'delete'].includes(event.detail.method.toLowerCase())) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            if (csrfToken) {
                event.detail.headers['X-CSRF-Token'] = csrfToken;
            }
        }
    });

    // === БЛОК ОБРАБОТКИ ОТВЕТОВ СЕРВЕРА ===
    document.body.addEventListener('htmx:beforeOnLoad', function (evt) {
        const path = evt.detail.requestConfig?.path;
        if (!path || !path.startsWith('/auth/')) return;

        // Блокируем стандартную вставку HTML от HTMX, чтобы обработать JSON вручную
        evt.preventDefault();

        const xhr = evt.detail.xhr;
        const targetForm = evt.detail.requestConfig.elt;
        const status = xhr.status;

        let data = {};
        try {
            if (xhr.responseText) {
                data = JSON.parse(xhr.responseText);
            }
        } catch (e) {
            data = { error: 'Неизвестный формат ответа сервера' };
        }

        // Скрываем вспомогательные подсказки
        document.getElementById('register-prompt')?.classList.remove('active');
        document.getElementById('verify-prompt')?.classList.remove('active');

        let messageText = '';
        let isError = true;

        switch (status) {
            case 201: // Регистрация успешна
                targetForm.reset();
                messageText = 'Аккаунт создан! Проверьте почту.';
                isError = false;
                break;

            case 200: // Вход успешен (но нужно проверить наличие токена)
                if (data.access_token) {
                    // Сохраняем токены локально для JS-доступа (проверка exp)
                    localStorage.setItem('accessToken', data.access_token);
                    localStorage.setItem('refreshToken', data.refresh_token);

                    showMessage(targetForm, 'success', 'Добро пожаловать!');

                    // Принудительный редирект после успешной авторизации
                    setTimeout(() => {
                        window.location.href = '/profile';
                    }, 300);
                    return; // Прерываем выполнение хэндлера

                } else {
                    messageText = data.error || 'Сервер вернул ответ без токена. Попробуйте снова.';
                }
                break;

            case 403: // Не подтвержден email
                messageText = 'Необходимо подтвердить адрес электронной почты.';
                document.getElementById('verify-prompt')?.classList.add('active');
                break;

            case 404: // Аккаунт не найден
                messageText = 'Аккаунт не найден.';
                document.getElementById('register-prompt')?.classList.add('active');
                break;

            case 401: // Неверный пароль
                // Маскировка любых случайно попавших в ошибку токенов (защита от утечки)
                let rawDetail = data.detail || '';
                const sanitizedDetail = rawDetail.replace(
                    /[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+/g,
                    '[токен скрыт]'
                );
                messageText = data.error || sanitizedDetail || 'Ошибка входа.';
                break;

            default:
                messageText = data.error || data.detail || `Ошибка сервера (${status})`;
        }

        showMessage(targetForm, isError ? 'danger' : 'success', messageText);
        scrollToMessageBox();
    });
}

/**
 * Инициализация защиты закрытых маршрутов.
 * Должна вызываться ДО инициализации UI компонентов.
 */
export function protectPrivateRoutes() {
    // Список путей, требующих авторизации
    const protectedPaths = ['/dashboard', '/profile', '/game'];

    if (protectedPaths.includes(window.location.pathname)) {
        if (!checkAuthValidity()) {
            // Мягкий редирект вместо жесткой ошибки браузера
            window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
        }
    }
}