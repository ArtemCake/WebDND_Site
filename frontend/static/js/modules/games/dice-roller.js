// frontend/static/js/modules/dice-roller.js

import { AppConfig } from './../../config/appConfig.js';

export function initDiceRollers(gameSystem) {
	document.body.addEventListener('click', (e) => {
		if (!e.target.matches('[data-dice-roll]')) return;
		e.preventDefault();

		const sides = parseInt(e.target.dataset.sides || '20');
		const modifier = parseInt(e.target.dataset.mod || '0');
		const mode = e.target.dataset.mode || 'normal';
		const quantity = parseInt(e.target.dataset.qty) || 1;

		const result = gameSystem.rollDice(sides, { modifier, mode, quantity });

		const resultBox = document.createElement('div');
		resultBox.className = 'dice-result-toast';

		const modeText = (mode === 'advantage') ? ' (Преимущество)' :
					   (mode === 'disadvantage') ? ' (Помеха)' : '';

		resultBox.textContent = `Результат (${sides}${modeText}): ${result.sum} (${result.rolls.join(' + ')}${modifier >= 0 ? ' + ' : ''}${modifier})`;
		document.body.appendChild(resultBox);

		setTimeout(() => resultBox.remove(), AppConfig.ui.toastDuration);
	});
}