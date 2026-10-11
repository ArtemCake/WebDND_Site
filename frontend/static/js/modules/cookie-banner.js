// frontend/static/js/modules/cookie-banner.js

const STORAGE_KEY = 'cookie-notice-dismissed';

export function initCookieBanner() {
    const banner = document.getElementById('cookie-banner');
    if (!banner) return;

    if (!localStorage.getItem(STORAGE_KEY)) {
        banner.classList.remove('hidden');
    }

    const acceptBtn = document.getElementById('cookie-banner-accept');
    acceptBtn?.addEventListener('click', () => {
        localStorage.setItem(STORAGE_KEY, '1');
        banner.classList.add('hidden');
    });
}