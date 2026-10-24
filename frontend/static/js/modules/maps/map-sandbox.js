// frontend/static/js/modules/maps/map-sandbox.js

export function initMapSandbox(root, image) {
	if (!root || root.dataset.initialized === 'true') return;
	root.dataset.initialized = 'true';

	const canvas = root.querySelector('[data-preview-canvas]');
	const ctx = canvas.getContext('2d');
	const mask = document.createElement('canvas');
	const maskCtx = mask.getContext('2d');
	const message = root.querySelector('[data-preview-message]');
	const mode = root.querySelector('[data-preview-mode]');
	const radius = root.querySelector('[data-preview-radius]');
	const memory = root.querySelector('[data-preview-memory]');
	const rowsInput = root.querySelector('[name="rows"]');
	const colsInput = root.querySelector('[name="cols"]');
	const grid = root.querySelector('[name="show_grid"]');
	const fog = root.querySelector('[name="fog_of_war_enabled"]');
	const generate = root.querySelector('[data-preview-generate]');

	let cells = [];
	let origin = null;
	let explored = new Set();
	let rows = 20;
	let cols = 20;
	let timer;
	let controller;
	let sequence = 0;
	let dragging = false;
	let initial = true;
	let ready = false;

	const key = cell => `${cell.q}:${cell.r}`;

	function geometry() {
		const widthUnits = Math.sqrt(3) * (
			cols + (rows > 1 ? 0.5 : 0)
		);
		const heightUnits = 2 + 1.5 * (rows - 1);
		const size = Math.min(
			canvas.width / widthUnits,
			canvas.height / heightUnits
		);

		return {
			size,
			left: (canvas.width - widthUnits * size) / 2,
			top: (canvas.height - heightUnits * size) / 2
		};
	}

	function center(cell, g) {
		return {
			x: g.left + Math.sqrt(3) * g.size * (
				cell.col + 0.5 * (cell.row & 1) + 0.5
			),
			y: g.top + g.size * (1 + 1.5 * cell.row)
		};
	}

	function polygon(context, cell, g) {
		const c = center(cell, g);
		context.beginPath();

		for (let i = 0; i < 6; i += 1) {
			const angle = Math.PI / 180 * (60 * i - 30);
			const x = c.x + g.size * Math.cos(angle);
			const y = c.y + g.size * Math.sin(angle);

			if (i === 0) context.moveTo(x, y);
			else context.lineTo(x, y);
		}

		context.closePath();
	}

	function draw() {
		const hasImage = Boolean(
			image?.getAttribute('src')
			&& image.complete
			&& image.naturalWidth
		);

		const sourceWidth = hasImage ? image.naturalWidth : 1200;
		const sourceHeight = hasImage ? image.naturalHeight : 800;
		const scale = Math.min(
			1, 1600 / sourceWidth, 1600 / sourceHeight
		);
		const width = Math.max(1, Math.round(sourceWidth * scale));
		const height = Math.max(1, Math.round(sourceHeight * scale));

		if (canvas.width !== width || canvas.height !== height) {
			canvas.width = width;
			canvas.height = height;
		}

		ctx.clearRect(0, 0, width, height);
		ctx.fillStyle = '#ddd';
		ctx.fillRect(0, 0, width, height);

		if (hasImage) ctx.drawImage(image, 0, 0, width, height);

		const g = geometry();
		const player = mode.value === 'player';

		if (fog.checked) {
			mask.width = width;
			mask.height = height;
			maskCtx.fillStyle = '#000';
			maskCtx.fillRect(0, 0, width, height);
			maskCtx.globalCompositeOperation = 'destination-out';

			for (const cell of cells) {
				const seen = memory.checked && (
					cell.explored || explored.has(key(cell))
				);
				const visible = ready && cell.visible;

				if (!visible && !seen) continue;

				maskCtx.globalAlpha = visible ? 1 : 0.3;
				polygon(maskCtx, cell, g);
				maskCtx.fill();
			}

			maskCtx.globalAlpha = 1;
			maskCtx.globalCompositeOperation = 'source-over';

			ctx.globalAlpha = player ? 1 : 0.4;
			ctx.drawImage(mask, 0, 0);
			ctx.globalAlpha = 1;
		}

		if (grid.checked) {
			ctx.strokeStyle = 'rgba(230, 230, 230, 0.8)';
			ctx.lineWidth = 1;

			for (const cell of cells) {
				const seen = memory.checked && (
					cell.explored || explored.has(key(cell))
				);

				if (
					player && fog.checked
					&& !(ready && cell.visible) && !seen
				) continue;

				polygon(ctx, cell, g);
				ctx.stroke();
			}
		}

		if (origin) {
			const cell = cells.find(cell => key(cell) === key(origin));

			if (cell) {
				const c = center(cell, g);
				ctx.beginPath();
				ctx.arc(c.x, c.y, Math.max(3, g.size * 0.35), 0, 2 * Math.PI);
				ctx.fillStyle = '#27a9ff';
				ctx.fill();
				ctx.strokeStyle = '#fff';
				ctx.lineWidth = 2;
				ctx.stroke();
			}
		}
	}

	async function post(url, data, signal) {
		const csrf = document.querySelector(
			'meta[name="csrf-token"]'
		)?.content;

		if (!csrf) {
			throw new Error('Не найден защитный токен. Обновите страницу.');
		}

		const response = await fetch(url, {
			method: 'POST',
			credentials: 'include',
			redirect: 'error',
			signal,
			headers: {
				'Accept': 'application/json',
				'Content-Type': 'application/json',
				'X-CSRF-Token': csrf
			},
			body: JSON.stringify(data)
		});

		const result = await response.json().catch(() => null);

		if (!response.ok) {
			throw new Error(
				typeof result?.detail === 'string'
					? result.detail
					: 'Не удалось получить данные предпросмотра.'
			);
		}

		return result;
	}

	async function refresh(requestId) {
		if (
			!rowsInput.checkValidity()
			|| !colsInput.checkValidity()
			|| !radius.checkValidity()
		) {
			message.textContent = 'Проверьте параметры сетки и радиуса.';
			return;
		}

		controller = new AbortController();
		message.textContent = 'Расчёт тестовой видимости…';

		try {
			const data = await post('/maps/preview', {
				game_id: root.dataset.gameId,
				map_id: root.dataset.mapId || null,
				rows: Number(rowsInput.value),
				cols: Number(colsInput.value),
				origin_q: origin?.q ?? null,
				origin_r: origin?.r ?? null,
				vision_radius: Number(radius.value)
			}, controller.signal);

			if (requestId !== sequence) return;

			cells = data.hexes;
			rows = data.rows;
			cols = data.cols;
			rowsInput.value = rows;
			colsInput.value = cols;

			if (root.dataset.mapId) {
				rowsInput.readOnly = data.persisted_grid;
				colsInput.readOnly = data.persisted_grid;

				if (initial) grid.checked = data.show_grid;
				if (generate) generate.hidden = data.persisted_grid;
			}

			for (const cell of cells) {
				if (cell.visible) explored.add(key(cell));
			}

			initial = false;
			ready = true;

			message.textContent = origin
				? 'Тестовый обзор рассчитан. Изменения не записаны в игру.'
				: 'Нажмите на карту, чтобы поставить тестовую фишку.';

			if (root.dataset.mapId && !data.persisted_grid) {
				message.textContent +=
					' У этой карты нет сохранённой сетки: показана тестовая.';
			}

			draw();
		} catch (error) {
			if (requestId !== sequence || error.name === 'AbortError') return;

			message.textContent = error.message;
			ready = false;
			draw();
		}
	}

	function schedule() {
		clearTimeout(timer);
		controller?.abort();
		const requestId = ++sequence;
		ready = false;
		draw();

		timer = setTimeout(() => refresh(requestId), 160);
	}

	function place(event) {
		const rect = canvas.getBoundingClientRect();
		const x = (event.clientX - rect.left) * canvas.width / rect.width;
		const y = (event.clientY - rect.top) * canvas.height / rect.height;
		const g = geometry();

		// Выбираем именно содержащий точку гекс,
		// а не ближайшую клетку за пределами сетки.
		for (const cell of cells) {
			polygon(ctx, cell, g);

			if (ctx.isPointInPath(x, y)) {
				if (origin && key(origin) === key(cell)) return;

				origin = { q: cell.q, r: cell.r };
				schedule();
				return;
			}
		}
	}

	canvas.addEventListener('pointerdown', event => {
		if (event.button !== 0) return;
		canvas.focus();
		dragging = true;
		canvas.setPointerCapture(event.pointerId);
		place(event);
	});

	canvas.addEventListener('pointermove', event => {
		if (dragging) place(event);
	});

	for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
		canvas.addEventListener(type, () => {
			dragging = false;
		});
	}

	canvas.addEventListener('keydown', event => {
		const directions = {
			ArrowLeft: [-1, 0],
			ArrowRight: [1, 0],
			ArrowUp: [0, -1],
			ArrowDown: [0, 1]
		};

		const delta = directions[event.key];
		if (!delta || !origin) return;
		event.preventDefault();

		const current = cells.find(cell => key(cell) === key(origin));
		const next = current && cells.find(cell => (
			cell.col === current.col + delta[0]
			&& cell.row === current.row + delta[1]
		));

		if (next) {
			origin = { q: next.q, r: next.r };
			schedule();
		}
	});

	for (const input of [rowsInput, colsInput]) {
		input.addEventListener('change', () => {
			origin = null;
			explored = new Set();
			schedule();
		});
	}

	radius.addEventListener('change', schedule);

	for (const input of [grid, fog, mode, memory]) {
		input.addEventListener('change', draw);
	}

	root.querySelector('[data-preview-reset]').addEventListener('click', () => {
		origin = null;
		explored = new Set();
		schedule();
	});

	generate?.addEventListener('click', async () => {
		if (!rowsInput.reportValidity() || !colsInput.reportValidity()) return;

		if (!window.confirm('Создать и сохранить сетку на этой карте?')) return;

		generate.disabled = true;

		try {
			await post(
				`/maps/${encodeURIComponent(root.dataset.mapId)}/hex-grid`,
				{
					rows: Number(rowsInput.value),
					cols: Number(colsInput.value)
				}
			);

			origin = null;
			explored = new Set();
			schedule();
		} catch (error) {
			message.textContent = error.message
				+ ' Перед повтором обновите страницу: сетка могла сохраниться.';
		} finally {
			generate.disabled = false;
		}
	});

	image?.addEventListener('load', draw);
	image?.addEventListener('error', draw);

	if (image) {
		const observer = new MutationObserver(draw);
		observer.observe(image, {
			attributes: true,
			attributeFilter: ['src']
		});

		window.addEventListener('pagehide', () => {
			observer.disconnect();
		}, { once: true });
	}

	window.addEventListener('pagehide', () => {
		clearTimeout(timer);
		controller?.abort();
	}, { once: true });

	schedule();
}