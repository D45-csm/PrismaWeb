document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-email-recovery-link]');
    const status = document.querySelector('[data-email-link-status]');
    if (!form || !status) return;

    const parameters = new URLSearchParams(window.location.hash.slice(1));
    const email = parameters.get('email') || '';
    const code = parameters.get('code') || '';
    window.history.replaceState(null, document.title, window.location.pathname + window.location.search);

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || !/^\d{8}$/.test(code)) {
        status.textContent = 'Este enlace no contiene un código válido. Solicita uno nuevo para continuar.';
        return;
    }

    form.elements.recovery_email.value = email;
    form.elements.code.value = code;
    status.textContent = 'Código listo. Te estamos llevando al siguiente paso.';
    form.requestSubmit();
});
