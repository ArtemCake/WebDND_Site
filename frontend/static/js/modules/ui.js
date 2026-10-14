// frontend/static/js/modules/ui.js


export function initPasswordToggles(root = document) {
	const fields = root.querySelectorAll('input[type="password"]:not([data-toggle-bound])');

	fields.forEach((input) => {
		input.setAttribute('data-toggle-bound', 'true');

		const wrapper = document.createElement('div');
		wrapper.className = 'password-field';
		input.parentNode.insertBefore(wrapper, input);
		wrapper.appendChild(input);

		const toggleBtn = document.createElement('button');
		toggleBtn.type = 'button';
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

const PRESET_THEMES = ['dark-fantasy', 'light-fantasy', 'fantasy'];

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

function getReadableTextColors(hexColor) {
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    const isLight = luminance > 0.6;
    return {
        primary: isLight ? '#1a1a1a' : '#e8e8ea',
        secondary: isLight ? '#4b4b4b' : '#c9c9cf',
    };
}

export function setAccentColor(color) {
    const { primary, secondary } = getReadableTextColors(color);
    document.documentElement.style.setProperty('--color-bg-page', color);
    document.documentElement.style.setProperty('--color-text-primary', primary);
    document.documentElement.style.setProperty('--color-text-secondary', secondary);
}

function clearAccentOverride() {
    document.documentElement.style.removeProperty('--color-bg-page');
    document.documentElement.style.removeProperty('--color-text-primary');
    document.documentElement.style.removeProperty('--color-text-secondary');
}

export function loadUserTheme() {
    const serverTheme = document.body.dataset.userTheme || '';
    const savedTheme = serverTheme || localStorage.getItem('user-theme') || 'dark-fantasy';
    const savedAccent = document.body.dataset.userAccent || localStorage.getItem('user-accent') || '#8a5cf6';

    if (serverTheme) {
        localStorage.setItem('user-theme', serverTheme);
        if (document.body.dataset.userAccent) {
            localStorage.setItem('user-accent', document.body.dataset.userAccent);
        }
    }

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

async function persistThemeToServer(themeName, themeColor) {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const isAuthenticated = document.body.dataset.userTheme !== undefined;
    if (!csrfMeta || !isAuthenticated) return;

    try {
        const response = await fetch('/profile/theme', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfMeta.content,
            },
            body: JSON.stringify({ theme: themeName, theme_color: themeColor ?? null }),
        });
        if (!response.ok) {
            console.error('[UI][THEME] save failed', response.status);
        }
    } catch (e) {
        console.error('[UI][THEME] network error', e);
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
            persistThemeToServer(themeName, themeName === 'custom' ? (accentPicker?.value ?? null) : null);

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
                persistThemeToServer('custom', e.target.value);
            }
        });
    }
}

export function initThemeSwitcher() {
    loadUserTheme();
    bindThemeControls();
}

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
        console.error('[UI][AVATAR] read failed', reader.error);
    };

    reader.readAsDataURL(file);
}

window.previewAvatar = previewAvatar;