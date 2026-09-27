// frontend/static/js/modules/systems/Dnd5eSystem.js

import { ISystem } from './ISystem.js';

/**
 * Реализация правил настольной ролевой игры Dungeons & Dragons 5th Edition.
 */
export class Dnd5eSystem extends ISystem {

    /**
     * @inheritdoc
     */
    rollDice(sides, options = {}) {
        const mode = options.mode || 'normal';
        const modifier = options.modifier || 0;
        const quantity = options.quantity || 1;

        let rolls = [];

        // Генерация базовых бросков
        for (let i = 0; i < quantity; i++) {
            if (mode === 'advantage') {
                // Преимущество: бросаем 2кХ, берем высший
                const r1 = Math.floor(Math.random() * sides) + 1;
                const r2 = Math.floor(Math.random() * sides) + 1;
                rolls.push(Math.max(r1, r2));
            } else if (mode === 'disadvantage') {
                // Помеха: бросаем 2кХ, берем низший
                const r1 = Math.floor(Math.random() * sides) + 1;
                const r2 = Math.floor(Math.random() * sides) + 1;
                rolls.push(Math.min(r1, r2));
            } else {
                // Обычный бросок
                rolls.push(Math.floor(Math.random() * sides) + 1);
            }
        }

        const sum = rolls.reduce((a, b) => a + b, 0) + modifier;
        return { sum, rolls, modifier };
    }

    /**
     * @inheritdoc
     * Формула D&D 5e: floor((Score - 10) / 2)
     */
    calculateModifier(score) {
        return Math.floor((score - 10) / 2);
    }

    /**
     * Специфичный расчет Классовой Брони (AC) для ДНД 5е.
     * @param {number} baseAc - Базовый КД (обычно 10).
     * @param {number} dexMod - Модификатор ловкости.
     * @param {number} armorBonus - Бонус от доспеха.
     * @param {number} shieldBonus - Бонус от щита.
     * @returns {number}
     */
    calculateArmorClass(baseAc, dexMod, armorBonus = 0, shieldBonus = 0) {
        return baseAc + dexMod + armorBonus + shieldBonus;
    }
}