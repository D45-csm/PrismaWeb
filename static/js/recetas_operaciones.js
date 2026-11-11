(() => {
    document.querySelectorAll('[data-recipe-operation]').forEach((card) => {
        const maximo = Number(card.dataset.recipeMax || 0);
        const cantidad = card.querySelector('[data-recipe-quantity]');
        const restar = card.querySelector('[data-recipe-decrement]');
        const sumar = card.querySelector('[data-recipe-increment]');
        if (!cantidad || maximo < 1) return;

        const limitar = () => {
            const valor = Number.parseInt(cantidad.value, 10);
            cantidad.value = String(
                Number.isFinite(valor) ? Math.min(maximo, Math.max(1, valor)) : 1,
            );
            restar.disabled = Number(cantidad.value) <= 1;
            sumar.disabled = Number(cantidad.value) >= maximo;
        };

        restar.addEventListener('click', () => {
            cantidad.value = String(Number(cantidad.value) - 1);
            limitar();
        });
        sumar.addEventListener('click', () => {
            cantidad.value = String(Number(cantidad.value) + 1);
            limitar();
        });
        cantidad.addEventListener('change', limitar);
        cantidad.addEventListener('input', limitar);
        limitar();
    });
})();
