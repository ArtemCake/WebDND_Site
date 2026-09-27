// frontend/static/js/main.js

// --- ИМПОРТ МОДУЛЕЙ (согласно ТЗ, стр. 62) ---
import { DiceService } from './modules/dice.js';
import { initGlobalUI } from './modules/ui.js';
import { setupAuthHandlers, protectPrivateRoutes } from './modules/auth.js';
import { GameMap } from './modules/map.js';

// --- ТОЧКА ВХОДА ПРИЛОЖЕНИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('[WEB-DND] Frontend initialized with modular architecture.');

    // 1. Инициализация глобальных настроек UI и библиотек (HTMX)
    initGlobalUI();

    // ===================================================================
    // БЛОК ГЛОБАЛЬНОЙ ОБРАБОТКИ ОШИБОК СЕТИ (FIX FOR ERROR TABLE)
    // ===================================================================

    /**
     * Универсальный парсер текста ошибки из ответа сервера.
     */
    function extractErrorMessage(xhr) {
        let msg = 'Неизвестная ошибка сети.';
        try {
            if (xhr.responseText) {
                const data = JSON.parse(xhr.responseText);
                if (data.error) return data.error;
                if (data.detail) return data.detail;
            }
        } catch (e) {
            // Если это не JSON (например, HTML заглушка 500)
            return xhr.statusText || 'Сервер вернул некорректный ответ.';
        }
        return msg;
    }

    // Обработка HTTP-ошибок (4xx, 5xx), которые возвращает FastAPI
    document.body.addEventListener('htmx:responseError', function(evt) {
        const errorMsg = extractErrorMessage(evt.detail.xhr);

        // Логируем полную ошибку в консоль разработчика
        console.error(`[NETWORK][HTTP-${evt.detail.xhr.status}] ${errorMsg}`, evt.detail);

        // Показываем пользователю дружелюбное сообщение
        showMessage(evt.detail.requestConfig.elt, 'danger',
            `Ошибка (${evt.detail.xhr.status}): ${errorMsg}`);
        scrollToMessageBox();
    });

    // Обработка критических сетевых сбоев (обрыв связи, DNS failure)
    document.body.addEventListener('htmx:xhr:abort', function(evt) {
        console.warn('[NETWORK][ABORTED] Request was aborted by user or network.', evt.detail);
        showMessage(evt.detail.elt, 'danger', 'Соединение прервано. Проверьте сеть.');
        scrollToMessageBox();
    });

    document.body.addEventListener('htmx:timeout', function(evt) {
        console.error('[NETWORK][TIMEOUT] Server did not respond in time.', evt.detail);
        showMessage(evt.detail.elt, 'danger', 'Превышено время ожидания ответа сервера.');
        scrollToMessageBox();
    });

    // Ловим случаи, когда htmx хочет вставить ошибочный HTML вместо JSON
    document.body.addEventListener('htmx:beforeSwap', function(evt) {
        if (evt.detail.targetError && evt.detail.xhr.status >= 400) {
            // Предотвращаем вставку сырого HTML страницы 500 в интерфейс
            evt.detail.shouldSwap = false;
            showMessage(evt.detail.elt, 'danger', 'Внутренняя ошибка приложения. Обратитесь к администратору.');
            scrollToMessageBox();
        }
    });
    // ===================================================================

    // 2. Навешивание обработчиков для форм авторизации (регистрация/вход)
    setupAuthHandlers();
    protectPrivateRoutes();

    // 3. Инициализация игровой карты (Canvas + PixiJS)
    const canvasRoot = document.getElementById('game-canvas-root');
    if (canvasRoot) {
        const gameMap = new GameMap('game-canvas-root');
        gameMap.drawHexGrid(64, 20, 20);
    }

    // 4. Делегирование событий для бросков кубиков (перенесено в dice.js)
    DiceService();
});