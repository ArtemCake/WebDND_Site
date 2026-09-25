// frontend/static/js/modules/auth.js

export function showMessage(formEl, type, text) {
  // Ищем по всему документу — блок теперь стоит отдельно от формы
  const box = document.getElementById('message-box');
  if (box) {
    box.innerHTML = `<div class="alert alert-${type}" role="alert">${text}</div>`;
  }
}

export function scrollToMessageBox() {
  const messageBox = document.getElementById('message-box');
  if (messageBox) {
    setTimeout(() => {
      messageBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 150);
  }
}

export function setupAuthHandlers() {
  document.body.addEventListener('htmx:beforeOnLoad', function (evt) {
    const path = evt.detail.requestConfig?.path;
    if (!path || !path.startsWith('/auth/')) return;

    // Блокируем HTMX от вставки ответа в целевой элемент
    evt.preventDefault();

    const xhr = evt.detail.xhr;
    const targetForm = evt.detail.requestConfig.elt;
    const status = xhr.status;

    let data = {};
    try {
      if (xhr.responseText) {
        data = JSON.parse(xhr.responseText);
      }
    } catch (e) {
      data = { error: xhr.responseText || 'Неизвестный формат ответа сервера' };
    }

    document.getElementById('register-prompt')?.classList.remove('active');
    document.getElementById('verify-prompt')?.classList.remove('active');

    let messageText = '';
    let isError = true;

    if (status === 201) {
      targetForm.reset();
      messageText = 'Аккаунт создан! Письмо отправлено.';
      isError = false;

    } else if (status === 200) {
      // Для регистрации 200 — это не «успех», если нет токена
      if (data.access_token) {
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('refreshToken', data.refresh_token);

        showMessage(targetForm, 'success', 'Добро пожаловать! Перенаправляем...');
        setTimeout(() => {
          window.location.href = '/profile';
        }, 300);
        return;
      } else {
        messageText = data.error || 'Сервер вернул ответ без токена. Попробуйте снова.';
      }

    } else if (status === 403) {
      messageText = 'Необходимо подтвердить адрес электронной почты.';
      document.getElementById('verify-prompt')?.classList.add('active');
      isError = true;

    } else if (status === 404) {
      messageText = 'Аккаунт не найден.';
      document.getElementById('register-prompt')?.classList.add('active');
      isError = true;

    } else if (status === 401) {
      let rawDetail = data.detail || '';
      const sanitizedDetail = rawDetail.replace(
        /[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+\.[A-Za-z0-9\-_.]+/g,
        '[токен скрыт]'
      );
      messageText = data.error || sanitizedDetail || 'Ошибка регистрации.';
      isError = true;

    } else {
      messageText = data.error || data.detail || `Ошибка сервера (${status})`;
      isError = true;
    }

    showMessage(targetForm, isError ? 'danger' : 'success', messageText);
    scrollToMessageBox();
  });
}