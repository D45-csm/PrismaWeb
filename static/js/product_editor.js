document.querySelectorAll('.product-image-field input[type="file"]').forEach((input) => {
    input.addEventListener('change', () => {
        const preview = input.closest('.product-image-field').querySelector('.product-image-preview');
        const file = input.files?.[0];
        if (!file) return;
        preview.src = URL.createObjectURL(file);
        preview.hidden = false;
    });
});
