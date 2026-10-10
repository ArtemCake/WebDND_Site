// frontend/static/js/theme-init.js

// Выставляет класс темы на <html> до основной инициализации main.min.js.
// Подключается как обычный синхронный <script> в <head>, без type="module",
// чтобы выполниться сразу при парсинге, не дожидаясь загрузки модулей.
(function () {
	var theme = localStorage.getItem('user-theme') || 'dark-fantasy';
	if (theme !== 'custom') {
		document.documentElement.classList.add('theme-' + theme);
	}
})();
