// frontend/static/js/modules/ui.js

/**
 * Глобальные настройки UI и сторонних библиотек (HTMX)
 */

export function initGlobalUI() {
    // Настройка HTMX: отключаем автопрокрутку к низу чата при каждом сообщении
    if (window.htmx) {
        htmx.config.scrollIntoViewOnBoost = false;
    }

    console.log('[UI] Global UI initialized.');
}