// frontend/static/js/modules/admin-game-systems.js

const root = document.querySelector('[data-game-systems-admin]');

if (root) {
	initGameSystemsAdmin(root);
}

function initGameSystemsAdmin(root) {
	const form = root.querySelector('[data-system-form]');
	const fields = root.querySelector('[data-system-fields]');
	const heading = root.querySelector('[data-system-form-title]');
	const submit = root.querySelector('[data-system-submit]');
	const cancel = root.querySelector('[data-system-cancel]');
	const refresh = root.querySelector('[data-systems-refresh]');
	const message = root.querySelector('[data-systems-message]');
	const empty = root.querySelector('[data-systems-empty]');
	const list = root.querySelector('[data-systems-list]');

	if (
		!form || !fields || !heading || !submit ||
		!cancel || !refresh || !message || !empty || !list
	) {
		return;
	}

	let systems = [];
	let editingId = null;
	let busy = false;

	function showMessage(text, type = 'info') {
		const node = document.createElement('div');
		node.className = `alert alert-${type}`;
		node.textContent = text;
		message.replaceChildren(node);
	}

	function setBusy(value) {
		busy = value;
		fields.disabled = value;
		refresh.disabled = value;

		list.querySelectorAll('button').forEach((button) => {
			button.disabled = value;
		});

		root.setAttribute('aria-busy', String(value));
	}

	function resetForm() {
		editingId = null;
		form.reset();
		heading.textContent = 'Новая игровая система';
		submit.textContent = 'Создать систему';
		cancel.hidden = true;
	}

	function getErrorMessage(data, status) {
		if (typeof data?.detail === 'string') {
			return data.detail;
		}

		if (Array.isArray(data?.detail)) {
			return data.detail.map((item) => {
				const path = Array.isArray(item.loc)
					? item.loc.filter((part) => part !== 'body').join('.')
					: '';

				return path ? `${path}: ${item.msg}` : item.msg;
			}).join('; ');
		}

		if (status === 401) {
			return 'Необходимо повторно войти в аккаунт.';
		}

		if (status === 403) {
			return 'Действие запрещено. Проверьте права и обновите страницу.';
		}

		return `Не удалось выполнить запрос (${status}).`;
	}

	async function request(path, method = 'GET', payload) {
		const headers = new Headers({
			Accept: 'application/json'
		});

		if (payload !== undefined) {
			headers.set('Content-Type', 'application/json');
		}

		if (method !== 'GET') {
			const csrf = document.querySelector(
				'meta[name="csrf-token"]'
			)?.content;

			if (!csrf) {
				throw new Error(
					'Не найден защитный токен. Обновите страницу.'
				);
			}

			headers.set('X-CSRF-Token', csrf);
		}

		let response;

		try {
			response = await fetch(path, {
				method,
				headers,
				credentials: 'same-origin',
				body: payload === undefined
					? undefined
					: JSON.stringify(payload)
			});
		} catch {
			throw new Error(
				'Не удалось связаться с сервером. ' +
				'Перед повторным сохранением обновите список: ' +
				'изменение могло уже сохраниться.'
			);
		}

		const freshCsrf = response.headers.get('X-CSRF-Token');

		if (freshCsrf) {
			document.querySelector('meta[name="csrf-token"]')
				?.setAttribute('content', freshCsrf);
		}

		const contentType = response.headers.get('Content-Type') || '';

		if (!contentType.includes('application/json')) {
			throw new Error(
				'Сервер вернул не JSON. Проверьте авторизацию ' +
				'и подключение административных API-маршрутов.'
			);
		}

		let data;

		try {
			data = await response.json();
		} catch {
			throw new Error(
				'Ответ сервера не удалось прочитать. ' +
				'Перед повторным сохранением обновите список.'
			);
		}

		if (!response.ok) {
			throw new Error(getErrorMessage(data, response.status));
		}

		return data;
	}

	function renderSystems() {
		const fragment = document.createDocumentFragment();

		for (const system of systems) {
			const card = document.createElement('article');
			card.className = 'admin-card';

			const title = document.createElement('h3');
			title.textContent = system.name;

			const details = document.createElement('p');
			details.textContent = [
				system.slug,
				`Движок: ${system.rules_engine_version}`,
				system.is_active ? 'Активна' : 'Неактивна'
			].join(' · ');

			const description = document.createElement('p');
			description.textContent = system.description || 'Без описания';

			const edit = document.createElement('button');
			edit.type = 'button';
			edit.className = 'btn btn-outline-primary';
			edit.textContent = 'Редактировать';
			edit.dataset.systemAction = 'edit';
			edit.dataset.systemId = system.id;

			const toggle = document.createElement('button');
			toggle.type = 'button';
			toggle.className = 'btn btn-outline-primary';
			toggle.textContent = system.is_active
				? 'Деактивировать'
				: 'Активировать';
			toggle.dataset.systemAction = 'toggle';
			toggle.dataset.systemId = system.id;

			edit.disabled = busy;
			toggle.disabled = busy;

			card.append(title, details, description, edit, toggle);
			fragment.append(card);
		}

		list.replaceChildren(fragment);
		empty.hidden = systems.length > 0;
		empty.textContent = 'Игровых систем пока нет. Создайте первую.';
	}

	async function loadSystems() {
		const data = await request('/admin/game-systems/list');

		if (!Array.isArray(data)) {
			throw new Error('Сервер вернул некорректный список систем.');
		}

		systems = data;
		renderSystems();
	}

	function replaceSystem(updated) {
		const index = systems.findIndex((item) => item.id === updated.id);

		if (index === -1) {
			systems.push(updated);
		} else {
			systems[index] = updated;
		}

		systems.sort((a, b) => {
			return Number(b.is_active) - Number(a.is_active)
				|| a.name.localeCompare(b.name, 'ru');
		});

		renderSystems();
	}

	async function refreshSystems() {
		if (busy) return;
		setBusy(true);

		try {
			await loadSystems();
			message.replaceChildren();
		} catch (error) {
			showMessage(error.message, 'error');
		} finally {
			setBusy(false);
		}
	}

	form.addEventListener('submit', async (event) => {
		event.preventDefault();
		if (busy || !form.reportValidity()) return;

		const values = new FormData(form);
		const payload = {
			name: String(values.get('name') || '').trim(),
			slug: String(values.get('slug') || '').trim(),
			description: String(values.get('description') || '').trim()
				|| null,
			rules_engine_version: String(
				values.get('rules_engine_version') || ''
			).trim(),
			is_active: values.has('is_active')
		};

		if (!payload.name || !payload.slug || !payload.rules_engine_version) {
			showMessage('Заполните обязательные поля без пустых пробелов.', 'error');
			return;
		}

		const isEditing = editingId !== null;
		const path = isEditing
			? `/admin/game-systems/${encodeURIComponent(editingId)}`
			: '/admin/game-systems';

		setBusy(true);

		try {
			const updated = await request(
				path,
				isEditing ? 'PATCH' : 'POST',
				payload
			);

			replaceSystem(updated);
			resetForm();
			showMessage(
				isEditing ? 'Изменения сохранены.' : 'Игровая система создана.',
				'success'
			);
		} catch (error) {
			showMessage(error.message, 'error');
		} finally {
			setBusy(false);
		}
	});

	cancel.addEventListener('click', () => {
		if (!busy) resetForm();
	});

	refresh.addEventListener('click', refreshSystems);

	list.addEventListener('click', async (event) => {
		if (!(event.target instanceof Element)) return;

		const button = event.target.closest('[data-system-action]');
		if (!button || !list.contains(button) || busy) return;

		const system = systems.find(
			(item) => item.id === button.dataset.systemId
		);

		if (!system) return;

		if (button.dataset.systemAction === 'edit') {
			editingId = system.id;
			form.elements.namedItem('name').value = system.name;
			form.elements.namedItem('slug').value = system.slug;
			form.elements.namedItem('description').value =
				system.description || '';
			form.elements.namedItem('rules_engine_version').value =
				system.rules_engine_version;
			form.elements.namedItem('is_active').checked = system.is_active;

			heading.textContent = 'Редактирование системы';
			submit.textContent = 'Сохранить изменения';
			cancel.hidden = false;
			form.elements.namedItem('name').focus();
			return;
		}

		if (button.dataset.systemAction !== 'toggle') return;

		setBusy(true);

		try {
			const updated = await request(
				`/admin/game-systems/${encodeURIComponent(system.id)}`,
				'PATCH',
				{ is_active: !system.is_active }
			);

			replaceSystem(updated);

			if (editingId === updated.id) {
				form.elements.namedItem('is_active').checked = updated.is_active;
			}

			showMessage(
				updated.is_active
					? 'Система активирована.'
					: 'Система деактивирована.',
				'success'
			);
		} catch (error) {
			showMessage(error.message, 'error');
		} finally {
			setBusy(false);
		}
	});

	void refreshSystems();
}