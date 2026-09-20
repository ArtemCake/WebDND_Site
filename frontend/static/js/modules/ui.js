// frontend/static/js/modules/ui.js

/**
 * Инициализирует IntersectionObserver для фиксации навигационной панели.
 * Функция вынесена на верхний уровень модуля для доступности при импорте.
 */
function initStickyNavigation() {
    const nav = document.getElementById('main-nav');

    if (!nav) return;

    // Используем rootMargin, чтобы меню "прилипало" чуть раньше визуальной границы,
    // предотвращая скачок контента.
    const observer = new IntersectionObserver(
        ([entry]) => {
            nav.classList.toggle('--scrolled', entry.intersectionRatio < 1 || entry.boundingClientRect.top < 0);
        },
        { threshold: [1], rootMargin: '0px 0px -1px 0px' }
    );

    observer.observe(nav);
}

/**
 * Применяет настройки HTMX и запускает фиксатор меню.
 */
export function initGlobalUI() {
    // Настройка HTMX: отключаем автопрокрутку к низу чата при каждом сообщении
    if (window.htmx) {
        htmx.config.scrollIntoViewOnBoost = false;
    }

    // Запуск наблюдателя за шапкой сайта
    initStickyNavigation();

    console.log('[UI] Global UI initialized.');
}

/* --- Блок управления темами (из предыдущего задания) --- */
export function applyTheme(themeName) {
    const root = document.documentElement;
    root.classList.remove('theme-dark-fantasy', 'theme-light', 'theme-high-contrast');
    root.classList.add(`theme-${themeName}`);
}

export function setAccentColor(color) {
    const root = document.documentElement;
    root.style.setProperty('--color-text-accent', color);
    root.style.setProperty('--color-border-accent', color);
}

export function loadUserTheme() {
    const savedTheme = localStorage.getItem('user-theme') || 'dark-fantasy';
    const savedAccent = localStorage.getItem('user-accent') || '#ffd700';

    applyTheme(savedTheme);
    setAccentColor(savedAccent);

    try {
        document.getElementById('theme-select').value = savedTheme;
        document.getElementById('accent-picker').value = savedAccent;
    } catch (e) {
        // Элементы формы могут отсутствовать на страницах авторизации
    }
}