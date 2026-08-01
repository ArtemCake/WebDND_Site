// static/js/main.js

// Импортируем все необходимые модули
import { initPasswordToggle } from './modules/passwordToggle.js';
import CookieBanner from './modules/cookieBanner.js';
import { initMenuToggle } from './modules/menuToggle.js';

// --- ОСНОВНАЯ ЛОГИКА: Запускается 1 раз при загрузке страницы ---
document.addEventListener('DOMContentLoaded', function () {

	// --- 2. Инициализация: Переключение пароля (Глазик) ---
	const toggleButton = document.querySelector('.password-toggle');
	const passwordField = document.querySelector('#password');
	if (toggleButton && passwordField) {
		initPasswordToggle(toggleButton, passwordField);
	}

	new CookieBanner();
	 initMenuToggle();

});