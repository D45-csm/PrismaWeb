(() => {
    const toggle = document.querySelector("[data-admin-nav-toggle]");
    if (!toggle) return;

    const menu = document.getElementById(toggle.getAttribute("aria-controls"));
    if (!menu) {
        console.error("No se encontró el menú de navegación administrativa.");
        return;
    }

    const setMenuOpen = (isOpen) => {
        menu.classList.toggle("show", isOpen);
        toggle.classList.toggle("is-open", isOpen);
        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.setAttribute(
            "aria-label",
            isOpen ? "Cerrar menú de administración" : "Abrir menú de administración",
        );
    };

    toggle.addEventListener("click", () => {
        setMenuOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    menu.addEventListener("click", (event) => {
        if (event.target.closest("a") && window.matchMedia("(max-width: 991.98px)").matches) {
            setMenuOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
            setMenuOpen(false);
            toggle.focus();
        }
    });

    window.addEventListener("resize", () => {
        if (window.matchMedia("(min-width: 992px)").matches) setMenuOpen(false);
    });
})();
