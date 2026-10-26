// frontend/static/js/modules/systems/game-system-rules-editor.js

const OPERATIONS = [
    ['sum', 'Сложить'],
    ['subtract', 'Вычесть из первого значения остальные'],
    ['multiply', 'Перемножить'],
    ['floor_div', 'Разделить с округлением вниз'],
    ['ceil_div', 'Разделить с округлением вверх'],
    ['min', 'Выбрать наименьшее'],
    ['max', 'Выбрать наибольшее']
];

const LABELS = {
    str: 'Сила',
    dex: 'Ловкость',
    con: 'Телосложение',
    int: 'Интеллект',
    wis: 'Мудрость',
    cha: 'Харизма'
};

const clone = (value) => JSON.parse(JSON.stringify(value));
const own = (object, key) =>
    Object.prototype.hasOwnProperty.call(object, key);

function element(tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
}

function createBasisIcon(code) {
    const namespace = 'http://www.w3.org/2000/svg';

    const svg = document.createElementNS(namespace, 'svg');
    svg.classList.add('system-editor__basis-icon');
    svg.setAttribute('viewBox', '0 0 64 64');
    svg.setAttribute('width', '64');
    svg.setAttribute('height', '64');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');

    const illustrations = {
        // Двадцатигранная кость.
        dnd5e_2014_srd51: [
            ['path', {
                d: 'M32 5 55 19 55 45 32 59 9 45 9 19Z',
                class: 'system-editor__icon-surface'
            }],
            ['path', {
                d: 'M32 5 20 25 44 25Z'
            }],
            ['path', {
                d: 'M9 19 20 25 9 45M55 19 44 25 55 45'
            }],
            ['path', {
                d: 'M20 25 32 47 44 25ZM9 45 32 47 55 45M32 47V59'
            }]
        ],

        // Щит с компасной звездой.
        pf2e_remaster: [
            ['path', {
                d: 'M32 5 53 13V30C53 43 44 53 32 59'
                    + ' 20 53 11 43 11 30V13Z',
                class: 'system-editor__icon-surface'
            }],
            ['path', {
                d: 'M32 11 47 17V30C47 40 41 48 32 53'
                    + ' 23 48 17 40 17 30V17Z'
            }],
            ['path', {
                d: 'M32 19 36 28 45 32 36 36'
                    + ' 32 45 28 36 19 32 28 28Z'
            }]
        ],

        // Свиток для авторских правил.
        custom: [
            ['path', {
                d: 'M17 10H47V45H23V18'
                    + 'C23 13 21 10 17 10Z',
                class: 'system-editor__icon-surface'
            }],
            ['path', {
                d: 'M17 10C13 10 10 13 10 17'
                    + 'V22H23V18C23 13 21 10 17 10Z'
            }],
            ['path', {
                d: 'M23 45H54V48C54 53 51 56 47 56'
                    + 'H23C19 56 16 53 16 49V45Z',
                class: 'system-editor__icon-surface'
            }],
            ['path', {
                d: 'M47 45V49C47 53 44 56 40 56'
            }],
            ['path', {
                d: 'M29 22H40M29 29H40M29 36H36'
            }]
        ]
    };

    const shapes = illustrations[code] || illustrations.custom;

    for (const [tag, attributes] of shapes) {
        const shape = document.createElementNS(namespace, tag);

        for (const [name, value] of Object.entries(attributes)) {
            shape.setAttribute(name, value);
        }

        svg.append(shape);
    }

    return svg;
}

function button(text, action) {
    const result = element('button', text, 'btn btn-outline-primary');
    result.type = 'button';
    result.addEventListener('click', action);
    return result;
}

function field(title, control) {
    const result = element('label', undefined, 'system-editor__field');
    result.append(element('span', title), control);
    return result;
}

function control(value, options = {}) {
    const result = document.createElement('input');
    result.type = options.type || 'text';

    for (const [name, item] of Object.entries(options)) {
        result.setAttribute(name, String(item));
    }

    result.value = value ?? '';
    return result;
}

function choices(options, value) {
    const result = document.createElement('select');

    for (const [key, label] of options) {
        const option = element('option', label);
        option.value = key;
        result.append(option);
    }

    result.value = value;
    return result;
}

function upgrade(raw) {
    const result = clone(raw);

    if (result.schema_version === 1) {
        result.schema_version = 2;
        result.calculations = {
            attributes: Object.fromEntries(
                result.attribute_codes.map((code) => [
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
    }

    if (
        result.schema_version !== 2 ||
        !result.calculations?.attributes ||
        !result.calculations?.derived
    ) {
        throw new Error('Эта версия правил пока не поддерживается редактором.');
    }

    return result;
}

export function createRulesEditor(host, {
    request,
    systemId,
    onBusy = () => {},
    onChange = () => {},
    onInvalid = () => {}
}) {
    if (!host) return null;

    const body = host.querySelector('[data-rules-body]');
    const basis = host.querySelector('[data-rules-basis]');
    const message = host.querySelector('[data-rules-message]');
    const controls = host.querySelector('[data-rules-controls]');

    let profile = null;
    let revision = null;
    let dirty = false;
    let busy = false;
    let parentBusy = true;
    let presets = [];
    let selectedPreset = '';
    let activePage = 'main';
    let result;
    let sampleLevel = '1';
    let samples = {};
    let sourceControls = [];

    function sync() {
        controls.disabled = busy || parentBusy;

        basis.querySelectorAll('button, select, input').forEach((item) => {
            item.disabled = busy || parentBusy;
        });
    }

    function clearResult() {
        if (result) {
            result.hidden = true;
            result.replaceChildren();
        }
    }

    function changed() {
        dirty = true;
        clearResult();
        message.textContent = 'Есть несохранённые настройки правил.';
        onChange();
    }

    function showPage(name) {
        activePage = name;

        body.querySelectorAll('[data-editor-panel]').forEach((panel) => {
            panel.hidden = panel.dataset.editorPanel !== name;
        });
    }

    function page(name, title, help) {
        const panel = element('section', undefined, 'system-editor__panel');
        panel.dataset.editorPanel = name;
        panel.setAttribute('aria-label', title);
        panel.append(element('h2', title), element('p', help, 'profile-note'));
        body.append(panel);
        return panel;
    }

    function details(title) {
        const result = element('details', undefined, 'system-editor__details');
        result.append(element('summary', title));
        return result;
    }

    function bindInput(title, value, options, setter, sample = false) {
        const input = control(value, options);

        if (sample) input.dataset.sample = 'true';

        input.addEventListener('input', () => {
            setter(input.value);
            if (sample) clearResult();
            else changed();
        });

        return field(title, input);
    }

    function sources(excludeCode) {
        const values = [
            ['#number', 'Число'],
            ['level', 'Уровень персонажа']
        ];

        if (!profile) return values;

        for (const [code, item] of Object.entries(
            profile.calculations.attributes
        )) {
            const title = item.label.trim() || 'Без названия';

            values.push(
                [`attribute.${code}`, `Значение: ${title}`],
                [`modifier.${code}`, `Модификатор: ${title}`]
            );
        }

        for (const [code, item] of Object.entries(
            profile.calculations.derived
        )) {
            if (code !== excludeCode) {
                values.push([
                    `stat.${code}`,
                    `Показатель: ${item.label.trim() || 'Без названия'}`
                ]);
            }
        }

        return values;
    }

    function refreshSources() {
        for (const item of sourceControls) {
            const current = item.select.value;
            const options = sources(item.code);

            if (!options.some(([value]) => value === current)) {
                options.push([current, 'Недоступный источник — выберите другой']);
            }

            const replacement = choices(options, current);
            item.select.replaceChildren(...replacement.children);
            item.select.value = current;
        }
    }

    function newCode(prefix, collection) {
        let number = 1;
        while (own(collection, `${prefix}_${number}`)) number += 1;
        return `${prefix}_${number}`;
    }

    function deleteEntry(kind, code) {
        const references = kind === 'attributes'
            ? [`attribute.${code}`, `modifier.${code}`]
            : [`stat.${code}`];

        const usedBy = Object.entries(profile.calculations.derived)
            .filter(([, item]) =>
                item.formula.arguments.some((arg) => references.includes(arg))
            )
            .map(([, item]) => item.label || 'Показатель без названия');

        if (usedBy.length) {
            message.textContent =
                `Сначала измените формулы, использующие этот элемент: ` +
                usedBy.join(', ') + '.';
            return;
        }

        if (
            kind === 'attributes' &&
            Object.keys(profile.calculations.attributes).length === 1
        ) {
            message.textContent =
                'Текущему движку нужна хотя бы одна характеристика.';
            return;
        }

        if (!window.confirm('Удалить этот элемент из черновика?')) return;

        delete profile.calculations[kind][code];
        delete samples[code];
        changed();
        render();
    }

    function renderBasis() {
        basis.replaceChildren();
        basis.append(element('h3', 'Основа правил'));

        if (profile) {
            const names = {
                dnd5e_2014_srd51: 'D&D 5e — SRD 5.1 / правила 2014 года',
                pf2e_remaster: 'Pathfinder 2e Remaster'
            };

            basis.append(element(
                'p',
                names[profile.base_ruleset] || profile.base_ruleset
            ));
            basis.append(element(
                'p',
                'Настройки основы можно изменять. ' +
                'Для замены всей основы загрузите страницу заново ' +
                'до начала редактирования или создайте другую систему.',
                'profile-note'
            ));
        } else {
            const cards = element(
                'div',
                undefined,
                'system-editor__basis-grid'
            );

            const descriptions = {
                dnd5e_2014_srd51: 'Правила 2014 года · SRD 5.1',
                pf2e_remaster: 'Remaster'
            };

            for (const preset of presets) {
                const card = element(
                    'label',
                    undefined,
                    'system-editor__basis-card'
                );

                const radio = document.createElement('input');
                radio.type = 'radio';
                radio.name = 'editor_basis_choice';
                radio.value = preset.code;
                radio.checked = selectedPreset === preset.code;

                const text = element(
                    'span',
                    undefined,
                    'system-editor__basis-text'
                );

                text.append(
                    element('strong', preset.name),
                    element(
                        'small',
                        descriptions[preset.code] ||
                            'Готовые настройки расчётов'
                    )
                );

                radio.addEventListener('change', () => {
                    selectedPreset = radio.value;

                    for (const option of cards.querySelectorAll(
                        '.system-editor__basis-card'
                    )) {
                        option.classList.toggle(
                            'is-selected',
                            option.querySelector('input').checked
                        );
                    }
                });

                card.classList.toggle('is-selected', radio.checked);
                card.append(radio, createBasisIcon(preset.code), text);
                cards.append(card);
            }

            // Информационная карточка, а не доступный пресет.
            const custom = element(
                'div',
                undefined,
                'system-editor__basis-card system-editor__basis-card--unavailable'
            );

            const customText = element(
                'span',
                undefined,
                'system-editor__basis-text'
            );

            customText.append(
                element('strong', 'Свои правила'),
                element('small', 'После расширения движка')
            );

            custom.append(createBasisIcon('custom'), customText);
            cards.append(custom);

            const apply = button('Использовать основу', () => {
                const preset = presets.find(
                    (item) => item.code === selectedPreset
                );

                if (!preset?.rules) {
                    message.textContent = 'Сначала выберите основу правил.';
                    cards.querySelector('input')?.focus();
                    return;
                }

                try {
                    profile = upgrade(preset.rules);
                    samples = {};
                    sampleLevel = '1';
                    changed();
                    renderBasis();
                    render();
                    sync();
                } catch (error) {
                    message.textContent = error.message;
                }
            });

            basis.append(
                cards,
                element(
                    'p',
                    'Основа заполняет настройки. Их можно изменить.',
                    'system-editor__basis-note'
                ),
                apply
            );
        }

        basis.append(element(
            'p',
            'Независимые авторские правила станут доступны после ' +
            'расширения движка. Сейчас можно изменять поддерживаемые ' +
            'характеристики и формулы выбранной основы.',
            'profile-note'
        ));
    }

    function renderAttributes(panel) {
        const mode = choices([
            ['score', 'Значение → вычисляемый модификатор'],
            ['modifier', 'Модификатор вводится напрямую']
        ], profile.attribute_mode);

        mode.addEventListener('change', () => {
            profile.attribute_mode = mode.value;
            changed();
            render();
        });

        panel.append(field('Как используются характеристики', mode));

        if (profile.attribute_mode === 'score') {
            panel.append(element(
                'p',
                'Из значения вычитается заданное число, затем результат ' +
                'делится с округлением вниз. Например: (14 − 10) / 2 → +2.'
            ));

            const settings = details('Настроить расчёт модификатора');

            settings.append(
                bindInput(
                    'Вычесть из значения',
                    profile.modifier_offset,
                    { type: 'number', required: true, min: -1000, max: 1000, step: 1 },
                    (value) => { profile.modifier_offset = value; }
                ),
                bindInput(
                    'Разделить на',
                    profile.modifier_divisor,
                    { type: 'number', required: true, min: 1, max: 1000, step: 1 },
                    (value) => { profile.modifier_divisor = value; }
                )
            );

            panel.append(settings);
        }

        const cards = element('div', undefined, 'system-editor__cards');

        for (const [code, item] of Object.entries(
            profile.calculations.attributes
        )) {
            const card = element('article', undefined, 'system-editor__card');

            card.append(bindInput(
                'Название характеристики',
                item.label,
                { required: true, maxlength: 100 },
                (value) => {
                    item.label = value;
                    refreshSources();
                }
            ));

            const settings = details('Настроить допустимые значения');

            settings.append(
                bindInput(
                    'Минимальное значение',
                    item.min_value,
                    { type: 'number', required: true, min: -1000, max: 1000, step: 1 },
                    (value) => { item.min_value = value; }
                ),
                bindInput(
                    'Максимальное значение',
                    item.max_value,
                    { type: 'number', required: true, min: -1000, max: 1000, step: 1 },
                    (value) => { item.max_value = value; }
                )
            );

            card.append(settings, button(
                'Удалить характеристику',
                () => deleteEntry('attributes', code)
            ));
            cards.append(card);
        }

        panel.append(cards, button('Добавить характеристику', () => {
            const collection = profile.calculations.attributes;

            if (Object.keys(collection).length >= 40) {
                message.textContent =
                    'Текущая версия движка поддерживает до 40 характеристик.';
                return;
            }

            const code = newCode('attribute', collection);
            collection[code] = {
                label: 'Новая характеристика',
                min_value: profile.attribute_mode === 'score' ? 1 : -10,
                max_value: profile.attribute_mode === 'score' ? 30 : 20
            };

            changed();
            render();
        }));
    }

    function renderDerived(panel) {
        panel.append(element(
            'p',
            'Источники выбираются по игровым названиям. ' +
            'Например: «Сложить» → число 10 и «Модификатор: Ловкость».'
        ));

        for (const [code, item] of Object.entries(
            profile.calculations.derived
        )) {
            const card = element('article', undefined, 'system-editor__card');

            card.append(bindInput(
                'Название показателя',
                item.label,
                { required: true, maxlength: 100 },
                (value) => {
                    item.label = value;
                    refreshSources();
                }
            ));

            const operation = choices(OPERATIONS, item.formula.operation);

            operation.addEventListener('change', () => {
                item.formula.operation = operation.value;
                changed();
            });

            card.append(field('Что сделать со значениями', operation));

            item.formula.arguments.forEach((arg, index) => {
                const row = element('div', undefined, 'system-editor__operand');
                const numeric = typeof arg === 'number' || arg === null;
                const current = numeric ? '#number' : arg;
                const options = sources(code);

                if (!options.some(([value]) => value === current)) {
                    options.push([
                        current,
                        'Недоступный источник — выберите другой'
                    ]);
                }

                const source = choices(options, current);
                sourceControls.push({ select: source, code });

                source.addEventListener('change', () => {
                    item.formula.arguments[index] =
                        source.value === '#number' ? 0 : source.value;
                    changed();
                    render();
                });

                row.append(field(`Значение ${index + 1}`, source));

                if (numeric) {
                    row.append(bindInput(
                        'Число',
                        arg,
                        { type: 'number', required: true, step: 1 },
                        (value) => {
                            item.formula.arguments[index] =
                                value === '' ? null : Number(value);
                        }
                    ));
                }

                row.append(button('Убрать значение', () => {
                    item.formula.arguments.splice(index, 1);
                    changed();
                    render();
                }));

                card.append(row);
            });

            card.append(
                button('Добавить значение в формулу', () => {
                    item.formula.arguments.push(0);
                    changed();
                    render();
                }),
                button('Удалить показатель', () => deleteEntry('derived', code))
            );

            panel.append(card);
        }

        panel.append(button('Добавить показатель', () => {
            const collection = profile.calculations.derived;

            if (Object.keys(collection).length >= 128) {
                message.textContent =
                    'Текущая версия движка поддерживает до 128 показателей.';
                return;
            }

            collection[newCode('stat', collection)] = {
                label: 'Новый показатель',
                formula: { operation: 'sum', arguments: [10] }
            };

            changed();
            render();
        }));
    }

    function renderPreview(panel) {
        panel.append(element(
            'p',
            'Значения примера нужны только для проверки. ' +
            'Они не сохраняются как характеристики будущих персонажей.'
        ));

        panel.append(bindInput(
            'Уровень персонажа для примера',
            sampleLevel,
            { type: 'number', required: true, min: 1, max: profile.max_level, step: 1 },
            (value) => { sampleLevel = value; },
            true
        ));

        for (const [code, item] of Object.entries(
            profile.calculations.attributes
        )) {
            const initial = profile.attribute_mode === 'score' ? 10 : 0;

            if (!own(samples, code)) {
                samples[code] = String(Math.max(
                    Number(item.min_value),
                    Math.min(initial, Number(item.max_value))
                ));
            }

            panel.append(bindInput(
                item.label || 'Характеристика без названия',
                samples[code],
                {
                    type: 'number',
                    required: true,
                    min: item.min_value,
                    max: item.max_value,
                    step: 1
                },
                (value) => { samples[code] = value; },
                true
            ));
        }

        panel.append(button('Проверить расчёт', () => void preview()));
        result = element('div', undefined, 'system-editor__result');
        result.setAttribute('aria-live', 'polite');
        result.hidden = true;
        panel.append(result);
    }

    function render() {
        body.replaceChildren();
        sourceControls = [];
        result = null;

        if (!profile) {
            for (const [name, title] of [
                ['attributes', 'Характеристики'],
                ['derived', 'Показатели'],
                ['preview', 'Проверка и сохранение']
            ]) {
                page(name, title, 'Сначала выберите основу на странице «Основное».');
            }
        } else {
            renderAttributes(page(
                'attributes',
                'Характеристики',
                'Это определения характеристик системы, а не значения персонажа.'
            ));
            renderDerived(page(
                'derived',
                'Вычисляемые показатели',
                'Порядок значений важен для вычитания и деления. ' +
                'Проверка допустимости формул выполняется сервером.'
            ));
            renderPreview(page(
                'preview',
                'Проверка на примере персонажа',
                'Проверьте результат, затем сохраните систему и черновик.'
            ));
        }

        showPage(activePage);
        sync();
    }

    function integer(value, title, min, max) {
        const number = Number(value);

        if (
            value === null || String(value).trim() === '' ||
            !Number.isSafeInteger(number) ||
            (min !== undefined && number < min) ||
            (max !== undefined && number > max)
        ) {
            throw new Error(`${title}: укажите целое число в допустимом диапазоне.`);
        }

        return number;
    }

    function validateControls(includeSamples = false) {
        for (const input of body.querySelectorAll('input, select')) {
            if (!includeSamples && input.dataset.sample === 'true') continue;

            if (!input.checkValidity()) {
                onInvalid(input);
                input.reportValidity();
                throw new Error('Проверьте выделенное поле.');
            }
        }
    }

    function collect() {
        if (!profile) {
            throw new Error('Выберите и примените основу на странице «Основное».');
        }

        validateControls();
        const rules = clone(profile);

        rules.modifier_offset = integer(
            rules.modifier_offset, 'Вычитаемое число', -1000, 1000
        );
        rules.modifier_divisor = integer(
            rules.modifier_divisor, 'Делитель', 1, 1000
        );

        for (const item of Object.values(rules.calculations.attributes)) {
            item.label = item.label.trim();

            if (!item.label) throw new Error('Укажите название характеристики.');

            item.min_value = integer(item.min_value, 'Минимум', -1000, 1000);
            item.max_value = integer(item.max_value, 'Максимум', -1000, 1000);

            if (item.min_value > item.max_value) {
                throw new Error(`${item.label}: минимум больше максимума.`);
            }
        }

        for (const [code, item] of Object.entries(rules.calculations.derived)) {
            item.label = item.label.trim();

            if (!item.label) throw new Error('Укажите название показателя.');
            if (!item.formula.arguments.length) {
                throw new Error(`${item.label}: добавьте значения в формулу.`);
            }

            const allowed = new Set(sources(code).map(([value]) => value));

            for (const arg of item.formula.arguments) {
                if (typeof arg === 'number' && Number.isSafeInteger(arg)) continue;

                if (
                    typeof arg !== 'string' ||
                    arg === '#number' ||
                    !allowed.has(arg)
                ) {
                    throw new Error(
                        `${item.label}: проверьте число или источник в формуле.`
                    );
                }
            }
        }

        rules.attribute_codes = Object.keys(rules.calculations.attributes);
        return rules;
    }

    async function preview() {
        if (busy || parentBusy) return;

        try {
            const rules = collect();
            validateControls(true);

            const attributes = Object.fromEntries(
                Object.entries(rules.calculations.attributes).map(([code, item]) => [
                    code,
                    integer(samples[code], item.label, item.min_value, item.max_value)
                ])
            );

            const level = integer(sampleLevel, 'Уровень', 1, rules.max_level);

            busy = true;
            onBusy(true);
            sync();
            clearResult();
            message.textContent = 'Проверка расчёта…';

            const data = await request(
                '/admin/game-systems/rules/attributes/preview',
                'POST',
                { rules, level, attributes },
                { readOnly: true }
            );

            if (!data?.modifiers || !data?.derived) {
                throw new Error('Ответ предпросмотра имеет неожиданный формат.');
            }

            result.append(element('h3', 'Результат'));

            for (const [title, values, definitions] of [
                ['Модификаторы', data.modifiers, rules.calculations.attributes],
                ['Показатели', data.derived, rules.calculations.derived]
            ]) {
                result.append(element('h4', title));
                const list = element('dl');

                for (const [code, value] of Object.entries(values)) {
                    list.append(
                        element('dt', definitions[code]?.label || code),
                        element('dd', String(value))
                    );
                }

                result.append(list);
            }

            result.hidden = false;
            message.textContent =
                'Расчёт выполнен. Пример персонажа и правила ещё не сохранены.';
        } catch (error) {
            message.textContent = error.message || 'Не удалось проверить расчёт.';
        } finally {
            busy = false;
            onBusy(false);
            sync();
        }
    }

    async function load() {
        if (busy) return;

        busy = true;
        sync();

        try {
            let loaded = null;

            if (systemId) {
                const state = await request(
                    `/admin/game-systems/${encodeURIComponent(systemId)}/rules/draft`
                );

                if (!state || !own(state, 'draft')) {
                    throw new Error('Не удалось проверить состояние черновика.');
                }

                loaded = state.draft;

                if (loaded && (
                    loaded.system_id !== systemId ||
                    !Number.isInteger(loaded.revision) ||
                    loaded.revision < 1 ||
                    !loaded.rules
                )) {
                    throw new Error('Сервер вернул некорректный черновик.');
                }
            }

            let nextPresets = [];

            if (!loaded) {
                nextPresets = await request(
                    '/admin/game-systems/rules/calculation-presets'
                );

                if (!Array.isArray(nextPresets) || !nextPresets.length) {
                    throw new Error('Не удалось загрузить основы правил.');
                }
            }

            const nextProfile = loaded ? upgrade(loaded.rules) : null;

            profile = nextProfile;
            revision = loaded?.revision ?? null;
            dirty = loaded?.rules.schema_version === 1;
            presets = nextPresets;
            selectedPreset = '';
            sampleLevel = '1';
            samples = {};

            renderBasis();
            render();

            message.textContent = loaded
                ? `Черновик загружен. Ревизия: ${revision}.`
                : 'Выберите основу правил. Создание на сервере ещё не выполнялось.';
        } finally {
            busy = false;
            sync();
        }
    }

    function acceptSaved(draft) {
        if (
            !draft?.rules ||
            !Number.isInteger(draft.revision) ||
            draft.revision < 1 ||
            (systemId && draft.system_id !== systemId)
        ) {
            throw new Error('Ответ сохранения черновика не удалось проверить.');
        }

        profile = upgrade(draft.rules);
        revision = draft.revision;
        dirty = false;
        renderBasis();
        render();
        message.textContent =
            `Сохранён черновик, ревизия ${revision}. Публикация не выполнялась.`;
    }

    return {
        load,
        collect,
        acceptSaved,
        showPage,
        getRevision: () => revision,
        hasUnsaved: () => dirty,
        isBusy: () => busy,
        setParentBusy(value) {
            parentBusy = value;
            sync();
        }
    };
}