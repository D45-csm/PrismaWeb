(() => {
    const filter = document.querySelector('[data-status-filter]');
    if (!filter) return;

    const select = filter.querySelector('select[name="estado"]');
    const trigger = filter.querySelector('.admin-status-trigger');
    const label = trigger.querySelector('[data-status-label]');
    const options = Array.from(filter.querySelectorAll('[data-status-option]'));
    const listbox = filter.querySelector('.admin-status-options');

    const selectedOption = () => options.find(
        (option) => option.dataset.statusOption === select.value,
    );

    const syncSelection = () => {
        const selected = selectedOption();
        if (!selected) return;
        label.textContent = selected.querySelector('strong').textContent;
        options.forEach((option) => {
            option.setAttribute(
                'aria-selected',
                String(option === selected),
            );
        });
    };

    const closeMenu = (returnFocus = false) => {
        listbox.hidden = true;
        filter.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
        if (returnFocus) trigger.focus();
    };

    const openMenu = (focusSelected = false) => {
        listbox.hidden = false;
        filter.classList.add('is-open');
        trigger.setAttribute('aria-expanded', 'true');
        if (focusSelected) selectedOption()?.focus();
    };

    trigger.addEventListener('click', () => {
        if (listbox.hidden) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    trigger.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            openMenu(true);
        }
    });

    options.forEach((option) => {
        option.addEventListener('click', () => {
            select.value = option.dataset.statusOption;
            syncSelection();
            closeMenu(true);
        });

        option.addEventListener('keydown', (event) => {
            const currentIndex = options.indexOf(option);
            let nextIndex = currentIndex;

            if (event.key === 'ArrowDown') nextIndex = (currentIndex + 1) % options.length;
            else if (event.key === 'ArrowUp') {
                nextIndex = (currentIndex - 1 + options.length) % options.length;
            } else if (event.key === 'Home') nextIndex = 0;
            else if (event.key === 'End') nextIndex = options.length - 1;
            else if (event.key === 'Escape') {
                event.preventDefault();
                closeMenu(true);
                return;
            } else if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                option.click();
                return;
            } else if (event.key === 'Tab') {
                closeMenu();
                return;
            } else {
                return;
            }

            event.preventDefault();
            options[nextIndex].focus();
        });
    });

    document.addEventListener('click', (event) => {
        if (!filter.contains(event.target)) closeMenu();
    });

    syncSelection();
    filter.classList.add('is-enhanced');
    trigger.hidden = false;
})();
