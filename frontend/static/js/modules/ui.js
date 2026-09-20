// frontend/static/js/modules/ui.js

function initStickyNavigation() {
    const nav = document.getElementById('main-nav');

    // Проверка наличия элемента на странице (защита от ошибок в шаблонах)
    if (!nav) return;

    // Использование IntersectionObserver вместо события 'scroll'
    // для предотвращения падения производительности при работе с тяжелыми картами VTT.
    const observer = new IntersectionObserver(
        ([entry]) => {
            // Если элемент скрыт менее чем на 100%, значит, страница прокручена
            nav.classList.toggle('--scrolled', entry.intersectionRatio < 1);
        },
        { threshold: [1] } // Срабатывает только когда видна вся область или не видна вовсе
    );

    // Начинаем наблюдение за верхней границей навбара
    observer.observe(nav);
}

export function initGlobalUI() {
    // Настройка HTMX: отключаем автопрокрутку к низу чата при каждом сообщении,
    // чтобы не сбивать позицию игрока при чтении истории.
    if (window.htmx) {
        htmx.config.scrollIntoViewOnBoost = false;
    }

    // Инициализация фиксатора меню сразу после готовности скриптов
    initStickyNavigation();

    console.log('[UI] Global UI initialized. Sticky navigation active.');
}