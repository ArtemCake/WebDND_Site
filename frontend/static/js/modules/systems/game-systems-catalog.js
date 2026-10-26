// frontend/static/js/modules/systems/game-systems-catalog.js

import {
	sessionClient,
	SessionRefreshError
} from '../games/session-client.js';
import {
	createRulesEditor
} from './game-system-rules-editor.js';

const root = document.querySelector('[data-game-systems-page]');

if (root) {
	initGameSystemsPage(root);
}

function initGameSystemsPage(root) {
	const mode = root.dataset.pageMode;
	const systemId = root.dataset.systemId;
	const message = root.querySelector('[data-page-message]');
	const login = root.querySelector('[data-page-login]');
	const reload = root.querySelector('[data-page-reload]');
	const content = root.querySelector('[data-page-content]');
	const list = root.querySelector('[data-systems-list]');
	const create = root.querySelector('[data-system-create]');
	const edit = root.querySelector('[data-system-edit]');
	const form = root.querySelector('[data-system-form]');
	const fields = root.querySelector('[data-system-fields]');

	if (!message || !login || !reload || !content) return;

	let access = null;
	let ready = false;
	let busy = false;
	let systems = [];
	const rulesEditor = mode === 'edit'
    		? createRulesEditor(
    			root.querySelector('[data-rules-editor]'),
    			{ request, systemId }
    		)
    		: null;

	function pageUrl(id) {
		return `/game-systems/catalog/${encodeURIComponent(id)}`;
	}

	function adminUrl(id) {
		return `/admin/game-systems/${encodeURIComponent(id)}`;
	}

	function makeError(text, status = 0) {
		const error = new Error(text);
		error.status = status;
		return error;
	}

	function setBusy(value) {
		busy = value;
		reload.disabled = value;
		root.setAttribute('aria-busy', String(value));

		if (fields) {
			fields.disabled = value || !ready;
		}

		list?.querySelectorAll('button').forEach((button) => {
			button.disabled = value || !ready;
		});
		rulesEditor?.setParentBusy(value || !ready);
	}

	function showError(error) {
		message.textContent = error.message
			|| 'Не удалось выполнить действие.';

		login.hidden = error.status !== 401;

		if (error.status === 401 || error.status === 403) {
			ready = false;
			content.hidden = true;
		}
	}

	function errorText(data, status) {
		if (status === 401) {
			return 'Сессия завершена. Войдите в аккаунт снова.';
		}

		if (status === 403) {
			return 'Недостаточно прав или запрос не прошёл защитную проверку.';
		}

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

		return `Не удалось выполнить запрос (${status}).`;
	}

	async function request(
    		path,
    		method = 'GET',
    		payload,
    		{ readOnly = false } = {}
    	) {
		const headers = new Headers({
			Accept: 'application/json'
		});

		if (payload !== undefined) {
			headers.set('Content-Type', 'application/json');
		}

		const mutation = method !== 'GET' && !readOnly;
		let response;

		try {
			response = await sessionClient.sessionFetch(path, {
				method,
				headers,
				cache: 'no-store',
				body: payload === undefined
					? undefined
					: JSON.stringify(payload)
			});
		} catch (error) {
			if (error instanceof SessionRefreshError) {
				throw makeError(error.message, error.status);
			}

			throw makeError(
				mutation
					? 'Связь с сервером прервалась. Изменение могло ' +
						'сохраниться. Проверьте список или заново ' +
						'загрузите данные перед повторным сохранением.'
					: 'Не удалось связаться с сервером. Повторите загрузку.'
			);
		}

		const contentType = response.headers.get('Content-Type') || '';
		let data = null;

		if (contentType.includes('application/json')) {
			try {
				data = await response.json();
			} catch {
				if (response.ok) {
					throw makeError(
						mutation
							? 'Ответ сервера не удалось прочитать. ' +
								'Перед повторным сохранением проверьте данные.'
							: 'Ответ сервера не удалось прочитать.'
					);
				}
			}
		}

		if (!response.ok) {
			throw makeError(
				errorText(data, response.status),
				response.status
			);
		}

		if (data === null) {
			throw makeError(
				mutation
					? 'Получен неожиданный ответ. Изменение могло ' +
						'сохраниться — проверьте данные перед повтором.'
					: 'Сервер вернул неожиданный формат ответа.'
			);
		}

		return data;
	}

	function details(system) {
		return [
			system.slug,
			system.rules_engine_version
				? `Движок: ${system.rules_engine_version}`
				: null,
			typeof system.is_active === 'boolean'
				? (system.is_active ? 'Активна' : 'Неактивна')
				: null
		].filter(Boolean).join(' · ');
	}

	function link(text, href) {
		const node = document.createElement('a');
		node.className = 'btn btn-outline-primary';
		node.textContent = text;
		node.href = href;
		return node;
	}

	function renderList() {
		const fragment = document.createDocumentFragment();

		for (const system of systems) {
			const card = document.createElement('article');
			card.className = 'admin-card';

			const title = document.createElement('h2');
			title.textContent = system.name;

			const info = document.createElement('p');
			info.textContent = details(system);

			const description = document.createElement('p');
			description.textContent = system.description || 'Без описания';

			card.append(
				title,
				info,
				description,
				link('Просмотр', pageUrl(system.id))
			);

			if (access.can_edit === true) {
				card.append(
					link('Редактировать', `${pageUrl(system.id)}/edit`)
				);
			}

			if (access.can_toggle === true) {
				const toggle = document.createElement('button');
				toggle.type = 'button';
				toggle.className = 'btn btn-outline-primary';
				toggle.textContent = system.is_active
					? 'Деактивировать'
					: 'Активировать';
				toggle.dataset.systemToggle = system.id;
				card.append(toggle);
			}

			fragment.append(card);
		}

		list.replaceChildren(fragment);
		create.hidden = access.can_create !== true;
	}

	function renderView(system) {
		root.querySelector('[data-system-name]').textContent = system.name;
		root.querySelector('[data-system-details]').textContent =
			details(system);
		root.querySelector('[data-system-description]').textContent =
			system.description || 'Без описания';

		edit.href = `${pageUrl(system.id)}/edit`;
		edit.hidden = access.can_edit !== true;
	}

	function fillForm(system) {
		for (const name of [
			'name', 'slug', 'description', 'rules_engine_version'
		]) {
			form.elements.namedItem(name).value = system[name] ?? '';
		}

		form.elements.namedItem('is_active').checked =
			system.is_active === true;
	}

	async function loadPage() {
		if (busy || rulesEditor?.isBusy()) return;

		ready = false;
		access = null;
		content.hidden = true;
		login.hidden = true;
		list?.replaceChildren();
		message.textContent = 'Загрузка…';
		setBusy(true);

		try {
			access = await request('/game-systems/access');

			const expectedListUrl = access.can_edit === true
				? '/admin/game-systems/list'
				: '/game-systems';

			if (access.list_url !== expectedListUrl) {
				throw makeError(
					'Сервер вернул несогласованные настройки доступа.'
				);
			}

			if (mode === 'list') {
				systems = await request(expectedListUrl);

				if (!Array.isArray(systems)) {
					throw makeError('Сервер вернул некорректный список.');
				}

				renderList();
			} else if (mode === 'create') {
				if (access.can_create !== true) {
					throw makeError('Создание систем недоступно.', 403);
				}

				form.reset();
			} else if (mode === 'view' || mode === 'edit') {
				if (mode === 'edit' && access.can_edit !== true) {
					throw makeError('Редактирование системы недоступно.', 403);
				}

				const path = access.can_edit === true
					? adminUrl(systemId)
					: `/game-systems/items/${encodeURIComponent(systemId)}`;

				const system = await request(path);

				if (mode === 'view') {
					renderView(system);
				} else {
                	fillForm(system);
                	await rulesEditor?.load();
                }
			} else {
				throw makeError('Неизвестный режим страницы.');
			}

			ready = true;
			content.hidden = false;
			message.textContent = mode === 'list'
				? (
					systems.length
						? `Загружено систем: ${systems.length}.`
						: 'Доступных игровых систем пока нет.'
				)
				: '';
		} catch (error) {
			showError(error);
		} finally {
			setBusy(false);
		}
	}

	form?.addEventListener('submit', async (event) => {
		event.preventDefault();

		if (rulesEditor?.isBusy()) {
        			message.textContent =
        				'Дождитесь завершения операции с черновиком правил.';
        			return;
        		}

        if (rulesEditor?.hasUnsaved()) {
            message.textContent =
            'Сначала сохраните черновик правил. ' +
            'Сохранение основных сведений переводит на страницу просмотра.';
            return;
        }
         if (busy || !ready || !form.reportValidity()) return;

		const isEditing = mode === 'edit';
		const allowed = isEditing
			? access.can_edit === true
			: access.can_create === true;

		if (!allowed) return;

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
			message.textContent =
				'Заполните обязательные поля без пустых пробелов.';
			return;
		}

		setBusy(true);
		login.hidden = true;
		message.textContent = 'Сохранение…';

		try {
			const saved = await request(
				isEditing ? adminUrl(systemId) : '/admin/game-systems',
				isEditing ? 'PATCH' : 'POST',
				payload
			);

			if (typeof saved.id !== 'string' || !saved.id) {
				throw makeError(
					'Ответ сохранения не содержит идентификатор системы. ' +
					'Проверьте список перед повторным сохранением.'
				);
			}

			window.location.assign(
            				isEditing
            					? pageUrl(saved.id)
            					: `${pageUrl(saved.id)}/edit`
            			);
		} catch (error) {
			showError(error);
		} finally {
			setBusy(false);
		}
	});

	list?.addEventListener('click', async (event) => {
		if (!(event.target instanceof Element)) return;

		const button = event.target.closest('[data-system-toggle]');

		if (
			!button || !list.contains(button) ||
			busy || !ready || access.can_toggle !== true
		) {
			return;
		}

		const system = systems.find(
			(item) => item.id === button.dataset.systemToggle
		);

		if (!system) return;

		setBusy(true);
		message.textContent = 'Сохранение…';

		try {
			const updated = await request(
				adminUrl(system.id),
				'PATCH',
				{ is_active: !system.is_active }
			);

			const index = systems.findIndex(
				(item) => item.id === system.id
			);

			systems[index] = updated;
			systems.sort((a, b) => {
				return Number(b.is_active) - Number(a.is_active)
					|| a.name.localeCompare(b.name, 'ru');
			});

			renderList();
			message.textContent = updated.is_active
				? 'Система активирована.'
				: 'Система деактивирована.';
		} catch (error) {
			showError(error);
		} finally {
			setBusy(false);
		}
	});

	reload.addEventListener('click', () => {
		if (busy || rulesEditor?.isBusy()) return;

		if (
			form && ready &&
			!window.confirm(
				'Загрузить данные заново? Несохранённые изменения будут потеряны.'
			)
		) {
			return;
		}

		void loadPage();
	});

	void loadPage();
}