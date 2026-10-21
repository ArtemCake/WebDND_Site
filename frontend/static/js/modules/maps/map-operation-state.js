// frontend/static/js/modules/maps/map-operation-state.js

let operationRunning = false;

export function acquireMapOperation() {
	if (operationRunning) return null;

	operationRunning = true;

	const controls = Array.from(document.querySelectorAll(
		'[data-map-action], [data-map-delete], #map-destination-game'
	));
	const previousStates = controls.map(control => ({
		control,
		disabled: control.disabled
	}));

	for (const { control } of previousStates) {
		control.disabled = true;
	}

	let released = false;

	return function releaseMapOperation() {
		if (released) return;
		released = true;

		for (const { control, disabled } of previousStates) {
			control.disabled = disabled;
		}

		operationRunning = false;
	};
}