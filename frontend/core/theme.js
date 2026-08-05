const THEMES = ["crt", "dark-pro", "light", "bubblebath", "polygon-window", "xtal", "isopropophlex", "octogon"];
const STORAGE_KEY = "rsu_theme";

// El identificador va sin diéresis (vale como atributo, como nombre de
// fichero y como clave de localStorage sin sorpresas de codificación); el
// nombre que se enseña sí la lleva.
const NOMBRES = { "octogon": "OCTÖGON" };

export function nombreTema(id) {
    return NOMBRES[id] || (id || "").toUpperCase();
}

export function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY) || "dark-pro";
    applyTheme(saved);
}

export function applyTheme(name) {
    if (!THEMES.includes(name)) name = "dark-pro";
    document.documentElement.setAttribute("data-theme", name);
    localStorage.setItem(STORAGE_KEY, name);
    document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: name } }));
}

export function cycleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark-pro";
    const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
    applyTheme(next);
}

export function getCurrentTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark-pro";
}