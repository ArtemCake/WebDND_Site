// static/js/modules/passwordToggle.js

/**
 * Переключает видимость пароля и меняет иконку глаза.
 */
export function initPasswordToggle(toggleButton, passwordField) {

	if (!toggleButton || !passwordField){
	console.error("Элементы не найдены.");
	return;
	}

	const closedEyeSvg = `
    <svg class="eye-icon" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="#000" stroke-width="2"/>
      <path d="M12 12C15.866 12 19 9.866 19 7V5C19 2.134 15.866 0 12 0C8.134 0 5 2.134 5 5V7C5 9.866 8.134 12 12 12z" fill="#000"/>
    </svg>
  `;

	const openEyeSvg = `
    <svg class="eye-icon" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="#000" stroke-width="2"/>
      <path d="M12 12C15.866 12 19 9.866 19 7V5C19 2.134 15.866 0 12 0C8.134 0 5 2.134 5 5V7C5 9.866 8.134 12 12 12z" fill="#000"/>
      <circle cx="12" cy="12" r="4" fill="#fff"/>
    </svg>
  `;

	let isVisible = false;

	function toggleVisibility() {
		isVisible = !isVisible;
		passwordField.type = isVisible ? 'text' : 'password';
		toggleButton.innerHTML = isVisible ? openEyeSvg : closedEyeSvg;
		toggleButton.setAttribute('aria-pressed', isVisible);
		toggleButton.setAttribute('aria-label', isVisible ? 'Скрыть пароль' : 'Показать пароль');
		toggleButton.querySelector('.eye-icon').setAttribute('aria-hidden', 'true');
		// Для скринридеров: добавляем текстовую метку
		toggleButton.setAttribute('data-state', isVisible ? 'показан' : 'скрыт');

		// Простой вариант с aria-live (если есть элемент с id="sr-status")
		const srStatus = document.getElementById('sr-status');
		if (srStatus) {
			srStatus.textContent = isVisible ? 'Пароль показан' : 'Пароль скрыт';
			srStatus.setAttribute('aria-live', 'polite');
			srStatus.setAttribute('role', 'status');
			srStatus.classList.add('sr-only');
			// Удаляем через секунду, чтобы не мешать другим сообщениям
			setTimeout(() => {
				srStatus.textContent = '';
			}, 1000);
		}
		// Для финального кода:
		toggleButton.setAttribute('data-state', isVisible ? 'показан' : 'скрыт');
		// Комментарий: для полной доступности рекомендуется добавить live-region с id="sr-status"
	}

	toggleButton.addEventListener('click', toggleVisibility);
	// Устанавливаем начальное состояние иконки и атрибутов
	toggleButton.innerHTML = closedEyeSvg;
	toggleButton.setAttribute('aria-pressed', 'false');
	toggleButton.setAttribute('aria-label', 'Показать пароль');
	toggleButton.querySelector('.eye-icon').setAttribute('aria-hidden', 'true');
}