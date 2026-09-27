// frontend/static/js/modules/systems/ISystem.js

/**
 * @fileoverview Абстрактный интерфейс игровой системы.
 * Все модули конкретных игровых механик (D&D 5e, Pathfinder 2e и др.)
 * обязаны имплементировать этот контракт.
 */

export class ISystem {
    /**
     * Бросок кубика с учетом параметров.
     * @param {number} sides - Количество граней (d4, d6, d20...).
     * @param {object} options - Опции броска.
     * @param {'advantage'|'disadvantage'|'normal'} [options.mode='normal'] - Режим броска.
     * @param {number} [options.modifier=0] - Модификатор характеристики.
     * @param {number} [options.quantity=1] - Количество кубиков.
     * @returns {{sum: number, rolls: number[], modifier: number}}
     */
    rollDice(sides, options = {}) {
        throw new Error('Method "rollDice" must be implemented.');
    }

    /**
     * Расчет значения характеристики (Ability Score) по правилу floor((score-10)/2).
     * @param {number} score - Значение характеристики (от 1 до 30).
     * @returns {number} Модификатор.
     */
    calculateModifier(score) {
        throw new Error('Method "calculateModifier" must be implemented.');
    }
}