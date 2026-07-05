// static/js/modules/cookieBanner.js

class CookieBanner {
    constructor() {
        this.banner = document.getElementById('cookie-banner');
        this.acceptBtn = document.getElementById('accept-cookie-btn');

        if (!this.banner || !this.acceptBtn) {
            console.warn('Элементы cookie-баннера не найдены.');
            return;
        }

        // ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ КЛАССА
        this.init();
    }

    init() {
        if (!localStorage.getItem('cookies_accepted')) {
            this.show();
        } else {
            this.hide();
        }

        // Просто передаем ссылку на метод, контекст уже верный
        this.acceptBtn.addEventListener('click', this.onAccept);
    }

    show() {
        this.banner.style.display = 'flex';
    }

    hide() {
        this.banner.style.display = 'none';
    }

    // ИЗМЕНЕННЫЙ МЕТОД:
    // Объявлен как свойство со стрелочной функцией
    onAccept = () => {
        localStorage.setItem('cookies_accepted', 'true');
        this.hide(); // Контекст this здесь правильный
    }
}

export default CookieBanner;