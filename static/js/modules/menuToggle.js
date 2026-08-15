// static/js/modules/menuToggle.js

/**
 * Модуль управления мобильной боковой панелью (Drawer).
 * Синхронизирует состояние <body> и сайдбара для корректной анимации HTMX/Tailwind.
 */
export function initMenuToggle() {
    const btn = document.getElementById('mobile-menu-button');

    // Ищем именно мобильный Drawer по его ID или специфичному классу
    const menu = document.getElementById('mobile-menu-sidebar');

    if (!btn || !menu) return;

    /**
     * Функция обновления состояния всей страницы.
     */
    const toggleState = () => {
        // Переключаем глобальный класс на body
        document.body.classList.toggle('sidebar-open');

        // Определяем текущее состояние ПОСЛЕ переключения
        const isOpen = document.body.classList.contains('sidebar-open');

        // Обновляем атрибуты доступности (A11y)
        btn.setAttribute('aria-expanded', isOpen.toString());
        menu.setAttribute('aria-hidden', (!isOpen).toString());

        // Блокируем прокрутку основного контента при открытом меню
        document.body.style.overflow = isOpen ? 'hidden' : '';

        // Если закрыли — возвращаем фокус на кнопку для удобства клавиатурной навигации
        if (!isOpen) {
            btn.focus();
        }
    };

    // --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

    // Открытие/закрытие по клику на бургер
    btn.addEventListener('click', (e) => {
        e.preventDefault(); // Предотвращаем случайный переход, если кнопка внутри <a>
        toggleState();
    });

    // Закрытие при клике на ссылку внутри меню
    menu.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]');
        if (link && !event.defaultPrevented) {
            // Даем время HTMX инициировать запрос перед тем, как скрыть UI
            setTimeout(toggleState, 100);
        }
    });

    // Закрытие по нажатию клавиши Escape
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
            toggleState();
        }
    });

    // --- ЗАЩИТА ОТ ДУБЛИРОВАНИЯ ПРИ HTMX ---
    btn.__menuInitialized = true;
    menu.__menuInitialized = true;
}

// Запуск модуля
const runInit = () => {
    // Проверяем, не запущен ли модуль ранее (защита от прямой вставки скрипта в тело)
    const btn = document.getElementById('mobile-menu-button');
    if (btn && !btn.__menuInitialized) {
        initMenuToggle();
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runInit);
} else {
    runInit();
}

// Перезапуск после подгрузки нового контента через HTMX
document.body.addEventListener('htmx:afterOnLoad', runInit);