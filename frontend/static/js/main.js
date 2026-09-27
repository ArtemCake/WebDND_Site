// frontend/static/js/main.js

/**
 * @fileoverview Точка входа фронтенд-приложения WebDND.
 * Инициализирует глобальные модули, UI-компоненты и обработчики событий.
 * Согласно правилу 1.5 Инструкции v9.0, здесь отсутствует inline-JS код,
 * вся логика разнесена по модулям каталога /modules/.
 */

// --- ИМПОРТ МОДУЛЕЙ ---
/**
 * Сервис бросков кубиков (инкапсулирует логику игровых систем).
 * @module modules/dice
 */
import { DiceService } from './modules/dice.js';

/**
 * Глобальная инициализация HTMX и вспомогательных функций UI.
 * @module modules/ui
 */
import { initGlobalUI } from './modules/ui.js';

/**
 * Настройка обработчиков форм авторизации и защиты маршрутов.
 * @module modules/auth
 */
import { setupAuthHandlers, protectPrivateRoutes } from './modules/auth.js';

/**
 * Рендерер игровой карты на базе PixiJS.
 * @module modules/map
 */
import { GameMap } from './modules/map.js';

// --- ИМПОРТ КОНФИГУРАЦИИ И СИСТЕМЫ ---
import { AppConfig } from './config/appConfig.js';
import { Dnd5eSystem } from './modules/systems/Dnd5eSystem.js';
import { ISystem } from './modules/systems/ISystem.js';

// --- ТОЧКА ВХОДА ПРИЛОЖЕНИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('[WEB-DND] Frontend initialized with modular architecture.');

    // ===================================================================
    // БЛОК ИНИЦИАЛИЗАЦИИ АКТИВНОЙ ИГРОВОЙ СИСТЕМЫ
    // Реализация модульной архитектуры для масштабируемости (исправление MAS-009)
    // ===================================================================
    /**
     * Интерфейс активной игровой системы.
     * @type {ISystem}
     */
    let gameSystem;

    try {
        switch (AppConfig.game.activeSystem) {
            case 'dnd5e':
                gameSystem = new Dnd5eSystem();
                break;
            default:
                throw new Error(`Unsupported system: ${AppConfig.game.activeSystem}`);
        }
        console.log(`[SYSTEM] Loaded: ${gameSystem.constructor.name}`);
    } catch (err) {
        console.error('[SYSTEM][FATAL]', err);
        // Fallback к базовой системе во избежание падения всего фронта
        gameSystem = new Dnd5eSystem();
    }
    // ===================================================================

    // 1. Инициализация глобальных настроек UI и библиотек (HTMX)
    /**
     * Инициализирует базовые настройки htmx.config и общие элементы интерфейса.
     * Вызывается первой строкой при загрузке DOM.
     */
    initGlobalUI();

    // ===================================================================
    // БЛОК ГЛОБАЛЬНОЙ ОБРАБОТКИ ОШИБОК СЕТИ (FIX FOR FUNC-005)
    // ===================================================================
    function registerNetworkErrorHandlers() {
        const extractErrorMessage = (xhr) => {
            let msg = 'Неизвестная ошибка сети.';
            try {
                if (xhr.responseText) {
                    const data = JSON.parse(xhr.responseText);
                    return data.error || data.detail || xhr.statusText;
                }
            } catch (_) {}
            return msg;
        };

        document.body.addEventListener('htmx:responseError', function(evt) {
            const errorMsg = extractErrorMessage(evt.detail.xhr);
            console.error(`[NETWORK][HTTP-${evt.detail.xhr.status}] ${errorMsg}`, evt.detail);
            showMessage(evt.detail.requestConfig.elt, 'danger', `Ошибка (${evt.detail.xhr.status}): ${errorMsg}`);
            scrollToMessageBox();
        });

        document.body.addEventListener('htmx:xhr:abort', function(evt) {
            console.warn('[NETWORK][ABORTED] Request was aborted.', evt.detail);
            showMessage(evt.detail.elt, 'danger', 'Соединение прервано. Проверьте сеть.');
            scrollToMessageBox();
        });

        document.body.addEventListener('htmx:timeout', function(evt) {
            console.error('[NETWORK][TIMEOUT] Server did not respond in time.', evt.detail);
            showMessage(evt.detail.elt, 'danger', 'Превышено время ожидания ответа сервера.');
            scrollToMessageBox();
        });

        document.body.addEventListener('htmx:beforeSwap', function(evt) {
            if (evt.detail.targetError && evt.detail.xhr.status >= 400) {
                evt.detail.shouldSwap = false;
                showMessage(evt.detail.elt, 'danger', 'Внутренняя ошибка приложения. Обратитесь к администратору.');
                scrollToMessageBox();
            }
        });
    }

    registerNetworkErrorHandlers();
    // ===================================================================

    // 2. Навешивание обработчиков для форм авторизации (регистрация/вход)
    /**
     * Подключает Htmx-интерсепторы для добавления CSRF-токенов
     * и парсер JSON-ответов от FastAPI.
     */
    setupAuthHandlers();

    /**
     * Проверяет валидность токена перед доступом к закрытым страницам
     * и перенаправляет на login при необходимости.
     */
    protectPrivateRoutes();

    // 3. Инициализация игровой карты (Canvas + PixiJS)
    /**
     * Создает экземпляр рендерера карты только если целевой контейнер существует на странице.
     * Это позволяет использовать main.js на страницах без игрового стола (login/register).
     */
    const canvasRoot = document.getElementById('game-canvas-root');
    if (canvasRoot) {
        const gameMap = new GameMap('game-canvas-root');
        // Использование параметров из конфига вместо магических чисел (CONF-008)
        gameMap.drawHexGrid(
            AppConfig.map.hexSize,
            AppConfig.map.gridCols,
            AppConfig.map.gridRows
        );
    }

    // ===================================================================
    // БЛОК ДЕЛЕГИРОВАНИЯ СОБЫТИЙ ДЛЯ БРОСКОВ КУБИКОВ
    // Полностью вынесено в отдельный поток с поддержкой разных систем (MAS-009)
    // ===================================================================
    document.body.addEventListener('click', (e) => {
        if (e.target.matches('[data-dice-roll]')) {
            e.preventDefault();

            const sides = parseInt(e.target.dataset.sides || '20');
            const modifier = parseInt(e.target.dataset.mod || '0');
            const mode = e.target.dataset.mode || 'normal';
            const quantity = parseInt(e.target.dataset.qty) || 1;

            // Делегирование расчета модулю игровой системы
            const result = gameSystem.rollDice(sides, {
                modifier: modifier,
                mode: mode,
                quantity: quantity
            });

            const resultBox = document.createElement('div');
            resultBox.className = 'dice-result-toast';

            const modeText = (mode === 'advantage') ? ' (Преимущество)' :
                           (mode === 'disadvantage') ? ' (Помеха)' : '';

            resultBox.textContent = `Результат (${sides}${modeText}): ${result.sum} (${result.rolls.join(' + ')}${modifier >= 0 ? ' + ' : ''}${modifier})`;
            document.body.appendChild(resultBox);

            // Длительность берется из единого центра конфигурации
            setTimeout(() => resultBox.remove(), AppConfig.ui.toastDuration);
        }
    });
    // ===================================================================
});