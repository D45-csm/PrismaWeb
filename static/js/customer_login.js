document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
        const password = document.getElementById(toggle.getAttribute('aria-controls'));
        const icon = toggle.querySelector('i');
        if (!password || !icon) return;

        toggle.addEventListener('click', () => {
            const showPassword = password.type === 'password';
            password.type = showPassword ? 'text' : 'password';
            icon.classList.toggle('fa-eye', !showPassword);
            icon.classList.toggle('fa-eye-slash', showPassword);
            icon.classList.add('fa-solid');
            toggle.setAttribute(
                'aria-label',
                `${showPassword ? 'Ocultar' : 'Mostrar'} ${password.labels[0]?.textContent.toLowerCase() || 'contraseña'}`,
            );
            toggle.setAttribute('aria-pressed', String(showPassword));
        });
    });
});
