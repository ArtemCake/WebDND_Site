// static/js/modules/menuToggle.js

/**
 * Модуль управления мобильным меню-бургером.
 */

/**
 * Инициализирует логику переключения мобильного меню.
 */
export function initMenuToggle() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    // Проверка наличия элементов на странице (защита от ошибок)
    if (!mobileMenuButton || !mobileMenu) return;

    // Переключение видимости по клику на бургер
    mobileMenuButton.addEventListener('click', () => {
        mobileMenu.classList.toggle('hidden');
    });

    // Закрытие меню при клике на ссылку внутри него
    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.add('hidden');
        });
    });
}