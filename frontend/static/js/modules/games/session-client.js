// frontend/static/js/modules/games/session-client.js

export class SessionRefreshError extends Error {
    constructor(status) {
        super(
            status === 401
                ? 'Сессия завершена. Выполните вход снова.'
                : `Не удалось обновить сессию (${status}).`
        );
        this.name = 'SessionRefreshError';
        this.status = status;
    }
}

function responseHeader(response, name) {
    // Поддерживаются и fetch Response, и XMLHttpRequest от HTMX.
    if (response.headers?.get) {
        return response.headers.get(name);
    }

    return response.getResponseHeader?.(name) || null;
}

export function isAuthenticationFailure(response) {
    return (
        response.status === 401 &&
        /^Bearer(?:\s|$)/i.test(
            responseHeader(response, 'WWW-Authenticate') || ''
        )
    );
}

export function createSessionClient({
    fetchImpl = (...args) => fetch(...args),
    origin = window.location.origin,
    getCsrfToken = () =>
        document.querySelector('meta[name="csrf-token"]')?.content || '',
    setCsrfToken = (token) => {
        document.querySelector('meta[name="csrf-token"]')
            ?.setAttribute('content', token);
    }
} = {}) {
    let generation = 0;
    let refreshInFlight = null;

    function localUrl(path) {
        const url = new URL(path, origin);

        if (url.origin !== origin) {
            throw new TypeError(
                'Клиент сессии разрешает только запросы к своему сайту.'
            );
        }

        return url.href;
    }

    function acceptCsrf(response) {
        const token = responseHeader(response, 'X-CSRF-Token');
        if (token) setCsrfToken(token);
        return response;
    }

    function prepareOptions(options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        const headers = new Headers(options.headers);

        // Этот клиент использует cookie-сессию.
        // Старый Bearer не должен перекрывать новую access-cookie.
        headers.delete('Authorization');

        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            const token = getCsrfToken();

            if (token) {
                headers.set('X-CSRF-Token', token);
            } else {
                headers.delete('X-CSRF-Token');
            }
        }

        return {
            ...options,
            method,
            headers,
            credentials: 'include',
            // Не принимаем HTML страницы входа после автоматического
            // редиректа за успешный ответ API.
            redirect: 'error'
        };
    }

    async function send(path, options) {
        const response = await fetchImpl(
            localUrl(path),
            prepareOptions(options)
        );
        return acceptCsrf(response);
    }

    async function refreshSession(expectedGeneration = generation) {
        // Другой запрос уже обновил cookie после отправки исходного.
        if (expectedGeneration !== generation) return;

        if (!refreshInFlight) {
            refreshInFlight = (async () => {
                const response = await send('/auth/refresh', {
                    method: 'POST'
                });

                if (!response.ok) {
                    throw new SessionRefreshError(response.status);
                }

                // JWT из тела ответа не читаем:
                // новые HttpOnly-cookie принимает браузер.
                generation += 1;
            })();
        }

        const pending = refreshInFlight;

        try {
            await pending;
        } finally {
            if (refreshInFlight === pending) {
                refreshInFlight = null;
            }
        }
    }

    async function recover(
        response,
        path,
        options = {},
        expectedGeneration = generation
    ) {
        if (!isAuthenticationFailure(response)) {
            return response;
        }

        await refreshSession(expectedGeneration);

        // Только один повтор. Повторный 401 возвращается вызывающему коду,
        // а не запускает ещё один refresh.
        return send(path, options);
    }

    async function sessionFetch(path, options = {}) {
        const expectedGeneration = generation;
        const response = await send(path, options);

        return recover(
            response,
            path,
            options,
            expectedGeneration
        );
    }

    return {
        sessionFetch,
        recover,
        refreshSession,
        getGeneration: () => generation
    };
}

export const sessionClient = createSessionClient({
    origin: globalThis.location?.origin || 'http://localhost'
});