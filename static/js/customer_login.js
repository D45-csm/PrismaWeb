document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.querySelector('[data-password-toggle]');
    if (!toggle) return;

    const password = document.getElementById(toggle.getAttribute('aria-controls'));
    if (!password) return;

    toggle.addEventListener('click', () => {
        const showPassword = password.type === 'password';
        password.type = showPassword ? 'text' : 'password';
        toggle.textContent = showPassword ? 'Ocultar' : 'Mostrar';
        toggle.setAttribute(
            'aria-label',
            showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña',
        );
        toggle.setAttribute('aria-pressed', String(showPassword));
    });
});
