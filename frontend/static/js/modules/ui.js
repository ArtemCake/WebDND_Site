// frontend/static/js/modules/ui.js

export function initGlobalUI() {
    // ... предыдущий код HTMX ...

    const themeSelect = document.getElementById('theme-select');
    const accentPicker = document.getElementById('accent-picker');

    if (!themeSelect || !accentPicker) return;

    // Загрузка сохраненных настроек при старте
    loadUserTheme();

    // Сохранение темы
    themeSelect.addEventListener('change', (e) => {
        applyTheme(e.target.value);
        localStorage.setItem('user-theme', e.target.value);
    });

    // Сохранение акцентного цвета
    accentPicker.addEventListener('input', (e) => {
        setAccentColor(e.target.value);
        localStorage.setItem('user-accent', e.target.value);
    });
}

function applyTheme(themeName) {
    const root = document.documentElement;
    root.classList.remove('theme-dark-fantasy', 'theme-light', 'theme-high-contrast');
    root.classList.add(`theme-${themeName}`);
}

function setAccentColor(color) {
    const root = document.documentElement;
    root.style.setProperty('--color-text-accent', color);
    root.style.setProperty('--color-border-accent', color);
}

function loadUserTheme() {
    const savedTheme = localStorage.getItem('user-theme') || 'dark-fantasy';
    const savedAccent = localStorage.getItem('user-accent') || '#ffd700';

    applyTheme(savedTheme);
    setAccentColor(savedAccent);

    // Синхронизируем состояние контролов в DOM
    document.getElementById('theme-select').value = savedTheme;
    document.getElementById('accent-picker').value = savedAccent;
}

// Инициализация фиксатора меню остается здесь
initStickyNavigation();
console.log('[UI] Global UI initialized with Theme Manager.');