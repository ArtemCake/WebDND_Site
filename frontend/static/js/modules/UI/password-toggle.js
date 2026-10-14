// frontend/static/js/modules/UI/password-toggle.js

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