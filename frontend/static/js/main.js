// frontend/static/js/main.js

/**
 * @fileoverview Точка входа фронтенд-приложения WorldLoom.
 * Инициализирует глобальные модули, UI-компоненты и обработчики событий.
 * Согласно правилу 1.5 Инструкции v9.0, здесь отсутствует inline-JS код,
 * вся логика разнесена по модулям каталога /modules/.
 */

// --- ИМПОРТ МОДУЛЕЙ ---
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

/**
 * Баннер-уведомление об использовании cookie.
 * @module modules/cookie-banner
 */
import { initCookieBanner } from './modules/cookie-banner.js';

/**
 * Модальное окно удаления аккаунта (страница профиля).
 * @module modules/delete-account
 */
import { initDeleteAccountModal } from './modules/delete-account.js';
import { initAdminPanel } from './modules/admin.js';
import './modules/UI/avatar-preview.js';

/**
 * Глобальная обработка сетевых ошибок HTMX (вынесено из main.js).
 * @module modules/network-error-handler
 */
import { initNetworkErrorHandlers } from './modules/network-error-handler.js';

/**
 * Делегирование кликов для бросков кубиков активной игровой системы (вынесено из main.js).
 * @module modules/dice-roller
 */
import { initDiceRollers } from './modules/dice-roller.js';

// --- ИМПОРТ КОНФИГУРАЦИИ И СИСТЕМЫ ---
import { AppConfig } from './config/appConfig.js';
import { Dnd5eSystem } from './modules/systems/Dnd5eSystem.js';
import { initMfaSetup } from './modules/mfa-setup.js';

// --- ТОЧКА ВХОДА ПРИЛОЖЕНИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('[WEB-DND] Frontend initialized with modular architecture.');

    // ===================================================================
    // БЛОК ИНИЦИАЛИЗАЦИИ АКТИВНОЙ ИГРОВОЙ СИСТЕМЫ (исправление MAS-009)
    // ===================================================================
    /**
     * Интерфейс активной игровой системы.
     * @type {import('./modules/systems/ISystem.js').ISystem}
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
        gameSystem = new Dnd5eSystem();
    }
    // ===================================================================

    // 1. Инициализация глобальных настроек UI и библиотек (HTMX)
    initGlobalUI();
    // Уведомление об использовании cookie
    initCookieBanner();
    // Модалка удаления аккаунта (страница профиля)
    initDeleteAccountModal();
    initAdminPanel();
    initMfaSetup();

    // Глобальная обработка сетевых ошибок HTMX
    initNetworkErrorHandlers();

    // 2. Навешивание обработчиков для форм авторизации (регистрация/вход)
    setupAuthHandlers();
    protectPrivateRoutes();

    // 3. Инициализация игровой карты (Canvas + PixiJS)
    const canvasRoot = document.getElementById('game-canvas-root');
    if (canvasRoot) {
        const gameMap = new GameMap('game-canvas-root');
        gameMap.drawHexGrid(
            AppConfig.map.hexSize,
            AppConfig.map.gridCols,
            AppConfig.map.gridRows
        );
    }

    // Делегирование кликов для бросков кубиков активной игровой системы
    initDiceRollers(gameSystem);
});