// frontend/static/js/main.js

// --- ИМПОРТ МОДУЛЕЙ (согласно ТЗ, стр. 62) ---
// Блок "Ядро" и "Механики"
import { DiceService } from './modules/dice.js';
import { initGlobalUI } from './modules/ui.js';
import { setupAuthHandlers } from './modules/auth.js';

// Блок "Геймплей" (Карты)
import { GameMap } from './modules/map.js';

// --- ТОЧКА ВХОДА ПРИЛОЖЕНИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('[WEB-DND] Frontend initialized with modular architecture.');

    // 1. Инициализация глобальных настроек UI и библиотек (HTMX)
    initGlobalUI();

    // 2. Навешивание обработчиков для форм авторизации (регистрация/вход)
    setupAuthHandlers();

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

    // 4. Делегирование событий для бросков кубиков (интерактивность без перезагрузки)
    // Находит кнопки с атрибутом data-dice-roll внутри всей страницы
    document.body.addEventListener('click', (e) => {
        if (e.target.matches('[data-dice-roll]')) {
            e.preventDefault();

            const sides = parseInt(e.target.dataset.sides || '20'); // d20 по умолчанию
            const modifier = parseInt(e.target.dataset.mod || '0');

            // Генерация результата
            const rolls = [];
            const numDice = parseInt(e.target.dataset.qty) || 1;

            for (let i = 0; i < numDice; i++) {
                const roll = Math.floor(Math.random() * sides) + 1;
                rolls.push(roll);
            }

            const sum = rolls.reduce((a, b) => a + b, 0) + modifier;

            // Отображение результата рядом с кнопкой или в консоль
            alert(`Результат: ${sum} (${rolls.join(' + ')}${modifier >= 0 ? ' + ' : ''}${modifier})`);
        }
    });
});