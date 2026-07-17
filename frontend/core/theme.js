const THEMES = ["crt", "dark-pro", "light", "bubblebath", "polygon-window"];
const STORAGE_KEY = "rsu_theme";

export function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY) || "crt";
    applyTheme(saved);
}

export function applyTheme(name) {
    if (!THEMES.includes(name)) name = "crt";
    document.documentElement.setAttribute("data-theme", name);
    localStorage.setItem(STORAGE_KEY, name);
    document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: name } }));
}

export function cycleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "crt";
    const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
    applyTheme(next);
}

export function getCurrentTheme() {
    return document.documentElement.getAttribute("data-theme") || "crt";
}