export function initThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    const htmlElement = document.documentElement;

    toggleBtn.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        htmlElement.setAttribute('data-theme', newTheme);
    });
}