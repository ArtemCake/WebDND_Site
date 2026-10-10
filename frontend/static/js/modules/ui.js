// frontend/static/js/modules/ui.js

/**
 * Инициализирует IntersectionObserver для фиксации навигационной панели.
 */
function initStickyNavigation() {
    const nav = document.getElementById('main-nav');
    if (!nav) return;

    const observer = new IntersectionObserver(
        ([entry]) => {
            nav.classList.toggle('navbar-main--scrolled', entry.intersectionRatio < 1 || entry.boundingClientRect.top < 0);
        },
        { threshold: [1], rootMargin: '0px 0px -1px 0px' }
    );

    observer.observe(nav);
}

export function initPasswordToggles(root = document) {
	const fields = root.querySelectorAll('input[type="password"]:not([data-toggle-bound])');

	fields.forEach((input) => {
		input.setAttribute('data-toggle-bound', 'true');

		const wrapper = document.createElement('div');
		wrapper.className = 'password-field';
		input.parentNode.insertBefore(wrapper, input);
		wrapper.appendChild(input);

		const toggleBtn = document.createElement('button');
		toggleBtn.type = 'button'; // не submit — чтобы Enter в поле не срабатывал на эту кнопку
		toggleBtn.className = 'password-toggle';
		toggleBtn.setAttribute('aria-label', 'Показать пароль');
		toggleBtn.textContent = '👁';

		toggleBtn.addEventListener('click', () => {
			const willShow = input.type === 'password';
			input.type = willShow ? 'text' : 'password';
			toggleBtn.textContent = willShow ? '🙈' : '👁';
			toggleBtn.setAttribute('aria-label', willShow ? 'Скрыть пароль' : 'Показать пароль');
		});

		wrapper.appendChild(toggleBtn);
	});
}

/**
 * Применяет настройки HTMX и запускает фиксатор меню.
 */
export function initGlobalUI() {
    if (window.htmx) {
        htmx.config.scrollIntoViewOnBoost = false;
    }

    initStickyNavigation();
    initPasswordToggles();
    initThemeSwitcher();

    document.body.addEventListener('htmx:afterSwap', () => {
        initThemeSwitcher();
    });

    console.log('[UI] Global UI initialized.');
}

/* --- Блок управления темами --- */
const PRESET_THEMES = ['dark-fantasy', 'light-fantasy', 'fantasy'];

// Фон для каждой пресетной темы — своя пятёрка картинок.
// У кастомной темы фона нет (там цветовой пикер), поэтому её в карте не держим.
const THEME_BACKGROUNDS = {
    'dark-fantasy': [
        '/frontend/static/images/backgrounds/dark_fantasy/fantasy-1.webp',
        '/frontend/static/images/backgrounds/dark_fantasy/fantasy-2.webp',
        '/frontend/static/images/backgrounds/dark_fantasy/fantasy-3.webp',
        '/frontend/static/images/backgrounds/dark_fantasy/fantasy-4.webp',
        '/frontend/static/images/backgrounds/dark_fantasy/fantasy-5.webp',
    ],
    'light-fantasy': [
        '/frontend/static/images/backgrounds/light_fantasy/fantasy-1.webp',
        '/frontend/static/images/backgrounds/light_fantasy/fantasy-2.webp',
        '/frontend/static/images/backgrounds/light_fantasy/fantasy-3.webp',
        '/frontend/static/images/backgrounds/light_fantasy/fantasy-4.webp',
        '/frontend/static/images/backgrounds/light_fantasy/fantasy-5.webp',
    ],
    'fantasy': [
        '/frontend/static/images/backgrounds/general_fantasy/fantasy-1.webp',
        '/frontend/static/images/backgrounds/general_fantasy/fantasy-2.webp',
        '/frontend/static/images/backgrounds/general_fantasy/fantasy-3.webp',
        '/frontend/static/images/backgrounds/general_fantasy/fantasy-4.webp',
        '/frontend/static/images/backgrounds/general_fantasy/fantasy-5.webp',
    ],
};

export function applyTheme(themeName, forceRerollBackground = false) {
     const root = document.documentElement;
     root.classList.remove('theme-dark-fantasy', 'theme-light-fantasy', 'theme-fantasy');
     if (PRESET_THEMES.includes(themeName)) {
         root.classList.add(`theme-${themeName}`);
     }
    applyThemeBackground(themeName, forceRerollBackground);
 }

 function applyThemeBackground(themeName, forceReroll) {
     const body = document.body;
     const list = THEME_BACKGROUNDS[themeName];

     if (!list) {
         // Кастомная тема — без фоновой картинки
         body.style.removeProperty('--bg-image-url');
         body.classList.remove('has-bg-image');
         return;
     }

     const storageKey = `theme-bg-${themeName}`;
     let chosen = forceReroll ? null : sessionStorage.getItem(storageKey);

     if (!chosen || !list.includes(chosen)) {
         chosen = list[Math.floor(Math.random() * list.length)];
         sessionStorage.setItem(storageKey, chosen);
     }

     body.style.setProperty('--bg-image-url', `url('${chosen}')`);
     body.classList.add('has-bg-image');
 }

export function setAccentColor(color) {
    document.documentElement.style.setProperty('--color-bg-page', color);
}

function clearAccentOverride() {
    document.documentElement.style.removeProperty('--color-bg-page');
}

export function loadUserTheme() {
    const savedTheme = localStorage.getItem('user-theme') || 'dark-fantasy';
    const savedAccent = localStorage.getItem('user-accent') || '#ffd700';

    applyTheme(savedTheme);

    const accentPicker = document.getElementById('accent-picker');

    if (savedTheme === 'custom') {
        setAccentColor(savedAccent);
        if (accentPicker) accentPicker.disabled = false;
    } else {
        clearAccentOverride();
        if (accentPicker) accentPicker.disabled = true;
    }

    try {
        document.getElementById('theme-select').value = savedTheme;
        if (accentPicker) accentPicker.value = savedAccent;
    } catch (e) {
        // Элементы формы могут отсутствовать на страницах авторизации
    }
}

function bindThemeControls() {
    const themeSelect = document.getElementById('theme-select');
    const accentPicker = document.getElementById('accent-picker');

    if (themeSelect && !themeSelect.dataset.themeBound) {
        themeSelect.dataset.themeBound = 'true';
        themeSelect.addEventListener('change', (e) => {
            const themeName = e.target.value;
            applyTheme(themeName, true);
            localStorage.setItem('user-theme', themeName);

            if (themeName === 'custom') {
                if (accentPicker) {
                    accentPicker.disabled = false;
                    setAccentColor(accentPicker.value);
                }
            } else {
                clearAccentOverride();
                if (accentPicker) accentPicker.disabled = true;
            }
        });
    }

    if (accentPicker && !accentPicker.dataset.themeBound) {
        accentPicker.dataset.themeBound = 'true';
        accentPicker.addEventListener('input', (e) => {
            if (themeSelect && themeSelect.value === 'custom') {
                setAccentColor(e.target.value);
                localStorage.setItem('user-accent', e.target.value);
            }
        });
    }
}

export function initThemeSwitcher() {
    loadUserTheme();
    bindThemeControls();
}

/**
 * Показывает превью выбранного файла аватара прямо в форме профиля,
 * до отправки на сервер. Вызывается из атрибута onchange в profile.html.
 */
export function previewAvatar(event) {
    const input = event.target;
    const file = input.files && input.files[0];
    if (!file) return;

    const img = input.closest('label')?.querySelector('img');
    if (!img) return;

    const reader = new FileReader();

    reader.onload = (e) => {
        img.src = e.target.result;
    };

    reader.onerror = () => {
        console.error('[UI][AVATAR] Не удалось прочитать файл для превью.', reader.error);
    };

    reader.readAsDataURL(file);
}

window.previewAvatar = previewAvatar;