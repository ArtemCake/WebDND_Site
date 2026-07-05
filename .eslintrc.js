// .eslintrc.js

module.exports = {
	"env": {
		"browser": true,
		"es2021": true
	},
	"extends": [
		"airbnb-base", // Используем строгий стиль Airbnb
		"plugin:prettier/recommended" // Интегрируем Prettier для форматирования
	],
	"parserOptions": {
		"ecmaVersion": 12,
		"sourceType": "module"
	},
	"plugins": [
		"prettier" // Подключаем плагин Prettier
	],
	"rules": {
		// Делаем правила Prettier обязательными (ошибками)
		"prettier/prettier": "error",

		// Опционально: правило для точки с запятой.
		// Выбери одно из двух:
		// 1. Если хочешь точки с запятой:
		"semi": ["error", "always"],
		// 2. Если НЕ хочешь точки с запятой (современный стиль):
		// "semi": ["error", "never"]
	}
};