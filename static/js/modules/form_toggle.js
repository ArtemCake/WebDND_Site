// static/js/modules/form_toggle.js

/**
 * Модуль управления видимостью блоков внутри форм на основе чекбоксов.
 * Используется, например, для скрытия JSON-полей Homebrew правил.
 */
export function initFormToggles() {
    // Используем делегирование на уровне документа, чтобы не зависеть от ID формы
    document.addEventListener('change', function(event) {

        // Проверяем, что измененный элемент - нужный нам чекбокс
        if (event.target.matches('input[name="is_homebrew"]')) {
            const rulesBlock = document.getElementById('homebrew_rules_block');

            if (rulesBlock) {
                // Если галочка стоит - показываем блок, иначе скрываем классом 'hidden'
                if (event.target.checked) {
                    rulesBlock.classList.remove('hidden');
                } else {
                    rulesBlock.classList.add('hidden');
                }
            }
        }
    });

    // Инициализация состояния ПРИ ЗАГРУЗКЕ СТРАНИЦЫ (для режима редактирования)
    // Находим ВСЕ такие чекбоксы на странице (на случай если их несколько)
    const homebrewCheckboxes = document.querySelectorAll('input[name="is_homebrew"]');

    homebrewCheckboxes.forEach(checkbox => {
        const associatedBlock = checkbox.closest('.space-y-6').querySelector('#homebrew_rules_block');

        // Если находим связанный блок рядом в DOM-дереве
        if (associatedBlock) {
            // Устанавливаем начальное состояние видимости
            if (!checkbox.checked) {
                associatedBlock.classList.add('hidden');
            }
        }
    });
}