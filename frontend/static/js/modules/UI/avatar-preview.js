// frontend/static/js/modules/UI/avatar-preview.js

export function previewAvatar(event) {
	const input = event.target;
	const file = input.files && input.files[0];
	if (!file) return;

	const img = input.closest('label')?.querySelector('img');
	if (!img) return;

	const reader = new FileReader();

	reader.onload = (e) => {
		img.src = e.target.result;
	};

	reader.onerror = () => {
		console.error('[AVATAR-PREVIEW] read failed', reader.error);
	};

	reader.readAsDataURL(file);
}

window.previewAvatar = previewAvatar;
