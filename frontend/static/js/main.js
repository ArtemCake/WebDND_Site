// frontend/static/js/main.js

// --- ИМПОРТ МОДУЛЕЙ (согласно ТЗ, стр. 62) ---
// Блок "Ядро" и "Механики"
import { DiceService } from './modules/dice.js';
import { initGlobalUI } from './modules/ui.js';
import { setupAuthHandlers, protectPrivateRoutes } from './modules/auth.js';

// Блок "Геймплей" (Карты)
import { GameMap } from './modules/map.js';

// --- ТОЧКА ВХОДА ПРИЛОЖЕНИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('[WEB-DND] Frontend initialized with modular architecture.');

    // 1. Инициализация глобальных настроек UI и библиотек (HTMX)
    initGlobalUI();

    // 2. Навешивание обработчиков для форм авторизации (регистрация/вход)
    setupAuthHandlers();
    protectPrivateRoutes();

    // 3. Инициализация игровой карты (Canvas + PixiJS)
    // Выполняется только если на странице присутствует корневой элемент #game-canvas-root
    const canvasRoot = document.getElementById('game-canvas-root');
    if (canvasRoot) {
        const gameMap = new GameMap('game-canvas-root');

        // Пример отрисовки сетки (в будущем заменится на загрузку данных из БД)
        gameMap.drawHexGrid(64, 20, 20);

        // [ДЛЯ РАЗРАБОТЧИКА] Пример сокета для динамического освещения
        // socket.on('reveal_hex', (data) => {
        //     gameMap.revealCircle(data.x, data.y, data.radius);
        // });
    }

    // 4. Делегирование событий для бросков кубиков перенесено в dice.js
    // Инициализация сервиса (если требуется привязка к DOM при старте)
     DiceService.init();
});