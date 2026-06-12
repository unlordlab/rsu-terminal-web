const THEMES = ["crt", "dark-pro", "light"];
const KEY = "rsu_theme";

export function initTheme() {
    const saved = localStorage.getItem(KEY) || "crt";
    applyTheme(saved);
}

export function applyTheme(name) {
    document.documentElement.setAttribute("data-theme", name);
    localStorage.setItem(KEY, name);
}

export function cycleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "crt";
    const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
    applyTheme(next);
}
