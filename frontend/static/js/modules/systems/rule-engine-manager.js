// frontend/static/js/modules/systems/rule-engine-manager.js

import {createRulesEditor} from './game-system-rules-editor.js';
import {
    blocksEngineMutation,
    createRuleEngineApi
} from './rule-engine-api.js';

function node(tag, text, className) {
    const value = document.createElement(tag);
    if (text !== undefined) value.textContent = text;
    if (className) value.className = className;
    return value;
}

export function mountRuleEngineManager(host, {
    request,
    isAllowed
}) {
    if (!host) return null;

    const api = createRuleEngineApi(request);

    // Только постоянная разметка.
    // Данные сервера вставляются через textContent и value.
    host.innerHTML = `
        <details class="system-editor__details">
            <summary>Мои движки правил</summary>

            <p class="profile-note">
                Здесь находятся ваши движки, включая неопубликованные.
                Создание движка не создаёт игровую систему.
            </p>

            <button type="button" class="btn btn-outline-primary"
                    data-engines-refresh>
                Загрузить мои движки
            </button>

            <button type="button" class="btn btn-primary"
                    data-engine-new>
                Новый движок
            </button>

            <p data-engines-message role="status"
               aria-live="polite"></p>

            <div class="admin-sections" data-engines-list></div>
            <div data-engine-editor></div>
        </details>
    `;

    const status = host.querySelector('[data-engines-message]');
    const list = host.querySelector('[data-engines-list]');
    const area = host.querySelector('[data-engine-editor]');
    const refresh = host.querySelector('[data-engines-refresh]');
    const newButton = host.querySelector('[data-engine-new]');

    let engines = [];
    let engine = null;
    let draft = null;
    let versions = [];
    let editor = null;
    let form = null;

    let busy = false;
    let editorBusy = false;
    let loaded = false;
    let blocked = false;
    let metadataDirty = false;

    function working() {
        return busy || editorBusy;
    }

    function unsaved() {
        return metadataDirty || Boolean(editor?.hasUnsaved());
    }

    function canDiscard() {
        return !unsaved() || window.confirm(
            'Перейти к другому черновику? ' +
            'Несохранённые изменения движка будут потеряны.'
        );
    }

    function alreadyPublished() {
        return draft && versions.some(
            (item) => item.source_draft_revision === draft.revision
        );
    }

    function sync() {
        const disabled = working() || !isAllowed();

        refresh.disabled = disabled;
        newButton.disabled = disabled || blocked;

        list.querySelectorAll('button').forEach((button) => {
            button.disabled = disabled;
        });

        if (!form) return;

        form.querySelector('[data-engine-metadata]').disabled =
            disabled;

        form.querySelector('[data-engine-save]').disabled =
            disabled || !loaded || blocked;

        form.querySelector('[data-engine-publish]').disabled =
            disabled ||
            !loaded ||
            blocked ||
            !engine ||
            unsaved() ||
            Boolean(alreadyPublished());

        editor?.setParentBusy(disabled || !loaded);
    }

    async function run(action, mutation = false, editing = true) {
        if (working() || !isAllowed()) return;
        if (mutation && blocked) return;

        busy = true;
        sync();

        try {
            await action();
        } catch (error) {
            if (mutation && blocksEngineMutation(error, editing)) {
                blocked = true;
            }

            status.textContent =
                (error.message || 'Не удалось выполнить действие.') +
                (blocked
                    ? ' Повторная запись заблокирована. ' +
                      'Загрузите список и откройте сохранённый движок ' +
                      'для сверки. Введённые данные оставлены в форме.'
                    : '');
        } finally {
            busy = false;
            sync();
        }
    }

    function renderList() {
        list.replaceChildren();

        for (const item of engines) {
            const card = node('article', undefined, 'admin-card');
            const open = node(
                'button',
                'Открыть черновик',
                'btn btn-outline-primary'
            );

            open.type = 'button';
            open.addEventListener('click', () => {
                if (working() || !isAllowed() || !canDiscard()) return;

                void run(async () => {
                    // Старую форму не заменяем до успешного чтения.
                    const state = await api.read(item.id);

                    if (state.draft.rules_engine_version !== '1.0') {
                        throw new Error(
                            'Этот интерфейс поддерживает ' +
                            'исполнитель версии 1.0.'
                        );
                    }

                    buildForm(item, state.draft, state.versions);
                    blocked = false;
                    status.textContent =
                        `Загружен черновик, ревизия ${draft.revision}.`;
                });
            });

            card.append(
                node('h3', item.name),
                node(
                    'p',
                    `${item.slug} · ` +
                    (item.visibility === 'public'
                        ? 'Публичный'
                        : 'Приватный') +
                    (item.is_active === false ? ' · Неактивный' : '')
                ),
                node('p', item.description || 'Без описания'),
                open
            );

            list.append(card);
        }

        if (!engines.length) {
            list.append(node('p', 'Ваших движков пока нет.'));
        }

        sync();
    }

    function showVersionState() {
        const info = form?.querySelector('[data-engine-version-state]');
        if (!info) return;

        const numbers = versions
            .map((item) => item.version_number)
            .sort((a, b) => a - b);

        info.textContent = [
            draft ? `Ревизия черновика: ${draft.revision}.` : 'Новый движок.',
            numbers.length
                ? `Публикации: ${numbers.join(', ')}.`
                : 'Публикаций пока нет.',
            alreadyPublished()
                ? 'Текущая ревизия уже опубликована.'
                : '',
            unsaved()
                ? 'Есть несохранённые изменения.'
                : ''
        ].filter(Boolean).join(' ');
    }

    function buildForm(nextEngine, nextDraft, nextVersions = []) {
        engine = nextEngine;
        draft = nextDraft;
        versions = nextVersions;
        loaded = false;
        metadataDirty = false;
        editor = null;

        area.innerHTML = `
            <form class="system-editor" novalidate>
                <h3 data-engine-heading></h3>

                <fieldset data-engine-metadata>
                    <legend>Карточка движка</legend>

                    <label class="system-editor__field">
                        Название
                        <input name="name" required maxlength="100">
                    </label>

                    <label class="system-editor__field">
                        Код
                        <input name="slug" required maxlength="100"
                               pattern="[a-z0-9]+((_|-)[a-z0-9]+)*"
                               autocomplete="off" spellcheck="false">
                    </label>

                    <label class="system-editor__field">
                        Описание
                        <textarea name="description" rows="3"></textarea>
                    </label>

                    <label class="system-editor__field">
                        Видимость
                        <select name="visibility">
                            <option value="private">Приватный</option>
                            <option value="public">Публичный</option>
                        </select>
                    </label>

                    <p class="profile-note">
                        Видимость задаётся при создании.
                        Публичная публикация может использоваться
                        другими администраторами в рамках текущего доступа.
                    </p>
                </fieldset>

                <p data-engine-card-note class="profile-note"></p>

                <div data-engine-rules>
                    <div data-rules-basis></div>
                    <p data-rules-message role="status"
                       aria-live="polite"></p>
                    <fieldset data-rules-controls disabled>
                        <legend>Правила движка</legend>
                        <div data-rules-body></div>
                    </fieldset>
                </div>

                <p data-engine-version-state role="status"
                   aria-live="polite"></p>

                <button type="submit" class="btn btn-primary"
                        data-engine-save>
                    Сохранить черновик
                </button>

                <button type="button" class="btn btn-outline-primary"
                        data-engine-publish>
                    Опубликовать сохранённую ревизию
                </button>
            </form>
        `;

        form = area.querySelector('form');
        form.querySelector('[data-engine-heading]').textContent =
            engine ? engine.name : 'Новый движок правил';

        const values = engine || {
            name: '',
            slug: `engine-${Date.now().toString(36)}-` +
                Math.random().toString(36).slice(2, 8),
            description: '',
            visibility: 'private'
        };

        for (const name of ['name', 'slug', 'description', 'visibility']) {
            const control = form.elements.namedItem(name);
            control.value = values[name] ?? '';

            if (engine) {
                if (control instanceof HTMLSelectElement) {
                    control.disabled = true;
                } else {
                    control.readOnly = true;
                }
            }
        }

        form.querySelector('[data-engine-card-note]').textContent =
            engine
                ? 'Карточка показана только для чтения: текущий API ' +
                  'сохраняет правила, но не изменяет название и видимость.'
                : 'Выберите расчётный пресет и настройте его правила. ' +
                  'Это не полный справочник D&D или Pathfinder.';

        editor = createRulesEditor(
            form.querySelector('[data-engine-rules]'),
            {
                request,
                systemId: null,
                standaloneOnly: true,
                singlePage: true,
                getExecutorVersion: () =>
                    draft?.rules_engine_version || '1.0',
                onBusy(value) {
                    editorBusy = value;
                    sync();
                },
                onChange() {
                    showVersionState();
                    sync();
                }
            }
        );

        form.addEventListener('input', (event) => {
            if (!(event.target instanceof HTMLElement)) return;
            if (event.target.dataset.sample === 'true') return;

            if (event.target.closest('[data-engine-metadata]')) {
                metadataDirty = true;
            }

            showVersionState();
            sync();
        });

        form.addEventListener('change', () => {
            showVersionState();
            sync();
        });

        form.addEventListener('submit', save);
        form.querySelector('[data-engine-publish]')
            .addEventListener('click', publish);

        if (draft) {
            editor.acceptEngineDraft(draft);
            loaded = true;
        }

        showVersionState();
        sync();
    }

    function save(event) {
        event.preventDefault();

        if (working() || !loaded || blocked || !isAllowed()) return;

        let rules;
        let data;

        // Локальная валидация до начала записывающего запроса.
        try {
            if (!form.reportValidity()) return;

            rules = editor.collect();

            if (!engine) {
                const name = form.elements.namedItem('name').value.trim();
                const slug = form.elements.namedItem('slug').value.trim();

                if (!name || !slug) {
                    throw new Error(
                        'Название и код не должны состоять из пробелов.'
                    );
                }

                data = {
                    name,
                    slug,
                    description:
                        form.elements.namedItem('description')
                            .value.trim() || null,
                    visibility:
                        form.elements.namedItem('visibility').value,
                    rules_engine_version: '1.0',
                    rules
                };
            }
        } catch (error) {
            status.textContent = error.message;
            return;
        }

        const editing = Boolean(engine);

        void run(async () => {
            if (editing) {
                const saved = await api.save(
                    engine.id,
                    rules,
                    draft.revision
                );

                editor.acceptEngineDraft(saved);
                draft = saved;
            } else {
                const saved = await api.create(data);

                // Сначала проверяем совместимость ответа с редактором.
                editor.acceptEngineDraft(saved.draft);

                engines = [...engines, saved.engine];
                buildForm(saved.engine, saved.draft);
                renderList();
            }

            metadataDirty = false;
            showVersionState();
            status.textContent =
                'Черновик движка сохранён. Публикация не выполнялась.';
        }, true, editing);
    }

    function publish() {
        if (
            working() || !isAllowed() || !loaded || blocked ||
            !engine || unsaved() || alreadyPublished()
        ) {
            return;
        }

        if (!window.confirm(
            `Опубликовать ревизию ${draft.revision} ` +
            `движка «${engine.name}»? ` +
            'Опубликованный снимок нельзя будет редактировать. ' +
            'Существующие системы автоматически не обновятся.'
        )) {
            return;
        }

        const engineId = engine.id;
        const expectedRevision = draft.revision;

        void run(async () => {
            const saved = await api.publish(
                engineId,
                expectedRevision
            );

            versions = [...versions, saved];
            showVersionState();

            status.textContent =
                `Опубликована версия №${saved.version_number}. ` +
                'Её можно выбрать при создании игровой системы.';
        }, true);
    }

    refresh.addEventListener('click', () => {
        void run(async () => {
            engines = await api.listOwned();
            renderList();

            status.textContent = blocked
                ? 'Список обновлён. Откройте сохранённый движок ' +
                  'и сверьте состояние перед новой записью.'
                : `Загружено ваших движков: ${engines.length}.`;
        });
    });

    newButton.addEventListener('click', () => {
        if (
            working() || blocked ||
            !isAllowed() || !canDiscard()
        ) {
            return;
        }

        void run(async () => {
            buildForm(null, null);
            await editor.load();

            loaded = true;
            showVersionState();
            status.textContent =
                'Выберите пресет и заполните карточку движка.';
        });
    });

    window.addEventListener('beforeunload', (event) => {
        if (!working() && !unsaved()) return;

        event.preventDefault();
        event.returnValue = '';
    });

    sync();

    return {
        isBusy: working,
        sync
    };
}