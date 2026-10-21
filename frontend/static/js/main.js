// frontend/static/js/main.js


// --- ИМПОРТ МОДУЛЕЙ ---
import { initGlobalUI } from './modules/ui.js';
import { setupAuthHandlers, protectPrivateRoutes } from './modules/auth.js';
import { GameMap } from './modules/map.js';
import { initCookieBanner } from './modules/cookie-banner.js';
import { initDeleteAccountModal } from './modules/delete-account.js';
import { initAdminPanel } from './modules/admin.js';
import './modules/UI/avatar-preview.js';
import { initNetworkErrorHandlers } from './modules/network-error-handler.js';
import { initDiceRollers } from './modules/dice-roller.js';
import { AppConfig } from './config/appConfig.js';
import { Dnd5eSystem } from './modules/systems/Dnd5eSystem.js';
import { initLobby } from './modules/lobby.js';
import { initSessionDice } from './modules/session-dice.js';
import { initMaps } from './modules/maps.js';
import { initMapView } from './modules/map-view.js';
import { initMapDelete } from './modules/map-delete.js';
import { initMapEdit } from './modules/map-edit.js';

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

    // Глобальная обработка сетевых ошибок HTMX
    initNetworkErrorHandlers();

    // 2. Навешивание обработчиков для форм авторизации (регистрация/вход)
    setupAuthHandlers();
    protectPrivateRoutes();
    initLobby();
    initSessionDice();
    initMaps();
    initMapView();
    initMapDelete();
    initMapEdit();

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