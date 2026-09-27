// frontend/static/js/modules/dice.js

/**
 * Сервис обработки игровых бросков кубиков.
 * Изолирован от основного потока приложения согласно правилу "один файл — один функционал".
 */
export class DiceService {

    /**
     * Устанавливает глобальный слушатель кликов для элементов с data-dice-roll.
     * Должен вызываться один раз при инициализации приложения.
     */
    static attachGlobalListener() {
        document.body.addEventListener('click', (e) => {
            if (e.target.matches('[data-dice-roll]')) {
                e.preventDefault();
                this.handleDiceClick(e.target);
            }
        });
    }

    /**
     * Основной метод расчета броска.
     * @param {HTMLElement} button - Элемент кнопки, инициировавшей бросок.
     */
    static handleDiceClick(button) {
        const sides = parseInt(button.dataset.sides || '20'); // d20 по умолчанию
        const modifier = parseInt(button.dataset.mod || '0');

        // Генерация результата
        const rolls = [];
        const numDice = parseInt(button.dataset.qty) || 1;

        for (let i = 0; i < numDice; i++) {
            const roll = Math.floor(Math.random() * sides) + 1;
            rolls.push(roll);
        }

        const sum = rolls.reduce((a, b) => a + b, 0) + modifier;

        // Отображение результата рядом с кнопкой или в консоль
        const resultBox = document.createElement('div');
        resultBox.className = 'dice-result-toast';
        resultBox.textContent = `Результат: ${sum} (${rolls.join(' + ')}${modifier >= 0 ? ' + ' : ''}${modifier})`;
        document.body.appendChild(resultBox);

        setTimeout(() => resultBox.remove(), 5000);
    }
}

// Автоматическая инициализация при подключении модуля
document.addEventListener('DOMContentLoaded', () => {
    DiceService.attachGlobalListener();
});