// frontend/static/js/modules/network-error-handler.js

import { showMessage, scrollToMessageBox } from './auth.js';

function extractErrorMessage(xhr) {
	let msg = 'Неизвестная ошибка сети.';
	try {
		if (xhr.responseText) {
			const data = JSON.parse(xhr.responseText);
			return data.error || data.detail || xhr.statusText;
		}
	} catch (_) {}
	return msg;
}

export function initNetworkErrorHandlers() {
	document.body.addEventListener('htmx:responseError', function(evt) {
		const errorMsg = extractErrorMessage(evt.detail.xhr);
		console.error(`[NETWORK][HTTP-${evt.detail.xhr.status}] ${errorMsg}`, evt.detail);
		showMessage(evt.detail.requestConfig.elt, 'danger', `Ошибка (${evt.detail.xhr.status}): ${errorMsg}`);
		scrollToMessageBox();
	});

	document.body.addEventListener('htmx:xhr:abort', function(evt) {
		console.warn('[NETWORK][ABORTED] Request was aborted.', evt.detail);
		showMessage(evt.detail.elt, 'danger', 'Соединение прервано. Проверьте сеть.');
		scrollToMessageBox();
	});

	document.body.addEventListener('htmx:timeout', function(evt) {
		console.error('[NETWORK][TIMEOUT] Server did not respond in time.', evt.detail);
		showMessage(evt.detail.elt, 'danger', 'Превышено время ожидания ответа сервера.');
		scrollToMessageBox();
	});

	document.body.addEventListener('htmx:beforeSwap', function(evt) {
		if (evt.detail.targetError && evt.detail.xhr.status >= 400) {
			evt.detail.shouldSwap = false;
			showMessage(evt.detail.elt, 'danger', 'Внутренняя ошибка приложения. Обратитесь к администратору.');
			scrollToMessageBox();
		}
	});
}