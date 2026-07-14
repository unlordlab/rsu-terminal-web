// ── THEME MAKER (solo Admin) ────────────────────────────────────────────────
//
// Herramienta para diseñar nuevos temas sin tener que pedírselo a Claude cada
// vez — elige colores, tipografía y efectos, ve una vista previa en vivo
// contra widgets realistas de la terminal, y exporta el CSS ya listo para
// pegar en frontend/themes/<nombre>.css.
//
// DELIBERADAMENTE sin backend: todo vive en localStorage (borrador actual) y
// el "guardado" real es exportar el CSS y pegarlo a mano, igual que con
// cualquier otro archivo de este proyecto — no le doy al backend permiso de
// escritura sobre el propio código fuente del frontend, sería una superficie
// de riesgo rara para una herramienta que se usa de higos a brevas.

const FUENTES_DISPONIBLES = [
    { valor: "'VT323', monospace",              etiqueta: 'VT323 (retro/CRT)' },
    { valor: "'Share Tech Mono', monospace",    etiqueta: 'Share Tech Mono' },
    { valor: "'JetBrains Mono', monospace",     etiqueta: 'JetBrains Mono' },
    { valor: "'Space Mono', monospace",         etiqueta: 'Space Mono' },
    { valor: "'Inter', sans-serif",             etiqueta: 'Inter (sans, no monoespaciada)' },
    { valor: 'custom',                          etiqueta: 'Personalizada (Google Fonts)...' },
];

const DRAFT_KEY = 'rsu_theme_maker_draft';

const DEFAULT_DRAFT = {
    nombre: 'mi-tema',
    bg: '#0a0a0d', surface: '#131318', surface2: '#1c1c23',
    borderColor: '#ffffff', borderOpacity: 12,
    accent: '#00ffad', secondary: '#00d9ff',
    text: '#e8e8ec', muted: '#7a7a85',
    fuente: FUENTES_DISPONIBLES[2].valor, fuenteCustom: '',
    scanlines: false, glow: true,
};

function cargarDraft() {
    try {
        const raw = localStorage.getItem(DRAFT_KEY);
        return raw ? { ...DEFAULT_DRAFT, ...JSON.parse(raw) } : { ...DEFAULT_DRAFT };
    } catch (e) {
        return { ...DEFAULT_DRAFT };
    }
}

function guardarDraft(draft) {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

function hexToRgba(hex, opacityPct) {
    const h = hex.replace('#', '');
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${(opacityPct / 100).toFixed(2)})`;
}

function construirCSS(draft) {
    const fuenteFinal = draft.fuente === 'custom'
        ? `'${draft.fuenteCustom || 'Mi Fuente'}', monospace`
        : draft.fuente;
    const scanlinesVal = draft.scanlines
        ? `repeating-linear-gradient(\n    0deg,\n    rgba(0,0,0,0.18) 0px,\n    rgba(0,0,0,0.18) 1px,\n    transparent 1px,\n    transparent 2px\n  )`
        : 'none';
    const glowAccent = draft.glow ? `0 0 8px ${hexToRgba(draft.accent, 40)}` : 'none';
    const glowText   = draft.glow ? `0 0 6px ${hexToRgba(draft.accent, 25)}` : 'none';

    return `[data-theme="${draft.nombre}"] {
  --color-bg:        ${draft.bg};
  --color-surface:   ${draft.surface};
  --color-surface2:  ${draft.surface2};
  --color-border:    ${hexToRgba(draft.borderColor, draft.borderOpacity)};
  --color-accent:    ${draft.accent};
  --color-secondary: ${draft.secondary};
  --color-text:      ${draft.text};
  --color-muted:     ${draft.muted};

  --font-mono:  ${fuenteFinal};
  --font-size:  14px;

  --scanlines:   ${scanlinesVal};

  --glow-accent: ${glowAccent};
  --glow-text:   ${glowText};
}
`;
}

export async function renderThemeMaker(content) {
    let draft = cargarDraft();

    content.innerHTML = `
        <div style="display:grid;grid-template-columns:340px 1fr;gap:1.5rem;align-items:start;">
            <div id="tm-controls" style="display:flex;flex-direction:column;gap:14px;"></div>
            <div id="tm-preview" style="position:sticky;top:1rem;"></div>
        </div>
        <div style="margin-top:1.5rem;">
            <button id="tm-export-btn" style="background:var(--color-accent);color:var(--color-bg);border:none;border-radius:var(--radius);padding:10px 18px;font-family:var(--font-mono);font-size:12px;font-weight:600;cursor:pointer;">EXPORTAR CSS</button>
            <button id="tm-reset-btn" style="background:transparent;color:var(--color-muted);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px 18px;font-family:var(--font-mono);font-size:12px;cursor:pointer;margin-left:8px;">Reiniciar borrador</button>
        </div>
        <div id="tm-export-output" style="margin-top:1rem;display:none;"></div>
    `;

    const controls = content.querySelector('#tm-controls');
    const preview   = content.querySelector('#tm-preview');

    function campoColor(id, label, value) {
        return `<div>
            <label style="display:block;color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:4px;">${label}</label>
            <div style="display:flex;gap:6px;align-items:center;">
                <input type="color" id="${id}" value="${value}" style="width:36px;height:30px;border:1px solid var(--color-border);border-radius:4px;background:none;cursor:pointer;padding:0;">
                <input type="text" id="${id}-hex" value="${value}" style="flex:1;background:var(--color-bg);border:1px solid var(--color-border);border-radius:4px;padding:6px 8px;color:var(--color-text);font-family:var(--font-mono);font-size:11px;">
            </div>
        </div>`;
    }

    function renderControls() {
        controls.innerHTML = `
            <div>
                <label style="display:block;color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:4px;">NOMBRE DEL TEMA (id interno, sin espacios)</label>
                <input type="text" id="tm-nombre" value="${draft.nombre}" style="width:100%;background:var(--color-bg);border:1px solid var(--color-border);border-radius:4px;padding:7px 9px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">
            </div>

            <div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;border-top:1px solid var(--color-border);padding-top:10px;">SUPERFICIES</div>
            ${campoColor('tm-bg', 'Fondo (--color-bg)', draft.bg)}
            ${campoColor('tm-surface', 'Superficie / tarjetas (--color-surface)', draft.surface)}
            ${campoColor('tm-surface2', 'Superficie secundaria (--color-surface2)', draft.surface2)}
            <div>
                <label style="display:block;color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:4px;">Borde — color + opacidad (${draft.borderOpacity}%)</label>
                <div style="display:flex;gap:6px;align-items:center;">
                    <input type="color" id="tm-borderColor" value="${draft.borderColor}" style="width:36px;height:30px;border:1px solid var(--color-border);border-radius:4px;background:none;cursor:pointer;padding:0;">
                    <input type="range" id="tm-borderOpacity" min="0" max="100" value="${draft.borderOpacity}" style="flex:1;">
                </div>
            </div>

            <div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;border-top:1px solid var(--color-border);padding-top:10px;">ACENTOS</div>
            ${campoColor('tm-accent', 'Acento principal (--color-accent)', draft.accent)}
            ${campoColor('tm-secondary', 'Acento secundario (--color-secondary)', draft.secondary)}

            <div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;border-top:1px solid var(--color-border);padding-top:10px;">TEXTO</div>
            ${campoColor('tm-text', 'Texto principal (--color-text)', draft.text)}
            ${campoColor('tm-muted', 'Texto secundario (--color-muted)', draft.muted)}

            <div style="color:var(--color-muted);font-size:10px;letter-spacing:0.08em;border-top:1px solid var(--color-border);padding-top:10px;">TIPOGRAFÍA Y EFECTOS</div>
            <div>
                <label style="display:block;color:var(--color-muted);font-size:10px;letter-spacing:0.06em;margin-bottom:4px;">Fuente (--font-mono)</label>
                <select id="tm-fuente" style="width:100%;background:var(--color-bg);border:1px solid var(--color-border);border-radius:4px;padding:7px 9px;color:var(--color-text);font-family:var(--font-mono);font-size:12px;">
                    ${FUENTES_DISPONIBLES.map(f => `<option value="${f.valor}" ${f.valor === draft.fuente ? 'selected' : ''}>${f.etiqueta}</option>`).join('')}
                </select>
                ${draft.fuente === 'custom' ? `
                <input type="text" id="tm-fuente-custom" placeholder="Nombre exacto en Google Fonts, ej: Sora" value="${draft.fuenteCustom}"
                    style="width:100%;margin-top:6px;background:var(--color-bg);border:1px solid var(--color-border);border-radius:4px;padding:7px 9px;color:var(--color-text);font-family:var(--font-mono);font-size:11px;">
                <div style="color:var(--color-muted);font-size:9px;margin-top:4px;">⚠ Si no está ya cargada en index.html, hay que añadirla a mano al &lt;link&gt; de Google Fonts.</div>
                ` : ''}
            </div>
            <label style="display:flex;align-items:center;gap:8px;color:var(--color-text);font-size:12px;cursor:pointer;">
                <input type="checkbox" id="tm-scanlines" ${draft.scanlines ? 'checked' : ''}> Líneas de escaneo (efecto CRT)
            </label>
            <label style="display:flex;align-items:center;gap:8px;color:var(--color-text);font-size:12px;cursor:pointer;">
                <input type="checkbox" id="tm-glow" ${draft.glow ? 'checked' : ''}> Resplandor en acentos (glow, derivado del acento principal)
            </label>
        `;

        // Sincronizar cada par color-picker + input de texto hex, y disparar
        // actualización de la vista previa en cada cambio. IMPORTANTE: usa
        // onChange(true) (solo repintar la vista previa) — nunca reconstruir
        // el panel de controles aquí, porque eso reemplaza el propio <input
        // type="color"> mientras su desplegable nativo está abierto, y el
        // navegador lo cierra de inmediato al perder el elemento del DOM.
        ['bg','surface','surface2','accent','secondary','text','muted','borderColor'].forEach(campo => {
            const picker = controls.querySelector(`#tm-${campo}`);
            const hexBox = controls.querySelector(`#tm-${campo}-hex`);
            if (picker) picker.addEventListener('input', () => {
                draft[campo] = picker.value;
                if (hexBox) hexBox.value = picker.value;
                onChange(true);
            });
            if (hexBox) hexBox.addEventListener('input', () => {
                if (/^#[0-9a-fA-F]{6}$/.test(hexBox.value)) {
                    draft[campo] = hexBox.value;
                    if (picker) picker.value = hexBox.value;
                    onChange(true);
                }
            });
        });
        controls.querySelector('#tm-nombre').addEventListener('input', (e) => {
            draft.nombre = e.target.value.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-');
            onChange(true);
        });
        controls.querySelector('#tm-borderOpacity').addEventListener('input', (e) => {
            draft.borderOpacity = Number(e.target.value);
            onChange(true); // true = solo repintar, no reconstruir todo el panel de controles
        });
        controls.querySelector('#tm-fuente').addEventListener('change', (e) => {
            draft.fuente = e.target.value;
            onChange(); // este SÍ reconstruye — necesita mostrar/ocultar el input de fuente personalizada
        });
        const fuenteCustomInput = controls.querySelector('#tm-fuente-custom');
        if (fuenteCustomInput) fuenteCustomInput.addEventListener('input', (e) => {
            draft.fuenteCustom = e.target.value;
            onChange(true);
        });
        controls.querySelector('#tm-scanlines').addEventListener('change', (e) => {
            draft.scanlines = e.target.checked;
            onChange(true);
        });
        controls.querySelector('#tm-glow').addEventListener('change', (e) => {
            draft.glow = e.target.checked;
            onChange(true);
        });
    }

    function renderPreview() {
        const fuenteFinal = draft.fuente === 'custom' ? `'${draft.fuenteCustom || 'Mi Fuente'}', monospace` : draft.fuente;
        const borderCss   = hexToRgba(draft.borderColor, draft.borderOpacity);
        const glowAccent  = draft.glow ? `0 0 8px ${hexToRgba(draft.accent, 40)}` : 'none';
        const glowText    = draft.glow ? `0 0 6px ${hexToRgba(draft.accent, 25)}` : 'none';
        const scanlinesBg = draft.scanlines
            ? `repeating-linear-gradient(0deg, rgba(0,0,0,0.18) 0px, rgba(0,0,0,0.18) 1px, transparent 1px, transparent 2px)`
            : 'none';

        preview.innerHTML = `
        <div style="font-family:${fuenteFinal};background:${draft.bg};padding:20px;border-radius:10px;position:relative;overflow:hidden;">
            <div style="position:absolute;inset:0;background:${scanlinesBg};pointer-events:none;"></div>
            <div style="position:relative;">
                <div style="background:${draft.surface};border:1px solid ${borderCss};border-radius:6px;overflow:hidden;margin-bottom:14px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid ${borderCss};">
                        <div style="color:${draft.accent};font-size:13px;letter-spacing:0.08em;text-shadow:${glowText};">RSU ALGORITMO</div>
                        <div style="color:${draft.muted};font-size:11px;">Vista previa</div>
                    </div>
                    <div style="padding:14px;">
                        <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid ${draft.surface2};">
                            <span style="color:${draft.muted};font-size:12px;">Score</span>
                            <span style="color:${draft.text};font-size:14px;font-weight:700;">72/100</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid ${draft.surface2};">
                            <span style="color:${draft.muted};font-size:12px;">Señal</span>
                            <span style="color:${draft.accent};font-size:12px;font-weight:700;text-shadow:${glowAccent};">VERDE</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:7px 0;">
                            <span style="color:${draft.muted};font-size:12px;">McClellan</span>
                            <span style="color:${draft.secondary};font-size:12px;font-weight:700;">+6.6</span>
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:10px;margin-bottom:14px;">
                    <button style="flex:1;background:${draft.accent};color:${draft.bg};border:none;border-radius:6px;padding:9px;font-family:${fuenteFinal};font-size:12px;font-weight:700;cursor:pointer;">EJECUTAR</button>
                    <button style="flex:1;background:transparent;color:${draft.text};border:1px solid ${borderCss};border-radius:6px;padding:9px;font-family:${fuenteFinal};font-size:12px;cursor:pointer;">CANCELAR</button>
                </div>
                <div style="background:${draft.surface2};border:1px solid ${borderCss};border-radius:6px;padding:12px;">
                    <div style="color:${draft.muted};font-size:10px;letter-spacing:0.06em;margin-bottom:8px;">TABLA DE EJEMPLO</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:11px;">
                        <span style="color:${draft.text};">AAPL</span><span style="color:${draft.accent};">+2.3%</span><span style="color:${draft.muted};">14:32</span>
                        <span style="color:${draft.text};">NVDA</span><span style="color:#f23645;">-1.1%</span><span style="color:${draft.muted};">14:31</span>
                        <span style="color:${draft.text};">MSFT</span><span style="color:${draft.secondary};">+0.4%</span><span style="color:${draft.muted};">14:30</span>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function onChange(soloRepintar) {
        guardarDraft(draft);
        renderPreview();
        if (!soloRepintar) renderControls();
    }

    renderControls();
    renderPreview();

    content.querySelector('#tm-reset-btn').addEventListener('click', () => {
        if (!confirm('¿Reiniciar el borrador a los valores por defecto? Se perderá lo que tengas sin exportar.')) return;
        draft = { ...DEFAULT_DRAFT };
        guardarDraft(draft);
        renderControls();
        renderPreview();
    });

    content.querySelector('#tm-export-btn').addEventListener('click', () => {
        if (!draft.nombre) { alert('Ponle un nombre al tema primero.'); return; }
        const css = construirCSS(draft);
        const out = content.querySelector('#tm-export-output');
        out.style.display = 'block';
        out.innerHTML = `
            <div style="color:var(--color-muted);font-size:11px;margin-bottom:8px;">
                Pasos para activarlo: guarda esto como <code>frontend/themes/${draft.nombre}.css</code> · añade
                <code>"${draft.nombre}"</code> al array <code>THEMES</code> en <code>frontend/core/theme.js</code> · enlázalo en
                <code>index.html</code> junto a los demás temas${draft.fuente === 'custom' ? ' · añade la fuente al &lt;link&gt; de Google Fonts si no está ya cargada' : ''}.
            </div>
            <textarea readonly style="width:100%;height:220px;background:var(--color-bg);border:1px solid var(--color-border);border-radius:6px;padding:10px;color:var(--color-text);font-family:var(--font-mono);font-size:11px;">${css}</textarea>
            <div style="margin-top:8px;">
                <button id="tm-copy-btn" style="background:var(--color-surface);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);padding:7px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;">📋 Copiar</button>
                <button id="tm-download-btn" style="background:var(--color-surface);color:var(--color-text);border:1px solid var(--color-border);border-radius:var(--radius);padding:7px 14px;font-family:var(--font-mono);font-size:11px;cursor:pointer;margin-left:6px;">⬇ Descargar .css</button>
            </div>
        `;
        out.querySelector('#tm-copy-btn').addEventListener('click', () => {
            navigator.clipboard.writeText(css);
            out.querySelector('#tm-copy-btn').textContent = '✓ Copiado';
            setTimeout(() => { out.querySelector('#tm-copy-btn').textContent = '📋 Copiar'; }, 1500);
        });
        out.querySelector('#tm-download-btn').addEventListener('click', () => {
            const blob = new Blob([css], { type: 'text/css' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${draft.nombre}.css`;
            a.click();
        });
    });
}