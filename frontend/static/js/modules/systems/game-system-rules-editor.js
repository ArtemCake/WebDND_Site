// frontend/static/js/modules/systems/game-system-rules-editor.js

const OPERATIONS = [
	['sum', 'Сложение'],
	['subtract', 'Вычитание'],
	['multiply', 'Умножение'],
	['floor_div', 'Деление с округлением вниз'],
	['ceil_div', 'Деление с округлением вверх'],
	['min', 'Минимум'],
	['max', 'Максимум']
];

const LABELS = {
	str: 'Сила',
	dex: 'Ловкость',
	con: 'Телосложение',
	int: 'Интеллект',
	wis: 'Мудрость',
	cha: 'Харизма'
};

const CODE_PATTERN = /^[a-z][a-z0-9_]{0,39}$/;

function copy(value) {
	return JSON.parse(JSON.stringify(value));
}

function node(tag, text) {
	const element = document.createElement(tag);
	if (text !== undefined) element.textContent = text;
	return element;
}

function input(value, options = {}) {
	const element = document.createElement('input');
	element.type = options.type || 'text';
	element.value = String(value);

	for (const [key, item] of Object.entries(options)) {
		element.setAttribute(key, String(item));
	}

	return element;
}

function select(options, value) {
	const element = document.createElement('select');

	for (const [code, label] of options) {
		const option = node('option', label);
		option.value = code;
		element.append(option);
	}

	element.value = value;
	return element;
}

function labelled(text, control) {
	const label = node('label', `${text} `);
	label.append(control);
	const paragraph = node('p');
	paragraph.append(label);
	return paragraph;
}

function button(text, action) {
	const element = node('button', text);
	element.type = 'button';
	element.className = 'btn btn-outline-primary';
	element.addEventListener('click', action);
	return element;
}

function integer(control, title) {
	const raw = control.value.trim();
	const value = Number(raw);

	if (!raw || !Number.isSafeInteger(value)) {
		throw new Error(`${title}: требуется целое число.`);
	}

	return value;
}

function table(headers, container) {
	const element = node('table');
	const head = node('thead');
	const row = node('tr');

	for (const title of headers) row.append(node('th', title));

	head.append(row);
	element.append(head, container);
	return element;
}

function cell(row, control) {
	const element = node('td');
	element.append(control);
	row.append(element);
}

export function createRulesEditor(host, { request, systemId }) {
	if (!host) return null;

	const message = host.querySelector('[data-rules-message]');
	const reload = host.querySelector('[data-rules-reload]');
	const controls = host.querySelector('[data-rules-controls]');
	const body = host.querySelector('[data-rules-body]');
	const result = host.querySelector('[data-rules-result]');

	const draftUrl =
		`/admin/game-systems/${encodeURIComponent(systemId)}/rules/draft`;

	let profile = null;
	let revision = null;
	let dirty = false;
	let busy = false;
	let parentBusy = true;
	let blocked = false;
	let saveButton = null;
	let attributeRows = [];
	let derivedRows = [];
	let modeControl;
	let offsetControl;
	let divisorControl;
	let levelControl;

	function sync() {
		controls.disabled = busy || parentBusy;
		reload.disabled = busy || parentBusy;

		if (saveButton) {
			saveButton.disabled = blocked || !dirty;
		}
	}

	function markDirty() {
		dirty = true;
		result.hidden = true;
		message.textContent = 'Есть несохранённые изменения.';
		sync();
	}

	function clearResult() {
		result.hidden = true;
		result.textContent = '';
	}

	function failure(error, saving = false) {
		message.textContent = error.message || 'Не удалось выполнить действие.';

		if (
			error.status === 409
			|| error.status === 401
			|| error.status === 403
			|| (saving && !error.status)
		) {
			blocked = true;

			message.textContent +=
				' Введённые данные оставлены на странице. ' +
				'Сохранение заблокировано до перезагрузки черновика. ' +
				'При необходимости скопируйте настройки перед перезагрузкой.';
		}
	}

	function upgrade(raw) {
		const next = copy(raw);

		if (next.schema_version === 2) return next;

		if (next.schema_version !== 1) {
			throw new Error('Редактор не поддерживает эту версию профиля.');
		}

		// Меняем только версию и добавляем определения характеристик.
		// Настройки проверок, владения и происхождения сохраняются.
		next.schema_version = 2;
		next.calculations = {
			attributes: Object.fromEntries(
				next.attribute_codes.map((code) => [
					code,
					{
						label: LABELS[code] || code,
						min_value: -1000,
						max_value: 1000
					}
				])
			),
			derived: {}
		};

		return next;
	}

	function removeRow(rows, item) {
		rows.splice(rows.indexOf(item), 1);
		item.element.remove();
		markDirty();
	}

	function addAttribute(container, code, definition) {
		const element = node('tr');

		const item = {
			element,
			code: input(code, { required: true, maxlength: 40 }),
			label: input(definition.label, {
				required: true,
				maxlength: 100
			}),
			min: input(definition.min_value, {
				type: 'number', min: -1000, max: 1000, step: 1,
				required: true
			}),
			max: input(definition.max_value, {
				type: 'number', min: -1000, max: 1000, step: 1,
				required: true
			})
		};

		const initial = profile.attribute_mode === 'score' ? 10 : 0;

		item.sample = input(
			Math.max(
				definition.min_value,
				Math.min(initial, definition.max_value)
			),
			{ type: 'number', step: 1, required: true }
		);
		item.sample.dataset.sample = 'true';

		for (const control of [
			item.code, item.label, item.min, item.max, item.sample
		]) {
			cell(element, control);
		}

		cell(element, button('Удалить', () => {
			removeRow(attributeRows, item);
		}));

		attributeRows.push(item);
		container.append(element);
	}

	function addDerived(container, code, definition) {
		const element = node('tr');

		const item = {
			element,
			code: input(code, { required: true, maxlength: 40 }),
			label: input(definition.label, {
				required: true,
				maxlength: 100
			}),
			operation: select(
				OPERATIONS,
				definition.formula.operation
			),
			arguments: input(
				definition.formula.arguments.join(', '),
				{ required: true }
			)
		};

		for (const control of [
			item.code, item.label, item.operation, item.arguments
		]) {
			cell(element, control);
		}

		cell(element, button('Удалить', () => {
			removeRow(derivedRows, item);
		}));

		derivedRows.push(item);
		container.append(element);
	}

	function renderProfile() {
		body.replaceChildren();
		clearResult();
		attributeRows = [];
		derivedRows = [];

		body.append(node(
			'p',
			`Основа: ${profile.base_ruleset}. ` +
			`Максимальный уровень: ${profile.max_level}. ` +
			`Ревизия: ${revision ?? 'черновик ещё не создан'}.`
		));

		modeControl = select([
			['score', 'Значение с вычисляемым модификатором'],
			['modifier', 'Непосредственный модификатор']
		], profile.attribute_mode);

		offsetControl = input(profile.modifier_offset, {
			type: 'number', min: -1000, max: 1000, step: 1,
			required: true
		});

		divisorControl = input(profile.modifier_divisor, {
			type: 'number', min: 1, max: 1000, step: 1,
			required: true
		});

		body.append(
			labelled('Режим характеристик', modeControl),
			labelled('Вычитаемое перед делением', offsetControl),
			labelled('Делитель модификатора', divisorControl),
			node(
				'p',
				'В режиме значения: из характеристики вычитается ' +
				'указанное число, результат делится с округлением вниз. ' +
				'В режиме непосредственного модификатора эти параметры ' +
				'не применяются.'
			),
			node('h3', 'Характеристики')
		);

		const attributes = node('tbody');

		body.append(table([
			'Код', 'Название', 'Минимум', 'Максимум',
			'Значение для проверки', 'Действия'
		], attributes));

		for (const [code, definition] of Object.entries(
			profile.calculations.attributes
		)) {
			addAttribute(attributes, code, definition);
		}

		body.append(button('Добавить характеристику', () => {
			if (attributeRows.length >= 40) {
				message.textContent = 'Допустимо не более 40 характеристик.';
				return;
			}

			addAttribute(attributes, '', {
				label: '',
				min_value: -1000,
				max_value: 1000
			});
			markDirty();
		}));

		body.append(
			node('h3', 'Вычисляемые показатели'),
			node(
				'p',
				'Аргументы через запятую: целые числа, level, ' +
				'attribute.dex, modifier.dex или stat.other. ' +
				'Для сложной формулы создайте промежуточный показатель. ' +
				'Переименование кода не переписывает ссылки автоматически.'
			)
		);

		const derived = node('tbody');

		body.append(table([
			'Код', 'Название', 'Операция', 'Аргументы', 'Действия'
		], derived));

		for (const [code, definition] of Object.entries(
			profile.calculations.derived
		)) {
			addDerived(derived, code, definition);
		}

		body.append(button('Добавить показатель', () => {
			if (derivedRows.length >= 128) {
				message.textContent = 'Допустимо не более 128 показателей.';
				return;
			}

			addDerived(derived, '', {
				label: '',
				formula: { operation: 'sum', arguments: [0] }
			});
			markDirty();
		}));

		levelControl = input(1, {
			type: 'number', min: 1, max: profile.max_level,
			step: 1, required: true
		});
		levelControl.dataset.sample = 'true';

		saveButton = button('Сохранить черновик', () => {
			void save();
		});

		body.append(
			node('h3', 'Предпросмотр'),
			labelled('Уровень для проверки', levelControl),
			button('Рассчитать', () => void preview()),
			saveButton
		);

		sync();
	}

	function collect() {
		for (const control of body.querySelectorAll('input, select')) {
			if (!control.reportValidity()) {
				throw new Error('Проверьте заполнение полей редактора.');
			}
		}

		if (!attributeRows.length) {
			throw new Error('Нужна хотя бы одна характеристика.');
		}

		const attributes = new Map();
		const samples = new Map();
		const derived = new Map();

		function codeOf(control, used) {
			const code = control.value.trim();

			if (!CODE_PATTERN.test(code)) {
				throw new Error(
					'Код: строчная латинская буква, затем буквы, ' +
					'цифры или подчёркивания; не более 40 символов.'
				);
			}

			if (used.has(code)) {
				throw new Error(`Повторяющийся код: ${code}.`);
			}

			return code;
		}

		for (const item of attributeRows) {
			const code = codeOf(item.code, attributes);
			const label = item.label.value.trim();
			const min = integer(item.min, `${code}: минимум`);
			const max = integer(item.max, `${code}: максимум`);

			if (!label) throw new Error(`${code}: укажите название.`);
			if (min > max) throw new Error(`${code}: минимум больше максимума.`);

			attributes.set(code, {
				label,
				min_value: min,
				max_value: max
			});
			samples.set(code, integer(item.sample, `${code}: значение`));
		}

		for (const item of derivedRows) {
			const code = codeOf(item.code, derived);
			const label = item.label.value.trim();

			if (!label) throw new Error(`${code}: укажите название.`);

			const args = item.arguments.value.split(',').map((raw) => {
				const value = raw.trim();

				if (!value) throw new Error(`${code}: пустой аргумент.`);

				if (/^-?\d+$/.test(value)) {
					const number = Number(value);

					if (!Number.isSafeInteger(number)) {
						throw new Error(`${code}: слишком большое число.`);
					}

					return number;
				}

				return value;
			});

			derived.set(code, {
				label,
				formula: {
					operation: item.operation.value,
					arguments: args
				}
			});
		}

		// Копируем весь исходный профиль, затем заменяем только
		// разделы, которыми управляет этот редактор.
		const rules = copy(profile);
		rules.schema_version = 2;
		rules.attribute_mode = modeControl.value;
		rules.modifier_offset = integer(offsetControl, 'Вычитаемое');
		rules.modifier_divisor = integer(divisorControl, 'Делитель');
		rules.attribute_codes = [...attributes.keys()];
		rules.calculations = {
			attributes: Object.fromEntries(attributes),
			derived: Object.fromEntries(derived)
		};

		return {
			rules,
			level: integer(levelControl, 'Уровень'),
			attributes: Object.fromEntries(samples)
		};
	}

	function showPreview(data) {
		const lines = ['Модификаторы:'];

		for (const [code, value] of Object.entries(data.modifiers)) {
			lines.push(`${code}: ${value}`);
		}

		lines.push('', 'Вычисляемые показатели:');

		for (const [code, value] of Object.entries(data.derived)) {
			lines.push(`${code}: ${value}`);
		}

		lines.push('', 'Последовательность расчёта:');

		for (const step of data.steps) {
			lines.push(
				`${step.code}: ${step.operation}` +
				`(${step.arguments.join(', ')})` +
				` → (${step.resolved_arguments.join(', ')})` +
				` → ${step.value}`
			);
		}

		result.textContent = lines.join('\n');
		result.hidden = false;
	}

	async function preview() {
		if (busy || parentBusy || !profile) return;

		try {
			const payload = collect();
			busy = true;
			sync();
			clearResult();
			message.textContent = 'Выполняется предпросмотр…';

			const data = await request(
				'/admin/game-systems/rules/attributes/preview',
				'POST',
				payload,
				{ readOnly: true }
			);

			showPreview(data);
			message.textContent =
				'Расчёт выполнен. Предпросмотр ничего не сохраняет.';
		} catch (error) {
			failure(error);
		} finally {
			busy = false;
			sync();
		}
	}

	async function save() {
		if (busy || parentBusy || blocked || !dirty || !profile) return;

		try {
			const { rules } = collect();
			const creating = revision === null;

			const payload = creating
				? { rules }
				: { rules, expected_revision: revision };

			busy = true;
			sync();
			message.textContent = 'Сохраняется черновик…';

			const saved = await request(
				draftUrl,
				creating ? 'POST' : 'PATCH',
				payload
			);

			if (
				saved.system_id !== systemId
				|| !Number.isInteger(saved.revision)
				|| saved.revision < 1
				|| !saved.rules
			) {
				throw new Error(
					'Ответ сохранения не удалось проверить. ' +
					'Перед повтором загрузите черновик заново.'
				);
			}

			profile = copy(saved.rules);
			revision = saved.revision;
			dirty = false;
			clearResult();

			message.textContent =
				`Черновик сохранён. Ревизия: ${revision}. ` +
				'Публикация не выполнялась.';
		} catch (error) {
			failure(error, true);
		} finally {
			busy = false;
			sync();
		}
	}

	async function renderEmpty() {
		const presets = await request(
			'/admin/game-systems/rules/calculation-presets'
		);

		if (!Array.isArray(presets) || !presets.length) {
			throw new Error('Не удалось получить основы правил.');
		}

		body.replaceChildren();
		saveButton = null;

		const choice = select(
			presets.map((preset) => [preset.code, preset.name]),
			presets[0].code
		);

		body.append(
			node(
				'p',
				'Черновика ещё нет. Выберите основу; ' +
				'она будет сохранена только по вашей команде.'
			),
			labelled('Основа правил', choice),
			button('Использовать основу', () => {
				const preset = presets.find(
					(item) => item.code === choice.value
				);

				profile = upgrade(preset.rules);
				dirty = true;
				renderProfile();
				message.textContent =
					'Основа загружена в редактор. Черновик ещё не сохранён.';
			})
		);
	}

	async function load() {
		if (busy) return;

		// При неудачной перезагрузке оставляем прежние поля.
		// Сохранение запрещено, пока ревизия не проверена.
		busy = true;
		blocked = true;
		sync();
		message.textContent = 'Загружается черновик…';

		try {
			const state = await request(draftUrl);

			if (
				!state
				|| !Object.prototype.hasOwnProperty.call(state, 'draft')
			) {
				throw new Error('Сервер вернул некорректное состояние черновика.');
			}

			if (state.draft === null) {
				// Сначала получаем пресеты, только затем заменяем поля.
				await renderEmpty();
				profile = null;
				revision = null;
				dirty = false;
			} else {
				const draft = state.draft;

				if (
					draft.system_id !== systemId
					|| !Number.isInteger(draft.revision)
					|| draft.revision < 1
				) {
					throw new Error('Некорректная ревизия черновика.');
				}

				const converted = draft.rules.schema_version === 1;
				const loadedProfile = upgrade(draft.rules);

				profile = loadedProfile;
				revision = draft.revision;
				dirty = converted;
				renderProfile();
			}

			blocked = false;
			clearResult();

			message.textContent = profile
				? (
					dirty
						? 'Старый профиль подготовлен к версии 2. ' +
							'Преобразование ещё не сохранено.'
						: `Загружен черновик, ревизия ${revision}.`
				)
				: 'Выберите основу для нового черновика.';
		} catch (error) {
			failure(error);
		} finally {
			busy = false;
			sync();
		}
	}

	body.addEventListener('input', (event) => {
		if (!profile || !(event.target instanceof HTMLElement)) return;

		if (event.target.dataset.sample === 'true') {
			result.hidden = true;
			return;
		}

		markDirty();
	});

	reload.addEventListener('click', () => {
		if (busy || parentBusy) return;

		if (
			dirty
			&& !window.confirm(
				'Загрузить серверный черновик? ' +
				'Несохранённые настройки будут потеряны.'
			)
		) {
			return;
		}

		void load();
	});

	window.addEventListener('beforeunload', (event) => {
		if (!dirty) return;
		event.preventDefault();
		event.returnValue = '';
	});

	return {
		load,
		hasUnsaved: () => dirty,
		isBusy: () => busy,
		setParentBusy(value) {
			parentBusy = value;
			sync();
		}
	};
}