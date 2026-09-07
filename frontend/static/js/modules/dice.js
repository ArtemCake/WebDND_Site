// frontend/static/js/modules/dice.js

export class DiceService {
    static roll(sides = 20, modifier = 0, options = {}) {
        const { advantage = null } = options;

        let rolls = [];
        let result;

        if (advantage === 'disadvantage') {
            const r1 = Math.floor(Math.random() * sides) + 1;
            const r2 = Math.floor(Math.random() * sides) + 1;
            rolls = [r1, r2];
            result = Math.min(r1, r2) + modifier;
        } else if (advantage === 'advantage') {
            const r1 = Math.floor(Math.random() * sides) + 1;
            const r2 = Math.floor(Math.random() * sides) + 1;
            rolls = [r1, r2];
            result = Math.max(r1, r2) + modifier;
        } else {
            const r1 = Math.floor(Math.random() * sides) + 1;
            rolls = [r1];
            result = r1 + modifier;
        }

        return { total: result, formula: `${rolls.join(' + ')} ${modifier >= 0 ? '+' : ''}${modifier}`, raw: rolls };
    }
}