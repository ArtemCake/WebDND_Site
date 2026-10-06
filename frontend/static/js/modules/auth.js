// frontend/static/js/modules/auth.js

/**
 * Отображение сообщения пользователю над формой.
 * @param {HTMLElement} formEl - Элемент формы (для контекста).
 * @param {'success'|'danger'} type - Тип сообщения.
 * @param {string} text - Текст сообщения.
 * @param {string|null} targetSelector - Явный CSS-селектор контейнера (hx-target формы), если есть.
 */
export function showMessage(formEl, type, text, targetSelector = null) {
    // Если у формы задан свой hx-target (как на странице профиля,
    // где смена пароля и обновление данных выводятся в разные блоки) —
    // используем именно его. Иначе — общий #message-box (страницы логина/регистрации).
    let box = null;

    if (targetSelector) {
        box = document.querySelector(targetSelector);
    }

    if (!box) {
        box = document.getElementById('message-box');
    }

    if (box) {
        box.innerHTML = `<div class="alert alert-${type}" role="alert">${text}</div>`;
    }
}

/**
 * Плавная прокрутка к сообщению об ошибке/успехе.
 */
export function scrollToMessageBox(targetSelector = null) {
    const messageBox = targetSelector
        ? document.querySelector(targetSelector)
        : document.getElementById('message-box');

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
 * Тихое обновление пары токенов через /auth/refresh при истёкшем access.
 * При успехе повторяет исходный HTMX-запрос; при неудаче — уводит на /login.
 * @param {object} requestConfig - evt.detail.requestConfig исходного запроса.
 * @param {HTMLElement} targetForm - элемент, инициировавший исходный запрос.
 */
async function attemptTokenRefresh(requestConfig, targetForm) {
    try {
        const resp = await fetch('/auth/refresh', {
            method: 'POST',
            credentials: 'include'
        });

        if (!resp.ok) {
            throw new Error('refresh_failed');
        }

        const data = await resp.json();
        if (data.access_token) {
            localStorage.setItem('accessToken', data.access_token);
        }
        if (data.refresh_token) {
            localStorage.setItem('refreshToken', data.refresh_token);
        }

        // Повторяем исходный запрос тем же методом и путём, что и упавший
        htmx.ajax(requestConfig.verb.toUpperCase(), requestConfig.path, {
            source: targetForm,
            target: targetForm
        });

    } catch (e) {
        console.warn('[AUTH] Token refresh failed, redirecting to login.', e);
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
    }
}

/**
 * Глобальная настройка обработчиков форм авторизации.
 * Фикс безопасности: Добавлен интерсептор для отправки CSRF-токена.
 * Фикс UX: /profile/* запросы разбираются как JSON, а не вставляются сырым текстом.
 * Фикс logout: выход больше не проваливается в ветку логина (она ждёт access_token),
 * а сразу чистит локальные токены и уводит на /login.
 * Фикс сессии: истёкший access на /profile/* теперь тихо обновляется через /auth/refresh
 * перед показом ошибки пользователю.
 */
export function setupAuthHandlers() {

    // === БЛОК CSRF ЗАЩИТЫ ===
    // Автоматически добавляем заголовок X-CSRF-Token во все запросы модификации данных
    document.body.addEventListener('htmx:configRequest', (event) => {
        if (['post', 'put', 'patch', 'delete'].includes(event.detail.verb.toLowerCase())) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            if (csrfToken) {
                event.detail.headers['X-CSRF-Token'] = csrfToken;
            }
        }
    });

    // === БЛОК ОБРАБОТКИ ОТВЕТОВ СЕРВЕРА ===
    document.body.addEventListener('htmx:beforeOnLoad', function (evt) {
        const path = evt.detail.requestConfig?.path;
        const isAuthPath = path && path.startsWith('/auth/');
        const isProfilePath = path && path.startsWith('/profile/');
        const isLogoutPath = path === '/auth/logout';

        if (!isAuthPath && !isProfilePath) return;

        evt.preventDefault();

        const xhr = evt.detail.xhr;

        // === Ручная обработка HX-Redirect ===
        // Раз мы сами глушим стандартную обработку HTMX через preventDefault,
        // заголовок HX-Redirect он больше не увидит — читаем его сами.
        const hxRedirect = xhr.getResponseHeader('HX-Redirect');
        if (hxRedirect) {
            if (isLogoutPath) {
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
            }
            window.location.href = hxRedirect;
            return;
        }

        const targetForm = evt.detail.requestConfig.elt;
        const status = xhr.status;

        // Запасной вариант для logout, если по какой-то причине заголовка не было
        if (isLogoutPath) {
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            window.location.href = '/login';
            return;
        }

        let data = {};
        try {
            if (xhr.responseText) {
                data = JSON.parse(xhr.responseText);
            }
        } catch (e) {
            data = { error: 'Неизвестный формат ответа сервера' };
        }

        // === Истёкший access-токен на защищённой профильной форме ===
        // Access теперь живёт недолго, поэтому 401 здесь — не всегда "выйди и зайди заново":
        // сначала пробуем тихо обновить пару токенов через refresh_token.
        if (isProfilePath && status === 401) {
            attemptTokenRefresh(evt.detail.requestConfig, targetForm);
            return;
        }

        // === Простые профильные формы (смена пароля, обновление профиля) ===
        if (isProfilePath) {
            const isError = status >= 400;
            const hxTarget = targetForm?.getAttribute('hx-target') || null;
            const text = isError
                ? (data.detail || data.error || `Ошибка сервера (${status})`)
                : (data.message || 'Изменения успешно сохранены.');

            showMessage(targetForm, isError ? 'danger' : 'success', text, hxTarget);
            scrollToMessageBox(hxTarget);

            if (!isError && data.redirect_url) {
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 1200);
            }
            return;
        }

        // === Существующая логика для /auth/* (логин, регистрация) ===
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

			case 401:
			    if (data.action === 'verify_email') {
			        messageText = data.error || 'Необходимо подтвердить адрес электронной почты.';
			        document.getElementById('verify-prompt')?.classList.add('active');
			    } else if (data.action === 'account_not_found') {
			        messageText = data.error || 'Аккаунт не найден.';
			        document.getElementById('register-prompt')?.classList.add('active');
			    } else {
			        let rawDetail = data.detail || '';
			        const sanitizedDetail = rawDetail.replace(
			            /[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+/g,
			            '[токен скрыт]'
			        );
			        messageText = data.error || sanitizedDetail || 'Ошибка входа.';
			    }
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