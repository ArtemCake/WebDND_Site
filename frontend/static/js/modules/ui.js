// frontend/static/js/modules/ui.js

import { initPasswordToggles } from './UI/password-toggle.js';
import { initThemeSwitcher } from './UI/theme-switcher.js';

export function initGlobalUI() {
	if (window.htmx) {
		htmx.config.scrollIntoViewOnBoost = false;
	}

	initPasswordToggles();
	initThemeSwitcher();

	document.body.addEventListener('htmx:afterSwap', () => {
		initThemeSwitcher();
	});

	console.log('[UI] Global UI initialized.');
}
