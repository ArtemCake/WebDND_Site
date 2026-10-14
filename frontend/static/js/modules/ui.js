// frontend/static/js/modules/ui.js

import { initPasswordToggles } from './UI/password-toggle.js';
import { initThemeSwitcher } from './UI/theme-switcher.js';
import { initStickyNavigation } from './UI/sticky-navigation.js';

export function initGlobalUI() {
	if (window.htmx) {
		htmx.config.scrollIntoViewOnBoost = false;
	}

	initPasswordToggles();
    initThemeSwitcher();
    initStickyNavigation();

	document.body.addEventListener('htmx:afterSwap', () => {
		initThemeSwitcher();
	});

	console.log('[UI] Global UI initialized.');
}
