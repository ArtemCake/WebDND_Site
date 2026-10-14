// frontend/static/js/modules/UI/sticky-navigation.js

const SCROLL_THRESHOLD = 10;
const SCROLLED_CLASS = 'navbar-main--scrolled';

function updateNavShadow(nav) {
	if (window.scrollY > SCROLL_THRESHOLD) {
		nav.classList.add(SCROLLED_CLASS);
	} else {
		nav.classList.remove(SCROLLED_CLASS);
	}
}

export function initStickyNavigation() {
	const nav = document.querySelector('.main-nav');
	if (!nav) return;

	updateNavShadow(nav);

	window.addEventListener('scroll', () => updateNavShadow(nav), { passive: true });
}