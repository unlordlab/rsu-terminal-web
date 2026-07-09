// ─────────────────────────────────────────────────────────────────────────────
// RSU ACADEMY — Gráficos SVG didácticos
// Cada función retorna un string SVG completo.
// Para añadir un gráfico: crea una función y regístrala en CHARTS al final.
// ─────────────────────────────────────────────────────────────────────────────

// Paleta compartida (se adapta al tema via CSS vars en el wrapper)
const C = {
    bg:       '#0f1117',
    surface:  '#1a1d27',
    border:   'rgba(255,255,255,0.08)',
    accent:   '#00ffad',
    cyan:     '#00d9ff',
    red:      '#f23645',
    orange:   '#ff9800',
    yellow:   '#ffd60a',
    muted:    '#555',
    text:     '#ccc',
    textDim:  '#888',
    grid:     'rgba(255,255,255,0.05)',
};

// Helper: polilínea de precios → coordenadas SVG
function priceToPath(prices, x0, y0, w, h) {
    const mn = Math.min(...prices), mx = Math.max(...prices);
    const range = mx - mn || 1;
    return prices.map((p, i) => {
        const x = x0 + (i / (prices.length - 1)) * w;
        const y = y0 + h - ((p - mn) / range) * h;
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');
}

function gridLines(x0, y0, w, h, rows = 4) {
    let g = '';
    for (let i = 0; i <= rows; i++) {
        const y = y0 + (i / rows) * h;
        g += `<line x1="${x0}" y1="${y.toFixed(1)}" x2="${x0+w}" y2="${y.toFixed(1)}" stroke="${C.grid}" stroke-width="1"/>`;
    }
    return g;
}

function candleRow(cx, y_open, y_close, y_high, y_low, bullish, w=10) {
    // En SVG Y crece hacia abajo: y_high (precio máximo) debe ser < y_low (precio mínimo)
    const svgTop    = Math.min(y_high, y_low, y_open, y_close);   // mecha arriba
    const svgBottom = Math.max(y_high, y_low, y_open, y_close);   // mecha abajo
    const bodyTop   = Math.min(y_open, y_close);
    const bodyBot   = Math.max(y_open, y_close);
    const color     = bullish ? C.accent : C.red;
    const bodyH     = Math.max(bodyBot - bodyTop, 2);
    return `<line x1="${cx}" y1="${svgTop.toFixed(1)}" x2="${cx}" y2="${svgBottom.toFixed(1)}" stroke="${color}" stroke-width="1.5"/>
            <rect x="${(cx - w/2).toFixed(1)}" y="${bodyTop.toFixed(1)}" width="${w}" height="${bodyH.toFixed(1)}" fill="${bullish ? color : 'none'}" stroke="${color}" stroke-width="1.5" rx="1"/>`;
}

// ─── GRÁFICO: Por qué empezar en mensual ─────────────────────────────────────
function monthly_why() {
    const W = 680, H = 220;
    // Tres series de "ruido" convergiendo en la misma tendencia
    const monthly = [100,105,98,112,108,120,115,130,128,142,138,155];
    const weekly  = [100,102,99,103,106,108,105,112,110,115,118,122,120,128,125,132,130,138,135,142,140,148,145,155];
    const daily   = [];
    for (let i=0; i<monthly.length*5; i++) {
        const base = monthly[Math.floor(i/5)] || 100;
        daily.push(base + (Math.random()-0.5)*8);
    }

    const labels = ['DIARIO (ruido)', 'SEMANAL (tendencia)', 'MENSUAL (estructura)'];
    const colors = [C.muted, C.cyan, C.accent];
    const series = [daily, weekly, monthly];

    let paths = '';
    series.forEach((s, idx) => {
        const x0 = 40, w = W - 80;
        const mn = Math.min(...s), mx = Math.max(...s), range = mx-mn||1;
        const pts = s.map((p,i) => {
            const x = x0 + (i/(s.length-1))*w;
            const y = 20 + 160 - ((p-mn)/range)*160;
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(' ');
        paths += `<polyline points="${pts}" fill="none" stroke="${colors[idx]}" stroke-width="${idx===2?2.5:idx===1?1.5:1}" opacity="${idx===0?0.35:idx===1?0.65:1}"/>`;
    });

    let legendItems = labels.map((l,i) =>
        `<rect x="${20 + i*200}" y="195" width="12" height="3" fill="${colors[i]}" rx="1"/>
         <text x="${38 + i*200}" y="202" fill="${colors[i]}" font-size="10" font-family="monospace" opacity="${i===0?0.5:1}">${l}</text>`
    ).join('');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(40,20,W-80,160)}
        ${paths}
        ${legendItems}
        <text x="${W/2}" y="13" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">MISMO ACTIVO — TRES TIMEFRAMES — MISMA DIRECCIÓN</text>
    </svg>`;
}

// ─── GRÁFICO: Estructura mensual ─────────────────────────────────────────────
function monthly_structure() {
    const W = 680, H = 240;
    const prices = [80, 95, 88, 110, 102, 125, 118, 138, 130, 150, 142, 162];
    const x0 = 50, y0 = 20, w = W-100, h = 160;

    const mn = Math.min(...prices)-5, mx = Math.max(...prices)+5, range=mx-mn;
    const px = (i) => x0 + (i/(prices.length-1))*w;
    const py = (v) => y0 + h - ((v-mn)/range)*h;

    // Candles simuladas (alcistas dominando)
    let candles = '';
    prices.forEach((p, i) => {
        if (i===0) return;
        const prev = prices[i-1];
        const bull = p > prev;
        const cx = px(i);
        const yO = py(prev * 0.995 + p * 0.005);
        const yC = py(p);
        const yH = py(p + (mx-mn)*0.025);
        const yL = py(prev - (mx-mn)*0.02);
        candles += candleRow(cx, yO, yC, yH, yL, bull, 14);
    });

    // Línea de tendencia
    const trendPath = `M ${px(0)} ${py(80)} L ${px(11)} ${py(165)}`;

    // Labels HH HL
    const hhPoints = [[2,95],[5,125],[8,138],[11,162]];
    const hlPoints = [[3,88],[6,118],[9,130]];

    let hhLabels = hhPoints.map(([i,v]) =>
        `<text x="${px(i)}" y="${py(v)-8}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">HH</text>
         <circle cx="${px(i)}" cy="${py(v)}" r="3" fill="${C.accent}"/>`).join('');
    let hlLabels = hlPoints.map(([i,v]) =>
        `<text x="${px(i)}" y="${py(v)+14}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">HL</text>
         <circle cx="${px(i)}" cy="${py(v)}" r="3" fill="${C.cyan}"/>`).join('');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${trendPath}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.4"/>
        ${candles}
        ${hhLabels}${hlLabels}
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            TENDENCIA ALCISTA MENSUAL — HH (Higher Highs) + HL (Higher Lows)
        </text>
        <rect x="8" y="${H-24}" width="60" height="14" fill="none" stroke="${C.accent}" stroke-width="1" rx="2" opacity="0.5"/>
        <text x="38" y="${H-14}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">HH = Alcista</text>
        <rect x="80" y="${H-24}" width="60" height="14" fill="none" stroke="${C.cyan}" stroke-width="1" rx="2" opacity="0.5"/>
        <text x="110" y="${H-14}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">HL = Soporte</text>
    </svg>`;
}

// ─── GRÁFICO: MA10 mensual ────────────────────────────────────────────────────
function ma10_monthly() {
    const W = 680, H = 220;
    const prices = [90,85,92,88,95,100,97,108,105,115,110,122,118,130,125,138,132,145,140,152];
    // MA10
    const ma10 = prices.map((_,i) => {
        if (i < 9) return null;
        return prices.slice(i-9, i+1).reduce((a,b)=>a+b,0)/10;
    });

    const x0=50, y0=15, w=W-80, h=160;
    const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    const pricePath = prices.map((p,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(p).toFixed(1)}`).join(' ');
    const maPath = ma10.filter(v=>v!==null).map((v,i)=>{
        const ri = i+9;
        return `${i===0?'M':'L'} ${px(ri).toFixed(1)} ${py(v).toFixed(1)}`;
    }).join(' ');

    // Zona buy (precio > MA10)
    let fillZones = '';
    const validMA = ma10.map((v,i)=>({v,i})).filter(x=>x.v!==null);
    validMA.forEach(({v,i}) => {
        const p = prices[i];
        if (p > v) {
            const x = px(i);
            const yP = py(p), yM = py(v);
            fillZones += `<rect x="${(x-8).toFixed(1)}" y="${Math.min(yP,yM).toFixed(1)}" width="16" height="${Math.abs(yP-yM).toFixed(1)}" fill="${C.accent}" opacity="0.07"/>`;
        }
    });

    // Cruce señal
    const crossX = px(9), crossY = py(ma10[9]);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${fillZones}
        <path d="${pricePath}" fill="none" stroke="${C.cyan}" stroke-width="1.5" opacity="0.7"/>
        <path d="${maPath}" fill="none" stroke="${C.orange}" stroke-width="2.5"/>
        <circle cx="${crossX}" cy="${crossY}" r="5" fill="${C.accent}" opacity="0.9"/>
        <text x="${crossX+8}" y="${crossY-6}" fill="${C.accent}" font-size="10" font-family="monospace">Cruce alcista</text>
        <text x="${W-130}" y="${y0+14}" fill="${C.orange}" font-size="10" font-family="monospace">── MA10 Mensual</text>
        <text x="${W-130}" y="${y0+28}" fill="${C.cyan}" font-size="10" font-family="monospace" opacity="0.7">── Precio</text>
        <rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="${C.accent}" opacity="0.03" rx="2"/>
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            PRECIO SOBRE MA10 = CONTEXTO ALCISTA ✓
        </text>
    </svg>`;
}

// ─── GRÁFICO: Niveles históricos ─────────────────────────────────────────────
function monthly_levels() {
    const W = 680, H = 230;
    const x0=50, y0=15, w=W-80, h=170;

    const resistanceY = y0 + h * 0.18;
    const supportY    = y0 + h * 0.68;
    const prices      = [130,125,138,132,145,150,148,162,158,170,165,155,148,152,160,168,172,165,170,175];
    const mn=110, mx=185, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    const pricePath = prices.map((p,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(p).toFixed(1)}`).join(' ');

    // Niveles de S/R
    const resLevel = 170, supLevel = 132;
    const resY = py(resLevel), supY = py(supLevel);

    // Toques en resistencia
    const resTouches = prices.map((p,i)=>({p,i})).filter(({p})=>Math.abs(p-resLevel)<4);
    // Toques en soporte
    const supTouches = prices.map((p,i)=>({p,i})).filter(({p})=>Math.abs(p-supLevel)<4);

    let touches = '';
    resTouches.forEach(({p,i})=>{
        touches += `<circle cx="${px(i).toFixed(1)}" cy="${py(p).toFixed(1)}" r="5" fill="none" stroke="${C.red}" stroke-width="1.5" opacity="0.8"/>`;
    });
    supTouches.forEach(({p,i})=>{
        touches += `<circle cx="${px(i).toFixed(1)}" cy="${py(p).toFixed(1)}" r="5" fill="none" stroke="${C.accent}" stroke-width="1.5" opacity="0.8"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-6}" width="${w}" height="12" fill="${C.red}" opacity="0.06"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="8,4"/>
        <rect x="${x0}" y="${supY-6}" width="${w}" height="12" fill="${C.accent}" opacity="0.06"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="8,4"/>
        <path d="${pricePath}" fill="none" stroke="${C.cyan}" stroke-width="2" opacity="0.8"/>
        ${touches}
        <text x="${x0+w+6}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES ${resLevel}</text>
        <text x="${x0+w+6}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SUP ${supLevel}</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            NIVELES HISTÓRICOS — CUANTOS MÁS TOQUES, MÁS FUERTES SON
        </text>
    </svg>`;
}

// ─── GRÁFICO: Tendencia semanal ───────────────────────────────────────────────
function weekly_trend() {
    const W = 680, H = 220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices = [100,96,103,99,107,104,112,108,117,113,120,116,125,121,129,125,133,129,138];
    const mn=90, mx=145, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles = '';
    prices.forEach((p,i)=>{
        if(i===0) return;
        const prev=prices[i-1], bull=p>prev;
        const cx=px(i);
        const yO=py(prev*0.998+p*0.002), yC=py(p);
        const yH=py(p+(mx-mn)*0.02), yL=py(Math.min(prev,p)-(mx-mn)*0.015);
        candles+=candleRow(cx,yO,yC,yH,yL,bull,16);
    });

    // EMA21 proxy
    let ema=prices[0], emas=[ema];
    const k=2/22;
    prices.slice(1).forEach(p=>{ ema=p*k+ema*(1-k); emas.push(ema); });
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.9"/>
        <text x="${x0+w-90}" y="${y0+14}" fill="${C.orange}" font-size="10" font-family="monospace">── EMA 21</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            GRÁFICO SEMANAL — IMPULSOS Y CORRECCIONES SOBRE EMA 21
        </text>
    </svg>`;
}

// ─── GRÁFICO: HH/HL en semanal ───────────────────────────────────────────────
function highs_lows_weekly() {
    const W = 680, H = 250;

    // Panel izquierdo: alcista
    const bullPrices = [100,94,108,102,118,112,125,119,135,128,142];
    // Panel derecho: bajista
    const bearPrices = [142,148,138,144,132,138,126,132,118,124,112];

    const panelW = (W-60)/2;
    const x0L=30, x0R=x0L+panelW+30;
    const y0=20, h=170;

    function panelCandles(prices, x0, bull) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>y0+h-((v-mn)/range)*h;
        let out='', labels='';
        prices.forEach((p,i)=>{
            if(i===0) return;
            const prev=prices[i-1], isBull=p>prev;
            const cx=px(i);
            const yO=py(prev), yC=py(p);
            const yH=py(Math.max(p,prev)+(mx-mn)*0.025);
            const yL=py(Math.min(p,prev)-(mx-mn)*0.02);
            out+=candleRow(cx,yO,yC,yH,yL,isBull,13);
        });
        // Labels HH/HL o LH/LL
        if(bull) {
            const hhIdx=[2,4,6,8,10], hlIdx=[1,3,5,7,9];
            hhIdx.filter(i=>i<prices.length).forEach(i=>{
                labels+=`<text x="${px(i).toFixed(1)}" y="${(py(prices[i])-8).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">HH</text>`;
            });
            hlIdx.filter(i=>i<prices.length).forEach(i=>{
                labels+=`<text x="${px(i).toFixed(1)}" y="${(py(prices[i])+14).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">HL</text>`;
            });
        } else {
            const lhIdx=[2,4,6,8,10], llIdx=[1,3,5,7,9];
            lhIdx.filter(i=>i<prices.length).forEach(i=>{
                labels+=`<text x="${px(i).toFixed(1)}" y="${(py(prices[i])-8).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">LH</text>`;
            });
            llIdx.filter(i=>i<prices.length).forEach(i=>{
                labels+=`<text x="${px(i).toFixed(1)}" y="${(py(prices[i])+14).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">LL</text>`;
            });
        }
        return out+labels;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="${x0L-5}" y="${y0-5}" width="${panelW+10}" height="${h+10}" fill="${C.accent}" opacity="0.03" rx="4"/>
        <rect x="${x0R-5}" y="${y0-5}" width="${panelW+10}" height="${h+10}" fill="${C.red}" opacity="0.03" rx="4"/>
        ${panelCandles(bullPrices, x0L, true)}
        ${panelCandles(bearPrices, x0R, false)}
        <text x="${x0L+panelW/2}" y="${H-6}" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">TENDENCIA ALCISTA</text>
        <text x="${x0R+panelW/2}" y="${H-6}" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">TENDENCIA BAJISTA</text>
        <line x1="${x0R-15}" y1="${y0}" x2="${x0R-15}" y2="${y0+h}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

// ─── GRÁFICO: EMAs en semanal ─────────────────────────────────────────────────
function weekly_emas() {
    const W = 680, H = 220;
    const x0=45, y0=15, w=W-80, h=165;
    const prices=[95,92,98,96,104,101,109,106,115,111,120,116,125,121,130,126,135,131,138];
    const mn=85, mx=145, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    function ema(data, span) {
        const k=2/(span+1); let e=data[0]; const out=[e];
        data.slice(1).forEach(p=>{ e=p*k+e*(1-k); out.push(e); });
        return out;
    }
    function sma(data, span) {
        return data.map((_,i)=> i<span-1 ? null : data.slice(i-span+1,i+1).reduce((a,b)=>a+b,0)/span);
    }

    const ema21 = ema(prices,21).map((v,i)=>({v,i}));
    const sma50 = sma(prices,50).map((v,i)=>({v,i})).filter(x=>x.v!==null);

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        const yO=py(prev),yC=py(p),yH=py(p+(mx-mn)*0.02),yL=py(Math.min(prev,p)-(mx-mn)*0.015);
        candles+=candleRow(cx,yO,yC,yH,yL,bull,13);
    });

    const ema21Path=ema21.map(({v,i})=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const sma50Path=sma50.length>1 ? sma50.map(({v,i},j)=>`${j===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ') : '';

    // Fill between price and EMA21 (alcista)
    let fillPts='';
    prices.forEach((p,i)=>{
        const e=ema21[i]?.v;
        if(e && p>e) fillPts+=`${px(i).toFixed(1)},${py(p).toFixed(1)} `;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${ema21Path}" fill="none" stroke="${C.orange}" stroke-width="2.2" opacity="0.9"/>
        ${sma50Path ? `<path d="${sma50Path}" fill="none" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>` : ''}
        <rect x="${W-160}" y="${y0+5}" width="8" height="8" fill="${C.orange}" rx="1"/>
        <text x="${W-148}" y="${y0+13}" fill="${C.orange}" font-size="10" font-family="monospace">EMA 21 (soporte dinámico)</text>
        <rect x="${W-160}" y="${y0+22}" width="8" height="8" fill="${C.cyan}" rx="1" opacity="0.6"/>
        <text x="${W-148}" y="${y0+30}" fill="${C.cyan}" font-size="10" font-family="monospace" opacity="0.6">SMA 50 (tendencia media)</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            RETROCESO A EMA 21 = ZONA DE ENTRADA EN TENDENCIA ALCISTA
        </text>
    </svg>`;
}

// ─── GRÁFICO: Momentum semanal / Divergencia ──────────────────────────────────
function weekly_momentum() {
    const W=680, H=260;
    const x0=45, y0=15, wChart=W-80;
    const hPrice=140, hRSI=70, gap=20;

    const prices=[100,105,102,110,108,118,114,124,120,132,128,138,134,142,138,146,142,150];
    const mn=92, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*wChart;
    const pyP=(v)=>y0+hPrice-((v-mn)/range)*hPrice;

    // RSI simulado con divergencia al final
    const rsi=[45,52,48,60,55,68,63,72,67,74,69,72,66,70,64,68,62,65];
    const rMn=40, rMx=80, rRange=rMx-rMn;
    const rsiY0=y0+hPrice+gap;
    const pyR=(v)=>rsiY0+hRSI-((v-rMn)/rRange)*hRSI;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,pyP(prev),pyP(p),pyP(p+(mx-mn)*0.02),pyP(Math.min(prev,p)-(mx-mn)*0.015),bull,13);
    });

    const pricePath=prices.map((p,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${pyP(p).toFixed(1)}`).join(' ');
    const rsiPath=rsi.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${pyR(v).toFixed(1)}`).join(' ');

    // Divergencia: precio HH pero RSI LH en últimas 4 velas
    const divX1=px(14), divY1P=pyP(142), divY1R=pyR(68);
    const divX2=px(17), divY2P=pyP(150), divY2R=pyR(65);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,wChart,hPrice)}
        ${candles}
        <text x="${x0+4}" y="${y0+12}" fill="${C.textDim}" font-size="9" font-family="monospace">PRECIO</text>

        ${gridLines(x0,rsiY0,wChart,hRSI,2)}
        <line x1="${x0}" y1="${pyR(70)}" x2="${x0+wChart}" y2="${pyR(70)}" stroke="${C.red}" stroke-width="1" opacity="0.3" stroke-dasharray="4,4"/>
        <line x1="${x0}" y1="${pyR(50)}" x2="${x0+wChart}" y2="${pyR(50)}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4"/>
        <line x1="${x0}" y1="${pyR(30)}" x2="${x0+wChart}" y2="${pyR(30)}" stroke="${C.accent}" stroke-width="1" opacity="0.3" stroke-dasharray="4,4"/>
        <path d="${rsiPath}" fill="none" stroke="${C.cyan}" stroke-width="1.8"/>
        <text x="${x0+4}" y="${rsiY0+12}" fill="${C.cyan}" font-size="9" font-family="monospace">RSI 14</text>
        <text x="${x0+wChart-30}" y="${pyR(70)+4}" fill="${C.red}" font-size="8" font-family="monospace" opacity="0.5">70</text>
        <text x="${x0+wChart-30}" y="${pyR(30)+4}" fill="${C.accent}" font-size="8" font-family="monospace" opacity="0.5">30</text>

        <line x1="${divX1}" y1="${divY1P}" x2="${divX2}" y2="${divY2P}" stroke="${C.red}" stroke-width="2" stroke-dasharray="5,3" opacity="0.8"/>
        <line x1="${divX1}" y1="${divY1R}" x2="${divX2}" y2="${divY2R}" stroke="${C.red}" stroke-width="2" stroke-dasharray="5,3" opacity="0.8"/>
        <circle cx="${divX2}" cy="${divY2P}" r="5" fill="none" stroke="${C.red}" stroke-width="1.5"/>
        <circle cx="${divX2}" cy="${divY2R}" r="5" fill="none" stroke="${C.red}" stroke-width="1.5"/>

        <rect x="${W/2-80}" y="${y0+hPrice+gap+hRSI+4}" width="160" height="16" fill="${C.red}" opacity="0.1" rx="3"/>
        <text x="${W/2}" y="${y0+hPrice+gap+hRSI+15}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">
            ⚠ DIVERGENCIA BAJISTA — Precio HH, RSI LH
        </text>
    </svg>`;
}

// ─── GRÁFICO: Diario en contexto ─────────────────────────────────────────────
function daily_context() {
    const W=680, H=200;
    const labels=['MENSUAL\n📈 ALCISTA','SEMANAL\n📈 ALCISTA','DIARIO\n🎯 ENTRADA'];
    const colors=[C.accent, C.cyan, C.orange];
    const bw=150, gap=40, startX=50;

    let boxes='';
    labels.forEach((l,i)=>{
        const x=startX+i*(bw+gap);
        const lines=l.split('\n');
        boxes+=`<rect x="${x}" y="50" width="${bw}" height="100" fill="${colors[i]}" opacity="${i===2?0.15:0.08}" rx="8" stroke="${colors[i]}" stroke-width="${i===2?2:1}"/>
        <text x="${x+bw/2}" y="95" fill="${colors[i]}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${lines[0]}</text>
        <text x="${x+bw/2}" y="115" fill="${colors[i]}" font-size="18" text-anchor="middle">${lines[1]}</text>`;
        if(i<2) {
            const ax=x+bw+5, ay=100;
            boxes+=`<path d="M ${ax} ${ay} L ${ax+gap-10} ${ay}" stroke="${C.muted}" stroke-width="2" marker-end="url(#arr)"/>`;
        }
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
                <path d="M 0 0 L 6 3 L 0 6 z" fill="${C.muted}"/>
            </marker>
        </defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${boxes}
        <text x="${W/2}" y="${H-10}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            TOP-DOWN: Las tres temporalidades deben alinearse antes de buscar entrada
        </text>
    </svg>`;
}

// ─── GRÁFICO: Setup en diario ─────────────────────────────────────────────────
function daily_setup() {
    const W=680, H=240;
    const x0=45, y0=15, w=W-80, h=180;
    const prices=[100,104,101,108,105,112,109,116,113,120,116,122,119,115,117,121,124,128,125,132];
    const mn=92, mx=140, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,12);
    });

    // EMA21
    let ema=prices[0], emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ ema=p*k+ema*(1-k); emas.push(ema); });
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // Zona de retroceso (velas 13-15)
    const zx1=px(12), zx2=px(16), zy1=py(125), zy2=py(113);
    // Vela catalizador (16)
    const catX=px(16), catY=py(121);
    // Entry arrow
    const arrX=px(17), arrY=py(124);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.9"/>
        <rect x="${zx1}" y="${zy2}" width="${zx2-zx1}" height="${zy1-zy2}" fill="${C.accent}" opacity="0.07" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,3"/>
        <text x="${(zx1+zx2)/2}" y="${zy2-5}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ZONA RETROCESO</text>

        <circle cx="${catX}" cy="${catY}" r="8" fill="none" stroke="${C.yellow}" stroke-width="2" opacity="0.9"/>
        <text x="${catX}" y="${catY-14}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">CATALIZADOR</text>

        <line x1="${arrX}" y1="${arrY+20}" x2="${arrX}" y2="${arrY+5}" stroke="${C.accent}" stroke-width="2" marker-end="url(#arr2)"/>
        <text x="${arrX}" y="${arrY+35}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">ENTRADA</text>

        <defs><marker id="arr2" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
            <path d="M 0 0 L 6 3 L 0 6 z" fill="${C.accent}"/>
        </marker></defs>
        <text x="${x0+w-90}" y="${y0+14}" fill="${C.orange}" font-size="10" font-family="monospace">── EMA 21</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ESTRUCTURA → NIVEL → CATALIZADOR = SETUP VÁLIDO
        </text>
    </svg>`;
}

// ─── GRÁFICO: Medias en diario ────────────────────────────────────────────────
function daily_mas() {
    const W=680, H=220;
    const x0=45, y0=15, w=W-80, h=170;
    const n=50;
    const prices=Array.from({length:n},(_,i)=>100+i*0.8+Math.sin(i/3)*6+(Math.random()-0.5)*3);
    const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
    const px=(i)=>x0+(i/(n-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    function emaArr(data,span){const k=2/(span+1);let e=data[0];const o=[e];data.slice(1).forEach(p=>{e=p*k+e*(1-k);o.push(e);});return o;}
    function smaArr(data,span){return data.map((_,i)=>i<span-1?null:data.slice(i-span+1,i+1).reduce((a,b)=>a+b)/span);}

    const e21=emaArr(prices,21);
    const s50=smaArr(prices,50);
    const s200=smaArr(prices.map((p,i)=>p*0.98-i*0.1),200); // simulated lower

    const path=(arr,clr,w,dash='')=>{
        const pts=arr.map((v,i)=>v===null?null:`${i===0||arr[i-1]===null?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).filter(Boolean).join(' ');
        return `<path d="${pts}" fill="none" stroke="${clr}" stroke-width="${w}" ${dash?`stroke-dasharray="${dash}"`:''}/>`;
    };

    const priceP=prices.map((p,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(p).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${priceP}" fill="none" stroke="${C.text}" stroke-width="1" opacity="0.4"/>
        ${path(e21,C.orange,2)}
        ${path(s50,C.cyan,1.5,'6,3')}
        ${path(s200.map(v=>v||80),C.red,1.5,'4,4')}
        <rect x="${x0+5}" y="${y0+5}" width="115" height="62" fill="${C.bg}" opacity="0.8" rx="4"/>
        <rect x="${x0+8}" y="${y0+8}" width="8" height="8" fill="${C.orange}" rx="1"/>
        <text x="${x0+20}" y="${y0+16}" fill="${C.orange}" font-size="10" font-family="monospace">EMA 21</text>
        <rect x="${x0+8}" y="${y0+24}" width="8" height="8" fill="${C.cyan}" rx="1" opacity="0.7"/>
        <text x="${x0+20}" y="${y0+32}" fill="${C.cyan}" font-size="10" font-family="monospace" opacity="0.7">SMA 50</text>
        <rect x="${x0+8}" y="${y0+40}" width="8" height="8" fill="${C.red}" rx="1" opacity="0.7"/>
        <text x="${x0+20}" y="${y0+48}" fill="${C.red}" font-size="10" font-family="monospace" opacity="0.7">SMA 200</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            GRÁFICO DIARIO — EMA21 + SMA50 + SMA200 = CONFIGURACIÓN MÍNIMA
        </text>
    </svg>`;
}

// ─── GRÁFICO: Salida en diario ────────────────────────────────────────────────
function daily_exit() {
    const W=680, H=220;
    const x0=45, y0=15, w=W-80, h=165;
    const prices=[100,104,102,109,106,114,111,119,116,124,121,128,125,132,129,136,133,138,136,130,128,124,120];
    const mn=92, mx=145, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.02),py(Math.min(prev,p)-(mx-mn)*0.015),bull,11);
    });

    let ema=prices[0], emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ ema=p*k+ema*(1-k); emas.push(ema); });
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // Entry zone
    const entryX=px(1), entryY=py(100);
    // Exit signal — close below EMA21
    const exitX=px(20), exitY=py(120);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.9"/>
        <line x1="${entryX}" y1="${y0}" x2="${entryX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.6"/>
        <text x="${entryX+4}" y="${y0+12}" fill="${C.accent}" font-size="9" font-family="monospace">ENTRADA</text>
        <line x1="${exitX}" y1="${y0}" x2="${exitX}" y2="${y0+h}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.6"/>
        <text x="${exitX-32}" y="${y0+12}" fill="${C.red}" font-size="9" font-family="monospace">SALIDA</text>
        <circle cx="${exitX}" cy="${exitY}" r="6" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            CIERRE POR DEBAJO DE EMA21 = SEÑAL DE SALIDA
        </text>
    </svg>`;
}

// ─── GRÁFICO: EMA vs SMA — velocidad de reacción ─────────────────────────────
function ema_vs_sma_reaction() {
    const W = 680, H = 220;
    const x0 = 45, y0 = 15, w = W-80, h = 165;
    // Precio plano y luego un salto brusco sostenido, para exponer la diferencia de reacción
    const prices = [];
    for (let i=0;i<15;i++) prices.push(100 + Math.sin(i/2)*1.5);
    for (let i=0;i<25;i++) prices.push(102 + i*1.3 + Math.sin(i/2)*1.5);
    const n = prices.length;
    const mn = Math.min(...prices)-4, mx = Math.max(...prices)+4, range = mx-mn;
    const px = (i) => x0 + (i/(n-1))*w;
    const py = (v) => y0 + h - ((v-mn)/range)*h;

    function emaArr(data,span){const k=2/(span+1);let e=data[0];const o=[e];data.slice(1).forEach(p=>{e=p*k+e*(1-k);o.push(e);});return o;}
    function smaArr(data,span){return data.map((_,i)=> i<span-1 ? data[0] : data.slice(i-span+1,i+1).reduce((a,b)=>a+b)/span);}

    const e10 = emaArr(prices, 10);
    const s10 = smaArr(prices, 10);

    const priceP = prices.map((p,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(p).toFixed(1)}`).join(' ');
    const path = (arr, clr, sw) => `<path d="${arr.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ')}" fill="none" stroke="${clr}" stroke-width="${sw}"/>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${priceP}" fill="none" stroke="${C.text}" stroke-width="1.5" opacity="0.5"/>
        ${path(s10, C.cyan, 2)}
        ${path(e10, C.orange, 2)}
        <line x1="${px(15).toFixed(1)}" y1="${y0}" x2="${px(15).toFixed(1)}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4"/>
        <text x="${px(15)+4}" y="${y0+12}" fill="${C.muted}" font-size="9" font-family="monospace">CAMBIO DE RÉGIMEN</text>
        <rect x="${x0+5}" y="${y0+5}" width="90" height="40" fill="${C.bg}" opacity="0.85" rx="4"/>
        <rect x="${x0+8}" y="${y0+8}" width="8" height="8" fill="${C.orange}" rx="1"/>
        <text x="${x0+20}" y="${y0+16}" fill="${C.orange}" font-size="10" font-family="monospace">EMA (10)</text>
        <rect x="${x0+8}" y="${y0+24}" width="8" height="8" fill="${C.cyan}" rx="1"/>
        <text x="${x0+20}" y="${y0+32}" fill="${C.cyan}" font-size="10" font-family="monospace">SMA (10)</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            MISMO PERIODO — LA EMA SIGUE EL CAMBIO DE PRECIO ANTES QUE LA SMA
        </text>
    </svg>`;
}

// ─── GRÁFICO: Entrada en EMA21 confirmada con volumen ────────────────────────
function ema_entry_volume() {
    const W = 680, H = 260;
    const x0 = 45, y0 = 15, w = W-80, h = 150;
    const volY0 = y0+h+15, volH = 55;
    const prices = [100,104,108,112,109,106,108,106,110,118,124,130,136];
    const vols   = [1.0,1.1,1.3,1.0,0.6,0.5,0.4,0.5,2.2,1.6,1.3,1.2,1.1];
    const n = prices.length;
    const mn = 98, mx = 140, range = mx-mn;
    const px = (i) => x0 + (i/(n-1))*w;
    const py = (v) => y0 + h - ((v-mn)/range)*h;

    let ema = prices[0], emas=[ema]; const k = 2/22;
    prices.slice(1).forEach(p => { ema = p*k + ema*(1-k); emas.push(ema); });
    const emaPath = emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1], bull=p>prev, cx=px(i);
        candles += candleRow(cx, py(prev), py(p), py(p+(mx-mn)*0.02), py(Math.min(prev,p)-(mx-mn)*0.015), bull, 13);
        const bh = vols[i]*volH*0.55;
        const isConfirm = i===8;
        volBars += `<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isConfirm?C.accent:bull?C.accent:C.muted}" opacity="${isConfirm?0.95:0.4}" rx="1"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2"/>
        ${candles}
        <rect x="${(px(4)-8).toFixed(1)}" y="${y0}" width="${(px(7)-px(4)+16).toFixed(1)}" height="${h}" fill="${C.muted}" opacity="0.08"/>
        <text x="${px(5.5).toFixed(1)}" y="${y0+12}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">RETROCESO · VOL BAJO</text>
        <circle cx="${px(8).toFixed(1)}" cy="${py(110).toFixed(1)}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(8).toFixed(1)}" y="${(y0-4).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">CONFIRMACIÓN + VOL↑</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            RETROCESO CON VOLUMEN BAJO + VELA DE REACCIÓN CON VOLUMEN ALTO = ENTRADA VÁLIDA
        </text>
    </svg>`;
}

// ─── GRÁFICO: Salida por cierre bajo la EMA vs. mecha (falsa señal) ──────────
function ema_exit_signal() {
    const W = 680, H = 230;
    const x0 = 45, y0 = 15, w = W-80, h = 165;
    const prices = [100,105,110,108,113,111,116,113,109,115,120,117,111,104];
    const n = prices.length;
    const mn = 96, mx = 124, range = mx-mn;
    const px = (i) => x0 + (i/(n-1))*w;
    const py = (v) => y0 + h - ((v-mn)/range)*h;

    let ema = prices[0], emas=[ema]; const k = 2/22;
    prices.slice(1).forEach(p => { ema = p*k + ema*(1-k); emas.push(ema); });
    const emaPath = emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // wick-only touch at index 8 (closes above EMA), real close-below at index 13
    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1], bull=p>prev, cx=px(i);
        const wickDown = (i===8) ? emas[i]-1.5 : Math.min(prev,p)-(mx-mn)*0.015;
        candles += candleRow(cx, py(prev), py(p), py(p+(mx-mn)*0.02), py(wickDown), bull, 13);
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2"/>
        ${candles}
        <circle cx="${px(8).toFixed(1)}" cy="${py(prices[8]).toFixed(1)}" r="8" fill="none" stroke="${C.yellow}" stroke-width="1.5"/>
        <text x="${px(8).toFixed(1)}" y="${(py(prices[8])-14).toFixed(1)}" fill="${C.yellow}" font-size="8.5" font-family="monospace" text-anchor="middle">MECHA — CIERRE OK</text>
        <circle cx="${px(13).toFixed(1)}" cy="${py(prices[13]).toFixed(1)}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(13).toFixed(1)}" y="${(py(prices[13])+16).toFixed(1)}" fill="${C.red}" font-size="8.5" font-family="monospace" text-anchor="middle">CIERRE BAJO EMA</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            SOLO EL CIERRE CUENTA — LA MECHA NO ES SEÑAL DE SALIDA
        </text>
    </svg>`;
}

// ─── GRÁFICO: Golden Cross / Death Cross (SMA 50 vs SMA 200) ────────────────
function golden_death_cross() {
    const W = 680, H = 230;
    const x0 = 45, y0 = 15, w = W-80, h = 165;
    // Precio: caída larga -> suelo -> recuperación sostenida (para exponer ambos cruces)
    const prices = [];
    for (let i=0;i<20;i++) prices.push(140 - i*2.6 + Math.sin(i/2)*2);
    for (let i=0;i<10;i++) prices.push(88 + Math.sin(i/2)*3);
    for (let i=0;i<30;i++) prices.push(90 + i*2.2 + Math.sin(i/2)*3);
    const n = prices.length;
    const mn = Math.min(...prices)-6, mx = Math.max(...prices)+6, range = mx-mn;
    const px = (i) => x0 + (i/(n-1))*w;
    const py = (v) => y0 + h - ((v-mn)/range)*h;

    function smaArr(data,span){return data.map((_,i)=> i<span-1 ? null : data.slice(i-span+1,i+1).reduce((a,b)=>a+b)/span);}
    const s10 = smaArr(prices, 10);  // proxy visual de SMA50 (escalado al dataset corto)
    const s25 = smaArr(prices, 25);  // proxy visual de SMA200

    const priceP = prices.map((p,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(p).toFixed(1)}`).join(' ');
    const pathOf = (arr, clr, sw) => {
        const pts = arr.map((v,i)=> v===null?null:`${(arr[i-1]===null||i===0)?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).filter(Boolean).join(' ');
        return `<path d="${pts}" fill="none" stroke="${clr}" stroke-width="${sw}"/>`;
    };

    // localizar cruces aproximados para las etiquetas
    let deathIdx = null, goldenIdx = null;
    for (let i=1;i<n;i++){
        if (s10[i]!==null && s25[i]!==null && s10[i-1]!==null && s25[i-1]!==null){
            if (s10[i-1] >= s25[i-1] && s10[i] < s25[i] && deathIdx===null) deathIdx = i;
            if (s10[i-1] <= s25[i-1] && s10[i] > s25[i] && deathIdx!==null && goldenIdx===null) goldenIdx = i;
        }
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${priceP}" fill="none" stroke="${C.text}" stroke-width="1" opacity="0.35"/>
        ${pathOf(s10, C.cyan, 2)}
        ${pathOf(s25, C.red, 2)}
        ${deathIdx ? `<circle cx="${px(deathIdx).toFixed(1)}" cy="${py(s10[deathIdx]).toFixed(1)}" r="7" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(deathIdx).toFixed(1)}" y="${(py(s10[deathIdx])+18).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">DEATH CROSS</text>` : ''}
        ${goldenIdx ? `<circle cx="${px(goldenIdx).toFixed(1)}" cy="${py(s10[goldenIdx]).toFixed(1)}" r="7" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(goldenIdx).toFixed(1)}" y="${(py(s10[goldenIdx])-12).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">GOLDEN CROSS</text>` : ''}
        <rect x="${x0+5}" y="${y0+5}" width="95" height="40" fill="${C.bg}" opacity="0.85" rx="4"/>
        <rect x="${x0+8}" y="${y0+8}" width="8" height="8" fill="${C.cyan}" rx="1"/>
        <text x="${x0+20}" y="${y0+16}" fill="${C.cyan}" font-size="10" font-family="monospace">SMA 50</text>
        <rect x="${x0+8}" y="${y0+24}" width="8" height="8" fill="${C.red}" rx="1"/>
        <text x="${x0+20}" y="${y0+32}" fill="${C.red}" font-size="10" font-family="monospace">SMA 200</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            AMBOS CRUCES LLEGAN SEMANAS DESPUÉS DE QUE EL PRECIO YA HAYA GIRADO
        </text>
    </svg>`;
}

// ─── GRÁFICO: Gráfico sucio vs limpio ────────────────────────────────────────
function chart_messy_vs_clean() {
    const W=680, H=220;
    const panelW=(W-50)/2;

    // Panel izquierdo: recargado (muchos elementos simulados)
    const messyLabels=['MACD','RSI','BB','STOCH','ADX','CCI','Williams'];
    let messyBars='';
    messyLabels.forEach((l,i)=>{
        const x=8+i*(panelW/7-2), y=30;
        messyBars+=`<rect x="${x}" y="${y}" width="${panelW/7-4}" height="${140+Math.sin(i)*20}" fill="${[C.red,C.cyan,C.orange,C.yellow,C.accent,'#9c27b0',C.muted][i]}" opacity="0.3" rx="2"/>
        <text x="${x+(panelW/7-4)/2}" y="185" fill="${C.muted}" font-size="7" font-family="monospace" text-anchor="middle" transform="rotate(-45, ${x+(panelW/7-4)/2}, 185)">${l}</text>`;
    });
    // Lineas encima
    for(let i=0;i<5;i++){
        const y=30+i*28;
        messyBars+=`<line x1="5" y1="${y}" x2="${panelW-5}" y2="${y+(Math.random()-0.5)*30}" stroke="${[C.red,C.cyan,C.orange,C.yellow,C.accent][i]}" stroke-width="1.5" opacity="0.6"/>`;
    }

    // Panel derecho: limpio
    const prices=[100,104,101,108,105,113,110,118,115,122,119,126,122,130];
    const mn=93, mx=136, range=mx-mn;
    const cleanX0=panelW+50, cleanW=panelW-10;
    const px=(i)=>cleanX0+(i/(prices.length-1))*cleanW;
    const py=(v)=>20+160-((v-mn)/range)*160;
    let cleanCandles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1], bull=p>prev, cx=px(i);
        cleanCandles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,14);
    });
    let ema=prices[0], emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k); emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.04" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.04" rx="5"/>
        <text x="${panelW/2}" y="16" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">❌ GRÁFICO SOBRECARGADO</text>
        ${messyBars}
        <text x="${cleanX0+cleanW/2}" y="16" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">✓ GRÁFICO LIMPIO</text>
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        ${gridLines(cleanX0, 20, cleanW, 160)}
        ${cleanCandles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2"/>
    </svg>`;
}

// ─── GRÁFICO: Setup limpio ────────────────────────────────────────────────────
function clean_chart_setup() {
    const W=680, H=220;
    const x0=50, y0=15, w=W-80, h=170;
    const prices=[100,104,101,109,106,114,111,119,116,124,121,129,126,134,131,138];
    const mn=92, mx=145, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    function emaArr(d,s){const k=2/(s+1);let e=d[0];const o=[e];d.slice(1).forEach(p=>{e=p*k+e*(1-k);o.push(e);});return o;}
    function smaArr(d,s){return d.map((_,i)=>i<s-1?null:d.slice(i-s+1,i+1).reduce((a,b)=>a+b)/s);}

    const e21=emaArr(prices,21);
    const s50=smaArr(prices,50);

    const e21Path=e21.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const s50Path=s50.map((v,i)=>v===null?null:`${i===0||s50[i-1]===null?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).filter(Boolean).join(' ');

    // Volume bars
    const vols=[1.0,1.2,0.8,1.5,0.9,1.8,1.1,2.1,1.3,1.6,1.0,1.9,1.2,2.2,1.4,2.5];
    let volBars='';
    const volY0=y0+h+5, volH=25;
    vols.forEach((v,i)=>{
        if(!i) return;
        const bull=prices[i]>prices[i-1];
        const bh=v*volH/2.5;
        volBars+=`<rect x="${(px(i)-7).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="14" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="0.4" rx="1"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H+35}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+35}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${e21Path}" fill="none" stroke="${C.orange}" stroke-width="2.2"/>
        ${s50Path?`<path d="${s50Path}" fill="none" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>`:''}
        ${volBars}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        <rect x="${W-175}" y="${y0+4}" width="165" height="50" fill="${C.bg}" opacity="0.9" rx="4" stroke="${C.border}" stroke-width="1"/>
        <rect x="${W-170}" y="${y0+8}" width="8" height="8" fill="${C.orange}" rx="1"/>
        <text x="${W-158}" y="${y0+16}" fill="${C.orange}" font-size="10" font-family="monospace">EMA 21 (soporte)</text>
        <rect x="${W-170}" y="${y0+24}" width="8" height="8" fill="${C.cyan}" rx="1" opacity="0.6"/>
        <text x="${W-158}" y="${y0+32}" fill="${C.cyan}" font-size="10" font-family="monospace" opacity="0.6">SMA 50</text>
        <rect x="${W-170}" y="${y0+40}" width="8" height="8" fill="${C.accent}" rx="1" opacity="0.4"/>
        <text x="${W-158}" y="${y0+48}" fill="${C.accent}" font-size="10" font-family="monospace" opacity="0.4">Volumen</text>
        <text x="${W/2}" y="${H+30}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            CONFIGURACIÓN PROFESIONAL — VELAS + EMA21 + SMA50 + VOLUMEN
        </text>
    </svg>`;
}

// ─── GRÁFICO: Anatomía de una vela ───────────────────────────────────────────
function candle_anatomy() {
    const W=680, H=240;

    // drawCandle(cx, yHigh, yOpen, yClose, yLow, isBullish, label, labelColor, annotations)
    function drawCandle(cx, yH, yO, yC, yL, isBull, label, labelColor, annotations) {
        const color = isBull ? C.accent : C.red;
        const top    = Math.min(yO, yC);
        const bottom = Math.max(yO, yC);
        const bodyH  = Math.max(bottom - top, 4);
        // Wick must go from high to low — ensure correct direction
        const wickTop    = Math.min(yH, top);
        const wickBottom = Math.max(yL, bottom);
        let out = `<line x1="${cx}" y1="${wickTop}" x2="${cx}" y2="${wickBottom}" stroke="${color}" stroke-width="2"/>
        <rect x="${cx-18}" y="${top}" width="36" height="${bodyH}" fill="${isBull ? color : 'none'}" stroke="${color}" stroke-width="2" rx="2"/>
        <text x="${cx}" y="${wickBottom+20}" fill="${labelColor}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        (annotations || []).forEach(({y, txt, side}) => {
            const lx     = side === 'right' ? cx + 28 : cx - 28;
            const anchor = side === 'right' ? 'start' : 'end';
            const lineX  = side === 'right' ? cx + 18 : cx - 18;
            out += `<line x1="${lineX}" y1="${y}" x2="${lx}" y2="${y}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="3,2"/>
            <text x="${lx + (side === 'right' ? 4 : -4)}" y="${y+4}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="${anchor}">${txt}</text>`;
        });
        return out;
    }

    // Vela alcista — yH=30(max), yO=120(open), yC=80(close), yL=160(min)
    let svg = drawCandle(90, 30, 120, 80, 160, true, 'ALCISTA', C.accent, [
        {y:30,  txt:'Máximo',   side:'left'},
        {y:80,  txt:'Cierre',   side:'left'},
        {y:120, txt:'Apertura', side:'left'},
        {y:160, txt:'Mínimo',   side:'left'},
    ]);
    svg += `<text x="90" y="195" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">Shadow (mecha)</text>
    <text x="115" y="102" fill="${C.accent}" font-size="9" font-family="monospace">Cuerpo</text>`;

    // Vela bajista — yH=35(max), yO=75(open), yC=125(close), yL=165(min)
    svg += drawCandle(230, 35, 75, 125, 165, false, 'BAJISTA', C.red, []);
    svg+=`<text x="230" y="190" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">Cuerpo sólido</text>
    <text x="230" y="200" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">(vendedores)</text>`;

    // Doji
    svg+=`<line x1="370" y1="40" x2="370" y2="170" stroke="${C.yellow}" stroke-width="2"/>
    <rect x="352" y="98" width="36" height="4" fill="${C.yellow}" stroke="${C.yellow}" stroke-width="1"/>
    <text x="370" y="190" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="middle">DOJI</text>
    <text x="370" y="202" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">(indecisión)</text>`;

    // Pin bar
    svg+=`<line x1="490" y1="30" x2="490" y2="160" stroke="${C.cyan}" stroke-width="2"/>
    <rect x="472" y="130" width="36" height="18" fill="${C.cyan}" stroke="${C.cyan}" stroke-width="1.5" rx="2"/>
    <text x="490" y="190" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">PIN BAR</text>
    <text x="490" y="202" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">(rechazo)</text>
    <text x="516" y="60" fill="${C.cyan}" font-size="8" font-family="monospace">Shadow</text>
    <text x="516" y="70" fill="${C.cyan}" font-size="8" font-family="monospace">largo</text>`;

    // Inside bar
    svg+=`<line x1="610" y1="40" x2="610" y2="165" stroke="${C.muted}" stroke-width="1.5" opacity="0.5"/>
    <rect x="592" y="65" width="36" height="80" fill="none" stroke="${C.muted}" stroke-width="1.5" rx="2" opacity="0.5"/>
    <line x1="610" y1="85" x2="610" y2="135" stroke="${C.orange}" stroke-width="2"/>
    <rect x="595" y="92" width="30" height="38" fill="${C.orange}" opacity="0.9" stroke="${C.orange}" stroke-width="1.5" rx="2"/>
    <text x="610" y="190" fill="${C.orange}" font-size="10" font-family="monospace" text-anchor="middle">INSIDE</text>
    <text x="610" y="202" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">(compresión)</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${svg}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            TIPOS DE VELA — El cierre es el dato más importante
        </text>
    </svg>`;
}

// ─── GRÁFICO: Colores de velas ────────────────────────────────────────────────
function candle_colors() {
    const W=680, H=160;
    const configs=[
        {name:'ESTÁNDAR',  bull:'#26a69a', bear:'#ef5350'},
        {name:'TERMINAL',  bull:'#00ffad', bear:'#f23645'},
        {name:'HOLLOW',    bull:'none',    bear:'#888', stroke_bull:'#26a69a', stroke_bear:'#888'},
        {name:'MONOCROME', bull:'#ddd',    bear:'none', stroke_bull:'#ddd',   stroke_bear:'#ddd'},
    ];
    const candlePrices=[100,96,104,100,109,106,113,110,117,113,120];
    const mn=88,mx=126,range=mx-mn;

    let content='';
    configs.forEach(({name,bull,bear,stroke_bull,stroke_bear},ci)=>{
        const x0=20+ci*(W/4);
        content+=`<text x="${x0+(W/4-20)/2}" y="20" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">${name}</text>`;
        const pw=(W/4-30)/(candlePrices.length);
        candlePrices.forEach((p,i)=>{
            if(!i) return;
            const prev=candlePrices[i-1], isBull=p>prev;
            const cx=x0+i*pw+pw/2;
            const pyFn=(v)=>30+100-((v-mn)/range)*100;
            const yO=pyFn(prev),yC=pyFn(p),yH=pyFn(p+range*0.03),yL=pyFn(Math.min(prev,p)-range*0.025);
            const fillC=isBull?bull:bear;
            const strkC=isBull?(stroke_bull||bull):(stroke_bear||bear);
            content+=`<line x1="${cx}" y1="${yH}" x2="${cx}" y2="${yL}" stroke="${strkC}" stroke-width="1.5"/>
            <rect x="${cx-5}" y="${Math.min(yO,yC)}" width="10" height="${Math.max(Math.abs(yO-yC),2)}" fill="${fillC}" stroke="${strkC}" stroke-width="1.5" rx="1"/>`;
        });
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${Array.from({length:3},(_,i)=>`<line x1="${20+(i+1)*(W/4)}" y1="5" x2="${20+(i+1)*(W/4)}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>`).join('')}
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El color es convención — la estructura de la vela es lo que importa
        </text>
    </svg>`;
}

// ─── MÓDULO 2: ESTRUCTURA DE MERCADO ─────────────────────────────────────────

function hh_definition() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    const prices=[100,96,108,103,118,112,126,120,134,128,142];
    const mn=88, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    // HH markers at peaks
    const peaks=[[2,108],[4,118],[6,126],[8,134],[10,142]];
    let markers='';
    peaks.forEach(([i,v],pi)=>{
        markers+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="${C.accent}" opacity="0.9"/>
        <text x="${px(i).toFixed(1)}" y="${(py(v)-10).toFixed(1)}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">HH${pi+1}</text>`;
    });

    // Arrow showing upward progression
    const arrowY = py(148);
    markers+=`<path d="M ${px(2)} ${arrowY} Q ${px(6)} ${arrowY-15} ${px(10)} ${arrowY}" fill="none" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.4"/>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${markers}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            MÁXIMOS CRECIENTES — Cada pico supera al anterior
        </text>
    </svg>`;
}

function hh_psychology() {
    const W=680, H=230;
    const x0=40, y0=20, w=W-80, h=170;
    const prices=[100,96,112,105,124,116,138,128,148];
    const mn=88, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,18);
    });

    // Label each phase
    const phases=[
        {i:2,v:112,label:'A',color:C.accent},
        {i:4,v:124,label:'B',color:C.accent},
        {i:6,v:138,label:'C',color:C.accent},
        {i:8,v:148,label:'D',color:C.accent},
    ];
    let labels='';
    phases.forEach(({i,v,label,color})=>{
        labels+=`<rect x="${(px(i)-12).toFixed(1)}" y="${(py(v)-22).toFixed(1)}" width="24" height="16" fill="${color}" rx="3"/>
        <text x="${px(i).toFixed(1)}" y="${(py(v)-10).toFixed(1)}" fill="#000" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
    });

    // Sellers zone annotations
    labels+=`<text x="${(px(1.5)).toFixed(1)}" y="${(py(104)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">vendedores</text>
    <text x="${(px(3.5)).toFixed(1)}" y="${(py(115)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">fracasan</text>
    <text x="${(px(5.5)).toFixed(1)}" y="${(py(128)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">fracasan</text>
    <text x="${(px(7.5)).toFixed(1)}" y="${(py(140)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">fracasan</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${labels}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cada HH = vendedores intentaron frenar el precio y FRACASARON
        </text>
    </svg>`;
}

function hh_identification() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    // Weekly-style clear HH pattern
    const prices=[100,94,110,103,122,114,134,125,140,132,150];
    const mn=86, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,18);
    });

    // Connecting line between HHs
    const hhPeaks=[[2,110],[4,122],[6,134],[8,140],[10,150]];
    const hhPath=hhPeaks.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    let marks='';
    hhPeaks.forEach(([i,v])=>{
        marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.accent}"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${hhPath}" fill="none" stroke="${C.accent}" stroke-width="2" stroke-dasharray="6,3" opacity="0.6"/>
        ${marks}
        <text x="${x0+w-5}" y="${py(152)}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="end">HH ascendente</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            LÍNEA QUE CONECTA HH — Si sube, tendencia alcista confirmada
        </text>
    </svg>`;
}

function hh_breakout() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,101,108,105,112,108,116,112,118,115,120,118,130,128,138];
    const mn=92, mx=146, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.018),bull,13);
    });

    const resLevel=120, resY=py(resLevel);
    // Breakout candle
    const brkX=px(13), brkY=py(130);
    // Retest zone
    const rtX=px(14), rtY=py(121);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-5}" width="${w}" height="10" fill="${C.red}" opacity="0.06"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="8,4"/>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES ${resLevel}</text>
        ${candles}
        <circle cx="${brkX}" cy="${brkY}" r="8" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${brkX}" y="${py(135)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <rect x="${(rtX-14).toFixed(1)}" y="${(resY-8).toFixed(1)}" width="28" height="16" fill="${C.accent}" opacity="0.1" stroke="${C.accent}" stroke-width="1" stroke-dasharray="3,2"/>
        <text x="${rtX}" y="${(resY+18).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RETEST</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            RUPTURA DE HH + RETEST = Entrada de menor riesgo
        </text>
    </svg>`;
}

function hl_definition() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    const prices=[100,96,112,106,124,116,136,126,144];
    const mn=88, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,20);
    });

    const lows=[[1,96],[3,106],[5,116],[7,126]];
    const lowPath=lows.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    let marks='';
    lows.forEach(([i,v])=>{
        marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="${C.cyan}"/>
        <text x="${px(i).toFixed(1)}" y="${(py(v)+16).toFixed(1)}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">HL</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${lowPath}" fill="none" stroke="${C.cyan}" stroke-width="2" stroke-dasharray="6,3" opacity="0.6"/>
        ${marks}
        <text x="${x0+4}" y="${py(128)}" fill="${C.cyan}" font-size="10" font-family="monospace">HL ascendente →</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            MÍNIMOS CRECIENTES — Cada corrección termina más arriba
        </text>
    </svg>`;
}

function hh_hl_combined() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,112,106,124,116,136,126,148,138,158];
    const mn=88, mx=166, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    const peaks=[[2,112],[4,124],[6,136],[8,148],[10,158]];
    const lows=[[1,96],[3,106],[5,116],[7,126],[9,138]];
    const hhPath=peaks.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const hlPath=lows.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    let marks='';
    peaks.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.accent}"/>`; });
    lows.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.cyan}"/>`; });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${hhPath}" fill="none" stroke="${C.accent}" stroke-width="2" stroke-dasharray="6,3" opacity="0.7"/>
        <path d="${hlPath}" fill="none" stroke="${C.cyan}" stroke-width="2" stroke-dasharray="6,3" opacity="0.7"/>
        ${marks}
        <rect x="${x0+5}" y="${y0+5}" width="90" height="38" fill="${C.bg}" opacity="0.9" rx="3"/>
        <circle cx="${x0+14}" cy="${y0+16}" r="4" fill="${C.accent}"/>
        <text x="${x0+22}" y="${y0+20}" fill="${C.accent}" font-size="10" font-family="monospace">HH — máximos</text>
        <circle cx="${x0+14}" cy="${y0+32}" r="4" fill="${C.cyan}"/>
        <text x="${x0+22}" y="${y0+36}" fill="${C.cyan}" font-size="10" font-family="monospace">HL — mínimos</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            HH + HL SIMULTÁNEOS = Tendencia alcista sana y establecida
        </text>
    </svg>`;
}

function hl_stop_loss() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,112,106,124,116,132,122,140,130,148];
    const mn=88, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    const hlLevels=[[1,96,92],[3,106,102],[5,116,112],[7,122,118],[9,130,126]];
    let stopLines='';
    hlLevels.forEach(([i,hl,stop])=>{
        const sy=py(stop);
        stopLines+=`<line x1="${(px(i)-10).toFixed(1)}" y1="${sy.toFixed(1)}" x2="${(px(i)+10).toFixed(1)}" y2="${sy.toFixed(1)}" stroke="${C.red}" stroke-width="2" opacity="0.7"/>`;
    });

    // Entry arrow
    const entX=px(3), entY=py(106);
    stopLines+=`<line x1="${entX}" y1="${(entY+20).toFixed(1)}" x2="${entX}" y2="${(entY+5).toFixed(1)}" stroke="${C.accent}" stroke-width="2" marker-end="url(#arrSL)"/>
    <text x="${entX}" y="${(entY+34).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs><marker id="arrSL" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 0 L 6 3 L 0 6 z" fill="${C.accent}"/></marker></defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        ${stopLines}
        <rect x="${x0+5}" y="${y0+5}" width="105" height="18" fill="${C.bg}" opacity="0.9" rx="3"/>
        <text x="${x0+10}" y="${y0+16}" fill="${C.red}" font-size="10" font-family="monospace">— Stop loss (bajo HL)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            STOP LOSS = Siempre por debajo del último HL relevante
        </text>
    </svg>`;
}

function hl_failure() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Tendencia alcista que empieza a fallar
    const prices=[100,96,112,106,124,116,132,120,128,115,120,108,114];
    const mn=88, mx=140, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,14);
    });

    // Good HLs then failure
    const goodHL=[[1,96],[3,106],[5,116]];
    const failHL=[[7,120],[9,115],[11,108]];

    let marks='';
    goodHL.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.cyan}"/>
    <text x="${px(i).toFixed(1)}" y="${(py(v)+14).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">HL✓</text>`; });
    failHL.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.red}"/>
    <text x="${px(i).toFixed(1)}" y="${(py(v)+14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">HL✗</text>`; });

    // Warning zone
    const warnX=px(6.5);
    marks+=`<line x1="${warnX}" y1="${y0}" x2="${warnX}" y2="${y0+h}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.6"/>
    <text x="${(warnX+4).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace">⚠ HL empieza a fallar</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${marks}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            HL que bajan = primera señal de debilidad alcista
        </text>
    </svg>`;
}

function lh_definition() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    const prices=[150,155,140,148,132,142,124,135,116,128,110];
    const mn=102, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    const peaks=[[1,155],[3,148],[5,142],[7,135],[9,128]];
    const peakPath=peaks.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    let marks='';
    peaks.forEach(([i,v])=>{
        marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="${C.red}"/>
        <text x="${px(i).toFixed(1)}" y="${(py(v)-10).toFixed(1)}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">LH</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${peakPath}" fill="none" stroke="${C.red}" stroke-width="2" stroke-dasharray="6,3" opacity="0.6"/>
        ${marks}
        <text x="${x0+4}" y="${py(126)}" fill="${C.red}" font-size="10" font-family="monospace">LH descendente ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            MÁXIMOS DECRECIENTES — Cada rebote llega menos lejos
        </text>
    </svg>`;
}

function lh_psychology() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[150,155,138,148,126,140,116,132,108];
    const mn=100, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,18);
    });

    // Labels at each LH
    const lhPoints=[[1,155,'Atrapados\nsalen'],[3,148,'Cortos\nagregan'],[5,140,'Compradores\nagotados'],[7,132,'Más cortos']];
    let labels='';
    lhPoints.forEach(([i,v,txt])=>{
        const lines=txt.split('\n');
        labels+=`<line x1="${px(i).toFixed(1)}" y1="${(py(v)-5).toFixed(1)}" x2="${px(i).toFixed(1)}" y2="${(py(v)-22).toFixed(1)}" stroke="${C.red}" stroke-width="1" opacity="0.5"/>`;
        lines.forEach((l,li)=>{
            labels+=`<text x="${px(i).toFixed(1)}" y="${(py(v)-26-li*11).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle" opacity="0.85">${l}</text>`;
        });
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${labels}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Tres fuerzas crean el LH: atrapados, cortos y compradores agotados
        </text>
    </svg>`;
}

function lh_short_entry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[150,155,138,149,130,142,122,135,114,128,108];
    const mn=100, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,14);
    });

    // Entry zone at LH
    const lhX=px(3), lhY=py(149);
    const entryZoneY1=py(152), entryZoneY2=py(144);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <rect x="${(lhX-20).toFixed(1)}" y="${entryZoneY1.toFixed(1)}" width="40" height="${(entryZoneY2-entryZoneY1).toFixed(1)}" fill="${C.red}" opacity="0.1" stroke="${C.red}" stroke-width="1" stroke-dasharray="4,3"/>
        <text x="${lhX.toFixed(1)}" y="${(entryZoneY1-6).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">ZONA CORTO</text>
        <line x1="${lhX}" y1="${(lhY-5).toFixed(1)}" x2="${lhX}" y2="${(lhY+15).toFixed(1)}" stroke="${C.red}" stroke-width="2" marker-end="url(#arrDown)"/>
        <defs><marker id="arrDown" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 0 L 6 3 L 0 6 z" fill="${C.red}"/></marker></defs>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            LH = Zona de entrada para posiciones cortas
        </text>
    </svg>`;
}

function lh_reversal() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Bajista que se recupera
    const prices=[150,154,138,148,128,140,118,132,110,126,108,122,120,132,128,140];
    const mn=100, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // Last LH that gets broken
    const lastLH=132, lastLHY=py(lastLH);
    const breakX=px(13);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${lastLHY.toFixed(1)}" x2="${x0+w}" y2="${lastLHY.toFixed(1)}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <text x="${x0+w+4}" y="${(lastLHY+4).toFixed(1)}" fill="${C.orange}" font-size="10" font-family="monospace">LH ${lastLH}</text>
        ${candles}
        <circle cx="${breakX}" cy="${py(132)}" r="7" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${breakX}" y="${(py(137)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA LH</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Primer rebote que supera el LH anterior = inicio de recuperación
        </text>
    </svg>`;
}

function ll_definition() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    const prices=[150,155,138,148,124,140,112,130,100,122,90];
    const mn=82, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    const lows=[[2,138],[4,124],[6,112],[8,100],[10,90]];
    const llPath=lows.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    let marks='';
    lows.forEach(([i,v])=>{
        marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="${C.orange}"/>
        <text x="${px(i).toFixed(1)}" y="${(py(v)+16).toFixed(1)}" fill="${C.orange}" font-size="10" font-family="monospace" text-anchor="middle">LL</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${llPath}" fill="none" stroke="${C.orange}" stroke-width="2" stroke-dasharray="6,3" opacity="0.6"/>
        ${marks}
        <text x="${x0+4}" y="${py(88)}" fill="${C.orange}" font-size="10" font-family="monospace">LL descendente ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            MÍNIMOS DECRECIENTES — Cada caída rompe el suelo anterior
        </text>
    </svg>`;
}

function lh_ll_combined() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[150,155,136,148,122,140,110,132,100,124,90];
    const mn=82, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    const peaks=[[1,155],[3,148],[5,140],[7,132],[9,124]];
    const lows=[[2,136],[4,122],[6,110],[8,100],[10,90]];
    const lhPath=peaks.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const llPath=lows.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    let marks='';
    peaks.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.red}"/>`; });
    lows.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.orange}"/>`; });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${lhPath}" fill="none" stroke="${C.red}" stroke-width="2" stroke-dasharray="6,3" opacity="0.7"/>
        <path d="${llPath}" fill="none" stroke="${C.orange}" stroke-width="2" stroke-dasharray="6,3" opacity="0.7"/>
        ${marks}
        <rect x="${x0+5}" y="${y0+5}" width="105" height="38" fill="${C.bg}" opacity="0.9" rx="3"/>
        <circle cx="${x0+14}" cy="${y0+16}" r="4" fill="${C.red}"/>
        <text x="${x0+22}" y="${y0+20}" fill="${C.red}" font-size="10" font-family="monospace">LH — rebotes</text>
        <circle cx="${x0+14}" cy="${y0+32}" r="4" fill="${C.orange}"/>
        <text x="${x0+22}" y="${y0+36}" fill="${C.orange}" font-size="10" font-family="monospace">LL — caídas</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            LH + LL SIMULTÁNEOS = Tendencia bajista establecida
        </text>
    </svg>`;
}

function ll_trailing_stop() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[150,155,136,148,122,140,110,132,100,122,90];
    const mn=82, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,14);
    });

    // Stop trail following LH down
    const stops=[[1,158],[3,152],[5,144],[7,136],[9,126]];
    let stopLines='';
    stops.forEach(([i,v],si)=>{
        const nextI=stops[si+1]?stops[si+1][0]:10;
        const sy=py(v);
        stopLines+=`<line x1="${px(i).toFixed(1)}" y1="${sy.toFixed(1)}" x2="${px(nextI).toFixed(1)}" y2="${sy.toFixed(1)}" stroke="${C.red}" stroke-width="1.5" opacity="0.6" stroke-dasharray="5,3"/>`;
    });

    // Entry
    stopLines+=`<text x="${px(1)}" y="${py(160)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">STOP</text>`;
    stopLines+=`<line x1="${px(0.5)}" y1="${(py(155)+5).toFixed(1)}" x2="${px(0.5)}" y2="${(py(155)+18).toFixed(1)}" stroke="${C.red}" stroke-width="2" marker-end="url(#arrD2)"/>
    <text x="${px(0.5)}" y="${(py(155)+32).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">CORTO</text>
    <defs><marker id="arrD2" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 0 L 6 3 L 0 6 z" fill="${C.red}"/></marker></defs>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${stopLines}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            TRAILING STOP en cortos: baja con cada nuevo LH
        </text>
    </svg>`;
}

function full_structure_read() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=185;
    // Full cycle: alcista → cambio → bajista
    const prices=[100,96,112,104,124,114,136,124,148,136,144,130,138,122,130,114,120,106,112,98];
    const mn=88, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    // Phase labels
    const phase1X=px(4), phase2X=px(9.5), phase3X=px(15);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${y0}" width="${(px(8)-x0).toFixed(1)}" height="${h}" fill="${C.accent}" opacity="0.03"/>
        <rect x="${px(8).toFixed(1)}" y="${y0}" width="${(px(11)-px(8)).toFixed(1)}" height="${h}" fill="${C.yellow}" opacity="0.03"/>
        <rect x="${px(11).toFixed(1)}" y="${y0}" width="${(x0+w-px(11)).toFixed(1)}" height="${h}" fill="${C.red}" opacity="0.03"/>
        ${candles}
        <text x="${phase1X}" y="${y0+14}" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">HH+HL</text>
        <text x="${phase1X}" y="${y0+26}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ALCISTA</text>
        <text x="${phase2X}" y="${y0+14}" fill="${C.yellow}" font-size="11" font-family="monospace" text-anchor="middle">CAMBIO</text>
        <text x="${phase2X}" y="${y0+26}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">TRANSICIÓN</text>
        <text x="${phase3X}" y="${y0+14}" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">LH+LL</text>
        <text x="${phase3X}" y="${y0+26}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">BAJISTA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            CICLO COMPLETO — HH+HL → Transición → LH+LL
        </text>
    </svg>`;
}

// ─── MÓDULO 3: ANÁLISIS DE TENDENCIA ─────────────────────────────────────────

function uptrend_phases() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Acumulación → Tendencia → Distribución
    const prices=[100,98,102,99,103,100,104,101,105,102,
                  108,115,112,120,116,126,122,132,128,138,134,144,140,150,
                  148,152,150,154,151,155,152,154,150,152,148];
    const mn=90, mx=162, range=mx-mn;
    const n=prices.length;
    const px=(i)=>x0+(i/(n-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.015),py(Math.min(prev,p)-(mx-mn)*0.012),bull,9);
    });

    // Phase backgrounds
    const p1End=px(9), p2End=px(23);
    const phases=[
        {x1:x0,x2:p1End,color:C.cyan,label:'ACUMULACIÓN',y:y0+14},
        {x1:p1End,x2:p2End,color:C.accent,label:'TENDENCIA',y:y0+14},
        {x1:p2End,x2:x0+w,color:C.orange,label:'DISTRIBUCIÓN',y:y0+14},
    ];

    let bg='';
    phases.forEach(({x1,x2,color,label,y})=>{
        bg+=`<rect x="${x1.toFixed(1)}" y="${y0}" width="${(x2-x1).toFixed(1)}" height="${h}" fill="${color}" opacity="0.05"/>
        <text x="${((x1+x2)/2).toFixed(1)}" y="${y}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" opacity="0.8">${label}</text>
        <line x1="${x2.toFixed(1)}" y1="${y0}" x2="${x2.toFixed(1)}" y2="${y0+h}" stroke="${color}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${bg}${candles}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            TRES FASES: Acumulación → Tendencia (donde se gana) → Distribución
        </text>
    </svg>`;
}

function uptrend_entries() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,104,100,110,105,114,108,120,113,124,118,130,122,136,128,142];
    const mn=88, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,13);
    });

    // EMA21
    let ema=prices[0],emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k);emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // Entry arrows at HLs
    const entries=[[1,96],[3,100],[5,105],[7,108],[9,113],[11,118],[13,122]];
    let arrows='';
    entries.forEach(([i,v])=>{
        const ax=px(i), ay=py(v);
        arrows+=`<line x1="${ax}" y1="${(ay+16).toFixed(1)}" x2="${ax}" y2="${(ay+4).toFixed(1)}" stroke="${C.accent}" stroke-width="1.5" marker-end="url(#arrUp3)"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs><marker id="arrUp3" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 5 L 2.5 0 L 5 5 z" fill="${C.accent}"/></marker></defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2"/>
        ${arrows}
        <text x="${x0+w-110}" y="${y0+14}" fill="${C.orange}" font-size="10" font-family="monospace">── EMA 21</text>
        <text x="${x0+w-110}" y="${y0+28}" fill="${C.accent}" font-size="10" font-family="monospace">↑ Entradas en HL</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            LAS ENTRADAS ESTÁN EN LOS RETROCESOS — No cuando el precio está arriba
        </text>
    </svg>`;
}

function uptrend_management() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,112,104,126,116,138,126,148,136,158,144,168];
    const mn=88, mx=176, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,16);
    });

    // Stop trail under HLs
    const hlStops=[[1,92],[3,100],[5,112],[7,122],[9,132],[11,140]];
    let stops='';
    hlStops.forEach(([i,v],si)=>{
        const nx=hlStops[si+1]?px(hlStops[si+1][0]):px(12);
        const sy=py(v);
        stops+=`<line x1="${px(i).toFixed(1)}" y1="${sy.toFixed(1)}" x2="${nx.toFixed(1)}" y2="${sy.toFixed(1)}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>`;
    });

    // Partial exit markers
    const partials=[[2,112],[4,126],[6,138],[8,148],[10,158]];
    let pExits='';
    partials.forEach(([i,v])=>{
        pExits+=`<line x1="${px(i)}" y1="${(py(v)-4).toFixed(1)}" x2="${px(i)}" y2="${(py(v)-16).toFixed(1)}" stroke="${C.yellow}" stroke-width="1.5" marker-end="url(#arrDn3)"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs><marker id="arrDn3" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 0 L 2.5 5 L 5 0 z" fill="${C.yellow}"/></marker></defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${stops}${pExits}
        <rect x="${x0+5}" y="${y0+5}" width="165" height="38" fill="${C.bg}" opacity="0.9" rx="3"/>
        <line x1="${x0+10}" y1="${y0+16}" x2="${x0+22}" y2="${y0+16}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="4,3"/>
        <text x="${x0+26}" y="${y0+20}" fill="${C.red}" font-size="10" font-family="monospace">Stop (sube con HL)</text>
        <line x1="${x0+10}" y1="${y0+32}" x2="${x0+22}" y2="${y0+32}" stroke="${C.yellow}" stroke-width="1.5"/>
        <text x="${x0+26}" y="${y0+36}" fill="${C.yellow}" font-size="10" font-family="monospace">Cierre parcial</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            STOP SUBE CON CADA HL — Cierre parcial en resistencias
        </text>
    </svg>`;
}

function uptrend_exhaustion() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=160;
    // Impulsos que se acortan
    const prices=[100,94,116,107,130,119,142,129,150,138,155,145,158,148,160,152,161];
    const mn=86, mx=168, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const rsiY0=y0+h+20, rsiH=35;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.02),py(Math.min(prev,p)-(mx-mn)*0.015),bull,12);
    });

    // RSI divergence (price HH, RSI LH)
    const rsi=[45,40,65,55,72,60,76,63,74,62,72,61,70,60,68,59,67];
    const rMn=35,rMx=82,rRange=rMx-rMn;
    const pyR=(v)=>rsiY0+rsiH-((v-rMn)/rRange)*rsiH;
    const rsiPath=rsi.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${pyR(v).toFixed(1)}`).join(' ');

    // Divergence lines
    const dX1=px(6),dX2=px(16);
    const dY1P=py(142),dY2P=py(161);
    const dY1R=pyR(76),dY2R=pyR(67);

    return `<svg viewBox="0 0 ${W} ${H+20}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+20}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <text x="${x0+4}" y="${y0+12}" fill="${C.textDim}" font-size="9" font-family="monospace">PRECIO</text>
        <line x1="${dX1}" y1="${dY1P}" x2="${dX2}" y2="${dY2P}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.5"/>
        <line x1="${dX1}" y1="${dY1R}" x2="${dX2}" y2="${dY2R}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,3"/>
        ${gridLines(x0,rsiY0,w,rsiH,2)}
        <path d="${rsiPath}" fill="none" stroke="${C.cyan}" stroke-width="1.8"/>
        <text x="${x0+4}" y="${rsiY0+12}" fill="${C.cyan}" font-size="9" font-family="monospace">RSI</text>
        <circle cx="${dX2}" cy="${dY2P}" r="4" fill="none" stroke="${C.accent}" stroke-width="1.5"/>
        <circle cx="${dX2}" cy="${dY2R}" r="4" fill="none" stroke="${C.red}" stroke-width="1.5"/>
        <text x="${W/2}" y="${H+16}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">
            ⚠ DIVERGENCIA: Precio HH — RSI LH = Agotamiento alcista
        </text>
    </svg>`;
}

function downtrend_characteristics() {
    const W=680, H=220;
    // Two panels: alcista (lenta) vs bajista (rápida)
    const panelW=(W-50)/2;
    const bullPrices=[100,98,104,101,108,105,112,108,116,112,120,116,124,120,128];
    const bearPrices=[130,125,110,118,102,114,88,105,74,98,62,90,52,82,44];

    function panel(prices, x0, isBull) {
        const mn=Math.min(...prices)-5,mx=Math.max(...prices)+5,range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>20+160-((v-mn)/range)*160;
        let out='';
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.03),py(Math.min(prev,p)-(mx-mn)*0.025),bull,13);
        });
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        <text x="${panelW/2}" y="16" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">ALCISTA — Lenta y ordenada</text>
        <text x="${panelW+28+panelW/2}" y="16" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">BAJISTA — Rápida y violenta</text>
        ${panel(bullPrices, 5, true)}
        ${panel(bearPrices, panelW+30, false)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Las bajistas caen más rápido de lo que las alcistas suben
        </text>
    </svg>`;
}

function downtrend_early_signs() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Tendencia alcista que empieza a deteriorarse
    const prices=[100,96,114,106,126,116,138,126,148,140,152,140,148,134,140,128,134,120,126];
    const mn=112, mx=160, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // SMA50 (flat/declining)
    const sma50=[null,null,null,null,null,null,null,null,null,126,128,129,130,130,129,128,127,125,123];
    const s50Path=sma50.map((v,i)=>v===null?null:`${sma50[i-1]===null?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).filter(Boolean).join(' ');

    // Warning markers
    const warn1X=px(9), warn1Y=py(140); // First LH
    const warn2X=px(13), warn2Y=py(134); // Price below SMA50

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${s50Path}" fill="none" stroke="${C.cyan}" stroke-width="1.8" stroke-dasharray="6,3" opacity="0.7"/>
        <circle cx="${warn1X}" cy="${warn1Y}" r="8" fill="none" stroke="${C.orange}" stroke-width="2"/>
        <text x="${warn1X}" y="${(warn1Y-12).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">1er LH</text>
        <circle cx="${warn2X}" cy="${warn2Y}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${warn2X}" y="${(warn2Y+20).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Bajo SMA50</text>
        <text x="${x0+w-100}" y="${y0+14}" fill="${C.cyan}" font-size="10" font-family="monospace">── SMA 50</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Señales tempranas: 1er LH + precio bajo SMA50
        </text>
    </svg>`;
}

function downtrend_responses() {
    const W=680, H=180;
    const items=[
        {label:'CASH 100%',pct:100,color:C.accent,desc:'Tendencia bajista clara'},
        {label:'REDUCIDO 25%',pct:25,color:C.yellow,desc:'Señales mixtas'},
        {label:'CORTO',pct:0,color:C.red,desc:'Estructura LH+LL clara',isShort:true},
    ];
    const bw=160, gap=40, startX=60;

    let content='';
    items.forEach(({label,pct,color,desc,isShort},i)=>{
        const x=startX+i*(bw+gap);
        const barH=isShort?80:pct*0.8;
        const barY=100-barH;
        content+=`<rect x="${x}" y="${barY}" width="${bw}" height="${barH}" fill="${color}" opacity="${isShort?0.2:0.15}" rx="4" stroke="${color}" stroke-width="1.5"/>
        ${isShort?`<text x="${x+bw/2}" y="${barY+barH/2}" fill="${color}" font-size="20" text-anchor="middle">↓</text>`:
        `<text x="${x+bw/2}" y="${barY+barH/2+5}" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle">${pct}%</text>`}
        <text x="${x+bw/2}" y="120" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle">${label}</text>
        <text x="${x+bw/2}" y="136" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${desc}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Tres respuestas válidas — ninguna es "mantener longs y esperar"
        </text>
    </svg>`;
}

function downtrend_bounces() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[148,155,136,150,122,142,108,136,96,130,86,124,78];
    const mn=70, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    // Bounce labels
    const bounces=[[1,155,'Trampa\n#1'],[3,150,'Trampa\n#2'],[5,142,'Trampa\n#3'],[7,136,'Trampa\n#4'],[9,130,'Trampa\n#5']];
    let traps='';
    bounces.forEach(([i,v,txt])=>{
        const lines=txt.split('\n');
        traps+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="6" fill="none" stroke="${C.red}" stroke-width="1.5" opacity="0.8"/>`;
        lines.forEach((l,li)=>{
            traps+=`<text x="${px(i).toFixed(1)}" y="${(py(v)-10-li*11).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`;
        });
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${traps}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            CADA REBOTE ES UNA TRAMPA hasta que la estructura cambie
        </text>
    </svg>`;
}

function range_definition() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    const prices=[120,118,124,121,128,124,122,126,120,124,128,122,126,120,124,128,122,126,120];
    const res=130, sup=118;
    const mn=112, mx=136, range_v=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range_v)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(Math.min(res-0.5,p+(mx-mn)*0.02)),py(Math.max(sup+0.5,Math.min(prev,p)-(mx-mn)*0.015)),bull,14);
    });

    const resY=py(res), supY=py(sup);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-4}" width="${w}" height="${supY-resY+8}" fill="${C.yellow}" opacity="0.04"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="2" stroke-dasharray="8,4"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="2" stroke-dasharray="8,4"/>
        ${candles}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES ${res}</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SUP ${sup}</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            RANGO LATERAL — Precio rebota entre soporte y resistencia horizontales
        </text>
    </svg>`;
}

function range_identification() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,115,128,118,132,122,126,118,130,120,128,116,132,120,130];
    const res=133, sup=115;
    const mn=109, mx=139, rv=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/rv)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(Math.min(res-0.3,p+(mx-mn)*0.02)),py(Math.max(sup+0.3,Math.min(prev,p)-(mx-mn)*0.018)),bull,14);
    });

    const resY=py(res), supY=py(sup);
    // Touch markers
    const resTouches=[[2,132],[4,132],[6,126],[8,130],[10,128],[12,132],[14,130]].filter(([,v])=>v>=130);
    const supTouches=[[1,115],[3,118],[5,122],[7,118],[9,120],[11,116],[13,120]].filter(([,v])=>v<=120);

    let marks='';
    resTouches.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="none" stroke="${C.red}" stroke-width="1.5"/>`; });
    supTouches.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="none" stroke="${C.accent}" stroke-width="1.5"/>`; });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}${marks}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RESISTENCIA</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SOPORTE</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            RANGO VÁLIDO — Mínimo 2 toques en cada extremo (marcados con círculos)
        </text>
    </svg>`;
}

function range_strategies() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,115,130,120,132,118,128,116,132,119,130,116,134,120,132];
    const res=134, sup=115;
    const mn=108, mx=140, rv=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/rv)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(Math.min(res-0.3,p+(mx-mn)*0.02)),py(Math.max(sup+0.3,Math.min(prev,p)-(mx-mn)*0.018)),bull,13);
    });

    const resY=py(res), supY=py(sup);

    // Buy at support arrows
    const buys=[[1,115],[3,120],[7,116],[11,116]];
    const sells=[[2,132],[4,132],[8,132],[12,134]];
    let arrows='';
    buys.forEach(([i,v])=>{ arrows+=`<line x1="${px(i)}" y1="${(py(v)+16).toFixed(1)}" x2="${px(i)}" y2="${(py(v)+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2" marker-end="url(#aUp4)"/>`; });
    sells.forEach(([i,v])=>{ arrows+=`<line x1="${px(i)}" y1="${(py(v)-4).toFixed(1)}" x2="${px(i)}" y2="${(py(v)-16).toFixed(1)}" stroke="${C.red}" stroke-width="2" marker-end="url(#aDn4)"/>`; });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <marker id="aUp4" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 5 L 2.5 0 L 5 5 z" fill="${C.accent}"/></marker>
            <marker id="aDn4" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 0 L 2.5 5 L 5 0 z" fill="${C.red}"/></marker>
        </defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}${arrows}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">VENDER</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">COMPRAR</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Compra en soporte ↑ — Vende en resistencia ↓ — El medio es tierra de nadie
        </text>
    </svg>`;
}

function range_patience() {
    const W=680, H=200;
    const x0=40, y0=20, w=W-80, h=140;
    const prices=[120,116,128,120,124,118,126,120,124,118,122,116,
                  126,118,122,116,124,118,130,140,148,142,155];
    const mn=108, mx=162, rv=mx-mn;
    const res=128, sup=116;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/rv)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(Math.min(mx-1,p+(mx-mn)*0.025)),py(Math.max(mn+1,Math.min(prev,p)-(mx-mn)*0.02)),bull,10);
    });

    const resY=py(res), supY=py(sup);
    const breakX=px(18);

    // Waiting zone background
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-2}" width="${(breakX-x0).toFixed(1)}" height="${(supY-resY+4).toFixed(1)}" fill="${C.yellow}" opacity="0.05"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.2" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${x0}" y1="${supY}" x2="${breakX}" y2="${supY}" stroke="${C.accent}" stroke-width="1.2" stroke-dasharray="6,4" opacity="0.7"/>
        ${candles}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>
        <text x="${(breakX+8).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${((x0+breakX)/2).toFixed(1)}" y="${y0+12}" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="middle" opacity="0.7">ESPERAR</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            En rango: espera la ruptura — No operes el medio
        </text>
    </svg>`;
}

function trendline_valid() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,114,106,128,116,140,128,152,140,164];
    const mn=88, mx=172, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,16);
    });

    // Trendline through lows: (1,96), (3,106), (5,116), (7,128), (9,140)
    const tlPoints=[[1,96],[3,106],[5,116],[7,128],[9,140]];
    const tlPath=tlPoints.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    // Extend to edge
    const extPath=`${tlPath} L ${px(11).toFixed(1)} ${py(152).toFixed(1)}`;

    let touches='';
    tlPoints.forEach(([i,v],ti)=>{
        touches+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="5" fill="${ti>=2?C.accent:'none'}" stroke="${C.accent}" stroke-width="1.5"/>`;
        if(ti>=2) touches+=`<text x="${px(i).toFixed(1)}" y="${(py(v)+16).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">T${ti+1}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${extPath}" fill="none" stroke="${C.accent}" stroke-width="2" opacity="0.8"/>
        ${touches}
        <text x="${px(8)}" y="${(py(140)-14).toFixed(1)}" fill="${C.accent}" font-size="10" font-family="monospace">Línea validada (3+ toques)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            LÍNEA VÁLIDA: 3+ toques en mínimos crecientes (T3, T4, T5 marcados)
        </text>
    </svg>`;
}

function trendline_drawing() {
    const W=680, H=230;
    // Two panels: correcto vs incorrecto
    const panelW=(W-50)/2;
    const prices=[100,95,114,104,128,114,140,126,152,138,164];
    const mn=86, mx=172, range=mx-mn;

    function drawPanel(x0, correct) {
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>20+170-((v-mn)/range)*170;
        let out='';
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.025),bull,12);
        });
        // Correct: through mecha lows (95, 104, 114)
        // Incorrect: through body lows (100, 108, 116)
        const pts=correct
            ? [[1,95],[3,104],[5,114],[7,126],[9,138],[11,152]]
            : [[0,100],[2,108],[4,118],[6,130],[8,142],[10,154]];
        const path=pts.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
        out+=`<path d="${path}" fill="none" stroke="${correct?C.accent:C.red}" stroke-width="2" stroke-dasharray="${correct?'none':'6,3'}"/>`;
        if(correct) pts.slice(0,3).forEach(([i,v])=>{ out+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.accent}"/>`; });
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        <text x="${panelW/2}" y="16" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">✓ Por mechas (correcto)</text>
        <text x="${panelW+28+panelW/2}" y="16" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">✗ Por cuerpos (incorrecto)</text>
        ${drawPanel(5, true)}
        ${drawPanel(panelW+30, false)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Conecta los mínimos de MECHA, no de cuerpo
        </text>
    </svg>`;
}

function price_channel() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const lows=[100,108,116,124,132,140,148];
    const highs=[114,122,130,138,146,154,162];
    const mn=92, mx=170, range=mx-mn;
    const n=lows.length;
    const px=(i)=>x0+(i/(n-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    // Generate candles between channels
    let candles='';
    for(let i=0;i<n-1;i++){
        const pts=2;
        for(let j=0;j<pts;j++){
            const t=(i*pts+j)/((n-1)*pts);
            const lo=lows[i]+(lows[i+1]-lows[i])*(j/pts);
            const hi=highs[i]+(highs[i+1]-highs[i])*(j/pts);
            const mid=(lo+hi)/2;
            const bull=j%2===0;
            const cx=x0+t*w;
            const yO=py(mid+(bull?-2:2));
            const yC=py(mid+(bull?2:-2));
            candles+=candleRow(cx,yO,yC,py(bull?hi:mid+1),py(bull?mid-1:lo),bull,12);
        }
    }

    const lowPath=lows.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const highPath=highs.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // Fill between
    const fillPath=`${lowPath} L ${px(n-1)} ${py(highs[n-1])} ${highs.map((v,i)=>`L ${px(n-1-i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ')} Z`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${fillPath}" fill="${C.accent}" opacity="0.04"/>
        ${candles}
        <path d="${lowPath}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <path d="${highPath}" fill="none" stroke="${C.cyan}" stroke-width="2"/>
        <text x="${x0+w-110}" y="${y0+14}" fill="${C.accent}" font-size="10" font-family="monospace">── Canal inferior</text>
        <text x="${x0+w-110}" y="${y0+28}" fill="${C.cyan}" font-size="10" font-family="monospace">── Canal superior</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            CANAL ALCISTA — Dos líneas paralelas definen el rango de la tendencia
        </text>
    </svg>`;
}

function trendline_break() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Alcista que rompe la línea
    const prices=[100,96,114,104,126,114,136,122,144,130,148,
                  136,138,124,126,112,118,106,114,102];
    const mn=94, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // Trendline through lows (extended)
    const tlStart=[1,96], tlMid=[3,104], tlBreak=[12,136];
    const tlY=(i)=> {
        const slope=(tlBreak[1]-tlStart[1])/(tlBreak[0]-tlStart[0]);
        return tlStart[1]+slope*(i-tlStart[0]);
    };
    const tlPath=`M ${px(tlStart[0]).toFixed(1)} ${py(tlStart[1]).toFixed(1)} L ${px(19).toFixed(1)} ${py(tlY(19)).toFixed(1)}`;

    // Break point
    const breakI=13, breakY=py(prices[13]);

    // Retest
    const retestI=16, retestY=py(tlY(16));

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${tlPath}" fill="none" stroke="${C.accent}" stroke-width="2" stroke-dasharray="7,3" opacity="0.7"/>
        <circle cx="${px(breakI).toFixed(1)}" cy="${breakY}" r="7" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(breakI).toFixed(1)}" y="${(breakY+20).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <circle cx="${px(retestI).toFixed(1)}" cy="${retestY.toFixed(1)}" r="6" fill="none" stroke="${C.orange}" stroke-width="2"/>
        <text x="${px(retestI).toFixed(1)}" y="${(retestY-12).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">RETEST</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura + Retest fallido = Confirmación de cambio de tendencia
        </text>
    </svg>`;
}

// ─── MÓDULO 4: SOPORTE Y RESISTENCIA ─────────────────────────────────────────

function fresh_support_formation() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=170;
    const prices=[130,126,118,112,106,110,116,122,128,134,140,136,142];
    const mn=98, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,16);
    });

    const supLevel=106, supY=py(supLevel);
    // Formation candle (strong bullish reversal at support)
    const formX=px(4), formY=py(106);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-4}" width="${w}" height="8" fill="${C.accent}" opacity="0.08"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="8,4"/>
        ${candles}
        <circle cx="${formX}" cy="${formY}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${formX}" y="${(formY+22).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">FORMACIÓN</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SUP ${supLevel}</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            SOPORTE FRESCO — Formado en el primer rechazo fuerte
        </text>
    </svg>`;
}

function fresh_support_formation_2() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[128,122,114,108,102,108,116,124,132,140,148];
    const mn=94, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,20);
    });

    const phases=[
        {i:0,i2:4,label:'CAÍDA',color:C.red},
        {i:4,i2:5,label:'REVERSIÓN',color:C.accent},
        {i:5,i2:10,label:'IMPULSO ALCISTA',color:C.accent},
    ];

    let phaseBgs='';
    phases.forEach(({i,i2,label,color})=>{
        const x1=px(i), x2=px(i2);
        phaseBgs+=`<rect x="${x1.toFixed(1)}" y="${y0}" width="${(x2-x1).toFixed(1)}" height="${h}" fill="${color}" opacity="0.04"/>
        <text x="${((x1+x2)/2).toFixed(1)}" y="${y0+13}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${label}</text>`;
    });

    const supY=py(102);
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${phaseBgs}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.6"/>
        ${candles}
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SUP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Caída → Reversión fuerte → Impulso = Soporte fresco formado
        </text>
    </svg>`;
}

function fresh_support_entry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[128,120,112,106,110,116,124,132,118,112,108,114,122,130,138,146];
    const mn=100, mx=154, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,13);
    });

    const supLevel=108, supY=py(supLevel);
    const retestX=px(10), retestY=py(108);
    const stopY=py(104);
    const targetY=py(132);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-5}" width="${w}" height="10" fill="${C.accent}" opacity="0.07"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        ${candles}
        <line x1="${retestX}" y1="${(retestY+18).toFixed(1)}" x2="${retestX}" y2="${(retestY+5).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUp5)"/>
        <defs><marker id="aUp5" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="10" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="10" font-family="monospace">OBJETIVO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retest del soporte fresco = Entrada de alta probabilidad
        </text>
    </svg>`;
}

function fresh_vs_consolidated() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    // Panel izq: soporte fresco (un rebote limpio)
    const freshPrices=[130,124,116,110,104,110,118,126,134,128,122,116,112,118,126,134];
    // Panel der: zona de consolidación actuando como soporte
    const consolPrices=[110,112,108,114,110,116,112,114,110,108,112,116,108,114,110,
                        120,128,136,144,132,126,120,116,122,130,138];

    function drawPanel(prices, x0, label, color) {
        const mn=Math.min(...prices)-4, mx=Math.max(...prices)+4, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>20+170-((v-mn)/range)*170;
        let out=`<text x="${x0+panelW/2}" y="16" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,10);
        });
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.cyan}" opacity="0.03" rx="5"/>
        ${drawPanel(freshPrices, 5, 'SOPORTE FRESCO — 1 toque', C.accent)}
        ${drawPanel(consolPrices, panelW+30, 'CONSOLIDACIÓN → SOPORTE', C.cyan)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ambos actúan como soporte — por mecanismos diferentes
        </text>
    </svg>`;
}

function resistance_why() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,106,112,118,124,130,136,130,124,118,112,118,124,130,134,128,122];
    const mn=94, mx=144, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const resLevel=136, resY=py(resLevel);
    // Trapped buyers zone (between 130-136)
    const trapTop=py(130), trapBot=py(136);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-3}" width="${w}" height="6" fill="${C.red}" opacity="0.08"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="2" stroke-dasharray="8,4"/>
        <rect x="${x0}" y="${Math.min(trapTop,trapBot)}" width="${w}" height="${Math.abs(trapTop-trapBot)}" fill="${C.orange}" opacity="0.05"/>
        ${candles}
        <text x="${px(6).toFixed(1)}" y="${(py(133)-8).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">Atrapados</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES ${resLevel}</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Los atrapados sobre la resistencia crean "overhead supply"
        </text>
    </svg>`;
}

function resistance_types() {
    const W=680, H=220;
    const x0=30, y0=20, w=W-60, h=160;
    const levels=[
        {v:95,label:'ATH — Máximo histórico',color:C.red,strength:5},
        {v:80,label:'Máximo 2 años',color:'#ff6b6b',strength:4},
        {v:65,label:'LH de tendencia bajista',color:C.orange,strength:3},
        {v:50,label:'Techo del rango actual',color:C.yellow,strength:2},
        {v:35,label:'Máximo intradiario',color:C.muted,strength:1},
    ];
    const mn=25, mx=105, range=mx-mn;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let lines='';
    levels.forEach(({v,label,color,strength})=>{
        const ly=py(v);
        const barW=(strength/5)*120;
        lines+=`<line x1="${x0}" y1="${ly}" x2="${x0+w-140}" y2="${ly}" stroke="${color}" stroke-width="${strength===5?2:1.5}" stroke-dasharray="${strength===5?'none':'6,4'}" opacity="${0.4+strength*0.12}"/>
        <rect x="${x0+w-130}" y="${ly-5}" width="${barW}" height="10" fill="${color}" opacity="0.3" rx="3"/>
        ${'★'.repeat(strength).split('').map((_,si)=>`<text x="${x0+w-128+si*14}" y="${ly+4}" fill="${color}" font-size="10">★</text>`).join('')}
        <text x="${x0+4}" y="${ly-4}" fill="${color}" font-size="9" font-family="monospace">${label}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${lines}
        <text x="${x0+w-70}" y="${y0+12}" fill="${C.textDim}" font-size="9" font-family="monospace">FUERZA →</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Jerarquía de resistencias — El ATH es la más poderosa
        </text>
    </svg>`;
}

function resistance_trading() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,106,114,122,130,136,140,143,141,138,134,128];
    const mn=92, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,16);
    });

    const resLevel=144, resY=py(resLevel);
    // Partial exit zone
    const partialX=px(6), partialY=py(140);
    const exitX=px(8), exitY=py(141);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-3}" width="${w}" height="6" fill="${C.red}" opacity="0.1"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="8,4"/>
        ${candles}
        <line x1="${partialX}" y1="${(partialY-4).toFixed(1)}" x2="${partialX}" y2="${(partialY-18).toFixed(1)}" stroke="${C.yellow}" stroke-width="2" marker-end="url(#aDn5)"/>
        <text x="${partialX}" y="${(partialY-24).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">50% salida</text>
        <line x1="${exitX}" y1="${(exitY-4).toFixed(1)}" x2="${exitX}" y2="${(exitY-18).toFixed(1)}" stroke="${C.red}" stroke-width="2" marker-end="url(#aDn5)"/>
        <text x="${exitX}" y="${(exitY-24).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Resto</text>
        <defs><marker id="aDn5" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 0 L 2.5 5 L 5 0 z" fill="${C.yellow}"/></marker></defs>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cerca de resistencia mayor: salida parcial anticipada
        </text>
    </svg>`;
}

function resistance_breakout() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,106,112,118,124,130,134,128,122,128,134,140,148,142,136,140,148,156];
    const mn=92, mx=164, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const resLevel=134, resY=py(resLevel);
    const breakX=px(11), retestX=px(14), retestY=py(136);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        ${candles}
        <circle cx="${breakX}" cy="${py(140)}" r="7" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${breakX}" y="${(py(145)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <rect x="${(retestX-14).toFixed(1)}" y="${(resY-8).toFixed(1)}" width="28" height="16" fill="${C.accent}" opacity="0.1" stroke="${C.accent}" stroke-width="1" stroke-dasharray="3,2"/>
        <text x="${retestX.toFixed(1)}" y="${(resY+18).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RETEST = SOPORTE</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES→SUP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            POLARIDAD: Resistencia rota → se convierte en soporte
        </text>
    </svg>`;
}

function zone_vs_level() {
    const W=680, H=220;
    const panelW=(W-50)/2;
    const prices=[120,114,108,112,110,114,112,116,114,118,116,120];
    const supExact=108, supZoneTop=111, supZoneBot=106;

    function drawPanel(x0, useZone) {
        const mn=100, mx=128, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>20+160-((v-mn)/range)*160;
        let out='';
        if(useZone) {
            out+=`<rect x="${x0}" y="${py(supZoneTop)}" width="${panelW}" height="${py(supZoneBot)-py(supZoneTop)}" fill="${C.accent}" opacity="0.08"/>
            <line x1="${x0}" y1="${py(supZoneTop)}" x2="${x0+panelW}" y2="${py(supZoneTop)}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>
            <line x1="${x0}" y1="${py(supZoneBot)}" x2="${x0+panelW}" y2="${py(supZoneBot)}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>
            <text x="${x0+panelW/2}" y="${py(109)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ZONA ${supZoneBot}-${supZoneTop}</text>`;
        } else {
            out+=`<line x1="${x0}" y1="${py(supExact)}" x2="${x0+panelW}" y2="${py(supExact)}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,3"/>
            <text x="${x0+panelW/2}" y="${py(supExact)-5}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">LÍNEA ${supExact} (demasiado exacto)</text>`;
        }
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.03),py(Math.min(prev,p)-(mx-mn)*0.025),bull,12);
        });
        out+=`<text x="${x0+panelW/2}" y="16" fill="${useZone?C.accent:C.red}" font-size="10" font-family="monospace" text-anchor="middle">${useZone?'✓ ZONA (correcto)':'✗ LÍNEA (incorrecto)'}</text>`;
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        ${drawPanel(5, false)}
        ${drawPanel(panelW+30, true)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El precio respeta ZONAS, no números exactos
        </text>
    </svg>`;
}

function zone_types() {
    const W=680, H=230;
    const x0=40, y0=10, w=W-80, h=185;
    const mn=80, mx=200, range=mx-mn;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    const zones=[
        {top:168,bot:160,label:'ZONA DE OFERTA',color:C.red,desc:'Caída rápida desde aquí'},
        {top:150,bot:142,label:'ZONA DE CONSOLIDACIÓN (RES)',color:C.orange,desc:'Rango largo anterior'},
        {top:120,bot:112,label:'ZONA DE CONSOLIDACIÓN (SUP)',color:C.cyan,desc:'Rango largo anterior'},
        {top:102,bot:94,label:'ZONA DE DEMANDA',color:C.accent,desc:'Subida rápida desde aquí'},
    ];

    let zoneRects='', psych='';
    zones.forEach(({top,bot,label,color,desc})=>{
        const yt=py(top), yb=py(bot);
        zoneRects+=`<rect x="${x0}" y="${yt}" width="${w}" height="${yb-yt}" fill="${color}" opacity="0.1" rx="2"/>
        <line x1="${x0}" y1="${yt}" x2="${x0+w}" y2="${yt}" stroke="${color}" stroke-width="1" opacity="0.5"/>
        <line x1="${x0}" y1="${yb}" x2="${x0+w}" y2="${yb}" stroke="${color}" stroke-width="1" opacity="0.5"/>
        <text x="${x0+6}" y="${((yt+yb)/2-2).toFixed(1)}" fill="${color}" font-size="10" font-family="monospace">${label}</text>
        <text x="${x0+6}" y="${((yt+yb)/2+11).toFixed(1)}" fill="${color}" font-size="8" font-family="monospace" opacity="0.7">${desc}</text>`;
    });

    // Psychological levels
    [100,150,200].forEach(v=>{
        if(v>=mn&&v<=mx) {
            const ly=py(v);
            psych+=`<line x1="${x0+w-50}" y1="${ly}" x2="${x0+w}" y2="${ly}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>
            <text x="${x0+w+4}" y="${ly+4}" fill="${C.yellow}" font-size="9" font-family="monospace">${v}$</text>`;
        }
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${zoneRects}${psych}
        <text x="${x0+w-30}" y="${y0+10}" fill="${C.yellow}" font-size="8" font-family="monospace">Psico.</text>
        <text x="${W/2}" y="${H-0}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cuatro tipos de zona — más niveles psicológicos redondos
        </text>
    </svg>`;
}

function zone_marking_process() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,110,106,114,108,118,112,122,116,126,120,130,124,134,128,138];
    const mn=92, mx=146, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // Monthly level (thick, bright)
    const monthlyY=py(106);
    // Weekly levels
    const weekly1Y=py(116), weekly2Y=py(128);
    // Daily level
    const dailyY=py(122);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${monthlyY-5}" width="${w}" height="10" fill="${C.red}" opacity="0.07"/>
        <line x1="${x0}" y1="${monthlyY}" x2="${x0+w}" y2="${monthlyY}" stroke="${C.red}" stroke-width="2.5" stroke-dasharray="10,4"/>
        <line x1="${x0}" y1="${weekly1Y}" x2="${x0+w}" y2="${weekly1Y}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${weekly2Y}" x2="${x0+w}" y2="${weekly2Y}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${dailyY}" x2="${x0+w}" y2="${dailyY}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.7"/>
        ${candles}
        <rect x="${x0+w-130}" y="${y0+5}" width="120" height="54" fill="${C.bg}" opacity="0.9" rx="3"/>
        <line x1="${x0+w-124}" y1="${y0+15}" x2="${x0+w-112}" y2="${y0+15}" stroke="${C.red}" stroke-width="2.5" stroke-dasharray="6,3"/>
        <text x="${x0+w-108}" y="${y0+19}" fill="${C.red}" font-size="9" font-family="monospace">Mensual</text>
        <line x1="${x0+w-124}" y1="${y0+30}" x2="${x0+w-112}" y2="${y0+30}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="${x0+w-108}" y="${y0+34}" fill="${C.orange}" font-size="9" font-family="monospace">Semanal</text>
        <line x1="${x0+w-124}" y1="${y0+45}" x2="${x0+w-112}" y2="${y0+45}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="4,4"/>
        <text x="${x0+w-108}" y="${y0+49}" fill="${C.yellow}" font-size="9" font-family="monospace">Diario</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            MARCADO TOP-DOWN — Mensual (mayor peso) → Semanal → Diario
        </text>
    </svg>`;
}

function zone_update() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=165;
    const prices=[100,108,116,124,132,140,136,130,122,116,122,128,134,142,150,158];
    const mn=92, mx=166, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const oldRes=py(140), newSup=py(140), newRes=py(158);
    const breakX=px(6);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${oldRes}" x2="${breakX}" y2="${oldRes}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.5"/>
        <line x1="${breakX}" y1="${newSup}" x2="${x0+w}" y2="${newSup}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${newRes}" x2="${x0+w}" y2="${newRes}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        ${candles}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
        <text x="${(breakX-4).toFixed(1)}" y="${y0+12}" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="end">RUPTURA</text>
        <text x="${x0+w+4}" y="${newSup+4}" fill="${C.accent}" font-size="9" font-family="monospace">SUP nuevo</text>
        <text x="${x0+w+4}" y="${newRes+4}" fill="${C.red}" font-size="9" font-family="monospace">RES nueva</text>
        <text x="${x0+4}" y="${oldRes-4}" fill="${C.red}" font-size="8" font-family="monospace" opacity="0.5">Res. antigua →</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Actualización semanal: elimina lo roto, añade los nuevos niveles
        </text>
    </svg>`;
}

function multiple_touches_strength() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,124,116,112,118,126,134,128,120,114,120,128,136,130,122,116,122,130,138,146];
    const supLevel=114, mn=106, mx=154, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const supY=py(supLevel);
    const touches=[[3,112],[9,114],[15,116]];
    let tMarks='';
    touches.forEach(([i,v],ti)=>{
        tMarks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="${6+ti*2}" fill="none" stroke="${C.accent}" stroke-width="1.5" opacity="${0.5+ti*0.25}"/>
        <text x="${px(i).toFixed(1)}" y="${(py(v)+20+ti*2).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">T${ti+1}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-5}" width="${w}" height="10" fill="${C.accent}" opacity="0.07"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="8,4"/>
        ${candles}${tMarks}
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SUP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cada toque (T1, T2, T3) refuerza el nivel y atrae más participantes
        </text>
    </svg>`;
}

function multiple_touches_paradox() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Many touches then break
    const prices=[130,122,116,120,128,122,116,120,128,122,116,120,128,122,116,120,118,114,110,106];
    const supLevel=116, mn=98, mx=136, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const supY=py(supLevel);
    const touchIs=[2,6,10,14];
    let tMarks='';
    touchIs.forEach((i,ti)=>{
        const strength=Math.max(0.3, 1-ti*0.2);
        tMarks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(supLevel).toFixed(1)}" r="5" fill="none" stroke="${C.accent}" stroke-width="1.5" opacity="${strength}"/>
        <text x="${px(i).toFixed(1)}" y="${(py(supLevel)+16).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle" opacity="${strength}">T${ti+1}</text>`;
    });

    const breakX=px(16);
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}${tMarks}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>
        <text x="${(breakX+4).toFixed(1)}" y="${y0+14}" fill="${C.red}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ⚠ Muchos toques = compradores agotados → mayor riesgo de ruptura
        </text>
    </svg>`;
}

function multiple_touches_volume() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const prices=[130,122,116,122,130,122,116,122,128,122,116,120,126,120,116,118];
    const mn=108, mx=138, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const volY0=y0+h+10, volH=50;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // Volumes: high first touch, decreasing
    const vols=[0.4,0.6,1.0,0.8,0.5,0.7,0.8,0.6,0.4,0.5,0.6,0.4,0.3,0.4,0.5,0.3];
    let volBars='';
    vols.forEach((v,i)=>{
        const bh=v*volH;
        const bull=i>0&&prices[i]>prices[i-1];
        volBars+=`<rect x="${(px(i)-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="0.5" rx="1"/>`;
    });

    // Highlight touch volumes (indices 2, 6, 10, 14)
    [2,6,10,14].forEach((i,ti)=>{
        const v=vols[i], bh=v*volH;
        const decaying=ti>0&&v<vols[[2,6,10,14][ti-1]];
        volBars+=`<rect x="${(px(i)-7).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="14" height="${bh.toFixed(1)}" fill="${decaying?C.orange:C.accent}" stroke="${decaying?C.orange:C.accent}" stroke-width="1" opacity="0.9" rx="1"/>
        <text x="${px(i).toFixed(1)}" y="${(volY0+volH+10).toFixed(1)}" fill="${decaying?C.orange:C.accent}" font-size="8" font-family="monospace" text-anchor="middle">T${ti+1}</text>`;
    });

    const supY=py(116);
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${x0}" y="${volY0-3}" fill="${C.textDim}" font-size="8" font-family="monospace">VOLUMEN</text>
        <text x="${W/2}" y="${H-2}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">
            Volumen decreciente en toques = compradores agotándose (naranja)
        </text>
    </svg>`;
}

function multiple_touches_break() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,122,116,120,128,122,116,120,128,122,116,120,126,
                  113,116,110,104,98]; // spike below then definitive break
    const supLevel=116, mn=90, mx=138, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const supY=py(supLevel);
    const stopHuntX=px(13), stopHuntY=py(113);
    const breakX=px(15);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <rect x="${(stopHuntX-16).toFixed(1)}" y="${(stopHuntY-10).toFixed(1)}" width="32" height="20" fill="${C.orange}" opacity="0.1" stroke="${C.orange}" stroke-width="1" stroke-dasharray="3,2" rx="3"/>
        <text x="${stopHuntX.toFixed(1)}" y="${(stopHuntY+20).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">STOP HUNT</text>
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.8"/>
        <text x="${(breakX+4).toFixed(1)}" y="${y0+14}" fill="${C.red}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SUP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Stop Hunt (spike) → Recuperación breve → Ruptura definitiva
        </text>
    </svg>`;
}

// ─── MÓDULO 5: OFERTA Y DEMANDA ──────────────────────────────────────────────

function supply_demand_basics() {
    const W=680, H=200;
    // Simple supply/demand diagram
    const x0=60, y0=20, w=W-120, h=150;

    const demandY = y0+h*0.72, supplyY = y0+h*0.28;
    const priceX = x0+w*0.5;

    // Demand curve (downward sloping)
    const dPath=`M ${x0} ${y0+h*0.1} Q ${x0+w*0.4} ${y0+h*0.5} ${x0+w} ${y0+h}`;
    // Supply curve (upward sloping)
    const sPath=`M ${x0} ${y0+h} Q ${x0+w*0.4} ${y0+h*0.6} ${x0+w} ${y0+h*0.1}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <path d="${dPath}" fill="none" stroke="${C.accent}" stroke-width="2.5"/>
        <path d="${sPath}" fill="none" stroke="${C.red}" stroke-width="2.5"/>
        <line x1="${priceX}" y1="${y0}" x2="${priceX}" y2="${y0+h}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <circle cx="${priceX}" cy="${y0+h*0.5}" r="6" fill="${C.yellow}"/>
        <text x="${x0-4}" y="${y0+12}" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="end">PRECIO</text>
        <text x="${x0+w+4}" y="${y0+12}" fill="${C.accent}" font-size="11" font-family="monospace">DEMANDA</text>
        <text x="${x0+w+4}" y="${y0+h}" fill="${C.red}" font-size="11" font-family="monospace">OFERTA</text>
        <text x="${priceX}" y="${y0+h*0.5-14}" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="middle">EQUILIBRIO</text>
        <text x="${x0}" y="${y0+h*0.25}" fill="${C.red}" font-size="9" font-family="monospace">Más vendedores →</text>
        <text x="${x0}" y="${y0+h*0.82}" fill="${C.accent}" font-size="9" font-family="monospace">Más compradores →</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El precio busca el equilibrio entre oferta y demanda constantemente
        </text>
    </svg>`;
}

function demand_zone_identification() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Drop-Base-Rally pattern
    const prices=[130,124,118,112,108,106,108,107,106,108,107,
                  116,128,140,152,164];
    const mn=98, mx=172, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // Demand zone box
    const zTop=py(110), zBot=py(104);
    const zX1=px(4), zX2=px(11);
    // Impulse arrow
    const impX=px(13), impY1=py(108), impY2=py(152);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <rect x="${zX1.toFixed(1)}" y="${zTop.toFixed(1)}" width="${(zX2-zX1).toFixed(1)}" height="${(zBot-zTop).toFixed(1)}" fill="${C.accent}" opacity="0.15" stroke="${C.accent}" stroke-width="1.5" rx="2"/>
        <text x="${((zX1+zX2)/2).toFixed(1)}" y="${((zTop+zBot)/2+4).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ZONA DEMANDA</text>
        <line x1="${impX}" y1="${impY1.toFixed(1)}" x2="${impX}" y2="${(impY2+8).toFixed(1)}" stroke="${C.accent}" stroke-width="2" stroke-dasharray="5,3" opacity="0.5"/>
        <text x="${(impX+6).toFixed(1)}" y="${((impY1+impY2)/2).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">IMPULSO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ZONA DE DEMANDA = Base antes del impulso alcista explosivo
        </text>
    </svg>`;
}

function demand_zone_types() {
    const W=680, H=220;
    const panelW=(W-60)/3;

    function panel(x0, prices, label, color) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>25+155-((v-mn)/range)*155;
        let out=`<text x="${x0+panelW/2}" y="16" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,11);
        });
        // Zone box around the base
        const baseI=prices.reduce((acc,p,i)=>Math.abs(p-Math.min(...prices))<5?i:acc,0);
        const zY1=py(Math.min(...prices)+8), zY2=py(Math.min(...prices)-2);
        const zX1=px(Math.max(0,baseI-2)), zX2=px(Math.min(prices.length-1,baseI+3));
        out+=`<rect x="${zX1.toFixed(1)}" y="${zY1.toFixed(1)}" width="${(zX2-zX1).toFixed(1)}" height="${(zY2-zY1).toFixed(1)}" fill="${color}" opacity="0.12" stroke="${color}" stroke-width="1" rx="2"/>`;
        return out;
    }

    const rbr=[100,106,112,108,106,107,108,107,116,124,132];
    const dbr=[120,112,104,100,98,100,99,100,112,126,140];
    const direct=[100,102,104,103,104,116,128,140];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(10, rbr, 'RBR — Rally·Base·Rally', C.cyan)}
        ${panel(10+panelW+10, dbr, 'DBR — Drop·Base·Rally ★', C.accent)}
        ${panel(10+panelW*2+20, direct, 'Rally·Base directo', C.yellow)}
        <line x1="${10+panelW+5}" y1="5" x2="${10+panelW+5}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <line x1="${10+panelW*2+15}" y1="5" x2="${10+panelW*2+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            DBR es el patrón más poderoso — caída → acumulación → explosión
        </text>
    </svg>`;
}

function demand_zone_entry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // First rally from demand, then retest
    const prices=[100,106,112,108,106,107,114,124,134,128,122,116,112,108,110,118,128,138,148];
    const mn=100, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const zTop=py(114), zBot=py(104);
    const zX1=px(2), zX2=px(6);
    const retestX=px(13), retestY=py(108);
    const stopY=py(102), targetY=py(134);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${zTop.toFixed(1)}" width="${w}" height="${(zBot-zTop).toFixed(1)}" fill="${C.accent}" opacity="0.08"/>
        <line x1="${x0}" y1="${zTop.toFixed(1)}" x2="${x0+w}" y2="${zTop.toFixed(1)}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="6,4" opacity="0.6"/>
        <line x1="${x0}" y1="${zBot.toFixed(1)}" x2="${x0+w}" y2="${zBot.toFixed(1)}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="6,4" opacity="0.6"/>
        <line x1="${x0}" y1="${stopY.toFixed(1)}" x2="${x0+w}" y2="${stopY.toFixed(1)}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${targetY.toFixed(1)}" x2="${x0+w}" y2="${targetY.toFixed(1)}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        ${candles}
        <line x1="${retestX}" y1="${(retestY+16).toFixed(1)}" x2="${retestX}" y2="${(retestY+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUp6)"/>
        <defs><marker id="aUp6" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${retestX.toFixed(1)}" y="${(retestY+30).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">TARGET</text>
        <text x="${x0+w+4}" y="${zTop+4}" fill="${C.accent}" font-size="9" font-family="monospace">ZONA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retest de zona de demanda fresca = entrada de alta probabilidad
        </text>
    </svg>`;
}

function supply_zone_identification() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Rally-Base-Drop
    const prices=[100,108,116,124,130,134,132,134,133,132,134,133,
                  122,108,94,80];
    const mn=72, mx=142, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const zBot=py(130), zTop=py(136);
    const zX1=px(4), zX2=px(11);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <rect x="${zX1.toFixed(1)}" y="${zTop.toFixed(1)}" width="${(zX2-zX1).toFixed(1)}" height="${(zBot-zTop).toFixed(1)}" fill="${C.red}" opacity="0.15" stroke="${C.red}" stroke-width="1.5" rx="2"/>
        <text x="${((zX1+zX2)/2).toFixed(1)}" y="${((zTop+zBot)/2+4).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">ZONA OFERTA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ZONA DE OFERTA = Base antes de la caída explosiva (RBD)
        </text>
    </svg>`;
}

function supply_zone_types() {
    const W=680, H=220;
    const panelW=(W-60)/3;

    function panel(x0, prices, label, color) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>25+155-((v-mn)/range)*155;
        let out=`<text x="${x0+panelW/2}" y="16" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,11);
        });
        const baseI=prices.reduce((acc,p,i)=>Math.abs(p-Math.max(...prices))<5?i:acc,0);
        const zY2=py(Math.max(...prices)+2), zY1=py(Math.max(...prices)-8);
        const zX1=px(Math.max(0,baseI-2)), zX2=px(Math.min(prices.length-1,baseI+3));
        out+=`<rect x="${zX1.toFixed(1)}" y="${zY2.toFixed(1)}" width="${(zX2-zX1).toFixed(1)}" height="${(zY1-zY2).toFixed(1)}" fill="${color}" opacity="0.12" stroke="${color}" stroke-width="1" rx="2"/>`;
        return out;
    }

    const dbd=[120,112,104,108,106,107,108,107,100,90,80];
    const rbd=[80,90,102,112,118,120,118,120,119,110,96,82];
    const direct=[80,86,92,98,104,108,106,108,98,86,74];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(10, dbd, 'DBD — Drop·Base·Drop', C.orange)}
        ${panel(10+panelW+10, rbd, 'RBD — Rally·Base·Drop ★', C.red)}
        ${panel(10+panelW*2+20, direct, 'Drop·Base directo', C.muted)}
        <line x1="${10+panelW+5}" y1="5" x2="${10+panelW+5}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <line x1="${10+panelW*2+15}" y1="5" x2="${10+panelW*2+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            RBD es el más potente — subida → distribución → colapso
        </text>
    </svg>`;
}

function supply_zone_entry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,112,104,108,106,107,116,124,132,140,136,132,134,133,132,124,114,102,90];
    const mn=82, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const zTop=py(136), zBot=py(130);
    const retestX=px(12), retestY=py(134);
    const stopY=py(140), targetY=py(106);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${zTop.toFixed(1)}" width="${w}" height="${(zBot-zTop).toFixed(1)}" fill="${C.red}" opacity="0.08"/>
        <line x1="${x0}" y1="${zTop.toFixed(1)}" x2="${x0+w}" y2="${zTop.toFixed(1)}" stroke="${C.red}" stroke-width="1" stroke-dasharray="6,4" opacity="0.6"/>
        <line x1="${x0}" y1="${zBot.toFixed(1)}" x2="${x0+w}" y2="${zBot.toFixed(1)}" stroke="${C.red}" stroke-width="1" stroke-dasharray="6,4" opacity="0.6"/>
        <line x1="${x0}" y1="${stopY.toFixed(1)}" x2="${x0+w}" y2="${stopY.toFixed(1)}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        <line x1="${x0}" y1="${targetY.toFixed(1)}" x2="${x0+w}" y2="${targetY.toFixed(1)}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        ${candles}
        <line x1="${retestX}" y1="${(retestY-5).toFixed(1)}" x2="${retestX}" y2="${(retestY-18).toFixed(1)}" stroke="${C.red}" stroke-width="2.5" marker-end="url(#aDn6)"/>
        <defs><marker id="aDn6" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 0 L 3 6 L 6 0 z" fill="${C.red}"/></marker></defs>
        <text x="${retestX.toFixed(1)}" y="${(retestY-24).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">CORTO</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">TARGET</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retest de zona de oferta = entrada corta de alta probabilidad
        </text>
    </svg>`;
}

function supply_becomes_demand() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,116,124,132,140,138,140,139,
                  128,116,104,116,128,132,138,140,142,148,156,164];
    const mn=96, mx=172, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const supplyZoneY1=py(142), supplyZoneY2=py(136);
    const breakX=px(14);
    const retestX=px(13), retestY=py(132);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supplyZoneY1.toFixed(1)}" width="${(breakX-x0).toFixed(1)}" height="${(supplyZoneY2-supplyZoneY1).toFixed(1)}" fill="${C.red}" opacity="0.08"/>
        <rect x="${breakX.toFixed(1)}" y="${supplyZoneY1.toFixed(1)}" width="${(x0+w-breakX).toFixed(1)}" height="${(supplyZoneY2-supplyZoneY1).toFixed(1)}" fill="${C.accent}" opacity="0.08"/>
        <line x1="${x0}" y1="${supplyZoneY1.toFixed(1)}" x2="${x0+w}" y2="${supplyZoneY1.toFixed(1)}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${supplyZoneY2.toFixed(1)}" x2="${x0+w}" y2="${supplyZoneY2.toFixed(1)}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
        <text x="${((x0+breakX)/2).toFixed(1)}" y="${(supplyZoneY1+14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">OFERTA</text>
        <text x="${((breakX+x0+w)/2).toFixed(1)}" y="${(supplyZoneY1+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">→ DEMANDA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Zona de oferta rota → se convierte en zona de demanda en el retest
        </text>
    </svg>`;
}

function rejection_area_definition() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;

    // Draw a pin bar rejection clearly
    const cx1=x0+w*0.35, cx2=x0+w*0.65;
    const resY=y0+h*0.25;

    // Left: rejection at resistance (bearish pin)
    const bearPin=`<line x1="${cx1}" y1="${resY-5}" x2="${cx1}" y2="${y0+h*0.75}" stroke="${C.red}" stroke-width="2"/>
    <rect x="${cx1-12}" y="${y0+h*0.55}" width="24" height="${h*0.2}" fill="${C.red}" stroke="${C.red}" stroke-width="1.5" rx="2"/>
    <text x="${cx1}" y="${resY-12}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">RECHAZO BAJISTA</text>
    <text x="${cx1}" y="${y0+h*0.88}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Mecha larga arriba</text>`;

    // Right: rejection at support (bullish pin)
    const supY=y0+h*0.75;
    const bullPin=`<line x1="${cx2}" y1="${y0+h*0.25}" x2="${cx2}" y2="${supY+5}" stroke="${C.accent}" stroke-width="2"/>
    <rect x="${cx2-12}" y="${y0+h*0.25}" width="24" height="${h*0.2}" fill="${C.accent}" stroke="${C.accent}" stroke-width="1.5" rx="2"/>
    <text x="${cx2}" y="${supY+20}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">RECHAZO ALCISTA</text>
    <text x="${cx2}" y="${supY+32}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Mecha larga abajo</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.5"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.5"/>
        ${bearPin}${bullPin}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Rechazo = el precio intenta un nivel y es empujado de vuelta con fuerza
        </text>
    </svg>`;
}

function rejection_types() {
    const W=680, H=230;
    const types=[
        {label:'PIN BAR\nEXTREMO',cx:80,yH:30,yO:150,yC:160,yL:180,bull:true,color:C.accent},
        {label:'ENGULFING\nALCISTA',cx:220,bull:true,color:C.accent,special:'engulf'},
        {label:'DOJI EN\nNIVEL',cx:370,yH:40,yO:105,yC:108,yL:180,bull:true,color:C.yellow},
        {label:'MECHA\nLARGA',cx:510,yH:40,yO:100,yC:130,yL:180,bull:true,color:C.cyan},
    ];

    let content='';
    types.forEach(({label,cx,yH,yO,yC,yL,bull,color,special})=>{
        const lines=label.split('\n');
        if(special==='engulf') {
            // Previous bearish + engulfing bullish
            content+=`<line x1="${cx-18}" y1="50" x2="${cx-18}" y2="160" stroke="${C.red}" stroke-width="1.5"/>
            <rect x="${cx-28}" y="70" width="20" height="80" fill="${C.red}" stroke="${C.red}" stroke-width="1.5" rx="1"/>
            <line x1="${cx+8}" y1="40" x2="${cx+8}" y2="170" stroke="${C.accent}" stroke-width="1.5"/>
            <rect x="${cx-4}" y="55" width="24" height="100" fill="${C.accent}" stroke="${C.accent}" stroke-width="1.5" rx="1"/>`;
        } else {
            content+=`<line x1="${cx}" y1="${yH}" x2="${cx}" y2="${yL}" stroke="${color}" stroke-width="2"/>
            <rect x="${cx-12}" y="${Math.min(yO,yC)}" width="24" height="${Math.max(Math.abs(yO-yC),4)}" fill="${bull?color:'none'}" stroke="${color}" stroke-width="2" rx="2"/>`;
        }
        lines.forEach((l,li)=>{
            content+=`<text x="${cx}" y="${195+li*12}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`;
        });
        content+=`<line x1="${cx-40}" y1="175" x2="${cx+40}" y2="175" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Pin bar extremo = rechazo más potente; siempre necesita contexto
        </text>
    </svg>`;
}

function rejection_realtime() {
    const W=680, H=220;
    // Show a candle forming progressively
    const x0=50, y0=20, h=160;
    const stages=[
        {pct:0.25, label:'15:00 — Precio sube\nhacia nivel', yH:60, yO:140, yC:100, yL:145},
        {pct:0.5,  label:'16:00 — Penetra zona,\nmecha crece', yH:40, yO:140, yC:90, yL:145},
        {pct:0.75, label:'17:00 — Empieza\na volver', yH:35, yO:140, yC:110, yL:145},
        {pct:1.0,  label:'18:00 — Cierre —\nPin bar confirmado', yH:35, yO:140, yC:150, yL:155},
    ];

    const panelW=140;
    let content='';
    stages.forEach(({pct,label,yH,yO,yC,yL},i) => {
        const cx=x0+i*(panelW+10)+panelW/2;
        const color=pct===1?C.red:C.muted;
        const lines=label.split('\n');
        content+=`<rect x="${cx-panelW/2}" y="${y0}" width="${panelW}" height="${h}" fill="${i===3?C.red:'transparent'}" opacity="0.03" rx="4"/>
        <line x1="${cx}" y1="${yH}" x2="${cx}" y2="${yL}" stroke="${color}" stroke-width="2"/>
        <rect x="${cx-14}" y="${Math.min(yO,yC)}" width="28" height="${Math.max(Math.abs(yO-yC),3)}" fill="${pct===1?C.red:'none'}" stroke="${color}" stroke-width="2" rx="2"/>
        <line x1="${cx-panelW/2+5}" y1="50" x2="${cx+panelW/2-5}" y2="50" stroke="${C.red}" stroke-width="1" stroke-dasharray="4,3" opacity="0.4"/>`;
        lines.forEach((l,li)=>{
            content+=`<text x="${cx}" y="${y0+h+14+li*12}" fill="${i===3?C.red:C.textDim}" font-size="8.5" font-family="monospace" text-anchor="middle">${l}</text>`;
        });
    });

    return `<svg viewBox="0 0 ${W} 240" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="240" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="234" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Espera el CIERRE de la vela para confirmar el rechazo
        </text>
    </svg>`;
}

function rejection_multi_tf() {
    const W=680, H=230;
    // Three panels: Monthly → Weekly → Daily all showing rejection at same level
    const panelW=(W-60)/3;

    function rejPanel(x0, label, timeframe, color) {
        const prices=[100,110,120,130,140,148,142,136,128];
        const mn=92, mx=155, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>25+160-((v-mn)/range)*160;
        let out=`<text x="${x0+panelW/2}" y="16" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${timeframe}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,Math.floor(panelW/prices.length)-2);
        });
        // Rejection candle at peak
        const rejCx=px(5), rejY=py(148);
        out+=`<circle cx="${rejCx}" cy="${rejY}" r="7" fill="none" stroke="${color}" stroke-width="2"/>
        <text x="${rejCx}" y="${py(153)}" fill="${color}" font-size="8" font-family="monospace" text-anchor="middle">REJ</text>`;
        const resY=py(148);
        out+=`<line x1="${x0}" y1="${resY}" x2="${x0+panelW}" y2="${resY}" stroke="${color}" stroke-width="1" stroke-dasharray="5,3" opacity="0.5"/>`;
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${rejPanel(10, 'Mensual', 'MENSUAL', C.red)}
        ${rejPanel(10+panelW+10, 'Semanal', 'SEMANAL', C.orange)}
        ${rejPanel(10+panelW*2+20, 'Diario', 'DIARIO', C.yellow)}
        <line x1="${10+panelW+5}" y1="5" x2="${10+panelW+5}" y2="${H-20}" stroke="${C.border}" stroke-width="1"/>
        <line x1="${10+panelW*2+15}" y1="5" x2="${10+panelW*2+15}" y2="${H-20}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Rechazo visible en 3 TF = señal de máxima potencia
        </text>
    </svg>`;
}

function base_formation_what() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=165;
    // Accumulation base then breakout
    const prices=[120,116,110,106,110,108,112,110,114,112,116,114,
                  118,116,118,116,118,128,140,152,164];
    const mn=98, mx=172, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,10);
    });

    const baseX1=px(2), baseX2=px(16);
    const baseTop=py(120), baseBot=py(104);
    const breakX=px(16);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${baseX1.toFixed(1)}" y="${baseTop.toFixed(1)}" width="${(baseX2-baseX1).toFixed(1)}" height="${(baseBot-baseTop).toFixed(1)}" fill="${C.cyan}" opacity="0.06" stroke="${C.cyan}" stroke-width="1" stroke-dasharray="4,3" rx="3"/>
        ${candles}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>
        <text x="${((baseX1+baseX2)/2).toFixed(1)}" y="${(baseTop+14).toFixed(1)}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">BASE (acumulación)</text>
        <text x="${(breakX+6).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La base parece "no hacer nada" — por dentro se acumula la energía
        </text>
    </svg>`;
}

function base_quality() {
    const W=680, H=230;
    const x0=40, y0=10, w=W-80, h=160;
    const volY0=y0+h+10, volH=40;
    // Base with contracting range and declining volume
    const prices=[120,116,112,115,118,114,116,113,115,112,114,
                  111,113,110,112,110,111,112,122,134];
    const mn=104, mx=140, range=mx-mn;
    const vols=[1.2,1.0,0.9,0.8,0.7,0.75,0.65,0.7,0.6,0.65,
                0.55,0.6,0.5,0.55,0.45,0.5,0.4,0.45,2.1,1.8];
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='',volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,10);
        const bh=vols[i]*volH;
        volBars+=`<rect x="${(cx-5).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="10" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="${i>=18?0.9:0.4}" rx="1"/>`;
    });

    // Contracting range lines
    const rangeLines=[
        {top:118,bot:112,i:2,color:C.muted,opacity:0.4},
        {top:116,bot:113,i:6,color:C.muted,opacity:0.5},
        {top:114,bot:111,i:10,color:C.yellow,opacity:0.6},
        {top:112,bot:110,i:14,color:C.accent,opacity:0.8},
    ];

    let rLines='';
    rangeLines.forEach(({top,bot,i,color,opacity})=>{
        const cx=px(i);
        rLines+=`<line x1="${(cx-8).toFixed(1)}" y1="${py(top).toFixed(1)}" x2="${(cx+24).toFixed(1)}" y2="${py(top).toFixed(1)}" stroke="${color}" stroke-width="1" opacity="${opacity}"/>
        <line x1="${(cx-8).toFixed(1)}" y1="${py(bot).toFixed(1)}" x2="${(cx+24).toFixed(1)}" y2="${py(bot).toFixed(1)}" stroke="${color}" stroke-width="1" opacity="${opacity}"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H+20}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+20}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}${rLines}
        <text x="${x0+4}" y="${y0+12}" fill="${C.textDim}" font-size="9" font-family="monospace">Rango contrayendo →</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${x0}" y="${volY0-3}" fill="${C.textDim}" font-size="8" font-family="monospace">VOL ↓ en base</text>
        <text x="${W/2}" y="${H+17}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Base de calidad: rango contrae + volumen decrece + soporte respetado
        </text>
    </svg>`;
}

function base_types() {
    const W=680, H=220;
    const panelW=(W-60)/4;

    function simplePanel(x0, prices, label, color) {
        const mn=Math.min(...prices)-3, mx=Math.max(...prices)+3, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>25+160-((v-mn)/range)*160;
        let out=`<text x="${x0+panelW/2}" y="16" fill="${color}" font-size="8.5" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.04),py(Math.min(prev,p)-range*0.03),bull,9);
        });
        return out;
    }

    // Flat base
    const flat=[100,102,98,101,99,102,100,98,101,99,102,114,126];
    // Cup & Handle
    const cup=[120,114,108,102,96,98,102,108,114,120,118,120,119,120,128,140];
    // VCP (volatility contraction)
    const vcp=[120,110,114,108,112,107,110,106,109,105,108,118,130];
    // Triangle
    const tri=[100,110,106,112,108,113,110,113,111,113,112,122,132];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${simplePanel(5, flat, 'FLAT BASE', C.accent)}
        ${simplePanel(5+panelW+5, cup, 'CUP & HANDLE', C.cyan)}
        ${simplePanel(5+panelW*2+10, vcp, 'VCP', C.yellow)}
        ${simplePanel(5+panelW*3+15, tri, 'TRIÁNGULO', C.orange)}
        ${[1,2,3].map(i=>`<line x1="${5+panelW*i+i*5-3}" y1="5" x2="${5+panelW*i+i*5-3}" y2="${H-15}" stroke="${C.border}" stroke-width="1"/>`).join('')}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cuatro bases clásicas — todas producen rupturas similares
        </text>
    </svg>`;
}

function base_breakout() {
    const W=680, H=230;
    const x0=40, y0=10, w=W-80, h=165;
    const volY0=y0+h+10, volH=40;
    // Base + high volume breakout
    const prices=[120,116,112,114,112,115,113,116,114,117,115,118,
                  116,118,116,118,130,144,158];
    const mn=104, mx=166, range=mx-mn;
    const vols=[0.6,0.5,0.7,0.6,0.55,0.65,0.6,0.7,0.55,0.65,0.6,0.7,
                0.55,0.65,0.6,0.65,2.8,2.2,1.6];
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='',volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,10);
        const bh=vols[i]*volH;
        volBars+=`<rect x="${(cx-5).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="10" height="${bh.toFixed(1)}" fill="${i>=16?C.accent:C.muted}" opacity="${i>=16?0.9:0.35}" rx="1"/>`;
    });

    const breakLevel=118, breakY=py(breakLevel), breakX=px(15);
    const stopY=py(114);

    return `<svg viewBox="0 0 ${W} ${H+20}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+20}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${breakY}" x2="${x0+w}" y2="${breakY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        ${candles}
        <circle cx="${px(16).toFixed(1)}" cy="${py(130).toFixed(1)}" r="8" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(16).toFixed(1)}" y="${(py(136)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${x0+w+4}" y="${breakY+4}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${W/2}" y="${H+17}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura con volumen 3x superior = confirmación institucional
        </text>
    </svg>`;
}

// ─── MÓDULO 6: COMPORTAMIENTO DE VELAS ───────────────────────────────────────

function bullish_engulfing_anatomy() {
    const W=680, H=230;
    const cx1=180, cx2=340;

    // Bearish candle
    const b1={yH:60,yO:90,yC:160,yL:180};
    // Bullish engulfing (body engulfs previous body)
    const b2={yH:50,yO:170,yC:75,yL:185};

    let svg=`<rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>`;
    svg+=gridLines(50,20,W-100,180);

    // Vela 1 bajista
    svg+=`<line x1="${cx1}" y1="${b1.yH}" x2="${cx1}" y2="${b1.yL}" stroke="${C.red}" stroke-width="2"/>
    <rect x="${cx1-22}" y="${b1.yO}" width="44" height="${b1.yC-b1.yO}" fill="${C.red}" stroke="${C.red}" stroke-width="2" rx="2"/>
    <text x="${cx1}" y="${H-30}" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">DÍA 1</text>
    <text x="${cx1}" y="${H-16}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Bajista</text>`;

    // Vela 2 alcista (engulfing)
    svg+=`<line x1="${cx2}" y1="${b2.yH}" x2="${cx2}" y2="${b2.yL}" stroke="${C.accent}" stroke-width="2"/>
    <rect x="${cx2-22}" y="${b2.yC}" width="44" height="${b2.yO-b2.yC}" fill="${C.accent}" stroke="${C.accent}" stroke-width="2" rx="2"/>
    <text x="${cx2}" y="${H-30}" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">DÍA 2</text>
    <text x="${cx2}" y="${H-16}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Engulfing alcista</text>`;

    // Annotations
    svg+=`<line x1="${cx1+30}" y1="${b1.yO}" x2="${cx2-30}" y2="${b2.yO}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>
    <line x1="${cx1+30}" y1="${b1.yC}" x2="${cx2-30}" y2="${b2.yC}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>`;

    // Bracket showing engulfing
    const bX=cx2+36;
    svg+=`<line x1="${bX}" y1="${b2.yC}" x2="${bX+10}" y2="${b2.yC}" stroke="${C.accent}" stroke-width="1.5"/>
    <line x1="${bX+10}" y1="${b2.yC}" x2="${bX+10}" y2="${b1.yO+5}" stroke="${C.accent}" stroke-width="1.5"/>
    <line x1="${bX}" y1="${b1.yO}" x2="${bX+10}" y2="${b1.yO}" stroke="${C.accent}" stroke-width="1.5"/>
    <text x="${bX+14}" y="${(b2.yC+b1.yO)/2+4}" fill="${C.accent}" font-size="9" font-family="monospace">Envuelve</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${svg}
        <text x="${W/2}" y="${H-2}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El cuerpo alcista envuelve completamente el cuerpo bajista anterior
        </text>
    </svg>`;
}

function bullish_engulfing_context() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,124,116,110,106,108,106,108,118,130,122,116,112,108,110,108,122,136,150];
    const mn=98, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,14);
    });

    const supY=py(108);
    // Engulfing at support (index 7-8 and 13-14)
    const eng1X=px(8), eng2X=px(14);

    let ema=prices[0],emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k);emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-5}" width="${w}" height="10" fill="${C.accent}" opacity="0.07"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="1.8" opacity="0.8"/>
        <circle cx="${eng1X}" cy="${py(110)}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <circle cx="${eng2X}" cy="${py(110)}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${eng1X}" y="${(py(103)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENGULFING</text>
        <text x="${eng2X}" y="${(py(103)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENGULFING</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SOPORTE</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Engulfing en soporte + EMA = señal de alta probabilidad
        </text>
    </svg>`;
}

function bullish_engulfing_trade() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,122,114,108,112,108,120,134,148];
    const mn=100, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,28);
    });

    // Entry at close of engulfing (index 6)
    const engX=px(6), engHighY=py(120), engLowY=py(106);
    const stopY=py(104), target1Y=py(134), target2Y=py(148);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${target1Y}" x2="${x0+w}" y2="${target1Y}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${target2Y}" x2="${x0+w}" y2="${target2Y}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        ${candles}
        <circle cx="${engX}" cy="${py(113)}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <line x1="${engX}" y1="${(py(107)+16).toFixed(1)}" x2="${engX}" y2="${(py(107)+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUp7)"/>
        <defs><marker id="aUp7" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${engX}" y="${(py(107)+32).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${target1Y+4}" fill="${C.yellow}" font-size="9" font-family="monospace">T1</text>
        <text x="${x0+w+4}" y="${target2Y+4}" fill="${C.yellow}" font-size="9" font-family="monospace">T2</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Stop bajo el mínimo del engulfing — T1 en resistencia, T2 extendido
        </text>
    </svg>`;
}

function bullish_engulfing_volume() {
    const W=680, H=230;
    const x0=40, y0=10, w=W-80, h=150;
    const volY0=y0+h+10, volH=50;
    const prices=[130,124,118,112,108,120,134,148];
    const mn=100, mx=156, range=mx-mn;
    const vols=[0.8,0.7,0.9,0.6,0.7,2.6,1.4,1.1];
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='',volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,24);
        const bh=vols[i]*volH;
        const isEng=i===5;
        volBars+=`<rect x="${(cx-11).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="22" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="${isEng?0.95:0.4}" rx="1"/>
        ${isEng?`<text x="${cx}" y="${(volY0+volH+11).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">3x vol</text>`:''}`;
    });

    // Avg vol line
    const avgVol=0.75*volH;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <line x1="${x0}" y1="${(volY0+volH-avgVol).toFixed(1)}" x2="${x0+w}" y2="${(volY0+volH-avgVol).toFixed(1)}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
        <text x="${x0+4}" y="${(volY0+volH-avgVol-3).toFixed(1)}" fill="${C.muted}" font-size="8" font-family="monospace">Promedio</text>
        <text x="${W/2}" y="${H-2}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Engulfing con volumen 3x promedio = confirmación institucional
        </text>
    </svg>`;
}

function bearish_engulfing_anatomy() {
    const W=680, H=230;
    const cx1=180, cx2=340;
    const b1={yH:60,yO:160,yC:90,yL:180};
    const b2={yH:50,yO:75,yC:170,yL:185};

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(50,20,W-100,180)}
        <line x1="${cx1}" y1="${b1.yH}" x2="${cx1}" y2="${b1.yL}" stroke="${C.accent}" stroke-width="2"/>
        <rect x="${cx1-22}" y="${b1.yC}" width="44" height="${b1.yO-b1.yC}" fill="${C.accent}" stroke="${C.accent}" stroke-width="2" rx="2"/>
        <text x="${cx1}" y="${H-30}" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">DÍA 1</text>
        <text x="${cx1}" y="${H-16}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Alcista</text>
        <line x1="${cx2}" y1="${b2.yH}" x2="${cx2}" y2="${b2.yL}" stroke="${C.red}" stroke-width="2"/>
        <rect x="${cx2-22}" y="${b2.yO}" width="44" height="${b2.yC-b2.yO}" fill="${C.red}" stroke="${C.red}" stroke-width="2" rx="2"/>
        <text x="${cx2}" y="${H-30}" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">DÍA 2</text>
        <text x="${cx2}" y="${H-16}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Engulfing bajista</text>
        <line x1="${cx1+30}" y1="${b1.yO}" x2="${cx2-30}" y2="${b2.yO}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>
        <line x1="${cx1+30}" y1="${b1.yC}" x2="${cx2-30}" y2="${b2.yC}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>
        <line x1="${cx2+36}" y1="${b2.yO}" x2="${cx2+46}" y2="${b2.yO}" stroke="${C.red}" stroke-width="1.5"/>
        <line x1="${cx2+46}" y1="${b2.yO}" x2="${cx2+46}" y2="${b1.yC-5}" stroke="${C.red}" stroke-width="1.5"/>
        <line x1="${cx2+36}" y1="${b1.yC}" x2="${cx2+46}" y2="${b1.yC}" stroke="${C.red}" stroke-width="1.5"/>
        <text x="${cx2+50}" y="${(b2.yO+b1.yC)/2+4}" fill="${C.red}" font-size="9" font-family="monospace">Envuelve</text>
        <text x="${W/2}" y="${H-2}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El cuerpo bajista envuelve completamente el cuerpo alcista anterior
        </text>
    </svg>`;
}

function bearish_engulfing_context() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,116,124,132,140,148,142,136,140,148,152,144,136,128,120,112];
    const mn=92, mx=160, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,14);
    });

    const resY=py(152);
    const engX=px(11);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY-5}" width="${w}" height="10" fill="${C.red}" opacity="0.07"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <circle cx="${engX}" cy="${py(148)}" r="10" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${engX}" y="${(py(142)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">ENGULFING</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Engulfing bajista en resistencia = señal de techo potente
        </text>
    </svg>`;
}

function bearish_engulfing_trade() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,118,128,136,144,150,140,128,116,104];
    const mn=96, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,20);
    });

    const engX=px(6), stopY=py(154), target1Y=py(130), target2Y=py(112);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${target1Y}" x2="${x0+w}" y2="${target1Y}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${target2Y}" x2="${x0+w}" y2="${target2Y}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        ${candles}
        <line x1="${engX}" y1="${(py(144)-5).toFixed(1)}" x2="${engX}" y2="${(py(144)-18).toFixed(1)}" stroke="${C.red}" stroke-width="2.5" marker-end="url(#aDn7)"/>
        <defs><marker id="aDn7" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 0 L 3 6 L 6 0 z" fill="${C.red}"/></marker></defs>
        <text x="${engX}" y="${(py(144)-24).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">CORTO</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${target1Y+4}" fill="${C.yellow}" font-size="9" font-family="monospace">T1</text>
        <text x="${x0+w+4}" y="${target2Y+4}" fill="${C.yellow}" font-size="9" font-family="monospace">T2</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Corto al cierre del engulfing — Stop sobre el máximo
        </text>
    </svg>`;
}

function bearish_engulfing_vs_simple() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    function panel(x0, label, color, isEngulfing) {
        const mn=90, mx=160, range=mx-mn;
        const px=(i)=>x0+(i/8)*panelW;
        const py=(v)=>20+170-((v-mn)/range)*170;
        const prices=isEngulfing
            ? [100,106,112,118,124,130,120,100]
            : [100,106,112,118,124,130,126,114];
        let out=`<text x="${x0+panelW/2}" y="16" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,16);
        });
        if(isEngulfing) {
            out+=`<circle cx="${px(7)}" cy="${py(115)}" r="9" fill="none" stroke="${C.red}" stroke-width="2"/>
            <text x="${px(7)}" y="${py(105)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">ENGULFING</text>`;
        }
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.04" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.muted}" opacity="0.03" rx="5"/>
        ${panel(5, 'ENGULFING BAJISTA ✓', C.red, true)}
        ${panel(panelW+30, 'VELA BAJISTA GRANDE (sin engulfing)', C.muted, false)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Solo el engulfing atrapa a los compradores del día anterior
        </text>
    </svg>`;
}

function pin_bar_anatomy() {
    const W=680, H=230;
    // Bullish pin bar
    const cx1=160, cx2=380;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(50,15,W-100,190)}
        <!-- Bullish pin bar -->
        <line x1="${cx1}" y1="30" x2="${cx1}" y2="190" stroke="${C.accent}" stroke-width="2.5"/>
        <rect x="${cx1-18}" y="155" width="36" height="28" fill="${C.accent}" stroke="${C.accent}" stroke-width="2" rx="2"/>
        <text x="${cx1}" y="${H-32}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">PIN BAR ALCISTA</text>
        <text x="${cx1}" y="${H-18}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">(Mecha abajo = rechazo de bajos)</text>
        <!-- Annotations bullish -->
        <line x1="${cx1-28}" y1="30" x2="${cx1-8}" y2="30" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx1-32}" y="34" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="end">Máximo</text>
        <line x1="${cx1-28}" y1="155" x2="${cx1-8}" y2="155" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx1-32}" y="159" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="end">Apertura</text>
        <line x1="${cx1-28}" y1="183" x2="${cx1-8}" y2="183" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx1-32}" y="187" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="end">Cierre</text>
        <line x1="${cx1-28}" y1="190" x2="${cx1-8}" y2="190" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx1-32}" y="194" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="end">Mínimo</text>
        <!-- Bearish pin bar -->
        <line x1="${cx2}" y1="25" x2="${cx2}" y2="185" stroke="${C.red}" stroke-width="2.5"/>
        <rect x="${cx2-18}" y="28" width="36" height="28" fill="${C.red}" stroke="${C.red}" stroke-width="2" rx="2"/>
        <text x="${cx2}" y="${H-32}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">PIN BAR BAJISTA</text>
        <text x="${cx2}" y="${H-18}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">(Mecha arriba = rechazo de altos)</text>
        <line x1="${cx2+28}" y1="25" x2="${cx2+8}" y2="25" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx2+32}" y="29" fill="${C.textDim}" font-size="8" font-family="monospace">Máximo</text>
        <line x1="${cx2+28}" y1="28" x2="${cx2+8}" y2="28" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx2+32}" y="32" fill="${C.textDim}" font-size="8" font-family="monospace">Apertura</text>
        <line x1="${cx2+28}" y1="56" x2="${cx2+8}" y2="56" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx2+32}" y="60" fill="${C.textDim}" font-size="8" font-family="monospace">Cierre</text>
        <line x1="${cx2+28}" y1="185" x2="${cx2+8}" y2="185" stroke="${C.muted}" stroke-width="1"/>
        <text x="${cx2+32}" y="189" fill="${C.textDim}" font-size="8" font-family="monospace">Mínimo</text>
    </svg>`;
}

function pin_bar_types() {
    const W=680, H=220;
    // Three pin bar types side by side
    const types=[
        {cx:120, label:'PIN ALCISTA', color:C.accent, yH:40, yO:155, yC:168, yL:195},
        {cx:340, label:'PIN BAJISTA', color:C.red,    yH:30, yO:55,  yC:68,  yL:185},
        {cx:560, label:'DOJI PIN\n(indecisión)', color:C.yellow, yH:30, yO:108, yC:112, yL:190},
    ];

    let svg='';
    types.forEach(({cx,label,color,yH,yO,yC,yL})=>{
        svg+=`<line x1="${cx}" y1="${yH}" x2="${cx}" y2="${yL}" stroke="${color}" stroke-width="2.5"/>
        <rect x="${cx-16}" y="${Math.min(yO,yC)}" width="32" height="${Math.max(Math.abs(yO-yC),4)}" fill="${yC<yO?color:'none'}" stroke="${color}" stroke-width="2" rx="2"/>`;
        const lines=label.split('\n');
        lines.forEach((l,li)=>{
            svg+=`<text x="${cx}" y="${H-22+li*13}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`;
        });
        // Level line
        svg+=`<line x1="${cx-60}" y1="175" x2="${cx+60}" y2="175" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${svg}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La dirección de la mecha larga indica la dirección del rechazo
        </text>
    </svg>`;
}

function pin_bar_entry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,124,116,110,106,108,120,134,148];
    const mn=98, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.025),bull,24);
    });

    // Pin bar is at index 4-5 (low of 104, close of 108)
    const pinX=px(4.5);
    const pinHigh=py(108), pinLow=py(102);
    const entry1Y=py(108); // aggressive at close
    const entry2Y=py(105); // 50% retrace
    const stopY=py(100);
    const targetY=py(130);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${entry1Y}" x2="${x0+w}" y2="${entry1Y}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${x0}" y1="${entry2Y}" x2="${x0+w}" y2="${entry2Y}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        ${candles}
        <text x="${x0+w+4}" y="${entry1Y+4}" fill="${C.accent}" font-size="9" font-family="monospace">E1 agresiva</text>
        <text x="${x0+w+4}" y="${entry2Y+4}" fill="${C.cyan}" font-size="9" font-family="monospace">E2 al 50%</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">TARGET</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Entrada al 50% del cuerpo = mejor ratio riesgo/recompensa
        </text>
    </svg>`;
}

function pin_bar_confluence() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,122,114,108,112,110,108,106,110,120,132,144];
    const mn=98, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.025),bull,16);
    });

    let ema=prices[0],emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k);emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const supY=py(108);
    const pinX=px(7);
    const factors=[
        {label:'1. Soporte histórico',y:supY,color:C.accent},
        {label:'2. EMA 21',y:py(109),color:C.orange},
    ];

    let lines='';
    factors.forEach(({label,y,color})=>{
        lines+=`<line x1="${x0}" y1="${y}" x2="${x0+w}" y2="${y}" stroke="${color}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${lines}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="1.8" opacity="0.8"/>
        <circle cx="${pinX}" cy="${py(107)}" r="10" fill="none" stroke="${C.yellow}" stroke-width="2"/>
        <rect x="${x0+5}" y="${y0+5}" width="200" height="42" fill="${C.bg}" opacity="0.9" rx="3"/>
        <text x="${x0+10}" y="${y0+18}" fill="${C.accent}" font-size="9" font-family="monospace">① Soporte histórico</text>
        <text x="${x0+10}" y="${y0+31}" fill="${C.orange}" font-size="9" font-family="monospace">② EMA 21 semanal</text>
        <text x="${x0+10}" y="${y0+44}" fill="${C.cyan}" font-size="9" font-family="monospace">③ Tendencia alcista (HH+HL)</text>
        <text x="${pinX}" y="${(py(100)).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">PIN BAR ★</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Pin bar en confluencia de 3 factores = señal de máxima calidad
        </text>
    </svg>`;
}

function inside_bar_definition() {
    const W=680, H=220;
    const cx1=180, cx2=370;
    // Mother bar
    const m={yH:40, yO:80, yC:175, yL:190};
    // Inside bar (smaller, inside mother)
    const ib={yH:80, yO:100, yC:150, yL:175};

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(40,15,W-80,180)}
        <!-- Mother bar -->
        <line x1="${cx1}" y1="${m.yH}" x2="${cx1}" y2="${m.yL}" stroke="${C.red}" stroke-width="2.5"/>
        <rect x="${cx1-22}" y="${m.yO}" width="44" height="${m.yC-m.yO}" fill="${C.red}" stroke="${C.red}" stroke-width="2" rx="2"/>
        <text x="${cx1}" y="${H-30}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">VELA MADRE</text>
        <text x="${cx1}" y="${H-16}" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">Rango completo</text>
        <!-- Inside bar -->
        <line x1="${cx2}" y1="${ib.yH}" x2="${cx2}" y2="${ib.yL}" stroke="${C.cyan}" stroke-width="2.5"/>
        <rect x="${cx2-22}" y="${ib.yC}" width="44" height="${ib.yO-ib.yC}" fill="${C.cyan}" stroke="${C.cyan}" stroke-width="2" rx="2"/>
        <text x="${cx2}" y="${H-30}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">INSIDE BAR</text>
        <text x="${cx2}" y="${H-16}" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">Dentro del rango madre</text>
        <!-- Range brackets -->
        <line x1="${cx1+36}" y1="${m.yH}" x2="${cx2-36}" y2="${ib.yH}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>
        <line x1="${cx1+36}" y1="${m.yL}" x2="${cx2-36}" y2="${ib.yL}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>
        <text x="${(cx1+cx2)/2}" y="35" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Max IB < Max Madre</text>
        <text x="${(cx1+cx2)/2}" y="${H-42}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Min IB > Min Madre</text>
        <text x="${W/2}" y="${H-2}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El inside bar no supera ni el máximo ni el mínimo de la vela madre
        </text>
    </svg>`;
}

function inside_bar_continuation() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,116,124,132,136,134,136,135,144,156,168];
    const mn=92, mx=176, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,16);
    });

    // Inside bar at indices 6-8
    const ibX1=px(6), ibX2=px(8);
    const ibTop=py(136), ibBot=py(132);

    // Breakout arrow
    const brkX=px(9), brkY=py(136);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${ibX1.toFixed(1)}" y="${ibTop.toFixed(1)}" width="${(ibX2-ibX1).toFixed(1)}" height="${(ibBot-ibTop).toFixed(1)}" fill="${C.cyan}" opacity="0.12" stroke="${C.cyan}" stroke-width="1.5" rx="2"/>
        <text x="${((ibX1+ibX2)/2).toFixed(1)}" y="${(ibTop-6).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">INSIDE BAR</text>
        ${candles}
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.6"/>
        <text x="${(brkX+4).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA →</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Inside bar en tendencia = pausa de continuación — entra en ruptura
        </text>
    </svg>`;
}

function inside_bar_reversal() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,116,124,132,140,148,152,150,152,151,140,128,116,104];
    const mn=96, mx=160, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const resY=py(152);
    // Inside bars at 7-9 (near resistance)
    const ibX1=px(7), ibX2=px(9);
    const ibTop=py(152), ibBot=py(148);
    const brkDownX=px(10);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <rect x="${ibX1.toFixed(1)}" y="${ibTop.toFixed(1)}" width="${(ibX2-ibX1).toFixed(1)}" height="${(ibBot-ibTop).toFixed(1)}" fill="${C.orange}" opacity="0.15" stroke="${C.orange}" stroke-width="1.5" rx="2"/>
        ${candles}
        <text x="${((ibX1+ibX2)/2).toFixed(1)}" y="${(ibTop-6).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">IB en RES</text>
        <line x1="${brkDownX}" y1="${y0}" x2="${brkDownX}" y2="${y0+h}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>
        <text x="${(brkDownX+4).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace">Ruptura ↓</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RES</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Inside bar en resistencia + ruptura bajista = techo confirmado
        </text>
    </svg>`;
}

function inside_bar_false_break() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Inside bar, false break down, then explosive up
    const prices=[120,116,112,118,116,118,117,118,112,114,116,118,130,144,158];
    const mn=104, mx=166, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,12);
    });

    // Inside bar zone (indices 4-6)
    const ibX1=px(4), ibX2=px(6);
    const ibTop=py(118), ibBot=py(115);
    // False break (index 8 - spike below)
    const fbX=px(8), fbY=py(112);
    // Re-entry
    const entryX=px(10), entryY=py(116);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${ibX1.toFixed(1)}" y="${ibTop.toFixed(1)}" width="${(ibX2-ibX1).toFixed(1)}" height="${(ibBot-ibTop).toFixed(1)}" fill="${C.cyan}" opacity="0.12" stroke="${C.cyan}" stroke-width="1.5" rx="2"/>
        <line x1="${x0}" y1="${ibBot}" x2="${x0+w}" y2="${ibBot}" stroke="${C.cyan}" stroke-width="1" stroke-dasharray="5,4" opacity="0.5"/>
        ${candles}
        <rect x="${(fbX-16).toFixed(1)}" y="${(fbY-8).toFixed(1)}" width="32" height="16" fill="${C.orange}" opacity="0.15" stroke="${C.orange}" stroke-width="1" stroke-dasharray="3,2" rx="3"/>
        <text x="${fbX.toFixed(1)}" y="${(fbY+22).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">FALSE BREAK</text>
        <line x1="${entryX}" y1="${(entryY+16).toFixed(1)}" x2="${entryX}" y2="${(entryY+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUp8)"/>
        <defs><marker id="aUp8" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${entryX.toFixed(1)}" y="${(entryY+30).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            False break = trampa para cortos → entrada alcista cuando regresa al rango
        </text>
    </svg>`;
}

// ─── MÓDULO 7: RUPTURAS DE PRECIO ────────────────────────────────────────────

function range_breakout_energy() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,116,124,118,126,120,124,118,126,120,124,118,
                  126,120,124,120,130,142,154,166];
    const mn=108, mx=174, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.018),py(Math.min(prev,p)-(mx-mn)*0.015),bull,10);
    });

    const resY=py(127), supY=py(117);
    const ampH=resY-supY;
    const brkX=px(15);
    const targetY=py(137); // project the range up

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY}" width="${(brkX-x0).toFixed(1)}" height="${ampH.toFixed(1)}" fill="${C.yellow}" opacity="0.05"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${supY}" x2="${brkX}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${brkX.toFixed(1)}" y1="${resY}" x2="${x0+w}" y2="${targetY}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="5,4" opacity="0.4"/>
        ${candles}
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>
        <line x1="${(brkX+20).toFixed(1)}" y1="${resY}" x2="${(brkX+20).toFixed(1)}" y2="${targetY}" stroke="${C.accent}" stroke-width="1" opacity="0.5"/>
        <line x1="${(brkX+16).toFixed(1)}" y1="${resY}" x2="${(brkX+24).toFixed(1)}" y2="${resY}" stroke="${C.accent}" stroke-width="1" opacity="0.5"/>
        <line x1="${(brkX+16).toFixed(1)}" y1="${targetY}" x2="${(brkX+24).toFixed(1)}" y2="${targetY}" stroke="${C.accent}" stroke-width="1" opacity="0.5"/>
        <text x="${(brkX+28).toFixed(1)}" y="${((resY+targetY)/2+4).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">Objetivo =\namplitud</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Objetivo mínimo = amplitud del rango proyectada en dirección de ruptura
        </text>
    </svg>`;
}

function range_breakout_real_vs_false() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    function panel(x0, prices, vols, label, color, isFalse) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>20+160-((v-mn)/range)*160;
        let out=`<text x="${x0+panelW/2}" y="15" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,12);
        });
        const resY=py(Math.max(...prices.slice(0,-4)));
        out+=`<line x1="${x0}" y1="${resY}" x2="${x0+panelW}" y2="${resY}" stroke="${color}" stroke-width="1.2" stroke-dasharray="5,3" opacity="0.5"/>`;
        return out;
    }

    const realPrices=[110,112,108,113,110,114,111,114,112,116,128,140,152];
    const falsePrices=[110,112,108,113,110,114,111,114,112,118,116,112,110];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        ${panel(5, realPrices, [], '✓ RUPTURA REAL (volumen alto)', C.accent, false)}
        ${panel(panelW+30, falsePrices, [], '✗ RUPTURA FALSA (vuelve al rango)', C.red, true)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            70% de las rupturas aparentes son falsas — el volumen es el filtro
        </text>
    </svg>`;
}

function range_breakout_entry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[116,112,118,112,118,112,118,112,118,112,124,130,
                  126,122,124,136,148];
    const mn=104, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(119), retestY=py(122), brkX=px(9);
    const e1Y=py(124), e2Y=py(122), e3Y=py(124);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.6"/>
        ${candles}
        <line x1="${px(10).toFixed(1)}" y1="${(e1Y+18).toFixed(1)}" x2="${px(10).toFixed(1)}" y2="${(e1Y+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2" marker-end="url(#aUp9)"/>
        <text x="${px(10).toFixed(1)}" y="${(e1Y+32).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">E1</text>
        <line x1="${px(13).toFixed(1)}" y1="${(e2Y+18).toFixed(1)}" x2="${px(13).toFixed(1)}" y2="${(e2Y+4).toFixed(1)}" stroke="${C.cyan}" stroke-width="2" marker-end="url(#aUp9)"/>
        <text x="${px(13).toFixed(1)}" y="${(e2Y+32).toFixed(1)}" fill="${C.cyan}" font-size="8" font-family="monospace" text-anchor="middle">E2 retest</text>
        <defs><marker id="aUp9" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 5 L 2.5 0 L 5 5 z" fill="${C.accent}"/></marker></defs>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="9" font-family="monospace">RES→SUP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            E1 en ruptura — E2 en retest (mejor ratio, no siempre disponible)
        </text>
    </svg>`;
}

function range_breakout_target() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[116,112,118,112,118,112,118,112,118,126,138,132,126,130,142,154];
    const mn=104, mx=162, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(119), supY=py(111);
    const amp=supY-resY;
    const targetY=py(127); // range amplitude above resistance

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <rect x="${x0+w-15}" y="${targetY}" width="12" height="${resY-targetY}" fill="${C.yellow}" opacity="0.1"/>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">OBJETIVO</text>
        ${candles}
        <text x="${(x0+w-2).toFixed(1)}" y="${((resY+targetY)/2+4).toFixed(1)}" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="end">=amplitud</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            T1 en objetivo medido → subir stop → dejar correr hacia niveles siguientes
        </text>
    </svg>`;
}

function trendline_break_significance() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,112,105,120,112,130,122,138,128,144,132,148,134,140,126,132,118];
    const mn=88, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    // Trendline through lows: 1,3,5,7,9,11 with values 96,105,112,122,128,132
    const tlPts=[[1,96],[3,105],[5,112],[7,122],[9,128],[11,132]];
    const tlPath=tlPts.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const extPath=`${tlPath} L ${px(17).toFixed(1)} ${py(148).toFixed(1)}`;

    let touches='';
    tlPts.forEach(([i,v],ti)=>{
        touches+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.accent}" opacity="${0.4+ti*0.1}"/>`;
    });

    const brkX=px(14), brkY=py(136);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${extPath}" fill="none" stroke="${C.accent}" stroke-width="2" opacity="0.7"/>
        ${candles}${touches}
        <circle cx="${brkX}" cy="${brkY}" r="9" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${brkX}" y="${(brkY+22).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <text x="${x0+4}" y="${y0+14}" fill="${C.accent}" font-size="9" font-family="monospace">6 toques → ruptura muy significativa</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Más toques válidos = ruptura más significativa
        </text>
    </svg>`;
}

function uptrend_line_break() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,112,104,124,114,134,122,140,128,144,
                  130,122,130,124,116,118,110,112,104];
    const mn=96, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const tlPts=[[1,96],[3,104],[5,114],[7,122],[9,128]];
    const slope=(tlPts[4][1]-tlPts[0][1])/(tlPts[4][0]-tlPts[0][0]);
    const tlY=(i)=>tlPts[0][1]+slope*(i-tlPts[0][0]);
    const tlPath=tlPts.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const extPath=`${tlPath} L ${px(19).toFixed(1)} ${py(tlY(19)).toFixed(1)}`;

    const brkX=px(11), retestX=px(13), retestY=py(tlY(13));

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${extPath}" fill="none" stroke="${C.accent}" stroke-width="1.8" stroke-dasharray="7,3" opacity="0.6"/>
        ${candles}
        <circle cx="${brkX}" cy="${py(130)}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${brkX}" y="${(py(123)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">①RUPTURA</text>
        <circle cx="${retestX}" cy="${retestY.toFixed(1)}" r="8" fill="none" stroke="${C.orange}" stroke-width="2"/>
        <text x="${retestX}" y="${(retestY-12).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">②RETEST</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ① Ruptura → ② Retest (resistencia) → caída confirmada
        </text>
    </svg>`;
}

function downtrend_line_break() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[150,155,138,148,126,140,114,130,104,122,96,
                  114,108,118,116,124,128,136,144];
    const mn=88, mx=163, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const tlPts=[[1,155],[3,148],[5,140],[7,130],[9,122]];
    const slope=(tlPts[4][1]-tlPts[0][1])/(tlPts[4][0]-tlPts[0][0]);
    const tlY=(i)=>tlPts[0][1]+slope*(i-tlPts[0][0]);
    const tlPath=tlPts.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const extPath=`${tlPath} L ${px(18).toFixed(1)} ${py(tlY(18)).toFixed(1)}`;

    const brkX=px(13);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${extPath}" fill="none" stroke="${C.red}" stroke-width="1.8" stroke-dasharray="7,3" opacity="0.6"/>
        ${candles}
        <circle cx="${brkX}" cy="${py(118)}" r="8" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${brkX}" y="${(py(112)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA ↑</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura de tendencia bajista = primera señal de recuperación
        </text>
    </svg>`;
}

function accelerated_breakout() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Parabolic move breaking upper channel
    const prices=[100,102,104,107,110,114,119,125,132,140,150,162,156,142,128,114];
    const mn=100, mx=170, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,13);
    });

    // Normal trendline (lower channel)
    const tl1=[px(0),py(100),px(9),py(140)];
    // Upper channel (parallel)
    const tl2=[px(0),py(114),px(9),py(154)];
    // Parabolic break
    const parPath=`M ${px(9).toFixed(1)} ${py(140).toFixed(1)} L ${px(11).toFixed(1)} ${py(162).toFixed(1)}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${tl1[0]}" y1="${tl1[1]}" x2="${tl1[2]}" y2="${tl1[3]}" stroke="${C.accent}" stroke-width="2" opacity="0.7"/>
        <line x1="${tl2[0]}" y1="${tl2[1]}" x2="${tl2[2]}" y2="${tl2[3]}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>
        ${candles}
        <path d="${parPath}" fill="none" stroke="${C.red}" stroke-width="2.5" stroke-dasharray="5,3"/>
        <circle cx="${px(11)}" cy="${py(162)}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(11)}" y="${(py(168)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">PARABOLICO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura parabolica del canal = señal de agotamiento final, no de compra
        </text>
    </svg>`;
}

function support_break_why() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Weakening bounces then break
    const prices=[130,122,118,126,120,116,122,116,112,116,112,108,112,
                  108,105,100,94];
    const mn=86, mx=138, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const supY=py(112);
    const bounces=[[3,126],[6,122],[9,116],[12,112]];
    let bMarks='';
    bounces.forEach(([i,v],bi)=>{
        const opacity=1-bi*0.2;
        bMarks+=`<line x1="${px(i)}" y1="${(py(v)-5).toFixed(1)}" x2="${px(i)}" y2="${(py(v)-16).toFixed(1)}" stroke="${C.accent}" stroke-width="${2-bi*0.4}" opacity="${opacity}" marker-end="url(#aDn8)"/>
        <text x="${px(i)}" y="${(py(v)-20).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle" opacity="${opacity}">↑${['fuerte','medio','débil','mínimo'][bi]}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs><marker id="aDn8" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 0 L 2.5 5 L 5 0 z" fill="${C.accent}"/></marker></defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}${bMarks}
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SOPORTE</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Rebotes decrecientes = soporte agotándose → ruptura inminente
        </text>
    </svg>`;
}

function support_break_types() {
    const W=680, H=220;
    const panelW=(W-65)/4;
    const types=[
        {label:'Limpia',prices:[120,112,104,96,88],color:C.red},
        {label:'Spike',prices:[120,114,108,104,108,106,100,94],color:C.orange},
        {label:'Lenta',prices:[120,116,114,112,110,109,108,106,102,98],color:C.yellow},
        {label:'Gap',prices:[120,116,112,108,96,90,84],color:C.muted},
    ];

    let content='';
    types.forEach(({label,prices,color},ti)=>{
        const x0=8+ti*(panelW+5);
        const mn=Math.min(...prices)-4, mx=Math.max(...prices)+4, range=mx-mn;
        const px=(i)=>x0+(i/(prices.length-1))*panelW;
        const py=(v)=>20+160-((v-mn)/range)*160;
        content+=`<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            const isGap=ti===3&&i===4;
            if(isGap){
                content+=`<line x1="${cx-6}" y1="${py(prev-8)}" x2="${cx+6}" y2="${py(p+4)}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="3,2" opacity="0.4"/>`;
            }
            content+=candleRow(cx,py(prev),py(p),py(p+range*0.035),py(Math.min(prev,p)-range*0.028),bull,Math.floor(panelW/prices.length)-2);
        });
        const supY=py(Math.max(...prices)*0.88);
        content+=`<line x1="${x0}" y1="${supY}" x2="${x0+panelW}" y2="${supY}" stroke="${color}" stroke-width="1.2" stroke-dasharray="4,3" opacity="0.5"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        ${[1,2,3].map(i=>`<line x1="${8+i*(panelW+5)-3}" y1="5" x2="${8+i*(panelW+5)-3}" y2="${H-15}" stroke="${C.border}" stroke-width="1"/>`).join('')}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cuatro formas de romper un soporte — cada una pide una reacción distinta
        </text>
    </svg>`;
}

function support_becomes_resistance() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,122,116,122,118,114,120,116,112,108,
                  106,112,108,106,100,94];
    const mn=86, mx=138, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,13);
    });

    const supLevel=116, supY=py(supLevel);
    const brkX=px(8), retestX=px(11), retestY=py(112);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-4}" width="${(brkX-x0).toFixed(1)}" height="8" fill="${C.accent}" opacity="0.08"/>
        <rect x="${brkX.toFixed(1)}" y="${supY-4}" width="${(x0+w-brkX).toFixed(1)}" height="8" fill="${C.red}" opacity="0.08"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.orange}" stroke-width="2" stroke-dasharray="7,4"/>
        ${candles}
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
        <text x="${((x0+brkX)/2).toFixed(1)}" y="${(supY+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">SOPORTE</text>
        <text x="${((brkX+x0+w)/2).toFixed(1)}" y="${(supY+14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">→ RESISTENCIA</text>
        <circle cx="${retestX}" cy="${retestY}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${retestX}" y="${(retestY-12).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">RETEST</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Soporte roto → retest desde abajo → rechazado como resistencia
        </text>
    </svg>`;
}

function support_break_action() {
    const W=680, H=220;
    const x0=30, y0=20, w=W-60, h=160;
    const scenarios=[
        {label:'CON STOP\ndefinido',icon:'✓',color:C.accent,desc:'Stop se activa automáticamente\nSal y analiza'},
        {label:'SIN STOP\ndefinido',icon:'⚠',color:C.orange,desc:'Sal al cierre de la vela\nque rompe el soporte'},
        {label:'PRECIO 10%\nbajo soporte',icon:'⚡',color:C.yellow,desc:'Evalúa probabilidad de retest\nantes de actuar'},
        {label:'NUNCA\nhacer',icon:'✗',color:C.red,desc:'Añadir a la posición\nperdedora esperando rebote'},
    ];

    const bw=130, gap=18, startX=x0+20;
    let content='';
    scenarios.forEach(({label,icon,color,desc},i)=>{
        const x=startX+i*(bw+gap);
        const lines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="${y0+20}" width="${bw}" height="${h-40}" fill="${color}" opacity="${i===3?0.12:0.08}" rx="6" stroke="${color}" stroke-width="${i===3?2:1}"/>
        <text x="${x+bw/2}" y="${y0+44}" fill="${color}" font-size="20" text-anchor="middle">${icon}</text>`;
        lines.forEach((l,li)=>{
            content+=`<text x="${x+bw/2}" y="${y0+68+li*14}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`;
        });
        descLines.forEach((l,li)=>{
            content+=`<text x="${x+bw/2}" y="${y0+106+li*12}" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">${l}</text>`;
        });
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La ruptura del soporte invalida la tesis de entrada — actúa en consecuencia
        </text>
    </svg>`;
}

function retest_why() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[116,112,118,112,118,112,118,112,126,138,132,126,124,128,138,150];
    const mn=104, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(119), brkX=px(8), retestX=px(11), retestY=py(124);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        ${candles}
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        <circle cx="${retestX}" cy="${retestY}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${retestX}" y="${(retestY+22).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RETEST</text>
        <text x="${(brkX+6).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.muted}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.accent}" font-size="9" font-family="monospace">RES→SUP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El retest = la segunda oportunidad de entrar con menor riesgo
        </text>
    </svg>`;
}

function retest_bullish() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[116,112,118,112,118,112,118,128,140,134,126,122,124,134,146,158];
    const mn=104, mx=166, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(119), brkX=px(7), retestX=px(12), retestY=py(122);
    const stopY=py(116), entry=px(12);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        ${candles}
        <circle cx="${retestX}" cy="${retestY}" r="9" fill="${C.accent}" opacity="0.15" stroke="${C.accent}" stroke-width="2"/>
        <line x1="${retestX}" y1="${(retestY+18).toFixed(1)}" x2="${retestX}" y2="${(retestY+5).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUp10)"/>
        <defs><marker id="aUp10" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${retestX}" y="${(retestY+32).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SOPORTE</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retest alcista: precio vuelve al nivel, muestra rechazo, entrada con stop pequeño
        </text>
    </svg>`;
}

function retest_bearish() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[130,122,118,124,118,112,108,116,112,108,102,96];
    const mn=88, mx=138, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,16);
    });

    const supLevel=118, supY=py(supLevel), brkX=px(4);
    const retestX=px(7), retestY=py(116);
    const stopY=py(121);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        ${candles}
        <circle cx="${retestX}" cy="${retestY}" r="9" fill="${C.red}" opacity="0.15" stroke="${C.red}" stroke-width="2"/>
        <line x1="${retestX}" y1="${(retestY-5).toFixed(1)}" x2="${retestX}" y2="${(retestY-18).toFixed(1)}" stroke="${C.red}" stroke-width="2.5" marker-end="url(#aDn9)"/>
        <defs><marker id="aDn9" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 0 L 3 6 L 6 0 z" fill="${C.red}"/></marker></defs>
        <text x="${retestX}" y="${(retestY-24).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">CORTO</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.orange}" font-size="9" font-family="monospace">SUP→RES</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retest bajista: soporte roto actúa como resistencia — entrada corta de calidad
        </text>
    </svg>`;
}

function retest_failed() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Price breaks support, retests from below, then breaks UP (failed bearish breakout)
    const prices=[130,122,116,122,116,110,106,112,108,114,110,116,122,130,138,146];
    const mn=98, mx=154, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const supY=py(116), brkX=px(5), retestX=px(10), failX=px(11);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        ${candles}
        <circle cx="${brkX}" cy="${py(110)}" r="7" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${brkX}" y="${(py(104)).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <circle cx="${retestX}" cy="${py(116)}" r="7" fill="none" stroke="${C.orange}" stroke-width="2"/>
        <text x="${retestX}" y="${(py(123)).toFixed(1)}" fill="${C.orange}" font-size="8" font-family="monospace" text-anchor="middle">RETEST</text>
        <circle cx="${failX}" cy="${py(122)}" r="7" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${failX}" y="${(py(129)).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">FALLO ↑</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.orange}" font-size="9" font-family="monospace">NIVEL</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retest fallido: ruptura bajista que vuelve al alza = señal alcista potente
        </text>
    </svg>`;
}

// ─── MÓDULO 0: RSU TERMINAL ──────────────────────────────────────────────────

function rsu_philosophy() {
    const W=680, H=210;
    const pillars=[
        {icon:'🔍',label:'ANÁLISIS',desc:'Herramientas para\nentender el mercado',color:C.accent},
        {icon:'🧠',label:'METODOLOGÍA',desc:'Marco de decisión\nreproducible',color:C.cyan},
        {icon:'⚡',label:'EJECUCIÓN',desc:'Disciplina para\nseguir el plan',color:C.yellow},
    ];
    const bw=170, gap=40, startX=50;
    let content='';
    pillars.forEach(({icon,label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="20" width="${bw}" height="155" fill="${color}" opacity="0.08" rx="8" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="58" font-size="30" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="82" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${104+li*16}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<2) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="20" text-anchor="middle">+</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">RSU Terminal = Análisis + Metodología + Ejecución. Los tres son necesarios.</text>
    </svg>`;
}

function rsu_community() {
    const W=680, H=210;
    const items=[
        {icon:'📡',label:'Datos live',desc:'WebSocket · yfinance · FMP'},
        {icon:'🤖',label:'IA integrada',desc:'Groq · Gemini · Perplexity'},
        {icon:'📊',label:'10 módulos',desc:'Market → Cartera → Research'},
        {icon:'🎓',label:'Academia',desc:'15 módulos · 60 lecciones'},
        {icon:'🌙',label:'Briefing',desc:'Análisis nocturno automático'},
        {icon:'👥',label:'Comunidad',desc:'~100 traders activos'},
    ];
    const cols=3, bw=190, bh=70, gap=10, startX=20, startY=15;
    let content='';
    items.forEach(({icon,label,desc},i)=>{
        const col=i%cols, row=Math.floor(i/cols);
        const x=startX+col*(bw+gap), y=startY+row*(bh+gap);
        content+=`<rect x="${x}" y="${y}" width="${bw}" height="${bh}" fill="${C.surface}" stroke="${C.border}" stroke-width="1" rx="5"/>
        <text x="${x+16}" y="${y+24}" font-size="18">${icon}</text>
        <text x="${x+42}" y="${y+24}" fill="${C.accent}" font-size="11" font-family="monospace" font-weight="bold">${label}</text>
        <text x="${x+42}" y="${y+40}" fill="${C.muted}" font-size="10" font-family="monospace">${desc}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Una plataforma completa construida y mantenida por la comunidad RSU</text>
    </svg>`;
}

function rsu_for_who() {
    const W=680, H=200;
    const profiles=[
        {label:'Con metodología\npropia',fit:'IDEAL',color:C.accent,icon:'✓'},
        {label:'Aprendiendo\na operar',fit:'VÁLIDO',color:C.cyan,icon:'✓'},
        {label:'Buscando señales\nautomáticas',fit:'NO ENCAJA',color:C.red,icon:'✗'},
        {label:'Inversor\npasivo',fit:'PARCIAL',color:C.yellow,icon:'~'},
    ];
    const bw=145, gap=10, startX=15;
    let content='';
    profiles.forEach(({label,fit,color,icon},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="50" fill="${color}" font-size="28" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${72+li*16}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<rect x="${x+15}" y="112" width="${bw-30}" height="22" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="127" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${fit}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">RSU Terminal potencia la metodología propia — no la reemplaza</text>
    </svg>`;
}

function rsu_topdown() {
    const W=680, H=220;
    const levels=[
        {label:'MERCADO GENERAL',desc:'S&P 500 · VIX · Breadth',tool:'Market Dashboard + FED & Macro',color:C.accent,w:620},
        {label:'SECTOR',desc:'Rotación · Líderes · Rezagados',tool:'RS/RW + CAN SLIM Heatmap',color:C.cyan,w:500},
        {label:'ACTIVO',desc:'RS Rating · Fundamentales · Estructura',tool:'CAN SLIM + Research',color:C.yellow,w:380},
        {label:'SETUP',desc:'Nivel · Trigger · R:R',tool:'Análisis técnico',color:C.orange,w:260},
        {label:'EJECUCIÓN',desc:'Entrada · Stop · Tamaño',tool:'Plan de trade',color:C.red,w:140},
    ];
    let content='';
    let y=12;
    levels.forEach(({label,desc,tool,color,w},i)=>{
        const x=(680-w)/2;
        content+=`<rect x="${x}" y="${y}" width="${w}" height="30" fill="${color}" opacity="${0.08+i*0.03}" rx="4" stroke="${color}" stroke-width="1"/>
        <text x="${680/2}" y="${y+13}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${680/2}" y="${y+24}" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">${tool}</text>`;
        y+=34;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Top-Down: del contexto más amplio al más específico. Siempre en este orden.</text>
    </svg>`;
}

function rsu_three_pillars() {
    const W=680, H=210;
    const pillars=[
        {n:'1',label:'CONTEXTO\nFAVORABLE',items:['Mercado alcista','Sector líder','M + S alineados'],color:C.accent},
        {n:'2',label:'ACTIVO\nDE CALIDAD',items:['RS Rating > 80','Fundamentales ok','Trend Template ok'],color:C.cyan},
        {n:'3',label:'SETUP CON\nR:R ≥ 1:2',items:['Nivel claro','Trigger definido','Stop calculado'],color:C.yellow},
    ];
    const bw=180, gap=28, startX=28;
    let content='';
    pillars.forEach(({n,label,items,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="170" fill="${color}" opacity="0.08" rx="8" stroke="${color}" stroke-width="2"/>
        <circle cx="${x+bw/2}" cy="44" r="18" fill="${color}" opacity="0.2" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="50" fill="${color}" font-size="16" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${74+li*15}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        items.forEach((item,li)=>{ content+=`<text x="${x+16}" y="${112+li*17}" fill="${C.muted}" font-size="10" font-family="monospace">✓ ${item}</text>`; });
        if(i<2) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.accent}" font-size="20" text-anchor="middle">+</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Si falta cualquiera de los tres pilares → no hay trade</text>
    </svg>`;
}

function rsu_risk_first() {
    const W=680, H=200;
    const pairs=[
        {bad:'"¿Cuánto puedo ganar?"',good:'"¿Cuánto puedo perder?"'},
        {bad:'Entra, luego piensa el stop',good:'Define el stop antes de entrar'},
        {bad:'Tamaño según "sensación"',good:'Tamaño según riesgo fijo 1%'},
        {bad:'Promedia pérdidas',good:'Nunca promedia pérdidas'},
    ];
    const rowH=38, startY=15, col1=20, col2=340;
    let content=`<text x="${col1+140}" y="12" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">AMATEUR</text>
    <text x="${col2+140}" y="12" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">METODOLOGÍA RSU</text>
    <line x1="${W/2}" y1="5" x2="${W/2}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>`;
    pairs.forEach(({bad,good},i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${col1}" y="${y}" width="300" height="${rowH-4}" fill="${C.red}" opacity="0.05" rx="4"/>
        <text x="${col1+8}" y="${y+rowH/2+4}" fill="${C.red}" font-size="10" font-family="monospace">${bad}</text>
        <rect x="${col2}" y="${y}" width="300" height="${rowH-4}" fill="${C.accent}" opacity="0.05" rx="4"/>
        <text x="${col2+8}" y="${y+rowH/2+4}" fill="${C.accent}" font-size="10" font-family="monospace">${good}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Gestión del riesgo primero — siempre. No es opcional.</text>
    </svg>`;
}

function rsu_patience() {
    const W=680, H=210;
    // Timeline: semanas con y sin trade
    const weeks=[0,0,1,0,0,1,0,0,0,1,0,1,0,0,0,0,1,0,1,0];
    const bw=28, gap=4, startX=20, y0=30, barH=100;
    let content='';
    let trades=0, capital=100;
    const results=[0,0,2.5,0,0,2.0,0,0,0,3.0,0,-1.0,0,0,0,0,2.5,0,3.0,0];

    weeks.forEach((hasTrade,i)=>{
        const x=startX+i*(bw+gap);
        if(hasTrade){
            const gain=results[i];
            const color=gain>0?C.accent:C.red;
            const bh=Math.abs(gain)*15;
            const barY=gain>0?y0+barH-bh:y0+barH;
            content+=`<rect x="${x}" y="${barY}" width="${bw}" height="${bh}" fill="${color}" opacity="0.7" rx="2"/>`;
            trades++;
        } else {
            content+=`<rect x="${x}" y="${y0+barH-2}" width="${bw}" height="4" fill="${C.border}" opacity="0.3" rx="1"/>`;
        }
        content+=`<text x="${x+bw/2}" y="${y0+barH+14}" fill="${C.muted}" font-size="7" font-family="monospace" text-anchor="middle">S${i+1}</text>`;
    });

    content+=`<line x1="${startX-5}" y1="${y0+barH}" x2="${startX+weeks.length*(bw+gap)}" y2="${y0+barH}" stroke="${C.border}" stroke-width="1"/>`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${y0-14}" fill="${C.muted}" font-size="11" font-family="monospace" text-anchor="middle">${trades} trades en 20 semanas — el resto: esperar. Eso es disciplina.</text>
        <rect x="${startX+weeks.length*(bw+gap)+10}" y="${y0}" width="120" height="50" fill="${C.surface}" stroke="${C.border}" stroke-width="1" rx="4"/>
        <text x="${startX+weeks.length*(bw+gap)+70}" y="${y0+18}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Semanas activas</text>
        <text x="${startX+weeks.length*(bw+gap)+70}" y="${y0+36}" fill="${C.accent}" font-size="16" font-family="monospace" text-anchor="middle" font-weight="bold">${trades}/20</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Menos operaciones, mejor selección → resultados más consistentes</text>
    </svg>`;
}

function tools_market_analysis() {
    const W=680, H=200;
    const tools=[
        {icon:'📊',name:'Market Dashboard',use:'Cada mañana',color:C.accent},
        {icon:'🏛️',name:'FED & Macro',use:'Días de datos',color:C.cyan},
        {icon:'⚡',name:'SPXL Strategy',use:'Correcciones',color:C.yellow},
        {icon:'₿',name:'BTC Stratum',use:'Acumulación',color:C.orange},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    tools.forEach(({icon,name,use,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="48" font-size="24" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="70" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${name}</text>
        <line x1="${x+15}" y1="80" x2="${x+bw-15}" y2="80" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="100" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Usar:</text>
        <text x="${x+bw/2}" y="116" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${use}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Contexto macro primero — siempre antes de mirar activos individuales</text>
    </svg>`;
}

function tools_stock_selection() {
    const W=680, H=200;
    const tools=[
        {icon:'🔍',name:'CAN SLIM',use:'Dominical',color:C.accent},
        {icon:'📈',name:'RS/RW Scanner',use:'Líderes/Rezagados',color:C.cyan},
        {icon:'💰',name:'Options Flow',use:'Flujo institucional',color:C.yellow},
        {icon:'🧠',name:'Research',use:'Due diligence',color:C.orange},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    tools.forEach(({icon,name,use,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="48" font-size="24" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="70" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${name}</text>
        <line x1="${x+15}" y1="80" x2="${x+bw-15}" y2="80" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="100" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Usar:</text>
        <text x="${x+bw/2}" y="116" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${use}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">De 5,000+ acciones a 5-10 candidatos de alta calidad</text>
    </svg>`;
}

function tools_management() {
    const W=680, H=200;
    const tools=[
        {icon:'💼',name:'Cartera',use:'Siempre abierta',color:C.accent},
        {icon:'🌙',name:'Resumen de Mercado Diario',use:'Cada noche',color:C.cyan},
        {icon:'📰',name:'Newsfeed',use:'Movimientos inexplicados',color:C.yellow},
    ];
    const bw=200, gap=15, startX=25;
    let content='';
    tools.forEach(({icon,name,use,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="55" font-size="32" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="82" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${name}</text>
        <line x1="${x+20}" y1="92" x2="${x+bw-20}" y2="92" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="115" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${use}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Seguimiento pasivo — sin estar pegado a la pantalla todo el día</text>
    </svg>`;
}

function tools_academy() {
    const W=680, H=200;
    const phases=[
        {label:'INTRO',mods:'Módulo 0',color:C.muted},
        {label:'FASE 1',mods:'Módulos 1-4',color:C.accent},
        {label:'FASE 2',mods:'Módulos 5-8',color:C.cyan},
        {label:'FASE 3',mods:'Módulos 9-11',color:C.yellow},
        {label:'FASE 4',mods:'Módulos 12-15',color:C.orange},
    ];
    const bw=118, gap=10, startX=12;
    let content='';
    phases.forEach(({label,mods,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="20" width="${bw}" height="145" fill="${color}" opacity="${0.05+i*0.02}" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="50" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${x+bw/2}" y="70" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${mods}</text>
        <text x="${x+bw/2}" y="90" fill="${color}" font-size="22" text-anchor="middle">${['🖥️','📍','🔬','🎯','🚀'][i]}</text>`;
        if(i<4) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="12" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">16 módulos · 64 lecciones · Teoría + práctica integradas en RSU Terminal</text>
    </svg>`;
}

function weekly_ritual_sunday() {
    const W=680, H=210;
    const steps=[
        {time:'Dom 9:00',task:'CAN SLIM Scan',tool:'Screener completo',color:C.accent},
        {time:'Dom 9:30',task:'RS/RW Sectores',tool:'Identificar líderes',color:C.cyan},
        {time:'Dom 10:00',task:'Market Dashboard',tool:'Sesgo + estado',color:C.yellow},
        {time:'Dom 10:20',task:'FED & Macro',tool:'Datos de la semana',color:C.orange},
        {time:'Dom 10:40',task:'Watchlist',tool:'5-10 candidatos + niveles',color:C.red},
    ];
    const bw=118, gap=8, startX=12;
    let content='';
    steps.forEach(({time,task,tool,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="5" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="34" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${time}</text>
        <line x1="${x+10}" y1="40" x2="${x+bw-10}" y2="40" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="62" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${task}</text>
        <text x="${x+bw/2}" y="82" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${tool}</text>
        <text x="${x+bw/2}" y="110" fill="${color}" font-size="20" text-anchor="middle">${['🔍','📈','📊','🏛️','📋'][i]}</text>
        <text x="${x+bw/2}" y="145" fill="${color}" font-size="22" text-anchor="middle">~${['30','15','15','20','30'][i]}min</text>`;
        if(i<4) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="12" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El ritual dominical: ~2 horas que definen la calidad de toda la semana</text>
    </svg>`;
}

function weekly_ritual_daily() {
    const W=680, H=200;
    const moments=[
        {label:'PRE-APERTURA\n8:30-9:15',items:['Market Dashboard','Newsfeed','Revisar stops'],color:C.accent,time:'15 min'},
        {label:'DURANTE SESIÓN\n9:30-16:00',items:['Cartera (pasivo)','Alertas si trigger','Nada más'],color:C.cyan,time:'Pasivo'},
        {label:'POST-CIERRE\n16:00-16:30',items:['Cartera (cierre)','Resumen de Mercado Diario','Prep mañana'],color:C.yellow,time:'15 min'},
    ];
    const bw=196, gap=16, startX=18;
    let content='';
    moments.forEach(({label,items,color,time},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${34+li*14}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        items.forEach((item,li)=>{ content+=`<text x="${x+16}" y="${74+li*18}" fill="${C.muted}" font-size="10" font-family="monospace">▸ ${item}</text>`; });
        content+=`<rect x="${x+20}" y="135" width="${bw-40}" height="22" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="150" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${time}</text>`;
        if(i<2) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="16" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">30 minutos al día son suficientes si tienes el plan del domingo</text>
    </svg>`;
}

function weekly_ritual_wait() {
    const W=680, H=200;
    const items=[
        {label:'VIX > 30',desc:'Mercado en pánico.\nEsperar estabilización.',color:C.red},
        {label:'Sin triple alineación',desc:'Contexto M+S+D\nno alineados.',color:C.orange},
        {label:'R:R < 1:2',desc:'El setup no ofrece\nsuficiente recompensa.',color:C.yellow},
        {label:'Plan no completo',desc:'Falta stop, objetivo\no trigger definido.',color:C.muted},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    items.forEach(({label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="40" fill="${color}" font-size="28" text-anchor="middle">✗</text>
        <text x="${x+bw/2}" y="62" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x+15}" y1="72" x2="${x+bw-15}" y2="72" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${92+li*16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="145" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">NO OPERAR</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Reconocer cuándo no operar es una habilidad, no un fracaso</text>
    </svg>`;
}

function weekly_ritual_adapt() {
    const W=680, H=200;
    const states=[
        {label:'CONFIRMED\nUPTREND',posture:'OFENSIVA',desc:'Buscar y abrir.\nTamaño completo.',color:C.accent},
        {label:'UNDER\nPRESSURE',posture:'DEFENSIVA',desc:'No abrir nuevas.\nProteger existentes.',color:C.yellow},
        {label:'RALLY\nATTEMPT',posture:'ESPERA',desc:'Preparar lista.\nEsperar FTD.',color:C.orange},
        {label:'MARKET\nCORRECTION',posture:'CAPITAL',desc:'Gestionar stops.\nReducir exposición.',color:C.red},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    states.forEach(({label,posture,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${36+li*15}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        content+=`<rect x="${x+15}" y="72" width="${bw-30}" height="20" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="86" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${posture}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${112+li*16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">La postura cambia con el mercado — la metodología siempre es la misma</text>
    </svg>`;
}

// ─── MÓDULO 8: ANÁLISIS DE VOLUMEN ───────────────────────────────────────────

function volume_confirms_price() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,104,108,112,116,120,124,128,132,136,140,144,148,152,156];
    const vols=  [1.0,1.2,1.4,1.3,1.5,1.8,1.6,2.0,1.7,1.9,1.5,1.3,1.1,0.9,0.8];
    const mn=92, mx=164, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,13);
        const bh=vols[i]*volH;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${C.accent}" opacity="${0.3+vols[i]*0.25}" rx="1"/>`;
    });

    // Volume trend line
    const volPath=prices.map((_,i)=>{
        if(!i) return null;
        const cx=px(i), bh=vols[i]*volH;
        return `${i===1?'M':'L'} ${cx.toFixed(1)} ${(volY0+volH-bh).toFixed(1)}`;
    }).filter(Boolean).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <path d="${volPath}" fill="none" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.6"/>
        <text x="${x0}" y="${y0+12}" fill="${C.textDim}" font-size="9" font-family="monospace">PRECIO ↑</text>
        <text x="${x0}" y="${volY0-3}" fill="${C.textDim}" font-size="9" font-family="monospace">VOLUMEN</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Precio y volumen suben juntos = tendencia alcista sana y confirmada
        </text>
    </svg>`;
}

function breakout_volume_valid() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[110,112,108,113,110,114,111,114,112,116,130,142,138,145,152];
    const vols=  [0.7,0.8,0.6,0.7,0.8,0.7,0.6,0.8,0.7,0.9,3.2,2.8,1.2,1.4,1.6];
    const mn=100, mx=160, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=vols[i]*volH;
        const isBreak=i>=10&&i<=11;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isBreak?C.accent:C.muted}" opacity="${isBreak?0.9:0.35}" rx="1"/>`;
    });

    const resY=py(116), brkX=px(9);
    const avgVolY=volY0+volH-0.75*volH;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.6"/>
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        <line x1="${x0}" y1="${avgVolY}" x2="${x0+w}" y2="${avgVolY}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
        <text x="${x0+4}" y="${avgVolY-3}" fill="${C.muted}" font-size="8" font-family="monospace">Promedio</text>
        ${volBars}
        <circle cx="${px(10).toFixed(1)}" cy="${py(130).toFixed(1)}" r="8" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(10).toFixed(1)}" y="${(py(138)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">3x vol</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="9" font-family="monospace">RES</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura válida = volumen 3x+ del promedio en el día de la ruptura
        </text>
    </svg>`;
}

function pullback_low_volume() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[110,112,110,113,111,114,112,128,136,132,128,124,122,126,134,142];
    const vols=  [0.7,0.8,0.7,0.8,0.7,0.9,0.8,2.8,2.2,0.6,0.5,0.4,0.3,0.7,1.4,1.8];
    const mn=102, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=vols[i]*volH;
        const isPullback=i>=9&&i<=12;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isPullback?C.red:C.accent}" opacity="${isPullback?0.4:0.5}" rx="1"/>`;
    });

    const resY=py(115);
    // Pullback zone
    const pbX1=px(8), pbX2=px(13);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.5"/>
        <rect x="${pbX1.toFixed(1)}" y="${y0}" width="${(pbX2-pbX1).toFixed(1)}" height="${h}" fill="${C.red}" opacity="0.04"/>
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${((pbX1+pbX2)/2).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">PULLBACK bajo vol.</text>
        <line x1="${px(13).toFixed(1)}" y1="${(py(122)+16).toFixed(1)}" x2="${px(13).toFixed(1)}" y2="${(py(122)+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUp11)"/>
        <defs><marker id="aUp11" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${px(13).toFixed(1)}" y="${(py(122)+30).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Pullback con volumen bajo = sin vendedores → entrada de menor riesgo
        </text>
    </svg>`;
}

function volume_candle_reading() {
    const W=680, H=230;
    const types=[
        {label:'Vela alcista\n+ vol. alto',  yH:40,yO:160,yC:65, yL:175, bull:true,  vol:0.9, color:C.accent, desc:'Compradores\nagresivos'},
        {label:'Vela pequeña\n+ vol. alto',  yH:45,yO:120,yC:95, yL:175, bull:true,  vol:0.9, color:C.yellow, desc:'Indecisión\nequilibrio'},
        {label:'Vela bajista\n+ vol. muy alto',yH:40,yO:65,yC:155,yL:175, bull:false, vol:1.0, color:C.red,    desc:'Capitulación\n/ distribución'},
        {label:'Vela alcista\n+ vol. bajo',   yH:45,yO:145,yC:80,yL:170, bull:true,  vol:0.3, color:C.muted,  desc:'Subida\nsin convicción'},
    ];

    const panelW=(W-60)/4;
    let content='';
    types.forEach(({label,yH,yO,yC,yL,bull,vol,color,desc},i)=>{
        const x0=8+i*(panelW+5);
        const cx=x0+panelW/2;
        const lines=label.split('\n'), descLines=desc.split('\n');
        lines.forEach((l,li)=>{ content+=`<text x="${cx}" y="${12+li*12}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=candleRow(cx,yO,yC,yH,yL,bull,22).replace('stroke-width="1.5"','stroke-width="2"');
        // Volume bar
        const bh=vol*40;
        const vY0=180;
        content+=`<rect x="${cx-12}" y="${vY0-bh}" width="24" height="${bh}" fill="${color}" opacity="${0.3+vol*0.5}" rx="2"/>
        <line x1="${x0}" y1="${vY0}" x2="${x0+panelW}" y2="${vY0}" stroke="${C.border}" stroke-width="1"/>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${cx}" y="${vY0+14+li*11}" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        ${[1,2,3].map(i=>`<line x1="${8+i*(panelW+5)-3}" y1="5" x2="${8+i*(panelW+5)-3}" y2="${H-15}" stroke="${C.border}" stroke-width="1"/>`).join('')}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Vela + Volumen = la historia completa de cada sesión
        </text>
    </svg>`;
}

function healthy_pullback_volume() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,104,108,113,118,124,130,136,132,128,124,120,122,126,132,138,144];
    const vols=  [0.8,1.0,1.2,1.4,1.6,1.8,2.0,2.2,0.7,0.5,0.4,0.3,0.5,1.0,1.4,1.8,2.0];
    const mn=92, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=vols[i]*volH;
        const isPullback=i>=8&&i<=11;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="${isPullback?0.35:0.55}" rx="1"/>`;
    });

    // EMA21
    let ema=prices[0],emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k);emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.8"/>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${px(9.5).toFixed(1)}" y="${(y0+13).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">vol. bajo ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retroceso saludable: precio baja en EMA21, volumen cae significativamente
        </text>
    </svg>`;
}

function pullback_volume_measure() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,106,112,118,124,130,136,142,137,132,127,122,120,125,132,140];
    const vols=  [0.8,1.0,1.2,1.4,1.6,1.8,2.0,2.4,0.8,0.6,0.5,0.4,0.3,0.7,1.2,1.8];
    const mn=112, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,12);
        const bh=vols[i]*volH;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="0.5" rx="1"/>`;
    });

    const avgVol=1.0*volH;
    const avgY=volY0+volH-avgVol;
    const lowZoneY=volY0+volH-0.7*volH;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <line x1="${x0}" y1="${avgY}" x2="${x0+w}" y2="${avgY}" stroke="${C.muted}" stroke-width="1.5" stroke-dasharray="5,3"/>
        <line x1="${x0}" y1="${lowZoneY}" x2="${x0+w}" y2="${lowZoneY}" stroke="${C.cyan}" stroke-width="1" stroke-dasharray="4,4" opacity="0.6"/>
        <text x="${x0+w+4}" y="${avgY+4}" fill="${C.muted}" font-size="9" font-family="monospace">Promedio</text>
        <text x="${x0+w+4}" y="${lowZoneY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">70%</text>
        <rect x="${x0}" y="${lowZoneY}" width="${w}" height="${volY0-lowZoneY}" fill="${C.accent}" opacity="0.04"/>
        <text x="${px(10).toFixed(1)}" y="${(volY0-4).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">zona bajo vol.</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retroceso saludable: volumen bajo el 70% del promedio durante la corrección
        </text>
    </svg>`;
}

function deep_pullback_low_volume() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,108,116,124,132,140,148,140,132,124,116,110,114,120,128,136,144];
    const vols=  [0.8,1.0,1.3,1.5,1.8,2.1,2.4,0.6,0.4,0.3,0.3,0.2,0.5,0.9,1.3,1.7,2.0];
    const mn=92, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=vols[i]*volH;
        const isPullback=i>=7&&i<=11;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isPullback?C.yellow:bull?C.accent:C.red}" opacity="${isPullback?0.6:0.5}" rx="1"/>`;
    });

    // Fib 50% retracement
    const fib50Y=py(124);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${fib50Y}" x2="${x0+w}" y2="${fib50Y}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,4" opacity="0.6"/>
        <text x="${x0+4}" y="${(fib50Y-4).toFixed(1)}" fill="${C.yellow}" font-size="8" font-family="monospace">Fib 50%</text>
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${px(9).toFixed(1)}" y="${(volY0-4).toFixed(1)}" fill="${C.yellow}" font-size="8" font-family="monospace" text-anchor="middle">vol. mínimo</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Retroceso profundo (50%) pero volumen mínimo = sin vendedores reales
        </text>
    </svg>`;
}

function volume_context_trap() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    function panel(x0, prices, vols, title, color, goodMsg, badMsg) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>25+130-((v-mn)/range)*130;
        const volH=45, volY0=165;
        let out=`<text x="${x0+panelW/2}" y="15" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${title}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,10);
            const bh=vols[i]*volH;
            out+=`<rect x="${(cx-5).toFixed(1)}" y="${(volY0-bh).toFixed(1)}" width="10" height="${bh.toFixed(1)}" fill="${vols[i]>1?C.accent:C.muted}" opacity="${vols[i]>1?0.8:0.35}" rx="1"/>`;
        });
        out+=`<line x1="${x0}" y1="${volY0}" x2="${x0+panelW}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        <text x="${x0+panelW/2}" y="210" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${goodMsg}</text>`;
        return out;
    }

    const bullPrices=[100,102,104,103,106,104,108,110,114,118,122];
    const bullVols=  [0.5,0.4,0.5,0.4,0.5,0.4,1.8,2.0,1.6,1.8,2.2]; // low in retrace, high in impulse
    const bearPrices=[122,120,118,122,120,116,114,110,106,102,98];
    const bearVols=  [0.5,0.4,0.5,1.8,1.6,0.5,0.4,0.5,0.4,0.5,0.4]; // high in bounce, low in decline

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        ${panel(5, bullPrices, bullVols, '✓ Vol. bajo en corrección = alcista', C.accent, 'Vol. bajo = sin vendedores', '')}
        ${panel(panelW+30, bearPrices, bearVols, '✗ Vol. bajo en impulso = bajista', C.red, 'Vol. bajo = sin compradores', '')}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El mismo dato — volumen bajo — tiene significados opuestos según el contexto
        </text>
    </svg>`;
}

function climax_volume_definition() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[140,136,130,124,118,112,106,100,92,96,104,112,120,128,134];
    const vols=  [0.8,0.9,1.0,1.2,1.4,1.6,1.8,5.5,4.2,1.2,1.0,1.2,1.4,1.3,1.1];
    const mn=84, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=Math.min(vols[i]*volH, volH*1.1);
        const isClimax=i===7;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isClimax?C.red:C.muted}" opacity="${isClimax?0.95:0.4}" rx="1"/>`;
    });

    const climaxX=px(7), climaxY=py(100);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <circle cx="${climaxX}" cy="${climaxY}" r="10" fill="none" stroke="${C.red}" stroke-width="2.5"/>
        <text x="${climaxX}" y="${(climaxY+24).toFixed(1)}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">CLÍMAX</text>
        <text x="${climaxX}" y="${(climaxY+36).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">5.5x promedio</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Clímax bajista: volumen 5x+ en el punto de máximo pánico → suelo potencial
        </text>
    </svg>`;
}

function selling_climax() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[140,132,124,116,108,100,90,84,86,88,84,90,98,108,116,124];
    const vols=  [0.8,1.0,1.2,1.4,1.6,1.8,4.8,3.5,0.8,0.5,0.6,1.2,1.5,1.8,1.6,1.4];
    const mn=76, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=Math.min(vols[i]*volH*0.9, volH);
        const isClimax=i===6||i===7;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isClimax?C.red:bull?C.accent:C.muted}" opacity="${isClimax?0.9:0.45}" rx="1"/>`;
    });

    const climaxX=px(6.5), retestX=px(10);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <rect x="${(climaxX-20).toFixed(1)}" y="${(py(90)-8).toFixed(1)}" width="40" height="16" fill="${C.red}" opacity="0.1" stroke="${C.red}" stroke-width="1" rx="3"/>
        <text x="${climaxX.toFixed(1)}" y="${(py(90)+5).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">CLÍMAX</text>
        <circle cx="${retestX}" cy="${py(84)}" r="7" fill="none" stroke="${C.orange}" stroke-width="1.5"/>
        <text x="${retestX}" y="${(py(78)).toFixed(1)}" fill="${C.orange}" font-size="8" font-family="monospace" text-anchor="middle">RETEST\nbajo vol.</text>
        <line x1="${px(11).toFixed(1)}" y1="${(py(90)+16).toFixed(1)}" x2="${px(11).toFixed(1)}" y2="${(py(90)+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2" marker-end="url(#aUp12)"/>
        <defs><marker id="aUp12" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${px(11).toFixed(1)}" y="${(py(90)+30).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Clímax → Retest bajo vol. → Entrada cuando supera máximo del clímax
        </text>
    </svg>`;
}

function buying_climax() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,106,112,118,124,130,136,142,148,156,150,144,138,132,128,124];
    const vols=  [0.8,1.0,1.2,1.3,1.5,1.6,1.8,2.0,2.2,4.8,1.2,0.9,0.8,0.7,0.6,0.8];
    const mn=116, mx=164, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=Math.min(vols[i]*volH*0.9, volH);
        const isClimax=i===9;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isClimax?C.orange:bull?C.accent:C.red}" opacity="${isClimax?0.9:0.5}" rx="1"/>`;
    });

    const climaxX=px(9), climaxY=py(156);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <circle cx="${climaxX}" cy="${climaxY}" r="10" fill="none" stroke="${C.orange}" stroke-width="2.5"/>
        <text x="${climaxX}" y="${(climaxY-14).toFixed(1)}" fill="${C.orange}" font-size="10" font-family="monospace" text-anchor="middle">CLÍMAX</text>
        <text x="${climaxX}" y="${(climaxY-2).toFixed(1)}" fill="${C.orange}" font-size="8" font-family="monospace" text-anchor="middle">ALCISTA</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Clímax alcista = último gran impulso antes del techo → reducir exposición
        </text>
    </svg>`;
}

function climax_at_level() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[120,114,108,102,96,90,86,82,84,86,82,88,96,104,112,120];
    const vols=  [0.7,0.9,1.0,1.2,1.4,1.6,1.8,4.5,0.7,0.5,0.6,1.0,1.3,1.5,1.4,1.2];
    const mn=74, mx=128, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=Math.min(vols[i]*volH*0.9, volH);
        const isClimax=i===7;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isClimax?C.red:bull?C.accent:C.muted}" opacity="${isClimax?0.9:0.4}" rx="1"/>`;
    });

    const supY=py(82);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-5}" width="${w}" height="10" fill="${C.accent}" opacity="0.08"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <circle cx="${px(7).toFixed(1)}" cy="${py(82).toFixed(1)}" r="10" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(7).toFixed(1)}" y="${(py(75)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">CLÍMAX</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SOPORTE</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Clímax en soporte histórico = señal de suelo de máxima convicción
        </text>
    </svg>`;
}

// ─── GRÁFICO: Clímax apilados (dos clímax en secuencia) ──────────────────────
function climax_stacking() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[130,120,110,100,92,88,90,96,92,84,76,72,74,80,90,100];
    const vols=  [0.6,0.9,1.1,1.4,1.7,4.6,0.9,0.6,1.0,1.6,2.0,5.5,1.0,0.7,0.9,1.0];
    const mn=64, mx=136, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=Math.min(vols[i]*volH*0.85, volH);
        const isClimax = (i===5 || i===11);
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isClimax?C.red:bull?C.accent:C.muted}" opacity="${isClimax?0.9:0.4}" rx="1"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <circle cx="${px(5).toFixed(1)}" cy="${py(88).toFixed(1)}" r="9" fill="none" stroke="${C.orange}" stroke-width="2"/>
        <text x="${px(5).toFixed(1)}" y="${(py(80)).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">1er CLÍMAX</text>
        <circle cx="${px(11).toFixed(1)}" cy="${py(72).toFixed(1)}" r="9" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(11).toFixed(1)}" y="${(py(64)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">2º CLÍMAX (mayor)</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Comprar el 1er clímax fue prematuro — el 2º clímax rompe su mínimo con más volumen
        </text>
    </svg>`;
}

function weak_participation() {
    const W=680, H=240;
    const vols=  [2.0,1.8,1.6,1.5,1.4,1.2,1.1,1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.4,0.3];
    const mn=92, mx=168, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=vols[i]*volH;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${C.accent}" opacity="${0.2+vols[i]*0.3}" rx="1"/>`;
    });

    // Declining volume trend
    const volTrendPath=prices.map((_,i)=>{
        if(!i) return null;
        const cx=px(i), bh=vols[i]*volH;
        return `${i===1?'M':'L'} ${cx.toFixed(1)} ${(volY0+volH-bh).toFixed(1)}`;
    }).filter(Boolean).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <path d="${volTrendPath}" fill="none" stroke="${C.red}" stroke-width="2" stroke-dasharray="6,3" opacity="0.7"/>
        <text x="${x0+w-80}" y="${(volY0+volH-0.3*volH-4).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace">vol. ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Precio sube pero volumen cae sistemáticamente = participación débil
        </text>
    </svg>`;
}

function weak_participation_signals() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    // Impulsos con poco vol, correcciones con más vol
    const prices=[100,104,102,107,104,109,106,111,108,113,110,115,112,117,114,119];
    const vols=  [0.4,0.6,0.8,0.5,0.9,0.5,0.8,0.5,0.9,0.5,0.8,0.5,0.9,0.5,0.8,0.5];
    const mn=92, mx=127, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,12);
        const bh=vols[i]*volH;
        // Vol alto en días bajistas = señal negativa
        const badVol=!bull&&vols[i]>0.7;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${badVol?C.red:C.accent}" opacity="${badVol?0.7:0.35}" rx="1"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <rect x="${x0+w-110}" y="${y0+5}" width="100" height="26" fill="${C.bg}" opacity="0.9" rx="3"/>
        <rect x="${x0+w-105}" y="${y0+9}" width="8" height="8" fill="${C.red}" rx="1" opacity="0.7"/>
        <text x="${x0+w-93}" y="${y0+17}" fill="${C.red}" font-size="9" font-family="monospace">Vol. días bajistas</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ⚠ Vol. alto en días bajistas = presión vendedora activa
        </text>
    </svg>`;
}

function volume_price_divergence() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,106,112,118,124,130,136,142,148,154,158,162];
    const vols=  [2.0,1.8,1.6,1.5,1.3,1.2,1.0,0.8,0.7,0.6,0.5,0.4];
    const mn=92, mx=170, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,16);
        const bh=vols[i]*volH;
        volBars+=`<rect x="${(cx-8).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="16" height="${bh.toFixed(1)}" fill="${C.accent}" opacity="${0.2+vols[i]*0.35}" rx="1"/>`;
    });

    // Price line (upward)
    const priceTrendPath=`M ${px(1)} ${py(106)} L ${px(11)} ${py(162)}`;
    // Volume line (downward)
    const volTrendPath=`M ${px(1)} ${(volY0+volH-vols[1]*volH).toFixed(1)} L ${px(11)} ${(volY0+volH-vols[11]*volH).toFixed(1)}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${priceTrendPath}" fill="none" stroke="${C.accent}" stroke-width="2" stroke-dasharray="6,3" opacity="0.5"/>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <path d="${volTrendPath}" fill="none" stroke="${C.red}" stroke-width="2" stroke-dasharray="6,3"/>
        <text x="${x0+w/2}" y="${py(165)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Precio ↑</text>
        <text x="${x0+w/2}" y="${(volY0+volH-0.6*volH-4).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Volumen ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">
            ⚠ DIVERGENCIA: Precio marca máximos, volumen marca mínimos → techo potencial
        </text>
    </svg>`;
}

function participation_recovery() {
    const W=680, H=240;
    const x0=40, y0=15, w=W-80, h=150;
    const volY0=y0+h+15, volH=55;
    const prices=[100,103,101,104,102,105,103,106,104,107,105,108,116,126,134,142];
    const vols=  [0.4,0.3,0.4,0.3,0.4,0.3,0.4,0.3,0.4,0.3,0.4,0.3,3.8,2.5,2.0,1.8];
    const mn=92, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='', volBars='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
        const bh=Math.min(vols[i]*volH*0.9, volH);
        const isExplosion=i>=12&&i<=13;
        volBars+=`<rect x="${(cx-6).toFixed(1)}" y="${(volY0+volH-bh).toFixed(1)}" width="12" height="${bh.toFixed(1)}" fill="${isExplosion?C.accent:C.muted}" opacity="${isExplosion?0.9:0.3}" rx="1"/>`;
    });

    const expX=px(12);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${expX}" y1="${y0}" x2="${expX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.6"/>
        <text x="${(expX+4).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">REGRESA el vol.</text>
        <line x1="${x0}" y1="${volY0}" x2="${x0+w}" y2="${volY0}" stroke="${C.border}" stroke-width="1"/>
        ${volBars}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Base de bajo vol. → explosión de volumen = institucionales entrando → aceleración
        </text>
    </svg>`;
}

// ─── MÓDULO 9: PATRONES DE GRÁFICO ───────────────────────────────────────────

function ascending_triangle_anatomy() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,106,102,110,104,114,106,116,108,118,110,120,112,122,114,124,122,130];
    const mn=92, mx=138, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(122);
    // Rising lows trendline
    const lows=[[1,100],[3,102],[5,104],[7,106],[9,108],[11,110],[13,112],[15,114]];
    const llPath=lows.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="2" stroke-dasharray="8,4"/>
        <path d="${llPath} L ${px(17).toFixed(1)} ${py(116).toFixed(1)}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        ${candles}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="10" font-family="monospace">RESISTENCIA</text>
        <text x="${px(14).toFixed(1)}" y="${(py(112)+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">Mínimos crecientes →</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Resistencia plana + mínimos crecientes = presión compradora acumulada
        </text>
    </svg>`;
}

function ascending_triangle_valid() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,102,112,105,116,108,118,110,120,112,120,114,122,116,122,118,128,136];
    const mn=92, mx=144, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,10);
    });

    const resY=py(122);
    const lows=[[1,100],[3,102],[5,105],[7,108],[9,110],[11,112],[13,114],[15,116]];
    const llPath=lows.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // Touch markers on resistance
    const resTouches=[2,5,7,9,11,13];
    let rMarks='';
    resTouches.forEach(i=>{ rMarks+=`<circle cx="${px(i).toFixed(1)}" cy="${resY}" r="4" fill="none" stroke="${C.red}" stroke-width="1.5"/>`; });

    const voluX=px(17), voluY=py(130);
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <path d="${llPath}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        ${candles}${rMarks}
        <circle cx="${voluX}" cy="${voluY}" r="8" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${voluX}" y="${(voluY-12).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            6 toques en resistencia (círculos) + mínimos crecientes = triángulo válido
        </text>
    </svg>`;
}

function ascending_triangle_breakout() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,102,114,106,118,110,120,112,122,114,122,116,128,138,148];
    const mn=92, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(122);
    // Height of triangle = 122-100 = 22, target = 122+22 = 144
    const targetY=py(144);
    const brkX=px(12);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        <line x1="${(brkX+15).toFixed(1)}" y1="${resY}" x2="${(brkX+15).toFixed(1)}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1" opacity="0.4"/>
        ${candles}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">OBJETIVO</text>
        <text x="${(brkX+19).toFixed(1)}" y="${((resY+targetY)/2+4).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace">altura</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Objetivo = ruptura + altura del triángulo (resistencia − primer mínimo)
        </text>
    </svg>`;
}

function ascending_triangle_context() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    function panel(x0, prices, label, color) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>20+175-((v-mn)/range)*175;
        let out=`<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,10);
        });
        // Resistance line
        const maxP=Math.max(...prices.slice(Math.floor(n/3)));
        const resY=py(maxP*0.92);
        out+=`<line x1="${x0+panelW*0.3}" y1="${resY}" x2="${x0+panelW}" y2="${resY}" stroke="${C.red}" stroke-width="1.2" stroke-dasharray="5,3" opacity="0.6"/>`;
        return out;
    }

    const cont=[90,96,92,98,94,100,96,102,98,104,100,106,102,108,116,126];
    const rev= [120,112,104,108,100,106,98,104,100,106,102,108,104,110,118,128];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.cyan}" opacity="0.03" rx="5"/>
        ${panel(5, cont, 'EN TENDENCIA ALCISTA (70-80%)', C.accent)}
        ${panel(panelW+30, rev, 'TRAS CAÍDA — REVERSIÓN (50-60%)', C.cyan)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El contexto determina la probabilidad — siempre opera a favor de la tendencia mayor
        </text>
    </svg>`;
}

function descending_triangle_anatomy() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[140,132,136,126,132,122,128,118,124,114,120,110,116,106,112,100];
    const mn=92, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const supY=py(100);
    const highs=[[1,140],[3,132],[5,128],[7,124],[9,120],[11,116],[13,112]];
    const hhPath=highs.map(([i,v],pi)=>`${pi===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="2" stroke-dasharray="8,4"/>
        <path d="${hhPath} L ${px(15).toFixed(1)} ${py(108).toFixed(1)}" fill="none" stroke="${C.red}" stroke-width="2"/>
        ${candles}
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="10" font-family="monospace">SOPORTE</text>
        <text x="${px(6).toFixed(1)}" y="${(py(132)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace">Máximos decrecientes ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Soporte plano + máximos decrecientes = presión vendedora acumulada
        </text>
    </svg>`;
}

function descending_triangle_breakdown() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[140,130,136,122,130,116,124,110,118,104,112,100,106,100,104,88,76];
    const mn=68, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const supY=py(100);
    const brkX=px(13);
    // Target = 100 - (140-100) = 60
    const targetY=py(60);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        ${candles}
        <circle cx="${px(13).toFixed(1)}" cy="${py(100)}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${px(13).toFixed(1)}" y="${(py(93)).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SUP</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">OBJETIVO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura bajista del soporte → stops en cascada → objetivo = soporte − altura
        </text>
    </svg>`;
}

function descending_triangle_trend() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Bajista, triángulo, bajista
    const prices=[150,140,130,120,126,116,122,112,118,108,114,104,110,100,106,100,104,90,78];
    const mn=70, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,10);
    });

    const supY=py(100);
    const triX1=px(4), triX2=px(13);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${triX1.toFixed(1)}" y="${y0}" width="${(triX2-triX1).toFixed(1)}" height="${h}" fill="${C.red}" opacity="0.04"/>
        <line x1="${triX1}" y1="${supY}" x2="${triX2}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        ${candles}
        <text x="${((triX1+triX2)/2).toFixed(1)}" y="${(y0+13).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">TRIÁNGULO DESC.</text>
        <line x1="${triX2}" y1="${y0}" x2="${triX2}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        <text x="${(triX2+6).toFixed(1)}" y="${(y0+13).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace">CONTINÚA ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Triángulo desc. en tendencia bajista = patrón de continuación de alta probabilidad
        </text>
    </svg>`;
}

function descending_triangle_management() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[138,128,134,120,128,114,120,108,114,100,106,100,104,88,94,88,80];
    const mn=72, mx=146, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const supY=py(100), brkX=px(11);
    const retestX=px(13), retestY=py(100);
    const stopY=py(106);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.orange}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        ${candles}
        <circle cx="${retestX}" cy="${retestY}" r="8" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${retestX}" y="${(retestY-12).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">RETEST</text>
        <line x1="${retestX}" y1="${(retestY-5).toFixed(1)}" x2="${retestX}" y2="${(retestY-18).toFixed(1)}" stroke="${C.red}" stroke-width="2" marker-end="url(#aDnT)"/>
        <defs><marker id="aDnT" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 0 L 2.5 5 L 5 0 z" fill="${C.red}"/></marker></defs>
        <text x="${retestX}" y="${(retestY-26).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">2º CORTO</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.orange}" font-size="9" font-family="monospace">SUP→RES</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura → Retest del soporte roto (ahora resistencia) → 2ª entrada en corto
        </text>
    </svg>`;
}

function rectangle_formation() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,114,122,116,124,118,122,116,124,118,122,116,124,118,122,116,124,130,140];
    const mn=106, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,10);
    });

    const resY=py(124), supY=py(114);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY}" width="${(px(16)-x0).toFixed(1)}" height="${(supY-resY).toFixed(1)}" fill="${C.yellow}" opacity="0.05"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${supY}" x2="${px(16)}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="9" font-family="monospace">RESISTENCIA</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SOPORTE</text>
        <line x1="${x0+10}" y1="${resY}" x2="${x0+10}" y2="${supY}" stroke="${C.yellow}" stroke-width="1" opacity="0.5"/>
        <text x="${(x0+16).toFixed(1)}" y="${((resY+supY)/2+4).toFixed(1)}" fill="${C.yellow}" font-size="8" font-family="monospace">amplitud</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Rectángulo: precio oscila entre dos niveles horizontales paralelos
        </text>
    </svg>`;
}

function rectangle_trading() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,114,122,116,124,118,122,116,124,118,122,116,124,118,122,116];
    const mn=106, mx=132, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,13);
    });

    const resY=py(124), supY=py(114);
    // Buy at support arrows
    const buys=[1,5,9,13];
    const sells=[2,6,10,14];
    let arrows='';
    buys.forEach(i=>{ arrows+=`<line x1="${px(i)}" y1="${(supY+16).toFixed(1)}" x2="${px(i)}" y2="${(supY+4).toFixed(1)}" stroke="${C.accent}" stroke-width="2" marker-end="url(#aUpR)"/>`; });
    sells.forEach(i=>{ arrows+=`<line x1="${px(i)}" y1="${(resY-4).toFixed(1)}" x2="${px(i)}" y2="${(resY-16).toFixed(1)}" stroke="${C.red}" stroke-width="2" marker-end="url(#aDnR)"/>`; });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <marker id="aUpR" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 5 L 2.5 0 L 5 5 z" fill="${C.accent}"/></marker>
            <marker id="aDnR" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 0 L 2.5 5 L 5 0 z" fill="${C.red}"/></marker>
        </defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY}" width="${w}" height="${(supY-resY).toFixed(1)}" fill="${C.yellow}" opacity="0.04"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="7,4"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4"/>
        ${candles}${arrows}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="9" font-family="monospace">VENDER ↓</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">COMPRAR ↑</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Comprar en soporte ↑ — Vender en resistencia ↓ — Solo en rectángulos amplios
        </text>
    </svg>`;
}

function rectangle_breakout() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[120,114,122,116,124,118,122,116,124,118,122,116,126,134,142,150];
    const mn=106, mx=158, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const resY=py(124), supY=py(114);
    // Amplitud = 124-114 = 10, target = 124+10 = 134
    const targetY=py(134), brkX=px(11);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${supY}" x2="${brkX}" y2="${supY}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="5,4" opacity="0.4"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        ${candles}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">OBJETIVO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura + amplitud del rango = objetivo mínimo de precio
        </text>
    </svg>`;
}

function rectangle_longterm() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Años de consolidación luego ruptura
    const prices=[120,112,124,110,126,112,122,108,124,112,122,108,124,110,126,112,
                  122,116,128,122,134,140,150,162,174,186];
    const mn=100, mx=194, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,7);
    });

    const resY=py(127), supY=py(107);
    const brkX=px(16);
    const targetY=py(147);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${resY}" width="${(brkX-x0).toFixed(1)}" height="${(supY-resY).toFixed(1)}" fill="${C.yellow}" opacity="0.05"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${supY}" x2="${brkX}" y2="${supY}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="5,4" opacity="0.4"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.6"/>
        ${candles}
        <text x="${(x0+brkX)/2}" y="${(y0+14).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">AÑOS DE CONSOLIDACIÓN</text>
        <text x="${(brkX+8).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA →</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.accent}" font-size="9" font-family="monospace">RUPTURA</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">OBJETIVO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Rectángulo de largo plazo roto = movimiento potente equivalente a la amplitud
        </text>
    </svg>`;
}

function flag_anatomy() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Pole (fast up) + flag (small pullback channel) + continuation
    const prices=[100,102,104,108,112,118,124,132,140,136,132,129,126,124,122,126,132,140,148,156];
    const mn=92, mx=164, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    // Flag channel lines
    const flagTopPath=`M ${px(8).toFixed(1)} ${py(140).toFixed(1)} L ${px(14).toFixed(1)} ${py(124).toFixed(1)}`;
    const flagBotPath=`M ${px(8).toFixed(1)} ${py(132).toFixed(1)} L ${px(14).toFixed(1)} ${py(118).toFixed(1)}`;

    // Pole bracket
    const poleX=x0+8;
    const labels=[
        {x:poleX-2, y1:py(100), y2:py(140), label:'ASTA', color:C.cyan},
    ];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${flagTopPath}" fill="none" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>
        <path d="${flagBotPath}" fill="none" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>
        <line x1="${(poleX).toFixed(1)}" y1="${py(100).toFixed(1)}" x2="${(poleX).toFixed(1)}" y2="${py(140).toFixed(1)}" stroke="${C.cyan}" stroke-width="1.5" opacity="0.5"/>
        <line x1="${(poleX-6).toFixed(1)}" y1="${py(100).toFixed(1)}" x2="${(poleX+6).toFixed(1)}" y2="${py(100).toFixed(1)}" stroke="${C.cyan}" stroke-width="1.5" opacity="0.5"/>
        <line x1="${(poleX-6).toFixed(1)}" y1="${py(140).toFixed(1)}" x2="${(poleX+6).toFixed(1)}" y2="${py(140).toFixed(1)}" stroke="${C.cyan}" stroke-width="1.5" opacity="0.5"/>
        <text x="${(poleX-10).toFixed(1)}" y="${((py(100)+py(140))/2+4).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="end">ASTA</text>
        <text x="${px(11).toFixed(1)}" y="${(py(130)-8).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">BANDERA</text>
        <text x="${px(17).toFixed(1)}" y="${(py(145)).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">CONT.</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            ASTA (impulso rápido) + BANDERA (corrección canal) + Continuación
        </text>
    </svg>`;
}

function flag_quality() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    function panel(x0, prices, label, color, isGood) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>20+175-((v-mn)/range)*175;
        let out=`<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,10);
        });
        return out;
    }

    const good=[100,104,108,114,120,128,136,144,140,136,133,130,128,132,138,146,154];
    const bad= [100,104,108,114,120,128,136,144,136,128,120,112,108,104,100,108,118];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        ${panel(5, good, '✓ BANDERA VÁLIDA (< 38% retroceso)', C.accent, true)}
        ${panel(panelW+30, bad, '✗ NO ES BANDERA (> 61.8% retroceso)', C.red, false)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Bandera válida: retroceso < 38-50% del asta — con volumen decreciente
        </text>
    </svg>`;
}

function flag_entry_target() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,110,116,124,132,140,136,132,128,124,122,126,134,142,150,158];
    const mn=92, mx=166, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    // Pole: 100→140 = 40pts, Flag: 140→122 = 18pts, Breakout at 122, Target = 122+40 = 162
    const poleH=py(100)-py(140); // in SVG coords
    const brkY=py(122), brkX=px(11);
    const targetY=py(162);
    const stopY=py(118);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${brkY}" x2="${x0+w}" y2="${brkY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.6"/>
        <line x1="${x0}" y1="${targetY}" x2="${x0+w}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,5" opacity="0.4"/>
        <line x1="${brkX}" y1="${y0}" x2="${brkX}" y2="${y0+h}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        ${candles}
        <line x1="${(brkX+15).toFixed(1)}" y1="${brkY}" x2="${(brkX+15).toFixed(1)}" y2="${targetY}" stroke="${C.yellow}" stroke-width="1" opacity="0.4"/>
        <text x="${(brkX+19).toFixed(1)}" y="${((brkY+targetY)/2+4).toFixed(1)}" fill="${C.yellow}" font-size="8" font-family="monospace">= asta</text>
        <text x="${x0+w+4}" y="${brkY+4}" fill="${C.accent}" font-size="9" font-family="monospace">ENTRADA</text>
        <text x="${x0+w+4}" y="${targetY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">OBJETIVO</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Objetivo = punto de ruptura + longitud del asta
        </text>
    </svg>`;
}

function bear_flag() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Bear pole (fast drop) + flag (small up channel) + drop
    const prices=[160,156,150,144,136,128,120,112,116,120,124,122,118,114,110,104,96,88];
    const mn=80, mx=168, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    // Bear flag channel (slightly up)
    const flagTopPath=`M ${px(7).toFixed(1)} ${py(112).toFixed(1)} L ${px(13).toFixed(1)} ${py(124).toFixed(1)}`;
    const flagBotPath=`M ${px(7).toFixed(1)} ${py(104).toFixed(1)} L ${px(13).toFixed(1)} ${py(116).toFixed(1)}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${flagTopPath}" fill="none" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>
        <path d="${flagBotPath}" fill="none" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>
        <text x="${px(3).toFixed(1)}" y="${(py(136)).toFixed(1)}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">ASTA ↓</text>
        <text x="${px(10).toFixed(1)}" y="${(py(128)).toFixed(1)}" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="middle">BANDERA ↗</text>
        <text x="${px(16).toFixed(1)}" y="${(py(102)).toFixed(1)}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">CAÍDA ↓</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Bandera bajista: asta bajista + canal ligeramente alcista → trampa de compradores
        </text>
    </svg>`;
}

// ─── MÓDULO 10: ALINEACIÓN MULTI-TEMPORALIDAD ────────────────────────────────

function monthly_bias_definition() {
    const W=680, H=220;
    const items=[
        {label:'SESGO\nALCISTA',icon:'📈',color:C.accent,desc:'HH+HL en mensual\nPrecio sobre MA10\nBuscar longs'},
        {label:'SESGO\nBAJISTA',icon:'📉',color:C.red,desc:'LH+LL en mensual\nPrecio bajo MA10\nCash o cortos'},
        {label:'SESGO\nNEUTRAL',icon:'↔️',color:C.yellow,desc:'Sin estructura clara\nPrecio en MA10\nReducir tamaño'},
    ];
    const bw=160, gap=50, startX=55;
    let content='';
    items.forEach(({label,icon,color,desc},i)=>{
        const x=startX+i*(bw+gap);
        const lines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="30" width="${bw}" height="130" fill="${color}" opacity="0.07" rx="8" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="68" font-size="24" text-anchor="middle">${icon}</text>`;
        lines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${88+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${126+li*12}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El sesgo mensual filtra qué tipo de operaciones son válidas esa semana
        </text>
    </svg>`;
}

function monthly_bias_how() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,112,104,124,114,136,124,148,136,144,130,138,122,130,116,124,130,138,146];
    const mn=88, mx=156, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    // MA10
    const ma10=prices.map((_,i)=>i<9?null:prices.slice(i-9,i+1).reduce((a,b)=>a+b)/10);
    const maPath=ma10.map((v,i)=>v===null?null:`${ma10[i-1]===null?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).filter(Boolean).join(' ');

    // Labels
    const peaks=[[2,112],[4,124],[6,136],[8,148]];
    const lows= [[1,96],[3,104],[5,114],[7,124]];
    let marks='';
    peaks.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.accent}"/>`; });
    lows.forEach(([i,v])=>{ marks+=`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.cyan}"/>`; });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.orange}" stroke-width="2.5" opacity="0.9"/>
        ${marks}
        <rect x="${x0+w-165}" y="${y0+5}" width="155" height="38" fill="${C.bg}" opacity="0.9" rx="3"/>
        <circle cx="${x0+w-155}" cy="${y0+16}" r="4" fill="${C.accent}"/>
        <text x="${x0+w-147}" y="${y0+20}" fill="${C.accent}" font-size="9" font-family="monospace">HH — Máximos crecientes</text>
        <circle cx="${x0+w-155}" cy="${y0+32}" r="4" fill="${C.cyan}"/>
        <text x="${x0+w-147}" y="${y0+36}" fill="${C.cyan}" font-size="9" font-family="monospace">HL — Mínimos crecientes</text>
        <text x="${x0+w+4}" y="${py(ma10.filter(Boolean).slice(-1)[0])+4}" fill="${C.orange}" font-size="9" font-family="monospace">MA10</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Sesgo alcista: HH+HL confirmados + precio sobre MA10 mensual
        </text>
    </svg>`;
}

function monthly_bias_change() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,96,114,106,126,116,136,124,144,130,138,122,130,114,118,106,110,98,102,92];
    const mn=84, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const ma10=prices.map((_,i)=>i<9?null:prices.slice(i-9,i+1).reduce((a,b)=>a+b)/10);
    const maPath=ma10.map((v,i)=>v===null?null:`${ma10[i-1]===null?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).filter(Boolean).join(' ');

    // Change signals
    const lhX=px(10), lhY=py(138);
    const llX=px(13), llY=py(114);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.8"/>
        <circle cx="${lhX}" cy="${lhY}" r="9" fill="none" stroke="${C.orange}" stroke-width="2"/>
        <text x="${lhX}" y="${(lhY-13).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">①1er LH</text>
        <circle cx="${llX}" cy="${llY}" r="9" fill="none" stroke="${C.red}" stroke-width="2"/>
        <text x="${llX}" y="${(llY+22).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">②1er LL</text>
        <line x1="${lhX}" y1="${y0}" x2="${lhX}" y2="${y0+h}" stroke="${C.orange}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        <line x1="${llX}" y1="${y0}" x2="${llX}" y2="${y0+h}" stroke="${C.red}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cambio de sesgo: ①1er LH (precaución) → ②1er LL (sesgo bajista confirmado)
        </text>
    </svg>`;
}

function monthly_bias_sectors() {
    const W=680, H=220;
    const sectors=[
        {name:'SPX',bias:'ALCISTA',color:C.accent,desc:'Tendencia alcista\nmensual confirmada'},
        {name:'TECH',bias:'ALCISTA',color:C.accent,desc:'Sector líder\nalineado con mercado'},
        {name:'ENERGY',bias:'BAJISTA',color:C.red,desc:'LH+LL mensuales\nNo operar longs'},
        {name:'NVDA',bias:'ALCISTA',color:C.accent,desc:'Individual alineado\n✓ OPERABLE'},
    ];
    const bw=130, gap=16, startX=20;
    let content='';
    sectors.forEach(({name,bias,color,desc},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        const isTarget=i===3;
        content+=`<rect x="${x}" y="25" width="${bw}" height="${H-50}" fill="${color}" opacity="${isTarget?0.12:0.06}" rx="6" stroke="${color}" stroke-width="${isTarget?2:1}"/>
        <text x="${x+bw/2}" y="52" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">${name}</text>
        <rect x="${x+20}" y="62" width="${bw-40}" height="18" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="75" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${bias}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${100+li*14}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Opera activos donde mercado + sector + individual apuntan en la misma dirección
        </text>
    </svg>`;
}

function weekly_structure_semaphore() {
    const W=680, H=220;
    const states=[
        {label:'VERDE\nOperar longs',color:C.accent,prices:[100,106,102,110,104,114,108,118,112,120,116,124]},
        {label:'AMARILLO\nEsperar',color:C.yellow,prices:[120,116,122,118,124,120,118,122,116,120,118,122]},
        {label:'ROJO\nNo longs',color:C.red,prices:[120,114,108,116,106,114,104,112,102,110,100,106]},
    ];
    const panelW=(W-60)/3;
    let content='';
    states.forEach(({label,color,prices},i)=>{
        const x0=10+i*(panelW+10);
        const mn=Math.min(...prices)-4, mx=Math.max(...prices)+4, range=mx-mn;
        const px=(j)=>x0+(j/(prices.length-1))*panelW;
        const py=(v)=>30+155-((v-mn)/range)*155;
        const lines=label.split('\n');
        content+=`<rect x="${x0}" y="18" width="${panelW}" height="${H-30}" fill="${color}" opacity="0.06" rx="5"/>`;
        lines.forEach((l,li)=>{ content+=`<text x="${x0+panelW/2}" y="${10+li*12}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        prices.forEach((p,j)=>{
            if(!j) return;
            const prev=prices[j-1],bull=p>prev,cx=px(j);
            content+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,12);
        });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        ${[1,2].map(i=>`<line x1="${10+i*(panelW+10)-5}" y1="5" x2="${10+i*(panelW+10)-5}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>`).join('')}
        <text x="${W/2}" y="${H-2}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El gráfico semanal actúa como semáforo para las decisiones de la semana
        </text>
    </svg>`;
}

function weekly_vs_monthly() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Mensual alcista (tendencia), semanal correctivo (retroceso dentro de alcista)
    const prices=[100,96,114,106,126,116,136,124,144,132,124,116,108,114,122,130,138];
    const mn=100, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,11);
    });

    const corrX1=px(9), corrX2=px(12);
    const emaArr=prices.map((_,i)=>i===0?prices[0]:null);
    let ema=prices[0]; const k=2/22;
    prices.slice(1).forEach((p,i)=>{ema=p*k+ema*(1-k); emaArr[i+1]=ema;});
    const emaPath=emaArr.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${corrX1.toFixed(1)}" y="${y0}" width="${(corrX2-corrX1).toFixed(1)}" height="${h}" fill="${C.yellow}" opacity="0.06"/>
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.8"/>
        <text x="${((corrX1+corrX2)/2).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">CORRECCIÓN\nSEMANAL</text>
        <text x="${px(4).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">MENSUAL ↑</text>
        <text x="${px(14).toFixed(1)}" y="${(y0+14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">REANUDA ↑</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mensual alcista + semanal correctivo = esperar, no entrar nuevos longs
        </text>
    </svg>`;
}

function weekly_pivot_point() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,108,116,124,130,136,142,136,128,120,114,110,114,120,128,136,144];
    const mn=102, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    let ema=prices[0],emas=[ema]; const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k);emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const pivotX=px(11), pivotY=py(110);
    const hlY=py(114);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${hlY}" x2="${x0+w}" y2="${hlY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.8"/>
        <circle cx="${pivotX}" cy="${pivotY}" r="10" fill="${C.accent}" opacity="0.15" stroke="${C.accent}" stroke-width="2"/>
        <line x1="${pivotX}" y1="${(pivotY+18).toFixed(1)}" x2="${pivotX}" y2="${(pivotY+5).toFixed(1)}" stroke="${C.accent}" stroke-width="2.5" marker-end="url(#aUpMTF)"/>
        <defs><marker id="aUpMTF" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M 0 6 L 3 0 L 6 6 z" fill="${C.accent}"/></marker></defs>
        <text x="${pivotX}" y="${(pivotY+34).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">PIVOT / ENTRADA</text>
        <text x="${x0+w+4}" y="${hlY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">Último HL</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Punto de giro semanal: corrección llega a EMA21 o HL anterior → vela de señal → entrada
        </text>
    </svg>`;
}

function weekly_zones_planning() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,108,113,118,124,130,136,142,148,152,148,142,136,130,124,120];
    const mn=112, mx=160, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const zones=[
        {v:152,label:'ZONA OFERTA',color:C.red},
        {v:142,label:'RESISTENCIA',color:C.orange},
        {v:130,label:'ZONA ENTRADA',color:C.accent},
        {v:120,label:'SOPORTE CLAVE',color:C.cyan},
    ];

    let zLines='';
    zones.forEach(({v,label,color})=>{
        const zy=py(v);
        zLines+=`<line x1="${x0}" y1="${zy}" x2="${x0+w}" y2="${zy}" stroke="${color}" stroke-width="1.2" stroke-dasharray="6,4" opacity="0.7"/>
        <text x="${x0+w+4}" y="${zy+4}" fill="${color}" font-size="9" font-family="monospace">${label}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${zLines}
        ${candles}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Plan semanal: 4 zonas marcadas — qué hacer si el precio llega a cada una
        </text>
    </svg>`;
}

function daily_setup_context() {
    const W=680, H=210;
    // Flow diagram: Monthly → Weekly → Daily → Entry
    const steps=[
        {label:'MENSUAL\nSESGO',value:'ALCISTA ✓',color:C.accent},
        {label:'SEMANAL\nESTRUCTURA',value:'ALCISTA ✓',color:C.accent},
        {label:'DIARIO\nSETUP',value:'RETROCESO\nEN EMA21',color:C.cyan},
        {label:'ENTRADA\nTRIGGER',value:'PIN BAR\nEN ZONA',color:C.yellow},
    ];
    const bw=130, gap=15, startX=15;
    let content='';
    steps.forEach(({label,value,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), valLines=value.split('\n');
        const isLast=i===steps.length-1;
        content+=`<rect x="${x}" y="20" width="${bw}" height="${H-40}" fill="${color}" opacity="${isLast?0.15:0.08}" rx="7" stroke="${color}" stroke-width="${isLast?2:1}"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${44+li*14}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle" opacity="0.8">${l}</text>`; });
        valLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${82+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        if(!isLast){ const ax=x+bw+gap/2; content+=`<text x="${ax}" y="${H/2+5}" fill="${C.muted}" font-size="18" text-anchor="middle">→</text>`; }
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cadena completa: sesgo → estructura → setup → trigger
        </text>
    </svg>`;
}

function daily_setup_types() {
    const W=680, H=230;
    const panelW=(W-60)/3;

    function panel(x0, prices, label, color, markIdx) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>25+175-((v-mn)/range)*175;
        let out=`<text x="${x0+panelW/2}" y="15" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,10);
        });
        if(markIdx!==null){
            const p=prices[markIdx], prev=prices[markIdx-1];
            const cx=px(markIdx);
            out+=`<circle cx="${cx}" cy="${py(Math.min(p,prev))}" r="7" fill="none" stroke="${color}" stroke-width="2"/>
            <line x1="${cx}" y1="${(py(Math.min(p,prev))+16).toFixed(1)}" x2="${cx}" y2="${(py(Math.min(p,prev))+4).toFixed(1)}" stroke="${color}" stroke-width="2" marker-end="url(#aUpD${markIdx})"/>
            <defs><marker id="aUpD${markIdx}" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 5 L 2.5 0 L 5 5 z" fill="${color}"/></marker></defs>`;
        }
        return out;
    }

    const retrace=[100,108,116,124,118,110,104,106,112,120,128,136];
    const breakout=[110,112,110,113,111,114,112,114,112,116,126,138];
    const reversal=[140,130,120,110,102,96,90,88,86,90,100,112];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(5, retrace, 'RETROCESO a EMA21', C.accent, 7)}
        ${panel(5+panelW+10, breakout, 'RUPTURA de base', C.cyan, 9)}
        ${panel(5+panelW*2+20, reversal, 'INVERSIÓN en soporte', C.yellow, 7)}
        ${[1,2].map(i=>`<line x1="${5+i*(panelW+10)-3}" y1="5" x2="${5+i*(panelW+10)-3}" y2="${H-15}" stroke="${C.border}" stroke-width="1"/>`).join('')}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Los tres setups diarios válidos en alineación multi-temporalidad
        </text>
    </svg>`;
}

function daily_setup_scaling() {
    const W=680, H=200;
    const scenarios=[
        {label:'M↑ + S↑ + D setup',size:100,color:C.accent,stop:'Amplio'},
        {label:'M↑ + S neutral + D',size:55,color:C.cyan,stop:'Normal'},
        {label:'M↑ + S↓ + rebote',size:28,color:C.yellow,stop:'Ajustado'},
        {label:'M neutral + S + D',size:38,color:C.muted,stop:'Normal'},
    ];
    const bw=140, gap=12, startX=15;
    let content='';
    scenarios.forEach(({label,size,color,stop},i)=>{
        const x=startX+i*(bw+gap);
        const barH=(size/100)*100;
        content+=`<rect x="${x}" y="${110-barH}" width="${bw}" height="${barH}" fill="${color}" opacity="${0.15+size/250}" rx="3"/>
        <text x="${x+bw/2}" y="${108-barH-4}" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${size}%</text>
        <text x="${x+bw/2}" y="124" fill="${color}" font-size="8" font-family="monospace" text-anchor="middle">${label}</text>
        <text x="${x+bw/2}" y="136" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">Stop: ${stop}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <line x1="15" y1="110" x2="${W-15}" y2="110" stroke="${C.border}" stroke-width="1"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mayor alineación = mayor tamaño de posición — menor alineación = menor tamaño
        </text>
    </svg>`;
}

function daily_intraday_timing() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Diario llega a zona, 4H muestra giro
    const prices=[130,124,118,112,108,104,108,106,104,102,106,110,116,124,132,140];
    const mn=94, mx=148, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.022),py(Math.min(prev,p)-(mx-mn)*0.018),bull,12);
    });

    const zoneY=py(104), pivotX=px(9), pivotY=py(102);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${zoneY-5}" width="${w}" height="10" fill="${C.accent}" opacity="0.08"/>
        <line x1="${x0}" y1="${zoneY}" x2="${x0+w}" y2="${zoneY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        ${candles}
        <circle cx="${pivotX}" cy="${pivotY}" r="9" fill="${C.accent}" opacity="0.15" stroke="${C.accent}" stroke-width="2"/>
        <text x="${pivotX}" y="${(pivotY+22).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">4H giro</text>
        <text x="${x0+w+4}" y="${zoneY+4}" fill="${C.accent}" font-size="9" font-family="monospace">ZONA D</text>
        <rect x="${x0+5}" y="${y0+5}" width="165" height="26" fill="${C.bg}" opacity="0.9" rx="3"/>
        <text x="${x0+10}" y="${y0+14}" fill="${C.cyan}" font-size="9" font-family="monospace">Análisis: Diario</text>
        <text x="${x0+10}" y="${y0+26}" fill="${C.accent}" font-size="9" font-family="monospace">Entrada: 4H (mejor precio)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Setup en diario → bajar a 4H para afinar la entrada y reducir el stop
        </text>
    </svg>`;
}

function trigger_definition() {
    const W=680, H=220;
    // Two panels: wait for trigger vs enter too early
    const panelW=(W-50)/2;

    function panel(x0, prices, label, color, hasTrigger) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>25+165-((v-mn)/range)*165;
        let out=`<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,12);
        });
        const entryI=hasTrigger?9:6;
        const ep=prices[entryI], prev=prices[entryI-1];
        const cx=px(entryI), cy=py(Math.min(ep,prev));
        out+=hasTrigger
            ? `<circle cx="${cx}" cy="${cy}" r="7" fill="none" stroke="${color}" stroke-width="2"/>
               <line x1="${cx}" y1="${(cy+15).toFixed(1)}" x2="${cx}" y2="${(cy+3).toFixed(1)}" stroke="${color}" stroke-width="2" marker-end="url(#aT${hasTrigger?1:0})"/>
               <text x="${cx}" y="${(cy+28).toFixed(1)}" fill="${color}" font-size="8" font-family="monospace" text-anchor="middle">CON TRIGGER</text>`
            : `<circle cx="${cx}" cy="${cy}" r="7" fill="none" stroke="${color}" stroke-width="2"/>
               <text x="${cx}" y="${(cy-12).toFixed(1)}" fill="${color}" font-size="8" font-family="monospace" text-anchor="middle">SIN TRIGGER</text>`;
        out+=`<defs><marker id="aT${hasTrigger?1:0}" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto"><path d="M 0 5 L 2.5 0 L 5 5 z" fill="${color}"/></marker></defs>`;
        return out;
    }

    const noTrig=[130,122,116,110,106,102,106,104,100,104,102,98,102,100,104,108];
    const withTrig=[130,122,116,110,106,102,106,104,100,102,108,116,124,132,140,148];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        ${panel(5, noTrig, '✗ Entrada sin trigger — el nivel falla', C.red, false)}
        ${panel(panelW+30, withTrig, '✓ Entrada con trigger — confirmado', C.accent, true)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El trigger protege capital cuando el nivel no aguanta
        </text>
    </svg>`;
}

function trigger_by_timeframe() {
    const W=680, H=220;
    const tfs=[
        {tf:'MENSUAL',trigger:'Semanal',color:C.red,y:35},
        {tf:'SEMANAL',trigger:'Diario',color:C.orange,y:75},
        {tf:'DIARIO',trigger:'4H',color:C.yellow,y:115},
        {tf:'4H',trigger:'1H',color:C.cyan,y:155},
        {tf:'1H',trigger:'15min',color:C.muted,y:185},
    ];
    let content='';
    tfs.forEach(({tf,trigger,color,y})=>{
        const barW=200;
        content+=`<rect x="30" y="${y-12}" width="${barW}" height="22" fill="${color}" opacity="0.12" rx="4"/>
        <text x="135" y="${y+4}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${tf}</text>
        <text x="${30+barW+12}" y="${y+4}" fill="${C.muted}" font-size="10" font-family="monospace">→  trigger en ${trigger}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="18" fill="${C.textDim}" font-size="11" font-family="monospace" text-anchor="middle">TF del Setup → TF del Trigger</text>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Siempre busca el trigger en el timeframe inmediatamente inferior al del setup
        </text>
    </svg>`;
}

function mtf_full_process() {
    const W=680, H=230;
    const steps=[
        {step:'DOM',label:'Sesgo mensual\n+ zonas semanal',color:C.accent},
        {step:'LUN',label:'¿Precio en zona\nde interés?',color:C.cyan},
        {step:'SETUP',label:'Setup diario\nconcurrente',color:C.yellow},
        {step:'4H/1H',label:'Esperar trigger\nespecífico',color:C.orange},
        {step:'ENTER',label:'Entrar con plan\ndefinido',color:C.accent},
    ];
    const bw=108, gap=10, startX=10;
    let content='';
    steps.forEach(({step,label,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="25" width="${bw}" height="${H-45}" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="1"/>
        <rect x="${x+15}" y="30" width="${bw-30}" height="22" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="45" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${step}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${72+li*14}" fill="${C.textDim}" font-size="8.5" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<steps.length-1){ const ax=x+bw+gap/2; content+=`<text x="${ax}" y="${H/2+5}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`; }
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El proceso completo — de mayor a menor timeframe, sin saltarse pasos
        </text>
    </svg>`;
}

function trigger_mistakes() {
    const W=680, H=220;
    const mistakes=[
        {icon:'⚡',label:'Anticipar',desc:'Entrar antes\ndel cierre de vela',color:C.red},
        {icon:'🔄',label:'Cambiar reglas',desc:'Inventar trigger\npara entrar igual',color:C.orange},
        {icon:'📊',label:'Sin volumen',desc:'Trigger sin\nvolumen mínimo',color:C.yellow},
        {icon:'😱',label:'FOMO',desc:'Entrar 3% tarde\ntras el trigger',color:C.red},
    ];
    const bw=140, gap=16, startX=15;
    let content='';
    mistakes.forEach(({icon,label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="20" width="${bw}" height="${H-40}" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="52" font-size="22" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="74" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${96+li*13}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="${H-25}" fill="${color}" font-size="22" text-anchor="middle">✗</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Los cuatro errores más comunes en el momento del trigger
        </text>
    </svg>`;
}

// ─── MÓDULO 11: PLANIFICACIÓN DEL TRADE ──────────────────────────────────────

function setup_definition() {
    const W=680, H=220;
    const items=[
        {label:'CORAZONADA',icon:'❓',color:'#f23645',desc:'"Parece que va\na subir"'},
        {label:'OPINIÓN',icon:'💭',color:'#ff9800',desc:'"Creo que el\nmercado está bien"'},
        {label:'SETUP',icon:'✓',color:C.accent,desc:'Condiciones X+Y+Z\n→ dirección A\n→ probabilidad P'},
    ];
    const bw=170, gap=35, startX=40;
    let content='';
    items.forEach(({label,icon,color,desc},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        const isSetup=i===2;
        content+=`<rect x="${x}" y="20" width="${bw}" height="${H-35}" fill="${color}" opacity="${isSetup?0.1:0.05}" rx="8" stroke="${color}" stroke-width="${isSetup?2:1}"/>
        <text x="${x+bw/2}" y="55" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="78" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${100+li*16}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<2) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="20" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Un setup es una hipótesis objetiva y repetible, no una opinión</text>
    </svg>`;
}

function setup_five_elements() {
    const W=680, H=220;
    const els=[
        {n:'1',label:'CONTEXTO',desc:'Sesgo M/S/D\nalineados',color:C.accent},
        {n:'2',label:'NIVEL',desc:'Precio exacto\ndel setup',color:C.cyan},
        {n:'3',label:'TRIGGER',desc:'Señal específica\nde entrada',color:C.yellow},
        {n:'4',label:'STOP',desc:'Invalidación\ndel análisis',color:C.red},
        {n:'5',label:'OBJETIVO',desc:'Target técnico\n+ R:R',color:C.orange},
    ];
    const bw=116, gap=8, startX=12;
    let content='';
    els.forEach(({n,label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="20" width="${bw}" height="${H-35}" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="1.5"/>
        <circle cx="${x+bw/2}" cy="48" r="16" fill="${color}" opacity="0.2" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="53" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>
        <text x="${x+bw/2}" y="80" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${100+li*14}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<4) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="12" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Los 5 elementos deben estar definidos ANTES de entrar. Si falta uno, no hay trade.</text>
    </svg>`;
}

function setup_types_context() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,108,104,100,104,108,112,108,104,108,112,116,120,124,128,132];
    const mn=92, mx=140, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{
        if(!i) return;
        const prev=prices[i-1],bull=p>prev,cx=px(i);
        candles+=candleRow(cx,py(prev),py(p),py(p+(mx-mn)*0.025),py(Math.min(prev,p)-(mx-mn)*0.02),bull,12);
    });

    let ema=prices[0],emas=[ema];const k=2/22;
    prices.slice(1).forEach(p=>{ema=p*k+ema*(1-k);emas.push(ema);});
    const emaPath=emas.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    // Setup markers
    const s1x=px(4), s1y=py(100); // retroceso
    const s2x=px(11), s2y=py(116); // ruptura

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${emaPath}" fill="none" stroke="${C.orange}" stroke-width="2" opacity="0.8"/>
        <circle cx="${s1x}" cy="${s1y}" r="8" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="2"/>
        <text x="${s1x}" y="${(s1y+22).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">RETROCESO</text>
        <circle cx="${s2x}" cy="${s2y}" r="8" fill="${C.accent}" opacity="0.2" stroke="${C.accent}" stroke-width="2"/>
        <text x="${s2x}" y="${(s2y-14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El mismo análisis técnico da setups de distinta calidad según el contexto mayor
        </text>
    </svg>`;
}

function setup_documentation() {
    const W=680, H=220;
    const fields=[
        ['TICKER','NVDA'],['FECHA','2026-06-16'],['SETUP','Retroceso EMA21'],
        ['CONTEXTO','M↑ S↑ D setup'],['ENTRADA','$875 cierre'],['TRIGGER','Pin bar alcista'],
        ['STOP','$845'],['OBJETIVO','$930'],['R:R','1:1.85'],['TAMAÑO','1% riesgo'],
    ];
    const cols=2, rows=Math.ceil(fields.length/cols);
    const colW=(W-40)/cols, rowH=(220-30)/rows;
    let content='';
    fields.forEach(([label,val],i)=>{
        const col=i%cols, row=Math.floor(i/cols);
        const x=20+col*colW, y=20+row*rowH;
        const isKey=label==='STOP'||label==='OBJETIVO'||label==='R:R';
        const valColor=label==='STOP'?C.red:label==='OBJETIVO'?C.accent:label==='R:R'?C.yellow:C.text;
        content+=`<rect x="${x}" y="${y}" width="${colW-6}" height="${rowH-4}" fill="${C.surface}" stroke="${C.border}" stroke-width="1" rx="3"/>
        <text x="${x+8}" y="${y+13}" fill="${C.muted}" font-size="9" font-family="monospace">${label}</text>
        <text x="${x+8}" y="${y+28}" fill="${valColor}" font-size="12" font-family="monospace" font-weight="500">${val}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Plantilla de trade completada antes de la entrada — 2 minutos que evitan errores costosos</text>
    </svg>`;
}

function rr_calculation() {
    const W=680, H=220;
    const x0=60, y0=15, w=W-120, h=175;
    const entryY=py_val(100,80,130,h,y0), stopY=py_val(92,80,130,h,y0), target1Y=py_val(116,80,130,h,y0), target2Y=py_val(124,80,130,h,y0);
    function py_val(v,mn,mx,h,y0){return y0+h-((v-mn)/(mx-mn))*h;}

    const prices=[88,90,92,96,100,98,96,94,96,100,104,108,112,116,120,124];
    const mn=82,mx=130,range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const entX=px(4);
    const entryPy=py(100), stopPy=py(92), t1Py=py(116), t2Py=py(124);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <line x1="${x0}" y1="${entryPy}" x2="${x0+w}" y2="${entryPy}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${stopPy}"  x2="${x0+w}" y2="${stopPy}"  stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${t1Py}"    x2="${x0+w}" y2="${t1Py}"    stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${t2Py}"    x2="${x0+w}" y2="${t2Py}"    stroke="${C.yellow}" stroke-width="1" stroke-dasharray="4,4"/>
        <line x1="${(x0+w+10).toFixed(1)}" y1="${entryPy}" x2="${(x0+w+10).toFixed(1)}" y2="${stopPy}" stroke="${C.red}" stroke-width="2"/>
        <line x1="${(x0+w+10).toFixed(1)}" y1="${entryPy}" x2="${(x0+w+10).toFixed(1)}" y2="${t1Py}" stroke="${C.accent}" stroke-width="2"/>
        <text x="${x0+w+4}" y="${entryPy+4}" fill="${C.cyan}" font-size="9" font-family="monospace">ENTRADA $100</text>
        <text x="${x0+w+4}" y="${stopPy+4}"  fill="${C.red}" font-size="9" font-family="monospace">STOP $92 (-1R)</text>
        <text x="${x0+w+4}" y="${t1Py+4}"    fill="${C.accent}" font-size="9" font-family="monospace">OBJ1 $116 (+2R)</text>
        <text x="${x0+w+4}" y="${t2Py+4}"    fill="${C.yellow}" font-size="9" font-family="monospace">OBJ2 $124 (+3R)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            R:R 1:2 mínimo → 1:3 ideal. Stop fijado por el mercado, objetivo por la estructura.
        </text>
    </svg>`;
}

function rr_minimum() {
    const W=680, H=220;
    // Bar chart: breakeven % needed for each R:R
    const ratios=[['1:1',55],['1:2',35],['1:3',27],['1:4',22],['1:5',18]];
    const bw=90, gap=20, startX=40, barMaxH=140, y0=15;
    let content='';
    ratios.forEach(([label,pct],i)=>{
        const x=startX+i*(bw+gap);
        const bh=(pct/60)*barMaxH;
        const color=pct>=50?C.red:pct>=35?C.orange:pct>=27?C.yellow:C.accent;
        content+=`<rect x="${x}" y="${y0+barMaxH-bh}" width="${bw}" height="${bh}" fill="${color}" opacity="0.3" rx="3"/>
        <text x="${x+bw/2}" y="${y0+barMaxH-bh-6}" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${pct}%</text>
        <text x="${x+bw/2}" y="${y0+barMaxH+15}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle">${label}</text>
        <text x="${x+bw/2}" y="${y0+barMaxH+28}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">aciertos mín.</text>`;
    });
    const midH=y0+(35/60)*barMaxH; // R:R 1:2 line
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <line x1="${startX-10}" y1="${y0+barMaxH-(50/60)*barMaxH}" x2="${W-20}" y2="${y0+barMaxH-(50/60)*barMaxH}" stroke="${C.red}" stroke-width="1" stroke-dasharray="5,4" opacity="0.5"/>
        <text x="${W-18}" y="${y0+barMaxH-(50/60)*barMaxH+4}" fill="${C.red}" font-size="9" font-family="monospace">50%</text>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            R:R 1:2 mínimo: solo necesitas acertar el 35% para ser rentable a largo plazo
        </text>
    </svg>`;
}

function rr_position_size() {
    const W=680, H=220;
    const steps=[
        {label:'Capital total',val:'$50,000',color:C.text},
        {label:'Riesgo 1%',val:'$500',color:C.orange},
        {label:'Stop distancia',val:'$5',color:C.red},
        {label:'Nº acciones',val:'100',color:C.yellow},
        {label:'Capital usado',val:'$10,000',color:C.cyan},
        {label:'Ganancia obj.',val:'$1,500',color:C.accent},
    ];
    const bw=90, gap=10, startX=20;
    let content='';
    steps.forEach(({label,val,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="25" width="${bw}" height="140" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="55" fill="${color}" font-size="16" font-family="monospace" text-anchor="middle" font-weight="bold">${val}</text>
        <text x="${x+bw/2}" y="90" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${label.split(' ').map((w,wi)=>`<tspan x="${x+bw/2}" dy="${wi>0?'12':'0'}">${w}</tspan>`).join('')}</text>`;
        if(i<steps.length-1) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Riesgo fijo ($) ÷ Distancia al stop = Número de acciones. Siempre así.
        </text>
    </svg>`;
}

function rr_alignment() {
    const W=680, H=220;
    const scenarios=[
        {label:'Triple\nalineación',tech:70,rr:'1:2',ev:'+1.10R',color:C.accent},
        {label:'Doble\nalineación',tech:60,rr:'1:2.5',ev:'+0.90R',color:C.cyan},
        {label:'Simple\nalineación',tech:50,rr:'1:3',ev:'+0.75R',color:C.yellow},
        {label:'Sin\nalineación',tech:40,rr:'1:4',ev:'+0.60R',color:C.muted},
    ];
    const bw=140, gap=12, startX=15;
    let content='';
    scenarios.forEach(({label,tech,rr,ev,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        const bh=(tech/100)*100;
        content+=`<rect x="${x}" y="20" width="${bw}" height="175" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${36+li*14}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="78" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Prob. éxito</text>
        <text x="${x+bw/2}" y="92" fill="${color}" font-size="16" font-family="monospace" text-anchor="middle" font-weight="bold">${tech}%</text>
        <text x="${x+bw/2}" y="118" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">R:R mínimo</text>
        <text x="${x+bw/2}" y="132" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle">${rr}</text>
        <text x="${x+bw/2}" y="158" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">EV esperado</text>
        <text x="${x+bw/2}" y="172" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle">${ev}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mayor alineación = mayor probabilidad → menor R:R mínimo aceptable
        </text>
    </svg>`;
}

function fixed_risk_principle() {
    const W=680, H=220;
    // Two scenarios: 2% risk vs 10% risk, showing drawdown after losing streaks
    const risks=[0.02,0.10];
    const labels=['2% riesgo por trade','10% riesgo por trade'];
    const colors=[C.accent,C.red];
    const panelW=(W-50)/2;

    function drawPanel(x0,risk,label,color) {
        let capital=100, points=[capital];
        for(let i=0;i<10;i++){capital*=(1-risk);points.push(capital);}
        const mn=Math.min(...points)-2, mx=102, range=mx-mn;
        const pw=panelW-20;
        const px=(i)=>x0+10+(i/(points.length-1))*pw;
        const py=(v)=>20+160-((v-mn)/range)*160;
        const path=points.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
        const finalLoss=((1-points[points.length-1]/100)*100).toFixed(1);
        return `<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>
        <path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>
        <line x1="${x0+10}" y1="${py(100)}" x2="${x0+10+pw}" y2="${py(100)}" stroke="${C.border}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
        <text x="${x0+10}" y="${py(100)-4}" fill="${C.muted}" font-size="8" font-family="monospace">100%</text>
        <text x="${x0+panelW/2}" y="${py(points[points.length-1])+14}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle">−${finalLoss}% tras 10 stops</text>`;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        ${drawPanel(5, 0.02, '2% riesgo por trade', C.accent)}
        ${drawPanel(panelW+30, 0.10, '10% riesgo por trade', C.red)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            10 stops consecutivos: −18% con riesgo 2% vs −65% con riesgo 10%
        </text>
    </svg>`;
}

function position_scaling() {
    const W=680, H=210;
    const levels=[
        {grade:'A+',desc:'Triple alineación',risk:2.0,color:C.accent},
        {grade:'A', desc:'Doble alineación', risk:1.5,color:C.cyan},
        {grade:'B', desc:'Parcial',           risk:1.0,color:C.yellow},
        {grade:'C', desc:'Sin alineación',    risk:0.5,color:C.orange},
        {grade:'D', desc:'Especulativo',      risk:0.25,color:C.red},
    ];
    const barMaxW=200, startX=160, y0=18, rowH=35;
    let content='';
    levels.forEach(({grade,desc,risk,color},i)=>{
        const y=y0+i*rowH;
        const bw=(risk/2)*barMaxW;
        content+=`<rect x="15" y="${y+2}" width="30" height="26" fill="${color}" opacity="0.2" rx="3" stroke="${color}" stroke-width="1"/>
        <text x="30" y="${y+19}" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${grade}</text>
        <text x="55" y="${y+19}" fill="${C.muted}" font-size="10" font-family="monospace">${desc}</text>
        <rect x="${startX}" y="${y+6}" width="${bw}" height="18" fill="${color}" opacity="0.3" rx="3"/>
        <text x="${startX+bw+8}" y="${y+19}" fill="${color}" font-size="12" font-family="monospace" font-weight="bold">${risk}%</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="30" y="12" fill="${C.muted}" font-size="9" font-family="monospace">Setup</text>
        <text x="160" y="12" fill="${C.muted}" font-size="9" font-family="monospace">Riesgo máximo del capital</text>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mayor alineación → mayor riesgo permitido. Mejor setup = más tamaño.
        </text>
    </svg>`;
}

function averaging_right_wrong() {
    const W=680, H=230;
    const panelW=(W-50)/2;

    function panel(x0, prices, label, color, entries, isGood) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>20+170-((v-mn)/range)*170;
        let out=`<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,10);
        });
        entries.forEach(({i,label,c})=>{
            const ex=px(i);
            out+=`<line x1="${ex}" y1="${20}" x2="${ex}" y2="${20+170}" stroke="${c}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.7"/>
            <text x="${ex}" y="${20+180}" fill="${c}" font-size="8" font-family="monospace" text-anchor="middle">${label}</text>`;
        });
        return out;
    }

    const bad=[100,96,92,88,84,80,84,80,76,72,68,72];
    const good=[100,104,102,106,104,108,112,116,114,118,122,126];

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        ${panel(5, bad, '✗ PROMEDIANDO PÉRDIDAS (nunca)', C.red,
            [{i:1,label:'E1',c:C.red},{i:3,label:'E2↓',c:C.red},{i:5,label:'E3↓↓',c:C.red}], false)}
        ${panel(panelW+30, good, '✓ AÑADIENDO EN GANADORES (válido)', C.accent,
            [{i:1,label:'E1',c:C.accent},{i:5,label:'+E2↑',c:C.accent},{i:9,label:'+E3↑↑',c:C.accent}], true)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Añadir a pérdidas = destruir cuenta. Añadir a ganancias = dejar correr ganadores.
        </text>
    </svg>`;
}

function sizing_psychology() {
    const W=680, H=210;
    const zones=[
        {label:'Demasiado pequeño',pct:0.1,desc:'Irrelevante psicológicamente.\nNo aprendes, no te afecta.',color:C.muted},
        {label:'Tamaño óptimo',pct:1.0,desc:'Suficiente para importar.\nPuedes seguir el plan.',color:C.accent},
        {label:'Demasiado grande',pct:5.0,desc:'Ansiedad. Decisiones emocionales.\nSales demasiado pronto o aguantas demasiado.',color:C.red},
    ];
    const zoneW=(W-40)/3, startX=20;
    let content='';
    zones.forEach(({label,pct,desc,color},i)=>{
        const x=startX+i*(zoneW+5);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${zoneW}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="${i===1?2:1}"/>
        <text x="${x+zoneW/2}" y="38" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${x+zoneW/2}" y="62" fill="${color}" font-size="20" font-family="monospace" text-anchor="middle">${pct}%</text>
        <text x="${x+zoneW/2}" y="76" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">riesgo</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+zoneW/2}" y="${105+li*14}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Si no puedes dormir con la posición abierta, el tamaño es demasiado grande
        </text>
    </svg>`;
}

function trade_plan_why() {
    const W=680, H=210;
    const states=[
        {label:'ANTES\nDE ENTRAR',icon:'🧠',desc:'Analítico · Objetivo\nSin emociones\nCEO del trade',color:C.accent},
        {label:'',icon:'→',desc:'',color:C.muted},
        {label:'PLAN\nESCRITO',icon:'📋',desc:'Decisiones tomadas\nen calma\nAntes del riesgo',color:C.yellow},
        {label:'',icon:'→',desc:'',color:C.muted},
        {label:'DURANTE\nEL TRADE',icon:'😰',desc:'Emocional · Sesgado\nBusca confirmación\nAccionista nervioso',color:C.red},
    ];
    const itemW=110, gap=12, startX=12;
    let content='';
    states.forEach(({label,icon,desc,color},i)=>{
        const x=startX+i*(itemW+gap);
        if(icon==='→'){
            content+=`<text x="${x+itemW/2}" y="${H/2+6}" fill="${C.muted}" font-size="24" text-anchor="middle">→</text>`;
            return;
        }
        const labelLines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${itemW}" height="${H-30}" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+itemW/2}" y="48" font-size="24" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+itemW/2}" y="${70+li*14}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        descLines.forEach((l,li)=>{ content+=`<text x="${x+itemW/2}" y="${108+li*13}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El plan escrito conecta al trader racional pre-trade con el trader emocional en trade
        </text>
    </svg>`;
}

function trade_plan_structure() {
    const W=680, H=220;
    const sections=[
        {title:'TESIS',items:['Contexto M/S/D','Nivel técnico','Catalizador'],color:C.cyan},
        {title:'ENTRADA',items:['Precio exacto','Trigger','Tamaño','Validez'],color:C.accent},
        {title:'GESTIÓN',items:['Stop inicial','Mover a BE','Añadir','Reducir'],color:C.yellow},
        {title:'SALIDA',items:['Objetivo 1','Runner','Salida anticipada'],color:C.orange},
    ];
    const bw=148, gap=10, startX=14;
    let content='';
    sections.forEach(({title,items,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="${H-30}" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="36" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${title}</text>
        <line x1="${x+10}" y1="42" x2="${x+bw-10}" y2="42" stroke="${color}" stroke-width="1" opacity="0.4"/>`;
        items.forEach((item,li)=>{ content+=`<text x="${x+14}" y="${58+li*18}" fill="${C.muted}" font-size="10" font-family="monospace">▸ ${item}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Las 4 secciones del plan. Cada una completada ANTES de abrir la posición.
        </text>
    </svg>`;
}

function trade_plan_scenarios() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,102,104,106,108,110,112,108,110,112,114,116,118,120,122,124];
    const mn=94, mx=130, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,12);});

    const entY=py(100), stopY=py(96), t1Y=py(116), t2Y=py(124);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${entY}"  x2="${x0+w}" y2="${entY}"  stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${t1Y}"   x2="${x0+w}" y2="${t1Y}"   stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${t2Y}"   x2="${x0+w}" y2="${t2Y}"   stroke="${C.yellow}" stroke-width="1" stroke-dasharray="4,4"/>
        ${candles}
        <text x="${x0+w+4}" y="${entY+4}"  fill="${C.cyan}" font-size="9" font-family="monospace">ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${t1Y+4}"   fill="${C.accent}" font-size="9" font-family="monospace">OBJ 1</text>
        <text x="${x0+w+4}" y="${t2Y+4}"   fill="${C.yellow}" font-size="9" font-family="monospace">OBJ 2</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Escenario ideal: precio sube directo → vender 50% en OBJ1, mover stop a BE, runner a OBJ2
        </text>
    </svg>`;
}

function trade_plan_expiry() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    // Trade que no avanza — time stop
    const prices=[100,101,100,102,100,101,99,100,101,100,98,99,100,99,98,97];
    const mn=90, mx=110, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,12);});

    const entY=py(100), stopY=py(96), t1Y=py(106);
    const timeStopX=px(10);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${entY}"  x2="${x0+w}" y2="${entY}"  stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${t1Y}"   x2="${x0+w}" y2="${t1Y}"   stroke="${C.accent}" stroke-width="1" stroke-dasharray="5,4" opacity="0.5"/>
        ${candles}
        <line x1="${timeStopX}" y1="${y0}" x2="${timeStopX}" y2="${y0+h}" stroke="${C.orange}" stroke-width="2" stroke-dasharray="6,3"/>
        <rect x="${(timeStopX-28).toFixed(1)}" y="${(y0+4).toFixed(1)}" width="56" height="18" fill="${C.orange}" opacity="0.15" rx="3"/>
        <text x="${timeStopX}" y="${(y0+16).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">TIME STOP</text>
        <text x="${x0+w+4}" y="${entY+4}"  fill="${C.cyan}" font-size="9" font-family="monospace">ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP</text>
        <text x="${x0+w+4}" y="${t1Y+4}"   fill="${C.accent}" font-size="9" font-family="monospace">OBJ</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El precio no avanza → TIME STOP: salir aunque el stop de precio no haya saltado
        </text>
    </svg>`;
}

// ─── MÓDULO 12: GESTIÓN DEL RIESGO ───────────────────────────────────────────

function fixed_risk_nonnegotiable() {
    const W=680, H=220;
    // Two equity curves: with fixed risk vs without
    const x0=40, y0=15, w=W-80, h=175;
    const n=20;
    const results=[1,-1,1,1,-1,1,-1,-1,1,1,1,-1,1,-1,1,1,-1,1,1,-1];

    // Fixed 1% risk
    let fixedEq=100, fixedData=[100];
    results.forEach(r=>{ fixedEq*=(1+r*0.01); fixedData.push(fixedEq); });

    // No risk control (varies between 3-15%)
    let freeEq=100, freeData=[100];
    const freeRisks=[0.03,0.08,0.05,0.12,0.15,0.04,0.10,0.08,0.03,0.06,0.05,0.12,0.04,0.08,0.06,0.10,0.15,0.04,0.05,0.08];
    results.forEach((r,i)=>{ freeEq*=(1+r*freeRisks[i]); freeData.push(freeEq); });

    const allVals=[...fixedData,...freeData];
    const mn=Math.min(...allVals)*0.97, mx=Math.max(...allVals)*1.02, range=mx-mn;
    const px=(i)=>x0+(i/(n))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    const fixedPath=fixedData.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const freePath=freeData.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${freePath}" fill="none" stroke="${C.red}" stroke-width="2" opacity="0.8"/>
        <path d="${fixedPath}" fill="none" stroke="${C.accent}" stroke-width="2.5"/>
        <line x1="${x0}" y1="${py(100)}" x2="${x0+w}" y2="${py(100)}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="5,4" opacity="0.4"/>
        <rect x="${x0+w-170}" y="${y0+5}" width="160" height="38" fill="${C.bg}" opacity="0.9" rx="3"/>
        <line x1="${x0+w-162}" y1="${y0+16}" x2="${x0+w-140}" y2="${y0+16}" stroke="${C.accent}" stroke-width="2"/>
        <text x="${x0+w-135}" y="${y0+20}" fill="${C.accent}" font-size="9" font-family="monospace">Riesgo fijo 1%</text>
        <line x1="${x0+w-162}" y1="${y0+30}" x2="${x0+w-140}" y2="${y0+30}" stroke="${C.red}" stroke-width="2"/>
        <text x="${x0+w-135}" y="${y0+34}" fill="${C.red}" font-size="9" font-family="monospace">Sin control (3-15%)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mismos resultados (W/L), diferente control de riesgo → resultados radicalmente distintos
        </text>
    </svg>`;
}

function risk_percentage_how() {
    const W=680, H=210;
    const levels=[
        {label:'EMPEZANDO',pct:0.5,color:C.muted,desc:'<1 año · Aprender\nsin destruir cuenta'},
        {label:'INTERMEDIO',pct:1.0,color:C.cyan,desc:'1-3 años · Equilibrio\naprendizaje/rentabilidad'},
        {label:'AVANZADO',pct:1.5,color:C.yellow,desc:'>3 años con resultados\nPositivos consistentes'},
        {label:'RACHA MALA',pct:0.25,color:C.red,desc:'>5 stops seguidos\nRecuperar confianza'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    levels.forEach(({label,pct,color,desc},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        const barH=(pct/2)*120;
        content+=`<rect x="${x}" y="15" width="${bw}" height="170" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="34" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${x+bw/2}" y="58" fill="${color}" font-size="28" font-family="monospace" text-anchor="middle" font-weight="bold">${pct}%</text>
        <text x="${x+bw/2}" y="72" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">por trade</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${92+li*14}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Ajusta el % según tu experiencia y momento actual — nunca más del 2%</text>
    </svg>`;
}

function risk_vs_exposure() {
    const W=680, H=220;
    const x0=40, y0=20, w=W-80, h=165;
    const prices=[195,197,200,198,196,198,200,202,204,206,208,210,208,206,204];
    const mn=188, mx=218, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const entY=py(200), stopY=py(198), t1Y=py(210);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${entY}" x2="${x0+w}" y2="${entY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${t1Y}" x2="${x0+w}" y2="${t1Y}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <text x="${x0+w+4}" y="${entY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">$200 ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">$198 STOP (−1%)</text>
        <text x="${x0+w+4}" y="${t1Y+4}" fill="${C.accent}" font-size="9" font-family="monospace">$210 OBJ (+5%)</text>
        <rect x="${x0+5}" y="${y0+5}" width="230" height="48" fill="${C.bg}" opacity="0.9" rx="3"/>
        <text x="${x0+10}" y="${y0+18}" fill="${C.muted}" font-size="9" font-family="monospace">250 acciones × $200 = $50K EXPOSICIÓN</text>
        <text x="${x0+10}" y="${y0+32}" fill="${C.red}" font-size="9" font-family="monospace">250 × $2 stop = $500 RIESGO REAL (1%)</text>
        <text x="${x0+10}" y="${y0+46}" fill="${C.accent}" font-size="9" font-family="monospace">Alta exposición + bajo riesgo = posible</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Riesgo ≠ Exposición. Stop técnico cerca → exposición alta con riesgo controlado.
        </text>
    </svg>`;
}

function risk_accumulation() {
    const W=680, H=210;
    const positions=[
        {ticker:'NVDA',sector:'Tech',risk:1},
        {ticker:'META',sector:'Tech',risk:1},
        {ticker:'AAPL',sector:'Tech',risk:1},
        {ticker:'LMT', sector:'Defense',risk:1},
        {ticker:'XOM', sector:'Energy',risk:1},
    ];
    const bw=116, gap=8, startX=14;
    let content='', totalRisk=0;
    positions.forEach(({ticker,sector,risk},i)=>{
        const x=startX+i*(bw+gap);
        totalRisk+=risk;
        const isTech=sector==='Tech';
        const color=isTech?C.red:C.accent;
        content+=`<rect x="${x}" y="15" width="${bw}" height="140" fill="${color}" opacity="${isTech?0.1:0.07}" rx="5" stroke="${color}" stroke-width="${isTech?2:1}"/>
        <text x="${x+bw/2}" y="40" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${ticker}</text>
        <text x="${x+bw/2}" y="57" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${sector}</text>
        <text x="${x+bw/2}" y="82" fill="${color}" font-size="18" font-family="monospace" text-anchor="middle" font-weight="bold">${risk}%</text>
        <text x="${x+bw/2}" y="97" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">riesgo</text>`;
    });
    content+=`<rect x="${startX}" y="165" width="${3*(bw+gap)+bw}" height="28" fill="${C.red}" opacity="0.1" rx="4" stroke="${C.red}" stroke-width="1.5"/>
    <text x="${startX+180}" y="183" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">Tech cae simultáneamente → riesgo real = 3% en un día</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Riesgo total de cartera = suma de riesgos individuales. Límite recomendado: 3-5%.
        </text>
    </svg>`;
}

function stop_types() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,102,104,106,108,110,112,114,116,118,116,118,120,122,124,126];
    const mn=92, mx=134, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const initStopY=py(96), entryY=py(100), beY=py(100), trailY=py(114);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${initStopY}" x2="${px(4)}" y2="${initStopY}" stroke="${C.red}" stroke-width="2" stroke-dasharray="6,3"/>
        <line x1="${px(4)}" y1="${beY}" x2="${px(9)}" y2="${beY}" stroke="${C.yellow}" stroke-width="2" stroke-dasharray="6,3"/>
        <line x1="${px(9)}" y1="${trailY}" x2="${x0+w}" y2="${trailY}" stroke="${C.orange}" stroke-width="2" stroke-dasharray="6,3"/>
        ${candles}
        <text x="${px(2)}" y="${(initStopY+14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">STOP INICIAL</text>
        <text x="${px(6.5)}" y="${(beY+14).toFixed(1)}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">BREAKEVEN</text>
        <text x="${px(13)}" y="${(trailY+14).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">TRAILING</text>
        <text x="${x0+w+4}" y="${initStopY+4}" fill="${C.red}" font-size="9" font-family="monospace">−1R</text>
        <text x="${x0+w+4}" y="${beY+4}" fill="${C.yellow}" font-size="9" font-family="monospace">0R</text>
        <text x="${x0+w+4}" y="${trailY+4}" fill="${C.orange}" font-size="9" font-family="monospace">+2R</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Stop inicial → Breakeven (1R ganancia) → Trailing (proteger ganancias)
        </text>
    </svg>`;
}

function stop_placement() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,108,112,108,104,100,96,98,102,106,110,114,118,122,126];
    const mn=88, mx=134, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const supY=py(96), stopY=py(94), entryY=py(102);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${supY-5}" width="${w}" height="10" fill="${C.accent}" opacity="0.08"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.7"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${entryY}" x2="${x0+w}" y2="${entryY}" stroke="${C.cyan}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
        ${candles}
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SOPORTE</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP (−0.5%)</text>
        <text x="${x0+w+4}" y="${entryY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">ENTRADA</text>
        <text x="${px(8).toFixed(1)}" y="${(stopY+18).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Margen bajo soporte</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Stop bajo soporte técnico + 0.5% de margen = evitar stops prematuros por ruido
        </text>
    </svg>`;
}

function trailing_stop_how() {
    const W=680, H=230;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,104,108,112,110,114,118,122,120,124,128,132,130,134,138,142];
    const mn=92, mx=150, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const trailLevels=[[0,96],[4,108],[8,118],[12,128],[15,136]];
    let trailPath='';
    trailLevels.forEach(([i,v],pi)=>{
        const nx=pi<trailLevels.length-1?trailLevels[pi+1][0]:15;
        trailPath+=`M ${px(i).toFixed(1)} ${py(v).toFixed(1)} L ${px(nx).toFixed(1)} ${py(v).toFixed(1)} `;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${trailPath}" fill="none" stroke="${C.orange}" stroke-width="2" stroke-dasharray="8,3"/>
        ${candles}
        ${trailLevels.map(([i,v])=>`<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="${C.orange}" opacity="0.8"/>`).join('')}
        <text x="${px(7.5).toFixed(1)}" y="${(py(116)+14).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">TRAILING STOP sube con el precio</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mover el trailing stop al último HL cada vez que el precio hace un nuevo HH
        </text>
    </svg>`;
}

function mental_stop_danger() {
    const W=680, H=220;
    const panelW=(W-50)/2;

    function panel(x0, prices, label, color, hasStop) {
        const mn=Math.min(...prices)-5, mx=Math.max(...prices)+5, range=mx-mn;
        const n=prices.length;
        const px=(i)=>x0+(i/(n-1))*panelW;
        const py=(v)=>20+160-((v-mn)/range)*160;
        let out=`<text x="${x0+panelW/2}" y="14" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        prices.forEach((p,i)=>{
            if(!i) return;
            const prev=prices[i-1],bull=p>prev,cx=px(i);
            out+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,10);
        });
        // Stop line
        const stopV=prices[0]*0.95;
        const stopY=py(stopV);
        out+=`<line x1="${x0}" y1="${stopY}" x2="${x0+panelW}" y2="${stopY}" stroke="${color}" stroke-width="${hasStop?2:1.5}" stroke-dasharray="${hasStop?'6,3':'4,4'}"/>
        <text x="${x0+panelW/2}" y="${stopY-4}" fill="${color}" font-size="8" font-family="monospace" text-anchor="middle">${hasStop?'STOP FÍSICO ✓':'STOP MENTAL ✗ (ignorado)'}</text>
        <text x="${x0+panelW/2}" y="${H-10}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${hasStop?'Ejecutado automáticamente':'Excusa → No ejecutado'}</text>`;
        return out;
    }

    const good=[100,98,96,94,92,90,88]; // drops to stop, exits
    const bad= [100,98,96,94,92,90,86,82,78,74,70]; // keeps dropping, no exit

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="2" y="2" width="${panelW}" height="${H-4}" fill="${C.accent}" opacity="0.03" rx="5"/>
        <rect x="${panelW+28}" y="2" width="${panelW}" height="${H-4}" fill="${C.red}" opacity="0.03" rx="5"/>
        ${panel(5, good, '✓ STOP FÍSICO en el broker', C.accent, true)}
        ${panel(panelW+30, bad, '✗ STOP MENTAL (nunca)', C.red, false)}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function revenge_trading_what() {
    const W=680, H=210;
    const stages=[
        {label:'Pérdida\nnormal',val:'−$500',color:C.muted,icon:'📉'},
        {label:'Rage trade\ndoble tamaño',val:'−$1,200',color:C.orange,icon:'😤'},
        {label:'Triple para\nrecuperar',val:'−$2,500',color:C.red,icon:'😡'},
        {label:'All-in\npara salvar',val:'−$6,000',color:'#8b0000',icon:'💀'},
    ];
    const bw=140, gap=12, startX=15;
    let content='';
    stages.forEach(({label,val,color,icon},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="${0.05+i*0.04}" rx="6" stroke="${color}" stroke-width="${1+i*0.5}"/>
        <text x="${x+bw/2}" y="48" font-size="24" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${70+li*15}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="115" fill="${color}" font-size="18" font-family="monospace" text-anchor="middle" font-weight="bold">${val}</text>`;
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.red}" font-size="16" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">La espiral del revenge trading: cada pérdida empeora el juicio → peores decisiones → más pérdidas</text>
    </svg>`;
}

function revenge_trading_signs() {
    const W=680, H=200;
    const signs=[
        '❗ Urgencia de entrar tras 2-3 pérdidas',
        '❗ Tamaño mayor al habitual',
        '❗ Setup no estaba en el watchlist',
        '❗ Activos no analizados el domingo',
        '❗ "El mercado me debe esta"',
        '❗ "Esta vez es diferente"',
    ];
    const cols=2, colW=(W-40)/cols;
    let content='';
    signs.forEach((sign,i)=>{
        const col=i%cols, row=Math.floor(i/cols);
        const x=20+col*colW, y=20+row*52;
        content+=`<rect x="${x}" y="${y}" width="${colW-8}" height="44" fill="${C.red}" opacity="0.07" rx="5" stroke="${C.red}" stroke-width="1"/>
        <text x="${x+10}" y="${y+27}" fill="${C.red}" font-size="11" font-family="monospace">${sign}</text>`;
    });
    content+=`<rect x="20" y="175" width="${W-40}" height="18" fill="${C.accent}" opacity="0.1" rx="4"/>
    <text x="${W/2}" y="187" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">→ Si detectas cualquiera de estas señales: CERRAR EL ORDENADOR. Hoy no más trades.</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function losing_streak_protocol() {
    const W=680, H=200;
    const steps=[
        {n:'3',label:'Revisar trades',desc:'¿Seguiste el plan?\n¿Error de proceso?',color:C.yellow},
        {n:'4',label:'Reducir 50%',desc:'Proteger capital\nmientras revisas',color:C.orange},
        {n:'5',label:'Paper trading',desc:'1 semana sin\nriesgo real',color:C.red},
        {n:'6+',label:'Parar',desc:'Revisión profunda\ndel sistema',color:'#8b0000'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach(({n,label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${color}" opacity="${0.07+i*0.02}" rx="6" stroke="${color}" stroke-width="${1+i*0.3}"/>
        <circle cx="${x+bw/2}" cy="46" r="20" fill="${color}" opacity="0.2" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="52" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">${n} stops</text>
        <text x="${x+bw/2}" y="82" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${102+li*16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Protocolo definido de antemano — no improvises cuando estás en racha mala</text>
    </svg>`;
}

function loss_mindset() {
    const W=680, H=200;
    const questions=[
        {q:'¿Seguiste el plan?',yes:'✓ Bien hecho.\nEl proceso fue correcto.',no:'✗ Ahí está el problema.\nCorrígelo, no el resultado.',color:C.accent},
    ];
    // Decision tree
    const cX=W/2, qY=40, yY=130, nY=130;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="${cX-160}" y="20" width="320" height="40" fill="${C.surface}" stroke="${C.border}" stroke-width="1.5" rx="6"/>
        <text x="${cX}" y="45" fill="${C.text}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">Después de cada stop: ¿Seguí mi plan?</text>
        <line x1="${cX-60}" y1="60" x2="${cX-100}" y2="105" stroke="${C.accent}" stroke-width="2"/>
        <line x1="${cX+60}" y1="60" x2="${cX+100}" y2="105" stroke="${C.red}" stroke-width="2"/>
        <text x="${cX-90}" y="85" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">SÍ</text>
        <text x="${cX+90}" y="85" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">NO</text>
        <rect x="${cX-240}" y="105" width="220" height="52" fill="${C.accent}" opacity="0.08" stroke="${C.accent}" stroke-width="1.5" rx="6"/>
        <text x="${cX-130}" y="126" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">✓ Proceso correcto.</text>
        <text x="${cX-130}" y="142" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">El resultado no estaba en</text>
        <text x="${cX-130}" y="156" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">tu control. Continúa.</text>
        <rect x="${cX+20}" y="105" width="220" height="52" fill="${C.red}" opacity="0.08" stroke="${C.red}" stroke-width="1.5" rx="6"/>
        <text x="${cX+130}" y="126" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">✗ El proceso falló.</text>
        <text x="${cX+130}" y="142" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">Identifica el error y</text>
        <text x="${cX+130}" y="156" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">corrígelo. No el resultado.</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Juzga el proceso, no el resultado de cada trade individual</text>
    </svg>`;
}

function capital_protection_rules() {
    const W=680, H=200;
    const rules=[
        {n:'1',rule:'Máx 2% por trade',detail:'Nunca en ningún caso',color:C.accent},
        {n:'2',rule:'Máx 5% total',detail:'Riesgo simultáneo\nen cartera',color:C.cyan},
        {n:'3',rule:'−10%: reducir 50%',detail:'Automático\nsin excepción',color:C.yellow},
        {n:'4',rule:'−20%: parar',detail:'Alto completo\nrevisión total',color:C.red},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    rules.forEach(({n,rule,detail,color},i)=>{
        const x=startX+i*(bw+gap);
        const detailLines=detail.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="2"/>
        <circle cx="${x+bw/2}" cy="45" r="18" fill="${color}" opacity="0.2" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="51" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>
        <text x="${x+bw/2}" y="76" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${rule}</text>`;
        detailLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${98+li*16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Las 4 reglas son absolutas. No tienen excepciones. No se negocian.</text>
    </svg>`;
}

function drawdown_management() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=175;
    // Equity curve with drawdown
    const equity=[100,102,104,106,105,107,108,106,104,102,100,98,96,98,100,102,104,106,108,110];
    const mn=90, mx=115, range=mx-mn;
    const px=(i)=>x0+(i/(equity.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    const eqPath=equity.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const maxV=Math.max(...equity.slice(0,8));
    const maxY=py(maxV), minV=Math.min(...equity.slice(7,14)), minY=py(minV);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${px(7).toFixed(1)}" y="${maxY}" width="${(px(13)-px(7)).toFixed(1)}" height="${(minY-maxY).toFixed(1)}" fill="${C.red}" opacity="0.08"/>
        <line x1="${px(7).toFixed(1)}" y1="${maxY}" x2="${px(13).toFixed(1)}" y2="${maxY}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="5,4" opacity="0.5"/>
        <path d="${eqPath}" fill="none" stroke="${C.accent}" stroke-width="2.5"/>
        <line x1="${px(7)+18}" y1="${maxY+4}" x2="${px(7)+18}" y2="${minY-4}" stroke="${C.red}" stroke-width="1.5"/>
        <text x="${px(7)+22}" y="${((maxY+minY)/2+4).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace">DD ~12%</text>
        <text x="${px(7).toFixed(1)}" y="${(maxY-6).toFixed(1)}" fill="${C.muted}" font-size="8" font-family="monospace">Máximo</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El drawdown es inevitable. Lo que importa es su magnitud y tiempo de recuperación.
        </text>
    </svg>`;
}

function position_correlation() {
    const W=680, H=210;
    // Two portfolios: all tech vs diversified
    const panelW=(W-50)/2;

    function panel(x0, tickers, label, colors, note) {
        let out=`<text x="${x0+panelW/2}" y="14" fill="${colors[0]}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        const bw=panelW/tickers.length-6;
        tickers.forEach((t,i)=>{
            const x=x0+i*(bw+6);
            out+=`<rect x="${x}" y="22" width="${bw}" height="130" fill="${colors[i%colors.length]}" opacity="0.08" rx="4" stroke="${colors[i%colors.length]}" stroke-width="1"/>
            <text x="${x+bw/2}" y="50" fill="${colors[i%colors.length]}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${t}</text>
            <text x="${x+bw/2}" y="68" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">1%</text>`;
        });
        out+=`<rect x="${x0}" y="160" width="${panelW}" height="30" fill="${colors[0]}" opacity="0.1" rx="4"/>
        <text x="${x0+panelW/2}" y="179" fill="${colors[0]}" font-size="9" font-family="monospace" text-anchor="middle">${note}</text>`;
        return out;
    }

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(5, ['NVDA','META','AAPL','MSFT','AMZN'], '✗ TODO TECH (correlación alta)', [C.red], 'Tech cae → todos caen → riesgo real 5%')}
        ${panel(panelW+30, ['NVDA','LMT','XOM','JNJ','GLD'], '✓ DIVERSIFICADO (correlación baja)', [C.accent,C.cyan,C.yellow,C.orange,C.muted], 'Sectores no correlacionados → riesgo distribuido')}
        <line x1="${panelW+15}" y1="5" x2="${panelW+15}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function capital_recovery_math() {
    const W=680, H=220;
    const scenarios=[
        {loss:10,recovery:11.1,color:C.yellow},
        {loss:20,recovery:25,color:C.orange},
        {loss:30,recovery:42.9,color:C.red},
        {loss:50,recovery:100,color:'#c00000'},
        {loss:75,recovery:300,color:'#8b0000'},
    ];
    const bw=116, gap=8, startX=14, maxH=140, y0=20;
    let content='';
    scenarios.forEach(({loss,recovery,color},i)=>{
        const x=startX+i*(bw+gap);
        const lossH=(loss/75)*maxH;
        const recH=Math.min((recovery/300)*maxH, maxH*1.1);
        content+=`<rect x="${x}" y="${y0+maxH-lossH}" width="${bw/2-2}" height="${lossH}" fill="${C.red}" opacity="0.4" rx="2"/>
        <rect x="${x+bw/2+2}" y="${y0+maxH-recH}" width="${bw/2-2}" height="${recH}" fill="${color}" opacity="0.4" rx="2"/>
        <text x="${x+bw/4}" y="${y0+maxH+14}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">−${loss}%</text>
        <text x="${x+bw*3/4}" y="${y0+maxH+14}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">+${recovery}%</text>
        <text x="${x+bw/2}" y="${y0+maxH+26}" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">para volver</text>`;
    });
    content+=`<line x1="${startX-5}" y1="${y0+maxH}" x2="${startX+5*(bw+gap)}" y2="${y0+maxH}" stroke="${C.border}" stroke-width="1"/>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Pérdida −50% requiere +100% para recuperar. Las pérdidas grandes son matemáticamente devastadoras.
        </text>
    </svg>`;
}

// ─── MÓDULO 13: EJECUCIÓN ─────────────────────────────────────────────────────

function confirmation_definition() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,102,104,103,105,104,106,108,107,109,111,110,112,114,116,118];
    const mn=94, mx=122, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const resY=py(109), prematureX=px(7), confirmedX=px(9);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${prematureX}" cy="${py(107)}" r="7" fill="${C.red}" opacity="0.2" stroke="${C.red}" stroke-width="2"/>
        <text x="${prematureX}" y="${(py(107)+20).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">SIN CIERRE</text>
        <text x="${prematureX}" y="${(py(107)+32).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">(no confirmado)</text>
        <circle cx="${confirmedX}" cy="${py(111)}" r="7" fill="${C.accent}" opacity="0.2" stroke="${C.accent}" stroke-width="2"/>
        <text x="${confirmedX}" y="${(py(111)-12).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">CIERRE > NIVEL</text>
        <text x="${confirmedX}" y="${(py(111)-24).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">(confirmado ✓)</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">RESISTENCIA</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Confirmación = evidencia objetiva (cierre), no interpretación (mecha tocando el nivel)
        </text>
    </svg>`;
}

function confirmation_types() {
    const W=680, H=210;
    const types=[
        {setup:'Ruptura',conf:'Cierre > nivel',color:C.accent},
        {setup:'Retroceso',conf:'Vela rechazo',color:C.cyan},
        {setup:'Continuación',conf:'Vol > 1.5x',color:C.yellow},
        {setup:'Reversión',conf:'Nuevo HH tras LL',color:C.orange},
        {setup:'Retest',conf:'Rechazo en nivel',color:C.red},
    ];
    const bw=120, gap=10, startX=15;
    let content='';
    types.forEach(({setup,conf,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="40" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${setup}</text>
        <line x1="${x+12}" y1="50" x2="${x+bw-12}" y2="50" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="75" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Confirmación:</text>
        <text x="${x+bw/2}" y="100" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${conf.split(' ')[0]}</text>
        <text x="${x+bw/2}" y="114" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${conf.split(' ').slice(1).join(' ')}</text>
        <text x="${x+bw/2}" y="150" fill="${color}" font-size="18" text-anchor="middle">✓</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Cada setup tiene su propia confirmación objetiva — defínela antes de operar</text>
    </svg>`;
}

function patience_vs_fear() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="45" font-size="30" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="70" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="80" x2="${x0+panelW-20}" y2="80" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${102+li*18}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'PACIENCIA','Esperas la señal\ndefinida en el plan.\nSi aparece, ejecutas.',C.accent,'🧘')}
        ${panel(panelW+35,'MIEDO','La señal ya apareció\npero sigues dudando\n"por si acaso".',C.red,'😰')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Si la confirmación ya está → es momento de ejecutar, no de seguir esperando</text>
    </svg>`;
}

function patience_training() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'Siente el impulso',desc:'de entrar antes\nde tiempo'},
        {n:'2',label:'Anota la situación',desc:'ticker, nivel,\nhora'},
        {n:'3',label:'Espera al cierre',desc:'no actúes\ntodavía'},
        {n:'4',label:'Registra resultado',desc:'¿habría ganado\no perdido?'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach(({n,label,desc},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.cyan}" opacity="0.06" rx="6" stroke="${C.cyan}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="42" r="16" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="47" fill="${C.cyan}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>
        <text x="${x+bw/2}" y="72" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${94+li*15}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Tras 20-30 registros, los datos te dirán si la impaciencia ayuda o perjudica</text>
    </svg>`;
}

function premature_entry_anatomy() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,102,104,106,108,106,104,102,104,106,108,110,108,106,108,110];
    const mn=96, mx=114, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const resY=py(108), prematureX=px(4), failedX=px(7);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${prematureX}" cy="${py(108)}" r="7" fill="${C.red}" opacity="0.3" stroke="${C.red}" stroke-width="2"/>
        <text x="${prematureX}" y="${(py(108)-14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">ENTRADA</text>
        <text x="${prematureX}" y="${(py(108)-26).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">PREMATURA</text>
        <circle cx="${failedX}" cy="${py(102)}" r="6" fill="${C.red}" opacity="0.5" stroke="${C.red}" stroke-width="2"/>
        <text x="${failedX}" y="${(py(102)+20).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">FALLA — STOP</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">NIVEL</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El precio se acerca al nivel pero retrocede — la confirmación nunca llegó
        </text>
    </svg>`;
}

function premature_entry_traps() {
    const W=680, H=200;
    const traps=[
        {label:'"Va a romper\nseguro"',icon:'🎯'},
        {label:'FOMO de\nmovimiento rápido',icon:'😱'},
        {label:'Anclaje en\nanálisis previo',icon:'⚓'},
        {label:'Pre-market /\nafter-hours',icon:'🌙'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    traps.forEach(({label,icon},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.red}" opacity="0.06" rx="6" stroke="${C.red}" stroke-width="1"/>
        <text x="${x+bw/2}" y="55" font-size="26" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${85+li*16}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="140" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Trampa #${i+1}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Reconocer el patrón mental es el primer paso para interrumpirlo</text>
    </svg>`;
}

function premature_entry_stats() {
    const W=680, H=210;
    const data=[
        {label:'Con confirmación\ncompleta',pct:60,color:C.accent},
        {label:'Anticipada\n(sin cierre)',pct:40,color:C.orange},
        {label:'Por FOMO\n(tarde)',pct:35,color:C.red},
    ];
    const bw=180, gap=30, startX=40, maxH=130, y0=20;
    let content='';
    data.forEach(({label,pct,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        const bh=(pct/65)*maxH;
        content+=`<rect x="${x+bw/2-30}" y="${y0+maxH-bh}" width="60" height="${bh}" fill="${color}" opacity="0.3" rx="4"/>
        <text x="${x+bw/2}" y="${y0+maxH-bh-8}" fill="${color}" font-size="16" font-family="monospace" text-anchor="middle" font-weight="bold">${pct}%</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${y0+maxH+20+li*15}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    content+=`<line x1="${startX-10}" y1="${y0+maxH}" x2="${startX+2*(bw+gap)+bw+10}" y2="${y0+maxH}" stroke="${C.border}" stroke-width="1"/>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El trigger filtra falsas señales — saltárselo reduce la tasa de éxito estructuralmente</text>
    </svg>`;
}

function anti_impatience_protocol() {
    const W=680, H=200;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <circle cx="${W/2}" cy="60" r="42" fill="${C.orange}" opacity="0.1" stroke="${C.orange}" stroke-width="2"/>
        <text x="${W/2}" y="55" font-size="22" text-anchor="middle">⏱️</text>
        <text x="${W/2}" y="75" fill="${C.orange}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">10 MINUTOS</text>
        <text x="${W/2}" y="120" fill="${C.muted}" font-size="11" font-family="monospace" text-anchor="middle">Siente el impulso → Espera 10 min sin tocar nada</text>
        <text x="${W/2}" y="138" fill="${C.muted}" font-size="11" font-family="monospace" text-anchor="middle">El impulso emocional se reduce significativamente</text>
        <text x="${W/2}" y="160" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">Trigger completo tras esperar → Entra</text>
        <text x="${W/2}" y="178" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">Trigger incompleto → Sigue esperando</text>
    </svg>`;
}

function why_abandon_plan() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*17}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'PLAN DISEÑADO','En calma.\nAntes del riesgo.\nObjetivo y racional.',C.accent,'🧠')}
        ${panel(panelW+35,'PLAN ABANDONADO','Bajo presión.\nDinero en riesgo.\nEmocional.',C.red,'🔥')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El plan existe precisamente para los momentos en que se siente abandonarlo</text>
    </svg>`;
}

function two_ways_abandon() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,102,104,102,100,98,96,98,100,102,104,106,108,110,108,106];
    const mn=92, mx=114, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const stopY=py(96), earlyExitX=px(3), lateLineY=py(96), lateExitX=px(6);
    const objY=py(108), earlyProfitX=px(11), lateProfitX=px(14);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${objY}" x2="${x0+w}" y2="${objY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${earlyExitX}" cy="${py(99)}" r="5" fill="${C.orange}" opacity="0.6"/>
        <text x="${earlyExitX}" y="${(py(99)-14).toFixed(1)}" fill="${C.orange}" font-size="8" font-family="monospace" text-anchor="middle">Salida ansiosa</text>
        <circle cx="${lateExitX}" cy="${py(96)}" r="5" fill="${C.red}" opacity="0.6"/>
        <text x="${lateExitX}" y="${(py(96)+16).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">Stop correcto</text>
        <circle cx="${earlyProfitX}" cy="${py(106)}" r="5" fill="${C.orange}" opacity="0.6"/>
        <text x="${earlyProfitX}" y="${(py(106)-14).toFixed(1)}" fill="${C.orange}" font-size="8" font-family="monospace" text-anchor="middle">Sale antes obj.</text>
        <circle cx="${lateProfitX}" cy="${py(108)}" r="5" fill="${C.accent}" opacity="0.6"/>
        <text x="${lateProfitX}" y="${(py(108)-14).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">Objetivo plan</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Salir antes del stop (miedo) o tras el stop (esperanza) — ambos rompen el plan
        </text>
    </svg>`;
}

function when_deviate_legit() {
    const W=680, H=200;
    const reasons=[
        {label:'Noticia material\ninesperada',icon:'📰',color:C.yellow},
        {label:'Cambio de régimen\nde mercado',icon:'⚡',color:C.orange},
        {label:'Error objetivo\nen el plan',icon:'🔍',color:C.cyan},
    ];
    const bw=200, gap=15, startX=20;
    let content='';
    reasons.forEach(({label,icon,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="55" font-size="28" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${85+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="145" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">✓ Legítimo</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Solo información NUEVA y objetiva justifica desviarse — nunca la emoción del momento</text>
    </svg>`;
}

function plan_following_habit() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=160;
    // Adherence over months increasing
    const months=['M1','M2','M3','M4','M5','M6'];
    const adherence=[60,68,75,82,88,95];
    const mn=50, mx=100, range=mx-mn;
    const bw=(w/months.length)-12;
    let content='';
    months.forEach((m,i)=>{
        const x=x0+i*(w/months.length)+6;
        const bh=((adherence[i]-mn)/range)*h;
        content+=`<rect x="${x}" y="${y0+h-bh}" width="${bw}" height="${bh}" fill="${C.accent}" opacity="${0.3+i*0.1}" rx="3"/>
        <text x="${x+bw/2}" y="${y0+h-bh-8}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${adherence[i]}%</text>
        <text x="${x+bw/2}" y="${y0+h+14}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${m}</text>`;
    });
    content+=`<line x1="${x0-5}" y1="${y0+h-((95-mn)/range)*h}" x2="${x0+w}" y2="${y0+h-((95-mn)/range)*h}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="5,4" opacity="0.4"/>
    <text x="${x0+w+5}" y="${y0+h-((95-mn)/range)*h+4}" fill="${C.accent}" font-size="9" font-family="monospace">Objetivo 95%</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">La adherencia al plan mejora con repetición consciente — registrarlo lo refuerza</text>
    </svg>`;
}

function ego_sabotage() {
    const W=680, H=200;
    const x0=20, y0=20, w=300, h=120;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="20" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">El ego convierte cada trade en una declaración de identidad</text>
        <rect x="40" y="40" width="260" height="120" fill="${C.cyan}" opacity="0.06" rx="8" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="170" y="68" fill="${C.cyan}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">TENER RAZÓN</text>
        <text x="170" y="92" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">"Mi análisis era</text>
        <text x="170" y="108" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">correcto"</text>
        <text x="170" y="140" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">No determina rentabilidad</text>
        <rect x="380" y="40" width="260" height="120" fill="${C.accent}" opacity="0.08" rx="8" stroke="${C.accent}" stroke-width="2"/>
        <text x="510" y="68" fill="${C.accent}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">GANAR DINERO</text>
        <text x="510" y="92" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">"El proceso fue</text>
        <text x="510" y="108" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">rentable"</text>
        <text x="510" y="140" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">El único objetivo real</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El objetivo no es tener razón — es ser rentable de forma consistente</text>
    </svg>`;
}

function exit_loss_no_ego() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'Stop salta',desc:'Ejecutas sin\ndudar'},
        {n:'2',label:'No miras 30 min',desc:'Evitas re-entrar\npor venganza'},
        {n:'3',label:'Anotas en journal',desc:'Resultado\nobjetivo'},
        {n:'4',label:'Siguiente setup',desc:'Sin carga\nemocional'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach(({n,label,desc},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.accent}" opacity="0.06" rx="6" stroke="${C.accent}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="42" r="16" fill="${C.accent}" opacity="0.2" stroke="${C.accent}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="47" fill="${C.accent}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>
        <text x="${x+bw/2}" y="72" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${94+li*15}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El stop ejecutado correctamente es el sistema funcionando, no fallando</text>
    </svg>`;
}

function exit_profit_no_ego() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,103,106,109,112,115,118,121,124,127,130,128,124,120,118,122];
    const mn=92, mx=134, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const objY=py(124), objX=px(9), greedX=px(10), revertX=px(13);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${objY}" x2="${x0+w}" y2="${objY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${objX}" cy="${py(124)}" r="6" fill="${C.accent}" opacity="0.6"/>
        <text x="${objX}" y="${(py(124)-14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">PLAN: vender</text>
        <circle cx="${greedX}" cy="${py(127)}" r="6" fill="${C.orange}" opacity="0.6"/>
        <text x="${greedX}" y="${(py(127)-26).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">CODICIA:</text>
        <text x="${greedX}" y="${(py(127)-14).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">"puedo más"</text>
        <circle cx="${revertX}" cy="${py(120)}" r="6" fill="${C.red}" opacity="0.6"/>
        <text x="${revertX}" y="${(py(120)+20).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Reversión: pierde ganancia</text>
        <text x="${x0+w+4}" y="${objY+4}" fill="${C.accent}" font-size="9" font-family="monospace">OBJETIVO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mover el objetivo "porque el momentum es fuerte" sin base técnica = codicia, no análisis
        </text>
    </svg>`;
}

function recognize_market_change() {
    const W=680, H=200;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="${W/2-220}" y="20" width="440" height="60" fill="${C.surface}" stroke="${C.border}" stroke-width="1.5" rx="6"/>
        <text x="${W/2}" y="44" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">¿Abrirías este trade HOY,</text>
        <text x="${W/2}" y="62" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">con la información que tienes ahora?</text>
        <line x1="${W/2-80}" y1="85" x2="${W/2-130}" y2="120" stroke="${C.accent}" stroke-width="2"/>
        <line x1="${W/2+80}" y1="85" x2="${W/2+130}" y2="120" stroke="${C.red}" stroke-width="2"/>
        <text x="${W/2-105}" y="105" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">SÍ</text>
        <text x="${W/2+105}" y="105" fill="${C.red}" font-size="11" font-family="monospace" text-anchor="middle">NO</text>
        <rect x="${W/2-220}" y="125" width="180" height="55" fill="${C.accent}" opacity="0.08" stroke="${C.accent}" stroke-width="1.5" rx="6"/>
        <text x="${W/2-130}" y="148" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">Mantén la posición</text>
        <text x="${W/2-130}" y="164" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">según el plan original</text>
        <rect x="${W/2+40}" y="125" width="180" height="55" fill="${C.red}" opacity="0.08" stroke="${C.red}" stroke-width="1.5" rx="6"/>
        <text x="${W/2+130}" y="148" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">Cierra la posición</text>
        <text x="${W/2+130}" y="164" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">sunk cost no cuenta</text>
    </svg>`;
}

// ─── MÓDULO 14: TRAMPAS DEL MERCADO ──────────────────────────────────────────

function fake_breakout_why() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,102,104,106,108,110,112,108,104,100,102,106,110,114,118,122];
    const mn=94, mx=128, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,11);});

    const resY=py(110), stopHuntX=px(6), realX=px(13);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${stopHuntX}" cy="${py(112)}" r="7" fill="${C.red}" opacity="0.3" stroke="${C.red}" stroke-width="2"/>
        <text x="${stopHuntX}" y="${(py(112)-14).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">CAZA DE STOPS</text>
        <text x="${stopHuntX}" y="${(py(112)-26).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">liquidez institucional</text>
        <circle cx="${realX}" cy="${py(118)}" r="7" fill="${C.accent}" opacity="0.3" stroke="${C.accent}" stroke-width="2"/>
        <text x="${realX}" y="${(py(118)-14).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">RUPTURA REAL</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">NIVEL</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Caza de stops antes de la ruptura real — patrón frecuente en niveles muy obvios
        </text>
    </svg>`;
}

function fake_breakout_anatomy() {
    const W=680, H=200;
    const headers=['Señal','Ruptura real','Falsa ruptura'];
    const rows=[
        ['Volumen','Alto >1.5x','Bajo/normal'],
        ['Cierre','Fuera del rango','Cerca del nivel'],
        ['Reversión','No en 1-2 días','En 1-3 velas'],
        ['Tendencia','A favor','Contra tendencia'],
    ];
    const colW=[160,180,180], startX=60, startY=25, rowH=38;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-8}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-8}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${headers[1]}</text>
    <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${startY-8}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${headers[2]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]+colW[2]}" height="${rowH-4}" fill="${i%2===0?C.surface:'transparent'}" rx="3"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2}" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${row[1]}</text>
        <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${y+rowH/2}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${row[2]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function fake_breakout_protection() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'Espera el\ncierre',color:C.accent},
        {n:'2',label:'Confirma\nvolumen >1.5x',color:C.cyan},
        {n:'3',label:'Espera el\nretest',color:C.yellow},
        {n:'4',label:'Evita contra\ntendencia mayor',color:C.orange},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach(({n,label,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="44" r="18" fill="${color}" opacity="0.2" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="50" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${78+li*16}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">+</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Más filtros = menos trades, pero mayor calidad en los que sí entras</text>
    </svg>`;
}

function fake_breakout_trapped() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,102,104,106,104,102,100,98,96,94,96,98];
    const mn=90, mx=110, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,14);});

    const entryY=py(106), stopY=py(98), entryX=px(3);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${entryY}" x2="${x0+w}" y2="${entryY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <text x="${x0+w+4}" y="${entryY+4}" fill="${C.cyan}" font-size="9" font-family="monospace">ENTRADA</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">STOP — EJECUTAR</text>
        <text x="${px(8)}" y="${(stopY+25).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">✗ No promediar · No mover el stop</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El stop ya invalidó la hipótesis — ejecutar, no negociar
        </text>
    </svg>`;
}

function late_entry_why() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=175;
    const prices=[100,103,106,109,112,115,118,121,124,127,130,133,136,134,132,130];
    const mn=94, mx=140, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,11);});

    const earlyX=px(2), lateX=px(11);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <rect x="${x0}" y="${y0}" width="${px(5)-x0}" height="${h}" fill="${C.accent}" opacity="0.05"/>
        <rect x="${px(9)}" y="${y0}" width="${x0+w-px(9)}" height="${h}" fill="${C.red}" opacity="0.05"/>
        <circle cx="${earlyX}" cy="${py(105)}" r="7" fill="${C.accent}" opacity="0.3" stroke="${C.accent}" stroke-width="2"/>
        <text x="${earlyX}" y="${(py(105)-14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">SETUP TEMPRANO</text>
        <text x="${earlyX}" y="${(py(105)-26).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">análisis propio</text>
        <circle cx="${lateX}" cy="${py(133)}" r="7" fill="${C.red}" opacity="0.3" stroke="${C.red}" stroke-width="2"/>
        <text x="${lateX}" y="${(py(133)-14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">"TODO EL MUNDO</text>
        <text x="${lateX}" y="${(py(133)-26).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">HABLA DE ELLO"</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cuando el movimiento es "obvio" en titulares, la parte de mejor R:R ya pasó
        </text>
    </svg>`;
}

function late_entry_signs() {
    const W=680, H=200;
    const signs=[
        {label:'Precio >20%\nsobre MA20',color:C.red},
        {label:'RSI diario\n>75 sostenido',color:C.orange},
        {label:'En titulares\nfinancieros',color:C.yellow},
        {label:'Stop > 2x\nobjetivo',color:'#8b0000'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    signs.forEach(({label,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="48" font-size="22" text-anchor="middle">⚠️</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${78+li*16}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="135" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Demasiado tarde</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Señales objetivas de que el R:R de entrar ahora es desfavorable</text>
    </svg>`;
}

function late_entry_alternatives() {
    const W=680, H=200;
    const options=[
        {label:'Esperar\npullback',desc:'Entrada en EMA\no soporte',color:C.accent,best:true},
        {label:'Reducir\ntamaño',desc:'Menos capital,\npeor R:R aceptado',color:C.yellow,best:false},
        {label:'Dejarlo\npasar',desc:'Esperar el\nsiguiente setup',color:C.cyan,best:true},
    ];
    const bw=200, gap=15, startX=20;
    let content='';
    options.forEach(({label,desc,color,best},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="${best?2:1}"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${42+li*16}" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${92+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(best) content+=`<text x="${x+bw/2}" y="145" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">✓ Recomendado</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Llegar tarde no impide participar — exige paciencia para mejor entrada</text>
    </svg>`;
}

function fomo_mechanism() {
    const W=680, H=200;
    const stages=['Ves el\nmovimiento','"Todos ganan\nmenos yo"','Entras sin\nanálisis','Compras\nel techo'];
    const bw=148, gap=9, startX=14;
    let content='';
    stages.forEach((label,i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        const color=i<2?C.yellow:C.red;
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="${0.06+i*0.02}" rx="6" stroke="${color}" stroke-width="1"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${75+li*16}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.red}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Es matemáticamente imposible capturar todos los movimientos — acéptalo</text>
    </svg>`;
}

function overtrading_definition() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="44" font-size="28" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="68" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="78" x2="${x0+panelW-20}" y2="78" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${100+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'TRADING DISCIPLINADO','Opera según\nsetups disponibles.\nFrecuencia variable.',C.accent,'🎯')}
        ${panel(panelW+35,'SOBRETRADING','Opera por necesidad\nde "hacer algo".\nFrecuencia constante.',C.red,'🔥')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Más trades no es más ganancias — frecuentemente lo contrario</text>
    </svg>`;
}

function overtrading_causes() {
    const W=680, H=210;
    const causes=[
        {label:'Aburrimiento',icon:'😑'},
        {label:'Revenge\ntrading',icon:'😡'},
        {label:'Adicción a\nla dopamina',icon:'⚡'},
        {label:'Sobreconfianza',icon:'😎'},
        {label:'FOMO\nacumulado',icon:'😱'},
    ];
    const bw=120, gap=10, startX=15;
    let content='';
    causes.forEach(({label,icon},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${C.red}" opacity="0.06" rx="6" stroke="${C.red}" stroke-width="1"/>
        <text x="${x+bw/2}" y="55" font-size="26" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${85+li*16}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Identificar la causa específica permite abordarla individualmente</text>
    </svg>`;
}

function overtrading_real_cost() {
    const W=680, H=210;
    const data=[
        {label:'5-10 trades/mes\n(calidad)',commission:50,color:C.accent},
        {label:'50 trades/mes\n(sobretrading)',commission:500,color:C.red},
    ];
    const bw=240, gap=40, startX=80, maxH=130, y0=20;
    let content='';
    data.forEach(({label,commission,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        const bh=(commission/550)*maxH;
        content+=`<rect x="${x+bw/2-40}" y="${y0+maxH-bh}" width="80" height="${bh}" fill="${color}" opacity="0.35" rx="4"/>
        <text x="${x+bw/2}" y="${y0+maxH-bh-10}" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">$${commission}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${y0+maxH+22+li*15}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    content+=`<line x1="${startX-10}" y1="${y0+maxH}" x2="${startX+bw+gap+bw+10}" y2="${y0+maxH}" stroke="${C.border}" stroke-width="1"/>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Comisiones y spread acumulados — coste estructural que erosiona la cuenta</text>
    </svg>`;
}

function overtrading_limits() {
    const W=680, H=210;
    const limits=[
        {label:'Límite diario',val:'2-3 trades',color:C.accent},
        {label:'Límite semanal',val:'Revisar domingo',color:C.cyan},
        {label:'Solo watchlist',val:'Nada improvisado',color:C.yellow},
        {label:'Cooldown',val:'1h tras stop',color:C.orange},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    limits.forEach(({label,val,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="48" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x+15}" y1="58" x2="${x+bw-15}" y2="58" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="95" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle">${val}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Límites mecánicos quitan la decisión del momento de presión emocional</text>
    </svg>`;
}

function why_ignore_volume() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=130;
    const prices=[100,103,101,105,102,107,104,109,106,111,108,113,110,115,112,117];
    const mn=94, mx=122, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const volH=40, volY=y0+h+12;
    const volumes=[40,42,38,80,35,90,40,30,38,95,42,35,40,38,90,45];
    const volMax=Math.max(...volumes);

    let candles='', vols='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.02),py(Math.min(prev,p)-range*0.016),bull,11);});
    volumes.forEach((v,i)=>{
        const cx=px(i), bh=(v/volMax)*volH, bull = i===0 || prices[i]>=prices[i-1];
        vols+=`<rect x="${(cx-5).toFixed(1)}" y="${(volY+volH-bh).toFixed(1)}" width="10" height="${bh.toFixed(1)}" fill="${bull?C.accent:C.red}" opacity="0.5"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <text x="${x0}" y="${volY-4}" fill="${C.muted}" font-size="8" font-family="monospace">VOLUMEN</text>
        ${vols}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mismo movimiento de precio — picos de volumen revelan dónde hay convicción real
        </text>
    </svg>`;
}

function volume_signals_ignored() {
    const W=680, H=200;
    const headers=['Patrón','Indica','Error común'];
    const rows=[
        ['Ruptura vol. bajo','Falsa ruptura prob.','Entrar igual'],
        ['Pullback vol. alto','Distribución','Comprar sin verificar'],
        ['Clímax en mínimos','Capitulación/suelo','No ver oportunidad'],
        ['Divergencia P-V','Perdiendo fuerza','Mantener sin cautela'],
    ];
    const colW=[170,170,170], startX=70, startY=25, rowH=38;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-8}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-8}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">${headers[1]}</text>
    <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${startY-8}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${headers[2]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]+colW[2]}" height="${rowH-4}" fill="${i%2===0?C.surface:'transparent'}" rx="3"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2}" fill="${C.text}" font-size="9" font-family="monospace" text-anchor="middle">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">${row[1]}</text>
        <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${y+rowH/2}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">${row[2]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function volume_integration_process() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'Identificar\nsetup',q:'¿Acumulación o\ndistribución?'},
        {n:'2',label:'Esperar\nconfirmación',q:'¿Trigger con\nvolumen alto?'},
        {n:'3',label:'Durante\nel trade',q:'¿Pullback con\nvol. bajo (sano)?'},
        {n:'4',label:'Considerar\nsalida',q:'¿Clímax o\ndivergencia?'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach(({n,label,q},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), qLines=q.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${C.cyan}" opacity="0.06" rx="6" stroke="${C.cyan}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="40" r="14" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="45" fill="${C.cyan}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${66+li*14}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        qLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${102+li*14}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El volumen integrado en cada fase, no solo como check final</text>
    </svg>`;
}

function volume_final_filter() {
    const W=680, H=190;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="${W/2-260}" y="20" width="520" height="55" fill="${C.surface}" stroke="${C.border}" stroke-width="1.5" rx="6"/>
        <text x="${W/2}" y="44" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">¿El volumen del día de la señal es</text>
        <text x="${W/2}" y="62" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">superior al promedio de 20 días?</text>
        <line x1="${W/2-100}" y1="80" x2="${W/2-150}" y2="115" stroke="${C.accent}" stroke-width="2"/>
        <line x1="${W/2+100}" y1="80" x2="${W/2+150}" y2="115" stroke="${C.orange}" stroke-width="2"/>
        <text x="${W/2-125}" y="100" fill="${C.accent}" font-size="11" font-family="monospace" text-anchor="middle">SÍ</text>
        <text x="${W/2+125}" y="100" fill="${C.orange}" font-size="11" font-family="monospace" text-anchor="middle">NO</text>
        <rect x="${W/2-260}" y="120" width="220" height="50" fill="${C.accent}" opacity="0.08" stroke="${C.accent}" stroke-width="1.5" rx="6"/>
        <text x="${W/2-150}" y="148" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">Alta convicción</text>
        <text x="${W/2-150}" y="162" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Tamaño normal</text>
        <rect x="${W/2+40}" y="120" width="220" height="50" fill="${C.orange}" opacity="0.08" stroke="${C.orange}" stroke-width="1.5" rx="6"/>
        <text x="${W/2+150}" y="148" fill="${C.orange}" font-size="10" font-family="monospace" text-anchor="middle">Especulativo</text>
        <text x="${W/2+150}" y="162" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Reducir tamaño o esperar</text>
    </svg>`;
}

// ─── MÓDULO 15: REVISIÓN POST-TRADE ──────────────────────────────────────────

function memory_unreliable() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'CAPTURA','Evidencia objetiva\ncongelada en el\nmomento exacto.',C.accent,'📸')}
        ${panel(panelW+35,'MEMORIA','Reconstruida para\nconfirmar la narrativa\nque ya tienes.',C.red,'🧠')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El sesgo retrospectivo distorsiona el recuerdo — la captura no</text>
    </svg>`;
}

function what_to_capture() {
    const W=680, H=200;
    const moments=[
        {n:'1',label:'PRE-ENTRADA',desc:'Gráfico con\nniveles marcados'},
        {n:'2',label:'AL ENTRAR',desc:'Vela de\nconfirmación'},
        {n:'3',label:'CONTEXTO MTF',desc:'M + S + D\nen el momento'},
        {n:'4',label:'AL SALIR',desc:'Stop u objetivo\nejecutado'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    moments.forEach(({n,label,desc},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.cyan}" opacity="0.06" rx="6" stroke="${C.cyan}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="42" r="16" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="47" fill="${C.cyan}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>
        <text x="${x+bw/2}" y="72" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${94+li*15}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">4 momentos clave documentan la evolución completa del trade</text>
    </svg>`;
}

function organize_screenshots() {
    const W=680, H=200;
    const tree=[
        {label:'📁 2026-06/',indent:0,color:C.accent},
        {label:'📁 NVDA_trade1/',indent:1,color:C.cyan},
        {label:'🖼️ pre-entrada.png',indent:2,color:C.muted},
        {label:'🖼️ entrada.png',indent:2,color:C.muted},
        {label:'🖼️ salida.png',indent:2,color:C.muted},
        {label:'📁 META_trade1/',indent:1,color:C.cyan},
        {label:'📄 journal.md',indent:1,color:C.yellow},
    ];
    let content='';
    tree.forEach(({label,indent,color},i)=>{
        const y=25+i*22;
        content+=`<text x="${40+indent*30}" y="${y}" fill="${color}" font-size="11" font-family="monospace">${label}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Estructura simple por mes/ticker — encontrar trades pasados en segundos</text>
    </svg>`;
}

function always_capture_discipline() {
    const W=680, H=190;
    const steps=['Definir\nstop','Definir\nobjetivo','Capturar\npantalla','Ejecutar'];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach((label,i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        const isCapture=i===2;
        content+=`<rect x="${x}" y="15" width="${bw}" height="140" fill="${isCapture?C.accent:C.surface}" opacity="${isCapture?0.12:1}" rx="6" stroke="${isCapture?C.accent:C.border}" stroke-width="${isCapture?2:1}"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${65+li*16}" fill="${isCapture?C.accent:C.muted}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="${isCapture?'bold':'normal'}">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Parte del checklist — no opcional, no solo "cuando sale interesante"</text>
    </svg>`;
}

function loss_vs_error() {
    const W=680, H=210;
    const quadrants=[
        {label:'Plan seguido\n+ pérdida',tag:'NO ES ERROR',color:C.accent},
        {label:'Plan seguido\n+ ganancia',tag:'CORRECTO',color:C.accent},
        {label:'Sin confirmación\n+ ganó',tag:'ERROR (suerte)',color:C.red},
        {label:'Movió el stop\n+ evitó pérdida',tag:'ERROR (suerte)',color:C.red},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    quadrants.forEach(({label,tag,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${50+li*16}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<rect x="${x+12}" y="125" width="${bw-24}" height="24" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="141" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${tag}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El resultado no determina si algo fue error — el proceso sí</text>
    </svg>`;
}

function error_categories() {
    const W=680, H=200;
    const cats=[
        {label:'Entrada',icon:'🎯',color:C.cyan},
        {label:'Gestión',icon:'⚙️',color:C.yellow},
        {label:'Salida',icon:'🚪',color:C.orange},
        {label:'Contexto',icon:'🌍',color:C.accent},
        {label:'Emocional',icon:'😤',color:C.red},
    ];
    const bw=120, gap=10, startX=15;
    let content='';
    cats.forEach(({label,icon,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="60" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x+bw/2}" y="90" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Clasificar permite ver patrones a lo largo del tiempo</text>
    </svg>`;
}

function error_log_format() {
    const W=680, H=200;
    const cols=[
        {label:'FECHA',val:'16/06'},
        {label:'TICKER',val:'NVDA'},
        {label:'CATEGORÍA',val:'Entrada'},
        {label:'QUÉ PASÓ',val:'Sin confirmar'},
        {label:'POR QUÉ',val:'FOMO'},
        {label:'PRÓXIMA VEZ',val:'Esperar cierre'},
    ];
    const colW=104, gap=4, startX=10;
    let content='';
    cols.forEach(({label,val},i)=>{
        const x=startX+i*(colW+gap);
        const isLast=i===5;
        content+=`<rect x="${x}" y="40" width="${colW}" height="120" fill="${isLast?C.accent:C.surface}" opacity="${isLast?0.1:1}" rx="4" stroke="${isLast?C.accent:C.border}" stroke-width="${isLast?2:1}"/>
        <text x="${x+colW/2}" y="58" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">${label}</text>
        <line x1="${x+8}" y1="65" x2="${x+colW-8}" y2="65" stroke="${C.border}" stroke-width="1"/>
        <text x="${x+colW/2}" y="100" fill="${isLast?C.accent:C.text}" font-size="9" font-family="monospace" text-anchor="middle">${val}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">"Próxima vez" es la columna que convierte el registro en aprendizaje</text>
    </svg>`;
}

function error_log_review() {
    const W=680, H=210;
    const errors=[
        {cat:'Entrada sin confirmación',pct:42,color:C.red},
        {cat:'Mover el stop',pct:25,color:C.orange},
        {cat:'Salida prematura',pct:18,color:C.yellow},
        {cat:'Sobretrading',pct:15,color:C.cyan},
    ];
    const barMaxW=320, startX=140, y0=25, rowH=38;
    let content='';
    errors.forEach(({cat,pct,color},i)=>{
        const y=y0+i*rowH;
        const bw=(pct/45)*barMaxW;
        content+=`<text x="130" y="${y+14}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="end">${cat}</text>
        <rect x="${startX}" y="${y}" width="${bw}" height="20" fill="${color}" opacity="0.3" rx="3"/>
        <text x="${startX+bw+8}" y="${y+14}" fill="${color}" font-size="11" font-family="monospace" font-weight="bold">${pct}%</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Revisión mensual: la categoría más frecuente es tu prioridad del próximo mes</text>
    </svg>`;
}

function setup_quality_separate() {
    const W=680, H=210;
    const quadrants=[
        {label:'Buen análisis\n+ Ganó',color:C.accent,desc:'Repetir'},
        {label:'Buen análisis\n+ Perdió',color:C.cyan,desc:'Seguir igual'},
        {label:'Mal análisis\n+ Ganó',color:'#8b0000',desc:'⚠ Peligroso'},
        {label:'Mal análisis\n+ Perdió',color:C.orange,desc:'Corregir'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    quadrants.forEach(({label,color,desc},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="${i===2?2:1}"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${55+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<rect x="${x+12}" y="130" width="${bw-24}" height="22" fill="${color}" opacity="0.2" rx="3"/>
        <text x="${x+bw/2}" y="145" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${desc}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">"Mal análisis + ganó" refuerza erróneamente comportamientos a corregir</text>
    </svg>`;
}

function setup_review_questions() {
    const W=680, H=200;
    const questions=[
        '¿Contexto M/S alineado al entrar?',
        '¿R:R ≥ 1:2 con base técnica real?',
        '¿Stop en nivel técnicamente válido?',
        '¿Confirmación de volumen en trigger?',
        '¿Setup estaba en la watchlist previa?',
    ];
    let content='';
    questions.forEach((q,i)=>{
        const y=25+i*32;
        content+=`<rect x="20" y="${y}" width="${W-40}" height="26" fill="${C.cyan}" opacity="0.05" rx="4"/>
        <text x="32" y="${y+18}" fill="${C.cyan}" font-size="11" font-family="monospace">☑ ${q}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function identify_best_setups() {
    const W=680, H=210;
    const setups=[
        {label:'Retroceso\nEMA21',pct:67,color:C.accent},
        {label:'Ruptura\nde base',pct:56,color:C.cyan},
        {label:'Reversión\ndesde suelo',pct:50,color:C.yellow},
        {label:'Ruptura\ntriángulo',pct:60,color:C.orange},
    ];
    const bw=148, gap=9, startX=14, maxH=120, y0=20;
    let content='';
    setups.forEach(({label,pct,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        const bh=(pct/75)*maxH;
        content+=`<rect x="${x+bw/2-25}" y="${y0+maxH-bh}" width="50" height="${bh}" fill="${color}" opacity="0.3" rx="4"/>
        <text x="${x+bw/2}" y="${y0+maxH-bh-8}" fill="${color}" font-size="14" font-family="monospace" text-anchor="middle" font-weight="bold">${pct}%</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${y0+maxH+18+li*15}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    content+=`<line x1="${startX-5}" y1="${y0+maxH}" x2="${startX+4*(bw+gap)}" y2="${y0+maxH}" stroke="${C.border}" stroke-width="1"/>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Tu edge personal documentado — más valioso que cualquier estrategia genérica</text>
    </svg>`;
}

function specialize_setups() {
    const W=680, H=190;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="155" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'ESPECIALIZARSE','Concentrar esfuerzo\nen tus setups de\nmejor edge documentado',C.accent,'🎯')}
        ${panel(panelW+35,'DIVERSIFICAR TODO','Operar cualquier setup\nteóricamente válido\nsin distinción',C.muted,'🎲')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function data_to_wisdom() {
    const W=680, H=200;
    const stages=[
        {label:'1 trade',desc:'Poca\ninformación',color:C.muted},
        {label:'20 trades',desc:'Patrones\nemergiendo',color:C.cyan},
        {label:'100 trades',desc:'Edge personal\nclaro',color:C.accent},
    ];
    const bw=200, gap=15, startX=20;
    let content='';
    stages.forEach(({label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="${0.05+i*0.04}" rx="6" stroke="${color}" stroke-width="${1+i*0.5}"/>
        <text x="${x+bw/2}" y="60" fill="${color}" font-size="18" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${90+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<2) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.accent}" font-size="16" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El aprendizaje compuesto de revisiones sistemáticas se acelera con el tiempo</text>
    </svg>`;
}

function lessons_document_structure() {
    const W=680, H=200;
    const sections=[
        {title:'MIS MEJORES\nSETUPS',color:C.accent},
        {title:'MIS ERRORES\nRECURRENTES',color:C.red},
        {title:'CONDICIONES\nÓPTIMAS',color:C.cyan},
        {title:'REGLAS\nPERSONALES',color:C.yellow},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    sections.forEach(({title,color},i)=>{
        const x=startX+i*(bw+gap);
        const titleLines=title.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>`;
        titleLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${75+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Documento vivo — se actualiza y refina con cada revisión periódica</text>
    </svg>`;
}

function personal_rules_evidence() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'Identificar\npatrón'},
        {n:'2',label:'Verificar\nmuestra ≥10'},
        {n:'3',label:'Formular\nregla'},
        {n:'4',label:'Añadir a\nchecklist'},
        {n:'5',label:'Revisar\ncada 3 meses'},
    ];
    const bw=116, gap=8, startX=12;
    let content='';
    steps.forEach(({n,label},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.yellow}" opacity="0.06" rx="6" stroke="${C.yellow}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="42" r="14" fill="${C.yellow}" opacity="0.2" stroke="${C.yellow}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="47" fill="${C.yellow}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${70+li*14}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<4) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="12" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Reglas con peso real porque están respaldadas por tus propios datos</text>
    </svg>`;
}

function continuous_improvement_cycle() {
    const W=680, H=220;
    const cx=W/2, cy=H/2-5, r=85;
    const stages=[
        {label:'Plan de\ntrade',angle:-90},
        {label:'Ejecución',angle:0},
        {label:'Revisión',angle:90},
        {label:'Lecciones\naprendidas',angle:180},
    ];
    let content='';
    stages.forEach(({label,angle},i)=>{
        const rad=angle*Math.PI/180;
        const x=cx+r*Math.cos(rad), y=cy+r*Math.sin(rad);
        const labelLines=label.split('\n');
        content+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="38" fill="${C.accent}" opacity="0.1" stroke="${C.accent}" stroke-width="1.5"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x.toFixed(1)}" y="${(y+4+li*13-(labelLines.length-1)*6).toFixed(1)}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    // Arrows between stages
    for(let i=0;i<4;i++){
        const a1=stages[i].angle*Math.PI/180, a2=stages[(i+1)%4].angle*Math.PI/180;
        const x1=cx+r*0.55*Math.cos(a1+0.3), y1=cy+r*0.55*Math.sin(a1+0.3);
        const x2=cx+r*0.55*Math.cos(a2-0.3), y2=cy+r*0.55*Math.sin(a2-0.3);
    }
    content+=`<circle cx="${cx}" cy="${cy}" r="${r*0.55}" fill="none" stroke="${C.muted}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El ciclo se repite — cada vuelta mejora la siguiente</text>
    </svg>`;
}

// ─── MÓDULO 16: LAS 4 ETAPAS (WEINSTEIN) ─────────────────────────────────────

function four_stages_overview() {
    const W=680, H=240;
    const x0=30, y0=15, w=W-60, h=175;
    // Synthetic full-cycle price path: stage1 range -> stage2 up -> stage3 top -> stage4 down -> stage1 again
    const prices=[
        60,63,59,62,58,61,59,63,60,62,            // Stage 1 (range)
        64,68,72,69,75,80,77,84,90,87,94,100,      // Stage 2 (up)
        102,99,104,100,106,101,105,99,103,         // Stage 3 (top)
        95,88,82,86,76,70,74,64,58,60,             // Stage 4 (down)
        58,61,57,60,                                // Stage 1 again
    ];
    const mn=52, mx=108, range=mx-mn;
    const n=prices.length;
    const px=(i)=>x0+(i/(n-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.018),py(Math.min(prev,p)-range*0.015),bull,7);});

    // MA30 smoothed-ish line (simple visual approximation)
    let ma=prices[0], maLine=[ma];
    prices.slice(1).forEach(p=>{ ma = ma*0.88 + p*0.12; maLine.push(ma); });
    const maPath=maLine.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const stageRanges=[
        {label:'ETAPA 1', from:0, to:9, color:C.muted},
        {label:'ETAPA 2', from:10, to:21, color:C.accent},
        {label:'ETAPA 3', from:22, to:30, color:C.yellow},
        {label:'ETAPA 4', from:31, to:40, color:C.red},
        {label:'ETAPA 1', from:41, to:44, color:C.muted},
    ];
    let bands='', labels='';
    stageRanges.forEach(({label,from,to,color})=>{
        const xFrom=px(from), xTo=px(to);
        bands+=`<rect x="${xFrom.toFixed(1)}" y="${y0}" width="${(xTo-xFrom).toFixed(1)}" height="${h}" fill="${color}" opacity="0.06"/>`;
        labels+=`<text x="${((xFrom+xTo)/2).toFixed(1)}" y="${y0+h+16}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${bands}
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.cyan}" stroke-width="1.5" opacity="0.8"/>
        ${labels}
        <text x="${x0+5}" y="${y0+12}" fill="${C.cyan}" font-size="8" font-family="monospace">MA 30 semanas</text>
        <text x="${W/2}" y="${H-4}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El ciclo completo de Weinstein — gráfico semanal, 4 etapas recurrentes
        </text>
    </svg>`;
}

function stage1_anatomy() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[60,63,59,62,57,61,59,64,58,62,60,63,58,61,59,62];
    const mn=52, mx=70, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,12);});

    const topY=py(64), botY=py(57);
    let ma=prices[0], maLine=[ma]; prices.slice(1).forEach(p=>{ma=ma*0.85+p*0.15; maLine.push(ma);});
    const maPath=maLine.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${topY}" width="${w}" height="${(botY-topY).toFixed(1)}" fill="${C.muted}" opacity="0.06"/>
        <line x1="${x0}" y1="${topY}" x2="${x0+w}" y2="${topY}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="5,4" opacity="0.6"/>
        <line x1="${x0}" y1="${botY}" x2="${x0+w}" y2="${botY}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="5,4" opacity="0.6"/>
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x0+w+4}" y="${topY+4}" fill="${C.muted}" font-size="9" font-family="monospace">Techo del rango</text>
        <text x="${x0+w+4}" y="${botY+4}" fill="${C.muted}" font-size="9" font-family="monospace">Suelo del rango</text>
        <text x="${x0+5}" y="${y0+12}" fill="${C.cyan}" font-size="8" font-family="monospace">MA 30 semanas (aplanada)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Rango horizontal · precio cruza la MA en ambas direcciones sin tendencia clara
        </text>
    </svg>`;
}

function stage1_accumulation_process() {
    const W=680, H=200;
    const groups=[
        {label:'Vendedores\nexhaustos',desc:'Compraron en\nmáximos previos,\ncapitulan ahora',color:C.red,icon:'😩'},
        {label:'Compradores\npacientes',desc:'Acumulan posición\nde forma discreta,\nsin prisa',color:C.accent,icon:'🧐'},
    ];
    const bw=280, gap=40, startX=40;
    let content='';
    groups.forEach(({label,desc,color,icon},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="160" fill="${color}" opacity="0.06" rx="8" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="55" font-size="32" text-anchor="middle">${icon}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${82+li*16}" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${(label.split('\\n').length*16+100)+li*15}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    content+=`<text x="${W/2}" y="${H/2+5}" fill="${C.muted}" font-size="18" text-anchor="middle">⇄</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El rango es una transferencia silenciosa de propiedad entre dos perfiles opuestos</text>
    </svg>`;
}

function stage1_identification_signals() {
    const W=680, H=200;
    const signals=[
        'MA 30 semanas sin pendiente clara',
        'Precio toca techo y suelo del rango ≥2 veces',
        'Sin secuencia clara de HH/HL',
        'Viene de una caída prolongada (Etapa 4 previa)',
    ];
    let content='';
    signals.forEach((s,i)=>{
        const y=25+i*38;
        content+=`<rect x="20" y="${y}" width="${W-40}" height="30" fill="${C.muted}" opacity="0.05" rx="5"/>
        <circle cx="40" cy="${y+15}" r="10" fill="${C.muted}" opacity="0.2" stroke="${C.muted}" stroke-width="1.5"/>
        <text x="40" y="${y+19}" fill="${C.muted}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${i+1}</text>
        <text x="60" y="${y+19}" fill="${C.text}" font-size="11" font-family="monospace">${s}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function stage2_breakout() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[60,62,59,61,58,62,60,68,72,69,75,80,77,84,90,87];
    const mn=52, mx=94, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const resY=py(64), breakoutX=px(7), throwbackX=px(9);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.muted}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${breakoutX}" cy="${py(68)}" r="7" fill="${C.accent}" opacity="0.3" stroke="${C.accent}" stroke-width="2"/>
        <text x="${breakoutX}" y="${(py(68)-14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA + VOL</text>
        <circle cx="${throwbackX}" cy="${py(69)}" r="6" fill="${C.cyan}" opacity="0.4" stroke="${C.cyan}" stroke-width="2"/>
        <text x="${throwbackX}" y="${(py(69)+18).toFixed(1)}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">THROWBACK</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.muted}" font-size="9" font-family="monospace">EX-TECHO RANGO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura con volumen alto → throwback al ex-techo (ahora soporte) → continuación
        </text>
    </svg>`;
}

function stage2_confirmation_signs() {
    const W=680, H=200;
    const headers=['Señal','Cómo se manifiesta'];
    const rows=[
        ['Estructura','HH y HL consistentes'],
        ['MA 30 semanas','Gira arriba, queda bajo el precio'],
        ['Relación c/ MA','Precio sostenido sobre la media'],
        ['Mínimo inicial','Doble suelo poco perfecto'],
        ['Volumen','Se expande en impulsos alcistas'],
    ];
    const colW=[170,330], startX=80, startY=25, rowH=32;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-8}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-8}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${headers[1]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]}" height="${rowH-4}" fill="${i%2===0?C.surface:'transparent'}" rx="3"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2}" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${row[1]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function stage2_higher_lows_rule() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[60,66,63,72,68,80,74,88,82,96];
    const mn=55, mx=100, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,16);});

    // Mark lows at indices 2,4,6,8 (the dips)
    const lowIdx=[2,4,6,8];
    let lowMarks='';
    lowIdx.forEach((idx,i)=>{
        const x=px(idx), y=py(prices[idx]);
        lowMarks+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" fill="${C.accent}" opacity="0.6"/>
        <text x="${x.toFixed(1)}" y="${(y+18).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">HL${i+1}</text>`;
    });
    const lowPath=lowIdx.map((idx,i)=>`${i===0?'M':'L'} ${px(idx).toFixed(1)} ${py(prices[idx]).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${lowPath}" fill="none" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.7"/>
        ${lowMarks}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cada mínimo más alto que el anterior — sin esto, no es Etapa 2 verdadera
        </text>
    </svg>`;
}

function stage2_exit_signal() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[70,75,80,85,90,86,88,82,78,74,70,66];
    const mn=60, mx=94, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,14);});

    let ma=prices[0], maLine=[ma]; prices.slice(1).forEach(p=>{ma=ma*0.82+p*0.18; maLine.push(ma);});
    const maPath=maLine.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    const crossX=px(8.5);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.cyan}" stroke-width="1.5"/>
        <line x1="${crossX}" y1="${y0}" x2="${crossX}" y2="${y0+h}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="${crossX}" y="${y0+h+14}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Precio cierra bajo MA30</text>
        <text x="${x0+5}" y="${y0+12}" fill="${C.cyan}" font-size="8" font-family="monospace">MA 30 semanas</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mientras el precio respeta la MA → mantener. Al cerrar por debajo → alerta de Etapa 3
        </text>
    </svg>`;
}

function stage3_formation() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[88,95,90,98,92,99,93,97,91,96,90,94];
    const mn=84, mx=104, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,16);});

    let ma=prices[0]-3, maLine=[ma]; prices.slice(1).forEach(p=>{ma=ma*0.92+p*0.08; maLine.push(ma);});
    const maPath=maLine.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x0+5}" y="${y0+12}" fill="${C.cyan}" font-size="8" font-family="monospace">MA 30 semanas (aplanándose)</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Picos y valles pronunciados — el precio busca nueva dirección sin encontrarla
        </text>
    </svg>`;
}

function stage3_trader_vs_investor() {
    const W=680, H=210;
    const headers=['Perfil','Acción recomendada'];
    const rows=[
        ['Trader','Tomar beneficios — la tendencia ya no está presente'],
        ['Inversor','Vender la mitad, mantener el resto'],
        ['Si reanuda Etapa 2','Mantener / recomprar la parte vendida'],
        ['Si rompe a la baja','Vender el resto sin excepción'],
    ];
    const colW=[150,380], startX=70, startY=25, rowH=38;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-8}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-8}" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="middle">${headers[1]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]}" height="${rowH-4}" fill="${i%2===0?C.surface:'transparent'}" rx="3"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2}" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2}" fill="${C.yellow}" font-size="10" font-family="monospace" text-anchor="middle">${row[1]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function stage3_volume_ambiguity() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=120;
    const prices=[90,96,91,97,92,98,91,96];
    const volumes=[40,70,35,85,30,90,55,60]; // ambiguous, no clear pattern vs outcome
    const mn=85, mx=102, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const volY=y0+h+15, volH=35, volMax=Math.max(...volumes);

    let candles='', vols='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,18);});
    volumes.forEach((v,i)=>{
        const cx=px(i), bh=(v/volMax)*volH;
        vols+=`<rect x="${(cx-9).toFixed(1)}" y="${(volY+volH-bh).toFixed(1)}" width="18" height="${bh.toFixed(1)}" fill="${C.yellow}" opacity="0.4"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <text x="${x0}" y="${volY-4}" fill="${C.muted}" font-size="8" font-family="monospace">VOLUMEN — patrón irregular, sin señal clara</text>
        ${vols}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El volumen sube y baja sin avisar si el resultado será ruptura alcista o bajista
        </text>
    </svg>`;
}

function stage3_vs_pullback() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="36" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="46" x2="${x0+panelW-20}" y2="46" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${72+li*18}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'PULLBACK EN ETAPA 2',
            'Breve (días-semanas)\nRespeta la MA30 como soporte\nSigue habiendo HL',C.accent)}
        ${panel(panelW+35,'INICIO DE ETAPA 3',
            'Extenso (semanas-meses)\nCruza la MA30 repetidamente\nLa progresión de HL se rompe',C.yellow)}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Ante la duda, trata la situación como posible Etapa 3 hasta confirmar lo contrario</text>
    </svg>`;
}

function stage4_breakdown() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[96,92,95,88,91,84,87,78,81,72,75,66];
    const mn=60, mx=100, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,14);});

    const supY=py(88), breakX=px(3), pullbackX=px(5);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.muted}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${breakX}" cy="${py(88)}" r="6" fill="${C.red}" opacity="0.4" stroke="${C.red}" stroke-width="2"/>
        <text x="${breakX}" y="${(py(88)+18).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">RUPTURA BAJISTA</text>
        <circle cx="${pullbackX}" cy="${py(91)}" r="5" fill="${C.orange}" opacity="0.4" stroke="${C.orange}" stroke-width="2"/>
        <text x="${pullbackX}" y="${(py(91)-12).toFixed(1)}" fill="${C.orange}" font-size="9" font-family="monospace" text-anchor="middle">Pullback al nivel</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.muted}" font-size="9" font-family="monospace">EX-SOPORTE ETAPA 3</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Ruptura del rango de Etapa 3 → posible pullback → continuación bajista sostenida
        </text>
    </svg>`;
}

function stage4_ma_resistance() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=150;
    const prices=[90,84,87,78,81,72,75,68,71,64];
    const mn=58, mx=94, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,16);});

    let ma=92, maLine=[ma]; prices.slice(1).forEach(p=>{ma=ma*0.93+p*0.07-0.3; maLine.push(ma);});
    const maPath=maLine.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <path d="${maPath}" fill="none" stroke="${C.red}" stroke-width="1.5"/>
        <text x="${x0+5}" y="${y0+12}" fill="${C.red}" font-size="8" font-family="monospace">MA 30 semanas — resistencia dinámica</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La MA queda por encima del precio durante toda la Etapa 4 — rebotes pierden fuerza ahí
        </text>
    </svg>`;
}

function stage4_buying_trap() {
    const W=680, H=200;
    const x0=40, y0=15, w=W-80, h=120;
    const prices=[100,90,80,70,60,52,46,42];
    const mn=38, mx=104, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const path=prices.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    let content='';
    [2,4,6].forEach((idx,i)=>{
        const x=px(idx), y=py(prices[idx]);
        content+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="6" fill="${C.red}" opacity="0.3" stroke="${C.red}" stroke-width="2"/>
        <text x="${x.toFixed(1)}" y="${(y-12).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">"¡Es una ganga!"</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${path}" fill="none" stroke="${C.red}" stroke-width="2"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Cada nivel "parece barato" comparado con el anterior — y sigue cayendo
        </text>
    </svg>`;
}

function stage4_to_stage1_cycle() {
    const W=680, H=240;
    const cx=W/2, cy=H/2-10, r=85;
    const stages=[
        {label:'1 — Acumulación',angle:-90,color:C.muted},
        {label:'2 — Avance',angle:0,color:C.accent},
        {label:'3 — Distribución',angle:90,color:C.yellow},
        {label:'4 — Declive',angle:180,color:C.red},
    ];
    let content='';
    // Arc arrows between stages
    for(let i=0;i<4;i++){
        const a1=(stages[i].angle+25)*Math.PI/180;
        const a2=(stages[(i+1)%4].angle-25)*Math.PI/180;
        const largeArc = 0;
        const x1=cx+r*Math.cos(a1), y1=cy+r*Math.sin(a1);
        const x2=cx+r*Math.cos(a2), y2=cy+r*Math.sin(a2);
        content+=`<path d="M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}" fill="none" stroke="${C.muted}" stroke-width="1.5" opacity="0.4" marker-end="url(#arrow)"/>`;
    }
    stages.forEach(({label,angle,color})=>{
        const rad=angle*Math.PI/180;
        const x=cx+r*Math.cos(rad), y=cy+r*Math.sin(rad);
        content+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="40" fill="${color}" opacity="0.1" stroke="${color}" stroke-width="2"/>
        <text x="${x.toFixed(1)}" y="${(y+4).toFixed(1)}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="${C.muted}" opacity="0.5"/></marker></defs>
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El ciclo se repite indefinidamente — cada etapa contiene la semilla de la siguiente</text>
    </svg>`;
}

// ─── MÓDULO 17: EL MERCADO DESCUENTA INFORMACIÓN ─────────────────────────────

function discounting_machine_concept() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    // Price rises ahead of "event", flat after confirmation
    const prices=[100,101,103,105,108,112,116,119,122,124,125,124,125,124,125,124];
    const mn=96, mx=130, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const eventX=px(10);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${y0}" width="${(eventX-x0).toFixed(1)}" height="${h}" fill="${C.cyan}" opacity="0.05"/>
        <rect x="${eventX.toFixed(1)}" y="${y0}" width="${(x0+w-eventX).toFixed(1)}" height="${h}" fill="${C.muted}" opacity="0.04"/>
        ${candles}
        <line x1="${eventX}" y1="${y0}" x2="${eventX}" y2="${y0+h}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="${eventX}" y="${y0-3}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">EVENTO CONFIRMADO</text>
        <text x="${(x0+eventX)/2}" y="${y0+h+16}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">Anticipación (descuento)</text>
        <text x="${(eventX+x0+w)/2}" y="${y0+h+16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Sin sorpresa = sin movimiento</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El precio sube ANTES del evento — al confirmarse, ya no queda sorpresa que mover
        </text>
    </svg>`;
}

function discounting_horizon_types() {
    const W=680, H=210;
    const types=[
        {label:'Programado\npredecible',horizon:'Semanas-meses',color:C.accent},
        {label:'Programado\nincierto',horizon:'Días antes',color:C.cyan},
        {label:'Sorpresa\nno programada',horizon:'Sin descuento',color:C.red},
        {label:'Tendencial\ngradual',horizon:'Continuo',color:C.yellow},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    types.forEach(({label,horizon,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${45+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        content+=`<line x1="${x+15}" y1="80" x2="${x+bw-15}" y2="80" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <text x="${x+bw/2}" y="105" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Horizonte:</text>
        <text x="${x+bw/2}" y="122" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${horizon}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">No todos los eventos se descuentan con la misma anticipación</text>
    </svg>`;
}

function already_priced_in() {
    const W=680, H=200;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <rect x="${W/2-260}" y="20" width="520" height="50" fill="${C.surface}" stroke="${C.border}" stroke-width="1.5" rx="6"/>
        <text x="${W/2}" y="50" fill="${C.text}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">"Esta empresa va a tener un trimestre excelente"</text>
        <line x1="${W/2}" y1="75" x2="${W/2}" y2="100" stroke="${C.muted}" stroke-width="2"/>
        <rect x="${W/2-280}" y="105" width="260" height="70" fill="${C.red}" opacity="0.07" stroke="${C.red}" stroke-width="1.5" rx="6"/>
        <text x="${W/2-150}" y="128" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">Si es consenso público</text>
        <text x="${W/2-150}" y="146" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Ya está en el precio</text>
        <text x="${W/2-150}" y="161" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">No es ventaja explotable</text>
        <rect x="${W/2+20}" y="105" width="260" height="70" fill="${C.accent}" opacity="0.07" stroke="${C.accent}" stroke-width="1.5" rx="6"/>
        <text x="${W/2+150}" y="128" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">La pregunta correcta</text>
        <text x="${W/2+150}" y="146" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">¿Mejor que lo YA esperado?</text>
        <text x="${W/2+150}" y="161" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Mucho más difícil de saber</text>
    </svg>`;
}

function discounting_practical_implications() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'¿Qué expectativa\nya refleja el precio?'},
        {n:'2',label:'Observa el movimiento\nde semanas previas'},
        {n:'3',label:'Compara resultado vs\nexpectativa, no absoluto'},
        {n:'4',label:'"Buena noticia" puede\ncaer si fue descontada'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach(({n,label},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.cyan}" opacity="0.06" rx="6" stroke="${C.cyan}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="42" r="16" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="47" fill="${C.cyan}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${75+li*15}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El movimiento previo al evento es tan informativo como el posterior</text>
    </svg>`;
}

function buy_rumour_anatomy() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,101,103,102,105,108,107,111,115,114,119,124,122,128,134,138];
    const mn=96, mx=142, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${y0}" width="${px(5)-x0}" height="${h}" fill="${C.muted}" opacity="0.04"/>
        <rect x="${px(5)}" y="${y0}" width="${px(11)-px(5)}" height="${h}" fill="${C.cyan}" opacity="0.05"/>
        <rect x="${px(11)}" y="${y0}" width="${x0+w-px(11)}" height="${h}" fill="${C.accent}" opacity="0.06"/>
        ${candles}
        <text x="${px(2.5)}" y="${y0+h+16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">Surge expectativa</text>
        <text x="${px(8)}" y="${y0+h+16}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">Posicionamiento</text>
        <text x="${px(13.5)}" y="${y0+h+16}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Refuerzo / FOMO</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La subida atrae más compradores que extrapolan el movimiento como confirmación
        </text>
    </svg>`;
}

function who_buys_rumour_first() {
    const W=680, H=210;
    const phases=[
        {label:'Temprana',who:'Analistas\nespecializados',vol:'Bajo',color:C.muted},
        {label:'Media',who:'Medios financieros\ntraders técnicos',vol:'Medio',color:C.cyan},
        {label:'Tardía',who:'Público general\nredes sociales',vol:'Alto',color:C.yellow},
        {label:'Pico',who:'Casi todos\nya posicionados',vol:'Máximo',color:C.red},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    phases.forEach(({label,who,vol,color},i)=>{
        const x=startX+i*(bw+gap);
        const whoLines=who.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x+bw/2}" y="38" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x+15}" y1="48" x2="${x+bw-15}" y2="48" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        whoLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${72+li*15}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="135" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">Volumen: ${vol}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">No todos acceden a la misma información al mismo tiempo</text>
    </svg>`;
}

function identify_rumour_phase() {
    const W=680, H=200;
    const signals=[
        'Evento conocido con fecha aproximada cercana',
        'Precio sube más que el sector sin catalizador confirmado',
        'Narrativa en medios centrada en el evento próximo',
        'Volumen y volatilidad implícita aumentando',
    ];
    let content='';
    signals.forEach((s,i)=>{
        const y=25+i*38;
        content+=`<rect x="20" y="${y}" width="${W-40}" height="30" fill="${C.cyan}" opacity="0.05" rx="5"/>
        <circle cx="40" cy="${y+15}" r="10" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="40" y="${y+19}" fill="${C.cyan}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${i+1}</text>
        <text x="60" y="${y+19}" fill="${C.text}" font-size="11" font-family="monospace">${s}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function late_rumour_risk() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=150;
    const prices=[100,104,108,114,120,128,136,142,146,148];
    const mn=96, mx=152, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const path=prices.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const earlyX=px(2), lateX=px(8);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${path}" fill="none" stroke="${C.yellow}" stroke-width="2"/>
        <circle cx="${earlyX}" cy="${py(108)}" r="7" fill="${C.accent}" opacity="0.3" stroke="${C.accent}" stroke-width="2"/>
        <text x="${earlyX}" y="${(py(108)-14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Entrada temprana</text>
        <text x="${earlyX}" y="${(py(108)-26).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">mejor R:R</text>
        <circle cx="${lateX}" cy="${py(146)}" r="7" fill="${C.red}" opacity="0.3" stroke="${C.red}" stroke-width="2"/>
        <text x="${lateX}" y="${(py(146)-14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Entrada tardía</text>
        <text x="${lateX}" y="${(py(146)-26).toFixed(1)}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">poco recorrido, alto riesgo</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La mejor relación riesgo-recompensa está en las fases temprana y media
        </text>
    </svg>`;
}

function sell_news_mechanism() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,104,108,114,120,128,134,138,134,128,124,120,122,120,118,119];
    const mn=96, mx=142, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const eventX=px(7);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${y0}" width="${(eventX-x0).toFixed(1)}" height="${h}" fill="${C.accent}" opacity="0.05"/>
        <rect x="${eventX.toFixed(1)}" y="${y0}" width="${(x0+w-eventX).toFixed(1)}" height="${h}" fill="${C.red}" opacity="0.05"/>
        ${candles}
        <line x1="${eventX}" y1="${y0}" x2="${eventX}" y2="${y0+h}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="${eventX}" y="${y0-3}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">SE CONFIRMA LA NOTICIA</text>
        <text x="${(x0+eventX)/2}" y="${y0+h+16}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Comprar el rumor</text>
        <text x="${(eventX+x0+w)/2}" y="${y0+h+16}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Vender la noticia</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El catalizador desaparece al confirmarse — toma de beneficios generalizada
        </text>
    </svg>`;
}

function three_outcome_scenarios() {
    const W=680, H=210;
    const scenarios=[
        {label:'Supera lo\ndescontado',reaction:'Sube más',color:C.accent,arrow:'↑'},
        {label:'Cumple lo\ndescontado',reaction:'Cae / lateral',color:C.yellow,arrow:'→'},
        {label:'No alcanza lo\ndescontado',reaction:'Cae fuerte',color:C.red,arrow:'↓'},
    ];
    const bw=200, gap=15, startX=20;
    let content='';
    scenarios.forEach(({label,reaction,color,arrow},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${45+li*17}" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        content+=`<text x="${x+bw/2}" y="105" font-size="30" text-anchor="middle" fill="${color}">${arrow}</text>
        <text x="${x+bw/2}" y="140" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle">${reaction}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Lo que mueve el precio es la sorpresa relativa, no el resultado absoluto</text>
    </svg>`;
}

function sell_news_vs_real_change() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'SELL THE NEWS','Mecánica de\ndescuento normal.\nToma de beneficios.',C.yellow,'⚙️')}
        ${panel(panelW+35,'CAMBIO DE TESIS REAL','Guidance débil,\ncomentarios de gestión,\ninfo nueva genuina.',C.red,'🔍')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Revisa si hay contenido sustantivo antes de asumir solo mecánica de descuento</text>
    </svg>`;
}

function trading_around_known_events() {
    const W=680, H=210;
    const tips=[
        {label:'Ya tienes\nposición',action:'Reduce parcial\nantes del evento',color:C.accent},
        {label:'Considerando\nentrar',action:'Evalúa si el R:R\nsigue siendo bueno',color:C.cyan},
        {label:'Resultado muy\nincierto',action:'Volatilidad implícita\nalta — cuidado',color:C.yellow},
        {label:'Tras el\nevento',action:'Espera confirmación,\nno reacciones al ruido',color:C.orange},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    tips.forEach(({label,action,color},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), actionLines=action.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="165" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${42+li*16}" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${l}</text>`; });
        content+=`<line x1="${x+15}" y1="74" x2="${x+bw-15}" y2="74" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        actionLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${98+li*16}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Calibrar riesgo y timing distinto a si el evento no existiera</text>
    </svg>`;
}

function earnings_guidance_importance() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,pct){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="36" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="22" font-family="monospace" text-anchor="middle" font-weight="bold">${pct}</text>
        <line x1="${x0+20}" y1="78" x2="${x0+panelW-20}" y2="78" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${100+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'CIFRA YA DESCONTADA',
            'Datos macro + comentarios\nprevios + indicadores\nde sector','#888','histórico')}
        ${panel(panelW+35,'GUIDANCE — INFO NUEVA',
            'No estaba descontado.\nMueve el precio\nmás significativamente',C.cyan,'futuro')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function post_earnings_reaction_timeline() {
    const W=680, H=200;
    const moments=[
        {label:'After-hours',desc:'Alta volatilidad,\nbaja liquidez'},
        {label:'Conference call',desc:'Ajustes por\ncomentarios gestión'},
        {label:'Apertura\nsiguiente',desc:'Más informada,\nmayor liquidez'},
        {label:'Días\nposteriores',desc:'Revisiones de\nanalistas'},
    ];
    const bw=148, gap=9, startX=14;
    let content='';
    moments.forEach(({label,desc},i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n'), descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${C.cyan}" opacity="0.06" rx="6" stroke="${C.cyan}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="38" r="13" fill="${C.cyan}" opacity="0.2" stroke="${C.cyan}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="43" fill="${C.cyan}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${i+1}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${65+li*15}" fill="${C.cyan}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${(65+label.split('\\n').length*15+15)+li*14}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2+4}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">La reacción inicial no siempre es la interpretación final del mercado</text>
    </svg>`;
}

function fed_decision_discounting() {
    const W=680, H=200;
    const bars=[
        {label:'Mantener',pct:15,color:C.muted},
        {label:'-25bp',pct:70,color:C.accent},
        {label:'-50bp',pct:15,color:C.cyan},
    ];
    const barMaxW=320, startX=160, y0=30, rowH=42;
    let content='<text x="' + (W/2) + '" y="18" fill="' + C.muted + '" font-size="10" font-family="monospace" text-anchor="middle">Probabilidad implícita en futuros de tipos (ejemplo)</text>';
    bars.forEach(({label,pct,color},i)=>{
        const y=y0+i*rowH;
        const bw=(pct/75)*barMaxW;
        content+=`<text x="150" y="${y+14}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="end">${label}</text>
        <rect x="${startX}" y="${y}" width="${bw}" height="22" fill="${color}" opacity="0.3" rx="3"/>
        <text x="${startX+bw+8}" y="${y+15}" fill="${color}" font-size="11" font-family="monospace" font-weight="bold">${pct}%</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El verdadero movimiento suele venir del tono (hawkish/dovish), no de la decisión esperada</text>
    </svg>`;
}

function pre_event_checklist() {
    const W=680, H=210;
    const questions=[
        '¿Qué expectativa de consenso ya refleja el precio?',
        '¿Cómo se movió el precio en semanas previas?',
        '¿Volatilidad implícita elevada o normal?',
        '¿Qué movimiento sería razonable si se cumple el consenso?',
    ];
    let content='';
    questions.forEach((q,i)=>{
        const y=25+i*42;
        content+=`<rect x="20" y="${y}" width="${W-40}" height="34" fill="${C.cyan}" opacity="0.05" rx="5"/>
        <rect x="32" y="${y+9}" width="16" height="16" fill="none" stroke="${C.cyan}" stroke-width="1.5" rx="3"/>
        <text x="58" y="${y+22}" fill="${C.text}" font-size="11" font-family="monospace">${q}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

// ─── MÓDULO 18: RISK/REWARD ───────────────────────────────────────────────────

function no_mans_land_vs_demand_zone() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[112,108,104,100,103,99,102,98,101,97,100,104,108,113,118,124];
    const mn=92, mx=128, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const zoneTopY=py(99), zoneBotY=py(96);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${zoneTopY.toFixed(1)}" width="${w}" height="${(zoneBotY-zoneTopY).toFixed(1)}" fill="${C.accent}" opacity="0.12"/>
        <rect x="${px(0)}" y="${y0}" width="${px(3)-px(0)}" height="${(zoneTopY-y0).toFixed(1)}" fill="${C.red}" opacity="0.05"/>
        ${candles}
        <text x="${px(1.5)}" y="${y0+14}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">"TIERRA DE NADIE"</text>
        <text x="${px(1.5)}" y="${y0+27}" fill="${C.red}" font-size="8" font-family="monospace" text-anchor="middle">sin nivel técnico</text>
        <text x="${x0+w+4}" y="${((zoneTopY+zoneBotY)/2+4).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">ZONA DE DEMANDA</text>
        <text x="${x0+w+4}" y="${((zoneTopY+zoneBotY)/2+18).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace">rechazo previo claro</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mismo precio numérico, contexto técnico radicalmente distinto
        </text>
    </svg>`;
}

function stop_distance_by_entry_quality() {
    const W=680, H=210;
    const headers=['Tipo de entrada','Distancia del stop'];
    const rows=[
        ['Límite de zona sólida','1-2%',C.accent],
        ['Mitad de zona amplia','2-3%',C.cyan],
        ['Tierra de nadie','4-8%',C.red],
    ];
    const barMaxW=280, startX=220, y0=30, rowH=42;
    let content='';
    rows.forEach(([label,dist,color],i)=>{
        const y=y0+i*rowH;
        const pct=parseFloat(dist.split('-')[1]);
        const bw=(pct/8)*barMaxW;
        content+=`<text x="210" y="${y+14}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="end">${label}</text>
        <rect x="${startX}" y="${y}" width="${bw}" height="22" fill="${color}" opacity="0.35" rx="3"/>
        <text x="${startX+bw+8}" y="${y+15}" fill="${color}" font-size="11" font-family="monospace" font-weight="bold">${dist}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El nivel técnico real define cuán ajustado puede ser el stop</text>
    </svg>`;
}

function rr_disparity_same_target() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,98,101,97,100,103,107,111,115,118,120];
    const mn=90, mx=124, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,18);});

    const objY=py(120), entryY=py(100), tightStopY=py(98.5), wideStopY=py(96);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${objY}" x2="${x0+w}" y2="${objY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${entryY}" x2="${x0+w}" y2="${entryY}" stroke="${C.cyan}" stroke-width="1.5" stroke-dasharray="5,4"/>
        <line x1="${x0}" y1="${tightStopY}" x2="${x0+w}" y2="${tightStopY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,3"/>
        <line x1="${x0}" y1="${wideStopY}" x2="${x0+w}" y2="${wideStopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,3"/>
        ${candles}
        <text x="${x0+w+4}" y="${objY+4}" fill="${C.accent}" font-size="9" font-family="monospace">OBJETIVO $120 (igual en ambos)</text>
        <text x="${x0+w+4}" y="${tightStopY+4}" fill="${C.accent}" font-size="9" font-family="monospace">Stop en zona: $98.5 → R:R 1:13</text>
        <text x="${x0+w+4}" y="${wideStopY+4}" fill="${C.red}" font-size="9" font-family="monospace">Stop tierra de nadie: $96 → R:R 1:5</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Mismo objetivo, misma entrada — el R:R cambia drásticamente solo por la calidad del stop
        </text>
    </svg>`;
}

function more_room_to_target() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[88,92,96,100,104,108,112,116,120];
    const mn=82, mx=124, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const path=prices.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const demandX=px(1), demandY=py(92);
    const noManX=px(4), noManY=py(104);
    const objY=py(120);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${objY}" x2="${x0+w}" y2="${objY}" stroke="${C.muted}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <path d="${path}" fill="none" stroke="${C.cyan}" stroke-width="2"/>
        <circle cx="${demandX}" cy="${demandY}" r="7" fill="${C.accent}" opacity="0.4" stroke="${C.accent}" stroke-width="2"/>
        <text x="${demandX}" y="${(demandY-14).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Compra en zona</text>
        <line x1="${demandX}" y1="${demandY}" x2="${demandX}" y2="${objY}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>
        <circle cx="${noManX}" cy="${noManY}" r="7" fill="${C.red}" opacity="0.4" stroke="${C.red}" stroke-width="2"/>
        <text x="${noManX}" y="${(noManY-14).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Compra en tierra de nadie</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Comprar más abajo en el mismo movimiento captura más puntos hasta el mismo objetivo
        </text>
    </svg>`;
}

function strong_demand_zone_anatomy() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[112,108,104,99,95,108,112,116];
    const mn=88, mx=120, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const volumes=[40,38,35,42,95,30,32,38];
    const volY=y0+h+15, volH=30, volMax=Math.max(...volumes);

    let candles='', vols='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,16);});
    volumes.forEach((v,i)=>{
        const cx=px(i), bh=(v/volMax)*volH;
        vols+=`<rect x="${(cx-7).toFixed(1)}" y="${(volY+volH-bh).toFixed(1)}" width="14" height="${bh.toFixed(1)}" fill="${v>70?C.accent:C.muted}" opacity="0.5"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H+45}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+45}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <circle cx="${px(4)}" cy="${py(95)}" r="9" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(4)}" y="${(py(95)-16).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Rechazo marcado</text>
        <text x="${x0}" y="${volY-4}" fill="${C.muted}" font-size="8" font-family="monospace">VOLUMEN</text>
        ${vols}
        <text x="${W/2}" y="${H+40}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Reversión rápida + volumen elevado en el rechazo = zona con convicción real
        </text>
    </svg>`;
}

function fresh_vs_tested_zones() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,touches){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="38" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>`;
        for(let i=0;i<touches;i++){
            out+=`<circle cx="${x0+40+i*35}" cy="60" r="6" fill="${color}" opacity="${0.7-i*0.15}"/>`;
        }
        out+=`<line x1="${x0+20}" y1="78" x2="${x0+panelW-20}" y2="78" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${100+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'ZONA FRESCA','Depósito de órdenes\nintacto · rebote\npotencialmente fuerte',C.accent,1)}
        ${panel(panelW+35,'ZONA TESTEADA 4x','Depósito agotado\nprogresivamente ·\nmayor riesgo de ruptura',C.red,4)}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function fake_support_vs_real_demand() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'PAUSA SIN CONVICCIÓN','El precio se detiene\nsin rechazo claro,\nsin volumen',C.red,'⚠️')}
        ${panel(panelW+35,'ZONA DE DEMANDA REAL','Rechazo decisivo\ncon volumen de\nconfirmación',C.accent,'✓')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">No todo lo que detiene una caída brevemente es soporte real</text>
    </svg>`;
}

function zone_as_range_not_line() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=150;
    const prices=[110,106,102,97,103,108,113];
    const mn=92, mx=116, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.025),py(Math.min(prev,p)-range*0.02),bull,18);});

    const topY=py(101), botY=py(97), stopY=py(95.5);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${topY.toFixed(1)}" width="${w}" height="${(botY-topY).toFixed(1)}" fill="${C.accent}" opacity="0.15"/>
        <line x1="${x0}" y1="${topY}" x2="${x0+w}" y2="${topY}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,4" opacity="0.6"/>
        <line x1="${x0}" y1="${botY}" x2="${x0+w}" y2="${botY}" stroke="${C.accent}" stroke-width="1" stroke-dasharray="4,4" opacity="0.6"/>
        <line x1="${x0}" y1="${stopY}" x2="${x0+w}" y2="${stopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,3"/>
        ${candles}
        <text x="${x0+w+4}" y="${topY+4}" fill="${C.accent}" font-size="9" font-family="monospace">Límite sup. = cierre cuerpo</text>
        <text x="${x0+w+4}" y="${botY+4}" fill="${C.accent}" font-size="9" font-family="monospace">Límite inf. = mínimo mecha</text>
        <text x="${x0+w+4}" y="${stopY+4}" fill="${C.red}" font-size="9" font-family="monospace">Stop bajo la zona</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La zona es un rango, no una línea — el stop va bajo todo el rango, no en mitad de él
        </text>
    </svg>`;
}

function anxiety_no_mans_land() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="26" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'ZONA DE DEMANDA','"Mientras no rompa\nla zona, la idea\nsigue siendo válida"',C.accent,'🧘')}
        ${panel(panelW+35,'TIERRA DE NADIE','"¿Debería haber\nesperado más?\n¿Esto es normal?"',C.red,'😰')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Una regla objetiva sustituye la duda emocional momento a momento</text>
    </svg>`;
}

function comparing_trade_experience() {
    const W=680, H=210;
    const headers=['Situación','En zona de demanda','En tierra de nadie'];
    const rows=[
        ['Caída del 2%','Normal, sin duda','Roza el stop'],
        ['Decisión en curso','Objetiva: ¿rompió?','Subjetiva: ¿aguanto?'],
        ['Mover el stop por miedo','Improbable','Frecuente'],
    ];
    const colW=[160,200,200], startX=70, startY=30, rowH=42;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-10}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-10}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${headers[1]}</text>
    <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${startY-10}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${headers[2]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]+colW[2]}" height="${rowH-6}" fill="${i%2===0?C.surface:'transparent'}" rx="4"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2-2}" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2-2}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${row[1]}</text>
        <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${y+rowH/2-2}" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">${row[2]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function fewer_losses_from_placement() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,98,101,97,99,102,100,103,106,110,114];
    const mn=92, mx=118, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,14);});

    const zoneTopY=py(99), zoneBotY=py(96), tightStopY=py(94);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${zoneTopY.toFixed(1)}" width="${w}" height="${(zoneBotY-zoneTopY).toFixed(1)}" fill="${C.accent}" opacity="0.1"/>
        <line x1="${x0}" y1="${tightStopY}" x2="${x0+w}" y2="${tightStopY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,3"/>
        ${candles}
        <text x="${x0+w+4}" y="${((zoneTopY+zoneBotY)/2).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace">Ruido normal — dentro de la zona</text>
        <text x="${x0+w+4}" y="${tightStopY+4}" fill="${C.red}" font-size="9" font-family="monospace">Stop con margen real</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El ruido del precio no ejecuta el stop cuando hay margen técnico real debajo
        </text>
    </svg>`;
}

function conviction_from_preparation() {
    const W=680, H=200;
    const steps=['Identificar\nla zona','Verificar\ncalidad','Esperar el\nprecio ahí','Confianza\ninformada'];
    const bw=148, gap=9, startX=14;
    let content='';
    steps.forEach((label,i)=>{
        const x=startX+i*(bw+gap);
        const labelLines=label.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="140" fill="${C.accent}" opacity="0.06" rx="6" stroke="${C.accent}" stroke-width="1"/>
        <circle cx="${x+bw/2}" cy="42" r="16" fill="${C.accent}" opacity="0.2" stroke="${C.accent}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="47" fill="${C.accent}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${i+1}</text>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${75+li*15}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        if(i<3) content+=`<text x="${x+bw+gap/2}" y="${H/2-10}" fill="${C.muted}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">La calma viene del trabajo previo, no de la actitud durante el trade</text>
    </svg>`;
}

function correct_process_order() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="24" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*15}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'CORRECTO','Zona primero →\nstop y objetivo\nse derivan de ella →\nR:R es el resultado',C.accent,'✓')}
        ${panel(panelW+35,'INCORRECTO','R:R deseado primero →\nbuscar dónde\nencaja después',C.red,'✗')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function demand_zone_insufficient_rr() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=150;
    const prices=[100,97,103,108,106];
    const mn=92, mx=112, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,22);});

    const zoneY=py(97), resY=py(106);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${(zoneY-4).toFixed(1)}" width="${w}" height="8" fill="${C.accent}" opacity="0.15"/>
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <text x="${x0+w+4}" y="${zoneY+4}" fill="${C.accent}" font-size="9" font-family="monospace">Excelente zona de demanda</text>
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="9" font-family="monospace">Resistencia muy cercana</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Zona de calidad ≠ trade válido — sin espacio hasta el objetivo, el R:R no compensa
        </text>
    </svg>`;
}

function comparing_multiple_opportunities() {
    const W=680, H=210;
    const headers=['Activo','Calidad zona','Espacio','R:R'];
    const rows=[
        ['A','Fresca, alto vol.','Amplio','Muy favorable',C.accent],
        ['B','Testeada 3x','Amplio','Moderado',C.yellow],
        ['C','Fresca, alto vol.','Estrecho','Insuficiente',C.red],
    ];
    const colW=[80,170,110,150], startX=80, startY=35, rowH=42;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-10}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-10}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[1]}</text>
    <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${startY-10}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[2]}</text>
    <text x="${startX+colW[0]+colW[1]+colW[2]+colW[3]/2}" y="${startY-10}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[3]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH; const color=row[4];
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]+colW[2]+colW[3]}" height="${rowH-6}" fill="${i%2===0?C.surface:'transparent'}" rx="4"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2-2}" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2-2}" fill="${C.text}" font-size="9" font-family="monospace" text-anchor="middle">${row[1]}</text>
        <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${y+rowH/2-2}" fill="${C.text}" font-size="9" font-family="monospace" text-anchor="middle">${row[2]}</text>
        <text x="${startX+colW[0]+colW[1]+colW[2]+colW[3]/2}" y="${y+rowH/2-2}" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${row[3]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function module_summary_connection() {
    const W=680, H=230;
    const cx=W/2, cy=H/2-5, r=80;
    const nodes=[
        {label:'Zona de\ndemanda real',angle:-90,color:C.accent},
        {label:'Stop\najustado',angle:-18,color:C.cyan},
        {label:'Más espacio\nal objetivo',angle:54,color:C.yellow},
        {label:'Calma\npsicológica',angle:126,color:C.muted},
        {label:'Buen R:R\n(resultado)',angle:198,color:C.orange},
    ];
    let content='';
    nodes.forEach(({label,angle,color})=>{
        const rad=angle*Math.PI/180;
        const x=cx+r*Math.cos(rad), y=cy+r*Math.sin(rad);
        const labelLines=label.split('\n');
        content+=`<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${color}" stroke-width="1" opacity="0.3"/>
        <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="36" fill="${color}" opacity="0.12" stroke="${color}" stroke-width="1.5"/>`;
        labelLines.forEach((l,li)=>{ content+=`<text x="${x.toFixed(1)}" y="${(y+4+li*12-(labelLines.length-1)*6).toFixed(1)}" fill="${color}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    content+=`<circle cx="${cx}" cy="${cy}" r="34" fill="${C.accent}" opacity="0.15" stroke="${C.accent}" stroke-width="2"/>
    <text x="${cx}" y="${cy-3}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">ZONA DE</text>
    <text x="${cx}" y="${cy+11}" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">ENTRADA</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Todo se conecta a la calidad del punto de entrada — el R:R favorable es la consecuencia</text>
    </svg>`;
}

// ─── MÓDULO 19: MÉTODOS DE CONFIRMACIÓN DE ENTRADA ───────────────────────────

function trendline_break_reversal_sequence() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[88,94,91,99,96,105,101,109,104,98,92,96,91,87];
    const mn=84, mx=112, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.02),py(Math.min(prev,p)-range*0.018),bull,12);});

    const trendUpPath=`M ${px(0).toFixed(1)} ${py(91).toFixed(1)} L ${px(7).toFixed(1)} ${py(104).toFixed(1)}`;
    const breakX=px(8);
    const trendDownPath=`M ${px(9).toFixed(1)} ${py(98).toFixed(1)} L ${px(13).toFixed(1)} ${py(87).toFixed(1)}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${trendUpPath}" fill="none" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.6"/>
        ${candles}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.yellow}" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="${breakX}" y="${y0-3}" fill="${C.yellow}" font-size="9" font-family="monospace" text-anchor="middle">TRENDLINE BREAK</text>
        <path d="${trendDownPath}" fill="none" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>
        <text x="${px(11)}" y="${(py(91)-12).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">TRENDLINE REVERSAL</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            La ruptura es el aviso — la nueva línea en sentido contrario es la confirmación
        </text>
    </svg>`;
}

function trendline_both_directions() {
    const W=680, H=210;
    const panelW=(W-50)/2;
    function panel(x0,label,color){
        const x1=x0+20, y1=20, pw=panelW-40, ph=140;
        const up = label==='ALCISTA';
        const pts = up ? [[0,90],[1,75],[2,82],[3,60],[4,68],[5,40]] : [[0,40],[1,68],[2,60],[3,82],[4,75],[5,90]];
        const path = pts.map(([i,v],idx)=>`${idx===0?'M':'L'} ${x1+(i/5)*pw} ${y1+(v/100)*ph}`).join(' ');
        const trend = up ? `M ${x1} ${y1+(82/100)*ph} L ${x1+pw} ${y1+(40/100)*ph}` : `M ${x1} ${y1+(60/100)*ph} L ${x1+pw} ${y1+(90/100)*ph}`;
        return `<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.05" rx="6" stroke="${color}" stroke-width="1"/>
        <text x="${x0+panelW/2}" y="28" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>
        <path d="${trend}" fill="none" stroke="${color}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.5"/>`;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'ALCISTA',C.accent)}
        ${panel(panelW+35,'BAJISTA',C.red)}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El mismo patrón funciona en espejo en ambas direcciones</text>
    </svg>`;
}

function wick_vs_close_break() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="24" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'SOLO MECHA','Perfora la línea\npero el cierre\nvuelve dentro',C.yellow,'〜')}
        ${panel(panelW+35,'CIERRE CONFIRMADO','El cuerpo cierra\nclaramente al\notro lado',C.accent,'✓')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El cierre, no la mecha, distingue ruptura real de ruido pasajero</text>
    </svg>`;
}

function support_resistance_multiple_touches() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,108,102,109,101,110,103,108,104,108];
    const mn=96, mx=114, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,16);});

    const resY=py(109), supY=py(100);
    const touchesRes=[3,5,7].map(i=>px(i));
    const touchesSup=[0,2,4].map(i=>px(i));

    let dots='';
    touchesRes.forEach(x=>{dots+=`<circle cx="${x}" cy="${resY}" r="5" fill="${C.red}" opacity="0.6"/>`;});
    touchesSup.forEach(x=>{dots+=`<circle cx="${x}" cy="${supY}" r="5" fill="${C.accent}" opacity="0.6"/>`;});

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${resY}" x2="${x0+w}" y2="${resY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        ${dots}
        <text x="${x0+w+4}" y="${resY+4}" fill="${C.red}" font-size="9" font-family="monospace">RESISTENCIA</text>
        <text x="${x0+w+4}" y="${supY+4}" fill="${C.accent}" font-size="9" font-family="monospace">SOPORTE</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Más toques con reacción similar = nivel más fiable como referencia
        </text>
    </svg>`;
}

function confirmation_at_level_touch() {
    const W=680, H=210;
    const x0=40, y0=15, w=W-80, h=150;
    const prices=[110,104,99,96,100,105];
    const mn=92, mx=113, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.03),py(Math.min(prev,p)-range*0.025),bull,22);});

    const supY=py(96);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${supY}" x2="${x0+w}" y2="${supY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <circle cx="${px(3)}" cy="${supY}" r="8" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(3)}" y="${(supY-16).toFixed(1)}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Vela de rechazo confirma</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Esperar la reacción en el nivel, no anticiparse antes de que el precio llegue
        </text>
    </svg>`;
}

function level_role_reversal() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[96,100,97,101,98,104,108,105,109,106];
    const mn=92, mx=112, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,14);});

    const levelY=py(101);
    const breakX=px(5);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${x0}" y1="${levelY}" x2="${breakX}" y2="${levelY}" stroke="${C.red}" stroke-width="1.5" stroke-dasharray="6,4"/>
        <line x1="${breakX}" y1="${levelY}" x2="${x0+w}" y2="${levelY}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,4"/>
        ${candles}
        <text x="${(x0+breakX)/2}" y="${levelY-8}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">Era resistencia</text>
        <text x="${(breakX+x0+w)/2}" y="${levelY-8}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">Ahora soporte</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El nivel roto invierte su función — el retest suele ofrecer buena entrada
        </text>
    </svg>`;
}

function fibonacci_retracement_levels() {
    const W=680, H=230;
    const x0=50, y0=20, w=W-100, h=160;
    const impulseStart={x:x0, v:90}, impulseEnd={x:x0+w*0.4, v:150};
    const mn=84, mx=156, range=mx-mn;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    const fib38=150-(150-90)*0.38, fib50=150-(150-90)*0.50, fib62=150-(150-90)*0.62;

    const priceUp=`M ${impulseStart.x} ${py(90)} L ${impulseStart.x+w*0.1} ${py(105)} L ${impulseStart.x+w*0.2} ${py(118)} L ${impulseStart.x+w*0.3} ${py(135)} L ${impulseEnd.x} ${py(150)}`;
    const priceRetrace=`M ${impulseEnd.x} ${py(150)} L ${impulseEnd.x+w*0.15} ${py(135)} L ${impulseEnd.x+w*0.3} ${py(fib50)} L ${impulseEnd.x+w*0.45} ${py(142)} L ${x0+w} ${py(148)}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <line x1="${impulseEnd.x}" y1="${py(fib38)}" x2="${x0+w}" y2="${py(fib38)}" stroke="${C.cyan}" stroke-width="1" stroke-dasharray="5,3" opacity="0.7"/>
        <text x="${x0+w+4}" y="${py(fib38)+3}" fill="${C.cyan}" font-size="9" font-family="monospace">38%</text>
        <line x1="${impulseEnd.x}" y1="${py(fib50)}" x2="${x0+w}" y2="${py(fib50)}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,3" opacity="0.7"/>
        <text x="${x0+w+4}" y="${py(fib50)+3}" fill="${C.yellow}" font-size="9" font-family="monospace">50%</text>
        <line x1="${impulseEnd.x}" y1="${py(fib62)}" x2="${x0+w}" y2="${py(fib62)}" stroke="${C.orange}" stroke-width="1" stroke-dasharray="5,3" opacity="0.7"/>
        <text x="${x0+w+4}" y="${py(fib62)+3}" fill="${C.orange}" font-size="9" font-family="monospace">62%</text>
        <path d="${priceUp}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <path d="${priceRetrace}" fill="none" stroke="${C.accent}" stroke-width="2" opacity="0.7"/>
        <text x="${impulseEnd.x}" y="${py(150)-12}" fill="${C.muted}" font-size="8" font-family="monospace" text-anchor="middle">Máximo del impulso</text>
        <text x="${W/2}" y="${H-5}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Niveles donde la corrección podría detenerse antes de continuar la tendencia
        </text>
    </svg>`;
}

function fibonacci_correct_drawing() {
    const W=680, H=200;
    const headers=['Nivel','Interpretación'];
    const rows=[
        ['38%','Retroceso superficial — tendencia muy fuerte',C.cyan],
        ['50%','Retroceso intermedio — equilibrio',C.yellow],
        ['62%','Retroceso profundo — última zona razonable',C.orange],
    ];
    const colW=[100,380], startX=80, startY=35, rowH=46;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-12}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-12}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[1]}</text>`;
    rows.forEach(([lvl,desc,color],i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]}" height="${rowH-8}" fill="${color}" opacity="0.06" rx="5" stroke="${color}" stroke-width="1"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2-4}" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${lvl}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2-4}" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle">${desc}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function fibonacci_confluence() {
    const W=680, H=210;
    const x0=50, y0=20, w=W-100, h=150;
    const mn=88, mx=152, range=mx-mn;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const fib50=152-(152-92)*0.50;

    const priceUp=`M ${x0} ${py(92)} L ${x0+w*0.35} ${py(152)}`;
    const priceRetrace=`M ${x0+w*0.35} ${py(152)} L ${x0+w*0.55} ${py(fib50)} L ${x0+w*0.75} ${py(135)} L ${x0+w} ${py(145)}`;

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${x0}" y="${(py(fib50)-6).toFixed(1)}" width="${w}" height="12" fill="${C.yellow}" opacity="0.1"/>
        <line x1="${x0}" y1="${py(fib50)}" x2="${x0+w}" y2="${py(fib50)}" stroke="${C.yellow}" stroke-width="1" stroke-dasharray="5,3" opacity="0.6"/>
        <text x="${x0+8}" y="${py(fib50)-8}" fill="${C.yellow}" font-size="8" font-family="monospace">Fib 50%</text>
        <path d="${priceUp}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <path d="${priceRetrace}" fill="none" stroke="${C.accent}" stroke-width="2" opacity="0.7"/>
        <text x="${x0+w*0.55}" y="${py(fib50)+18}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">+ soporte previo</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Fibonacci + otro nivel de contexto = confirmación más sólida
        </text>
    </svg>`;
}

function consolidation_within_trend() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[90,96,101,107,104,107,103,106,104,109,114,119];
    const mn=86, mx=122, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const consStart=px(4), consEnd=px(8);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${consStart}" y="${y0}" width="${(consEnd-consStart).toFixed(1)}" height="${h}" fill="${C.cyan}" opacity="0.08"/>
        ${candles}
        <text x="${(consStart+consEnd)/2}" y="${y0-3}" fill="${C.cyan}" font-size="9" font-family="monospace" text-anchor="middle">CONSOLIDACIÓN</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Pausa dentro de la tendencia — el mercado digiere antes de continuar
        </text>
    </svg>`;
}

function quality_consolidation_signs() {
    const W=680, H=210;
    const headers=['Característica','Calidad','Indecisión'];
    const rows=[
        ['Rango','Cada vez más estrecho','Errático'],
        ['Volumen','Decreciente','Irregular'],
        ['Duración','Breve frente al impulso','Se extiende sin resolución'],
    ];
    const colW=[130,210,160], startX=60, startY=35, rowH=46;
    let content=`<text x="${startX+colW[0]/2}" y="${startY-12}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${headers[0]}</text>
    <text x="${startX+colW[0]+colW[1]/2}" y="${startY-12}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">${headers[1]}</text>
    <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${startY-12}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">${headers[2]}</text>`;
    rows.forEach((row,i)=>{
        const y=startY+i*rowH;
        content+=`<rect x="${startX}" y="${y}" width="${colW[0]+colW[1]+colW[2]}" height="${rowH-8}" fill="${i%2===0?C.surface:'transparent'}" rx="4"/>
        <text x="${startX+colW[0]/2}" y="${y+rowH/2-4}" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle">${row[0]}</text>
        <text x="${startX+colW[0]+colW[1]/2}" y="${y+rowH/2-4}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">${row[1]}</text>
        <text x="${startX+colW[0]+colW[1]+colW[2]/2}" y="${y+rowH/2-4}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">${row[2]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
    </svg>`;
}

function consolidation_resolution_entry() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[96,102,108,105,107,104,106,105,111,117,123];
    const mn=92, mx=126, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    const breakX=px(7), breakY=py(105);

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <rect x="${px(3)}" y="${y0}" width="${(px(7)-px(3)).toFixed(1)}" height="${h}" fill="${C.cyan}" opacity="0.06"/>
        ${candles}
        <line x1="${breakX}" y1="${y0}" x2="${breakX}" y2="${y0+h}" stroke="${C.accent}" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="${breakX}" y="${y0-3}" fill="${C.accent}" font-size="9" font-family="monospace" text-anchor="middle">RESOLUCIÓN + VOLUMEN</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Salida en dirección de la tendencia previa, idealmente con repunte de volumen
        </text>
    </svg>`;
}

function three_gap_types() {
    const W=680, H=210;
    const types=[
        {label:'BG',name:'Breakaway',desc:'Inicio de\nmovimiento',color:C.accent},
        {label:'RG',name:'Runaway',desc:'Continuación\nde tendencia',color:C.cyan},
        {label:'EG',name:'Exhaustion',desc:'Posible fin\ndel movimiento',color:C.red},
    ];
    const bw=200, gap=15, startX=20;
    let content='';
    types.forEach(({label,name,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        const descLines=desc.split('\n');
        content+=`<rect x="${x}" y="15" width="${bw}" height="155" fill="${color}" opacity="0.07" rx="6" stroke="${color}" stroke-width="1.5"/>
        <circle cx="${x+bw/2}" cy="45" r="18" fill="${color}" opacity="0.2" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="50" fill="${color}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${x+bw/2}" y="80" fill="${color}" font-size="10" font-family="monospace" text-anchor="middle">${name} Gap</text>`;
        descLines.forEach((l,li)=>{ content+=`<text x="${x+bw/2}" y="${105+li*15}" fill="${C.muted}" font-size="9" font-family="monospace" text-anchor="middle">${l}</text>`; });
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El mismo evento técnico, tres mensajes distintos según el momento</text>
    </svg>`;
}

function gap_context_identification() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=160;
    const prices=[100,98,99,108,113,117,121,130,128,123,119];
    const mn=94, mx=134, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;

    let candles='';
    prices.forEach((p,i)=>{if(!i)return;const prev=prices[i-1],bull=p>prev,cx=px(i);candles+=candleRow(cx,py(prev),py(p),py(p+range*0.022),py(Math.min(prev,p)-range*0.018),bull,12);});

    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${candles}
        <circle cx="${px(3)}" cy="${py(108)}" r="7" fill="${C.accent}" opacity="0.5" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(3)}" y="${(py(108)-14).toFixed(1)}" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">BG: sale de rango</text>
        <circle cx="${px(7)}" cy="${py(130)}" r="7" fill="${C.cyan}" opacity="0.5" stroke="${C.cyan}" stroke-width="2"/>
        <text x="${px(7)}" y="${(py(130)-14).toFixed(1)}" fill="${C.cyan}" font-size="8" font-family="monospace" text-anchor="middle">RG: en plena tendencia</text>
        <text x="${W/2}" y="${H-3}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            El contexto que rodea al gap, no el gap aislado, define su significado
        </text>
    </svg>`;
}

function gap_fill_behavior() {
    const W=680, H=200;
    const panelW=(W-50)/2;
    function panel(x0,label,desc,color,icon){
        const descLines=desc.split('\n');
        let out=`<rect x="${x0}" y="10" width="${panelW}" height="165" fill="${color}" opacity="0.06" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x0+panelW/2}" y="42" font-size="24" text-anchor="middle">${icon}</text>
        <text x="${x0+panelW/2}" y="65" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <line x1="${x0+20}" y1="75" x2="${x0+panelW-20}" y2="75" stroke="${color}" stroke-width="1" opacity="0.3"/>`;
        descLines.forEach((l,li)=>{ out+=`<text x="${x0+panelW/2}" y="${98+li*16}" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">${l}</text>`; });
        return out;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${panel(15,'NO SE RELLENA','Refuerza convicción\nen BG/RG —\nmovimiento real',C.accent,'↗')}
        ${panel(panelW+35,'SE RELLENA RÁPIDO','Refuerza lectura\nde agotamiento\nen EG',C.red,'↩')}
        <line x1="${panelW+25}" y1="5" x2="${panelW+25}" y2="${H-5}" stroke="${C.border}" stroke-width="1"/>
    </svg>`;
}

function volume_trend_pattern() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=120;
    const prices=[96,100,104,109,114,120,127];
    const volumes=[30,38,45,55,65,78,92];
    const mn=92, mx=130, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const path=prices.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const volY=y0+h+15, volH=35, volMax=Math.max(...volumes);
    let vols='';
    volumes.forEach((v,i)=>{
        const cx=px(i), bh=(v/volMax)*volH;
        vols+=`<rect x="${(cx-10).toFixed(1)}" y="${(volY+volH-bh).toFixed(1)}" width="20" height="${bh.toFixed(1)}" fill="${C.accent}" opacity="0.5"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H+50}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+50}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${path}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${x0}" y="${volY-4}" fill="${C.muted}" font-size="8" font-family="monospace">VOLUME TREND</text>
        ${vols}
        <text x="${W/2}" y="${H+45}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Volumen creciendo de forma gradual junto al precio — respaldo saludable
        </text>
    </svg>`;
}

function volume_climax_pattern() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=120;
    const prices=[96,103,110,118,127,137,142,134];
    const volumes=[32,40,48,58,70,95,32,28];
    const mn=92, mx=145, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const path=prices.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    const volY=y0+h+15, volH=35, volMax=Math.max(...volumes);
    let vols='';
    volumes.forEach((v,i)=>{
        const cx=px(i), bh=(v/volMax)*volH, isClimax=v===Math.max(...volumes);
        vols+=`<rect x="${(cx-10).toFixed(1)}" y="${(volY+volH-bh).toFixed(1)}" width="20" height="${bh.toFixed(1)}" fill="${isClimax?C.red:C.muted}" opacity="${isClimax?0.7:0.4}"/>`;
    });

    return `<svg viewBox="0 0 ${W} ${H+50}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+50}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${path}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        <text x="${px(5)}" y="${(py(137)-12).toFixed(1)}" fill="${C.red}" font-size="9" font-family="monospace" text-anchor="middle">VOLUME CLIMAX</text>
        <text x="${x0}" y="${volY-4}" fill="${C.muted}" font-size="8" font-family="monospace">VOLUMEN</text>
        ${vols}
        <text x="${W/2}" y="${H+45}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            Pico extremo de volumen tras extensión — suele señalar agotamiento, no continuidad
        </text>
    </svg>`;
}

function vt_vc_alternation() {
    const W=680, H=220;
    const x0=40, y0=15, w=W-80, h=120;
    const prices=[94,100,107,103,108,115,111,108,114,121,126];
    const volTags=['VT','VT','VC','VT','VT','VC','VT','VT','VT','VC',''];
    const mn=90, mx=129, range=mx-mn;
    const px=(i)=>x0+(i/(prices.length-1))*w;
    const py=(v)=>y0+h-((v-mn)/range)*h;
    const path=prices.map((v,i)=>`${i===0?'M':'L'} ${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');

    let tags='';
    volTags.forEach((t,i)=>{
        if(!t) return;
        tags+=`<text x="${px(i)}" y="${y0+h+22}" fill="${t==='VC'?C.red:C.muted}" font-size="8" font-family="monospace" text-anchor="middle">${t}</text>`;
    });

    return `<svg viewBox="0 0 ${W} ${H+40}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H+40}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        <path d="${path}" fill="none" stroke="${C.accent}" stroke-width="2"/>
        ${tags}
        <text x="${W/2}" y="${H+35}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">
            VT confirma el tramo, VC señala pausa — si VT se reanuda, el fondo del movimiento sigue
        </text>
    </svg>`;
}

// ─── REGISTRO ─────────────────────────────────────────────────────────────────

// ─── GRÁFICO: Desglose del RSU Score (5 factores x 20 pts) ──────────────────
function rsu_score_breakdown() {
    const W = 680, H = 240;
    const rows = [
        { label: 'Crecimiento Ingresos', pts: 15, max: 20, val: '18.2%' },
        { label: 'ROE',                  pts: 20, max: 20, val: '31.4%' },
        { label: 'Margen Neto',          pts: 10, max: 20, val: '6.8%' },
        { label: 'Consenso Analistas',   pts: 20, max: 20, val: '82% alcistas' },
        { label: 'Potencial P.Objetivo', pts: 15, max: 20, val: '+17.3%' },
    ];
    const total = rows.reduce((s, r) => s + r.pts, 0);
    const x0 = 190, barW = 400, rowH = 34, y0 = 24;
    let bars = '';
    rows.forEach((r, i) => {
        const y = y0 + i * rowH;
        const w = (r.pts / r.max) * barW;
        const color = r.pts >= 15 ? C.accent : r.pts >= 10 ? C.yellow : C.red;
        bars += `<text x="${x0-12}" y="${y+15}" fill="${C.textDim}" font-size="11" font-family="monospace" text-anchor="end">${r.label}</text>
            <rect x="${x0}" y="${y}" width="${barW}" height="18" fill="${C.surface}" stroke="${C.border}" rx="3"/>
            <rect x="${x0}" y="${y}" width="${w}" height="18" fill="${color}" rx="3"/>
            <text x="${x0+barW+10}" y="${y+15}" fill="${color}" font-size="11" font-family="monospace">${r.pts}/${r.max}</text>
            <text x="${x0+barW+55}" y="${y+15}" fill="${C.muted}" font-size="10" font-family="monospace">(${r.val})</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${bars}
        <text x="${W/2}" y="${y0+rows.length*rowH+14}" fill="${C.accent}" font-size="13" font-family="monospace" text-anchor="middle">TOTAL: ${total}/100 · EJEMPLO ILUSTRATIVO</text>
    </svg>`;
}

// ─── GRÁFICO: Escala de etiquetas del RSU Score ──────────────────────────────
function rsu_score_labels() {
    const W = 680, H = 130;
    const zones = [
        { from:0,  to:35,  label:'EVITAR',        color:C.red },
        { from:35, to:50,  label:'PRECAUCIÓN',    color:C.red },
        { from:50, to:65,  label:'NEUTRAL',        color:C.yellow },
        { from:65, to:80,  label:'COMPRA',         color:C.accent },
        { from:80, to:100, label:'COMPRA FUERTE',  color:C.accent },
    ];
    const x0 = 30, w = W - 60, y0 = 40, h = 30;
    let segs = '';
    zones.forEach(z => {
        const sx = x0 + (z.from/100)*w;
        const sw = ((z.to - z.from)/100)*w;
        segs += `<rect x="${sx.toFixed(1)}" y="${y0}" width="${sw.toFixed(1)}" height="${h}" fill="${z.color}" opacity="0.75"/>
            <text x="${(sx+sw/2).toFixed(1)}" y="${y0+h+16}" fill="${z.color}" font-size="9" font-family="monospace" text-anchor="middle">${z.label}</text>
            <text x="${(sx+sw/2).toFixed(1)}" y="${y0+h/2+4}" fill="#000" font-size="10" font-family="monospace" text-anchor="middle" font-weight="600">${z.from}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="20" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">ESCALA DEL RSU SCORE (0-100)</text>
        ${segs}
        <text x="${x0+w}" y="${y0+h+16}" fill="${C.text}" font-size="9" font-family="monospace" text-anchor="end">100</text>
    </svg>`;
}

// ─── GRÁFICO: Los 9 criterios del Piotroski F-Score ──────────────────────────
function piotroski_criteria() {
    const W = 680, H = 260;
    const items = [
        { l:'ROA positivo', p:true }, { l:'CFO positivo', p:true }, { l:'ROA mejora', p:false },
        { l:'Calidad beneficio (CFO>BN)', p:true }, { l:'Apalancamiento estable', p:true }, { l:'Liquidez mejora', p:null },
        { l:'Sin dilución', p:true }, { l:'Margen bruto mejora', p:false }, { l:'Rotación activos mejora', p:true },
    ];
    const cols = 3, cw = (W-40)/cols, ch = 60;
    let cells = '';
    items.forEach((it, i) => {
        const col = i % cols, row = Math.floor(i / cols);
        const x = 20 + col*cw, y = 20 + row*ch;
        const color = it.p === true ? C.accent : it.p === false ? C.red : C.muted;
        const icon  = it.p === true ? '✓' : it.p === false ? '✗' : '–';
        cells += `<rect x="${x}" y="${y}" width="${cw-10}" height="${ch-10}" fill="${C.surface}" stroke="${color}" stroke-width="1" rx="4"/>
            <text x="${x+14}" y="${y+34}" fill="${color}" font-size="20" font-family="monospace" font-weight="700">${icon}</text>
            <text x="${x+38}" y="${y+30}" fill="${C.text}" font-size="9.5" font-family="monospace">${it.l}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${cells}
        <text x="${W/2}" y="${H-10}" fill="${C.accent}" font-size="12" font-family="monospace" text-anchor="middle">EJEMPLO: 6/9 → SÓLIDO</text>
    </svg>`;
}

// ─── GRÁFICO: Escala del Piotroski (0-9) ─────────────────────────────────────
function piotroski_scale() {
    const W = 680, H = 120;
    const zones = [
        { from:0, to:4, label:'DÉBIL',    color:C.red },
        { from:4, to:6, label:'NEUTRAL',  color:C.yellow },
        { from:6, to:8, label:'SÓLIDO',   color:'#90ee90' },
        { from:8, to:9, label:'EXCELENTE',color:C.accent },
    ];
    const x0 = 30, w = W - 60, y0 = 36, h = 30, max = 9;
    let segs = '';
    zones.forEach(z => {
        const sx = x0 + (z.from/max)*w, sw = ((z.to-z.from)/max)*w;
        segs += `<rect x="${sx.toFixed(1)}" y="${y0}" width="${sw.toFixed(1)}" height="${h}" fill="${z.color}" opacity="0.8"/>
            <text x="${(sx+sw/2).toFixed(1)}" y="${y0+h+16}" fill="${z.color}" font-size="10" font-family="monospace" text-anchor="middle">${z.label}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="18" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">ESCALA PIOTROSKI F-SCORE (0-9)</text>
        ${segs}
        <text x="${x0}" y="${y0+h+16}" fill="${C.text}" font-size="9" font-family="monospace">0</text>
        <text x="${x0+w}" y="${y0+h+16}" fill="${C.text}" font-size="9" font-family="monospace" text-anchor="end">9</text>
    </svg>`;
}

// ─── GRÁFICO: Comparativa sectorial de un múltiplo ───────────────────────────
function sector_comparison_example() {
    const W = 680, H = 200;
    const rows = [
        { l:'P/E Trailing', ticker:18.4, sector:24.1, favorable:true },
        { l:'EV/EBITDA',    ticker:11.2, sector:9.8,  favorable:false },
        { l:'ROE',          ticker:22.5, sector:15.3, favorable:true },
    ];
    const x0 = 140, w = 460, rowH = 50, y0 = 20;
    let bars = '';
    rows.forEach((r, i) => {
        const y = y0 + i*rowH;
        const maxV = Math.max(r.ticker, r.sector) * 1.15;
        const tw = (r.ticker/maxV)*w, sw = (r.sector/maxV)*w;
        const col = r.favorable ? C.accent : C.red;
        bars += `<text x="${x0-10}" y="${y+22}" fill="${C.textDim}" font-size="11" font-family="monospace" text-anchor="end">${r.l}</text>
            <rect x="${x0}" y="${y}" width="${tw.toFixed(1)}" height="14" fill="${col}" rx="2"/>
            <text x="${x0+tw+8}" y="${y+11}" fill="${col}" font-size="10" font-family="monospace">TICKER ${r.ticker}</text>
            <rect x="${x0}" y="${y+20}" width="${sw.toFixed(1)}" height="14" fill="${C.cyan}" opacity="0.5" rx="2"/>
            <text x="${x0+sw+8}" y="${y+31}" fill="${C.cyan}" font-size="10" font-family="monospace">SECTOR ${r.sector}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${bars}
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">VERDE/ROJO = FAVORABLE O NO FRENTE A LA MEDIANA DEL SECTOR</text>
    </svg>`;
}

// ─── GRÁFICO: Flujo de lectura de Research ───────────────────────────────────
function research_workflow() {
    const W = 680, H = 160;
    const steps = ['RSU\nSCORE', 'PIOTROSKI', 'SECTOR', 'INSIDERS', 'INSTITUC.', 'TÉCNICO'];
    const n = steps.length, boxW = 92, gap = (W - n*boxW) / (n+1);
    let items = '';
    steps.forEach((s, i) => {
        const x = gap + i*(boxW+gap);
        const y = 55;
        const lines = s.split('\n');
        items += `<rect x="${x}" y="${y}" width="${boxW}" height="46" fill="${C.surface}" stroke="${C.accent}" stroke-width="1.2" rx="5"/>
            ${lines.map((ln,li) => `<text x="${x+boxW/2}" y="${y+20+li*14}" fill="${C.text}" font-size="10.5" font-family="monospace" text-anchor="middle">${ln}</text>`).join('')}
            <text x="${x-gap/2}" y="${y+27}" fill="${C.accent}" font-size="13" text-anchor="middle">${i>0?'→':''}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="24" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">FUNDAMENTALES Y SENTIMIENTO PRIMERO — TIMING TÉCNICO AL FINAL</text>
        ${items}
    </svg>`;
}

// ─── GRÁFICO: Estado de resultados trimestral (cascada) ──────────────────────
function income_statement_quarters() {
    const W = 680, H = 240;
    const quarters = [
        { rev:100, gp:62, op:28, ni:20 },
        { rev:112, gp:70, op:33, ni:24 },
        { rev:121, gp:77, op:37, ni:27 },
        { rev:138, gp:90, op:45, ni:33 },
    ];
    const labels = ['Ingresos', 'Bº Bruto', 'Bº Operativo', 'Bº Neto'];
    const colors = [C.cyan, C.accent, C.yellow, '#90ee90'];
    const x0 = 50, y0 = 20, w = W-90, h = 170, groupW = w/quarters.length, barW = groupW/5.5;
    const maxV = 150;
    let bars = '';
    quarters.forEach((q, qi) => {
        const gx = x0 + qi*groupW;
        [q.rev, q.gp, q.op, q.ni].forEach((v, vi) => {
            const bh = (v/maxV)*h;
            const bx = gx + vi*(barW+3);
            bars += `<rect x="${bx.toFixed(1)}" y="${(y0+h-bh).toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" fill="${colors[vi]}" rx="1"/>`;
        });
        bars += `<text x="${gx+groupW/2-barW}" y="${y0+h+16}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">Q${qi+1}</text>`;
    });
    const legend = labels.map((l,i) => `<rect x="${50+i*150}" y="${H-16}" width="10" height="10" fill="${colors[i]}" rx="2"/>
        <text x="${64+i*150}" y="${H-7}" fill="${colors[i]}" font-size="9.5" font-family="monospace">${l}</text>`).join('');
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${gridLines(x0,y0,w,h)}
        ${bars}
        ${legend}
    </svg>`;
}

// ─── GRÁFICO: Escalera de márgenes ────────────────────────────────────────────
function margin_ladder() {
    const W = 680, H = 200;
    const steps = [
        { l:'Ingresos', v:100, color:C.cyan },
        { l:'– COGS', v:38, color:C.red },
        { l:'= Bº Bruto', v:62, color:C.accent },
        { l:'– Op.Ex', v:28, color:C.red },
        { l:'= Bº Operativo', v:34, color:C.accent },
        { l:'– Int./Imp.', v:10, color:C.red },
        { l:'= Bº Neto', v:24, color:'#90ee90' },
    ];
    const x0 = 20, w = W-40, y0=24, h=140, barW = w/steps.length - 8;
    let bars = '';
    steps.forEach((s,i) => {
        const x = x0 + i*(w/steps.length) + 4;
        const bh = (s.v/100)*h;
        bars += `<rect x="${x.toFixed(1)}" y="${(y0+h-bh).toFixed(1)}" width="${barW.toFixed(1)}" height="${bh.toFixed(1)}" fill="${s.color}" opacity="${s.l.startsWith('–')?0.55:1}" rx="2"/>
            <text x="${(x+barW/2).toFixed(1)}" y="${(y0+h-bh-6).toFixed(1)}" fill="${s.color}" font-size="9.5" font-family="monospace" text-anchor="middle">${s.v}</text>
            <text x="${(x+barW/2).toFixed(1)}" y="${y0+h+16}" fill="${C.textDim}" font-size="8.5" font-family="monospace" text-anchor="middle">${s.l}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${bars}
    </svg>`;
}

// ─── GRÁFICO: El mismo múltiplo, distinto contexto sectorial ────────────────
function valuation_multiples_context() {
    const W = 680, H = 200;
    const panels = [
        { sector:'TECNOLOGÍA (alto crecimiento)', pe:30, sectorAvg:34, verdict:'RAZONABLE', color:C.accent },
        { sector:'UTILITY (crecimiento bajo)',     pe:30, sectorAvg:16, verdict:'CARO',      color:C.red },
    ];
    const pw = (W-60)/2;
    let panelsHtml = '';
    panels.forEach((p,i) => {
        const x = 20 + i*(pw+20);
        panelsHtml += `<rect x="${x}" y="20" width="${pw}" height="150" fill="${C.surface}" stroke="${C.border}" rx="6"/>
            <text x="${x+pw/2}" y="42" fill="${C.textDim}" font-size="9.5" font-family="monospace" text-anchor="middle">${p.sector}</text>
            <text x="${x+pw/2}" y="85" fill="${C.text}" font-size="26" font-family="monospace" text-anchor="middle">P/E ${p.pe}x</text>
            <text x="${x+pw/2}" y="108" fill="${C.muted}" font-size="10" font-family="monospace" text-anchor="middle">Mediana sector: ${p.sectorAvg}x</text>
            <text x="${x+pw/2}" y="140" fill="${p.color}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="700">${p.verdict}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="14" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">MISMO P/E — VEREDICTO OPUESTO SEGÚN EL SECTOR</text>
        ${panelsHtml}
    </svg>`;
}

// ─── GRÁFICO: Línea temporal de catalizadores en torno a earnings ───────────
function earnings_catalysts_timeline() {
    const W = 680, H = 150;
    const events = [
        { x:0.12, l:'Compras\ninsider (P)', color:C.accent },
        { x:0.32, l:'Revisión\nanalistas', color:C.cyan },
        { x:0.55, l:'EARNINGS', color:C.yellow },
        { x:0.78, l:'Reacción\npost-earnings', color:C.accent },
        { x:0.95, l:'Ajuste\nestimaciones', color:C.cyan },
    ];
    const x0 = 30, w = W-60, y = 75;
    let items = `<line x1="${x0}" y1="${y}" x2="${x0+w}" y2="${y}" stroke="${C.border}" stroke-width="2"/>`;
    events.forEach(e => {
        const cx = x0 + e.x*w;
        const lines = e.l.split('\n');
        items += `<circle cx="${cx.toFixed(1)}" cy="${y}" r="5" fill="${e.color}"/>
            ${lines.map((ln,li) => `<text x="${cx.toFixed(1)}" y="${y-14-li*12}" fill="${e.color}" font-size="9.5" font-family="monospace" text-anchor="middle">${ln}</text>`).join('')}`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="${W/2}" y="18" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">CATALIZADORES ALREDEDOR DE UN EVENTO DE EARNINGS</text>
        ${items}
    </svg>`;
}

function triangle_three_pillars() {
    const W=680, H=270;
    const top={x:340,y:38}, bl={x:110,y:230}, br={x:570,y:230};
    const nodes=[
        {p:top,  label:'TÉCNICA',        sub:'Breakout · Trendline',      color:C.yellow, ly:top.y-24},
        {p:bl,   label:'ORDER FLOW',     sub:'Options Flow',              color:C.accent, ly:bl.y+34},
        {p:br,   label:'POSICIONAMIENTO',sub:'Insiders · Institucional',  color:C.cyan,   ly:br.y+34},
    ];
    let lines=`<line x1="${top.x}" y1="${top.y}" x2="${bl.x}" y2="${bl.y}" stroke="${C.border}" stroke-width="1.5"/>
    <line x1="${top.x}" y1="${top.y}" x2="${br.x}" y2="${br.y}" stroke="${C.border}" stroke-width="1.5"/>
    <line x1="${bl.x}" y1="${bl.y}" x2="${br.x}" y2="${br.y}" stroke="${C.border}" stroke-width="1.5"/>`;
    let nodesSvg='';
    nodes.forEach(({p,label,sub,color,ly})=>{
        nodesSvg+=`<circle cx="${p.x}" cy="${p.y}" r="22" fill="${color}" opacity="0.15" stroke="${color}" stroke-width="2"/>
        <text x="${p.x}" y="${ly}" fill="${color}" font-size="12" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${p.x}" y="${ly+16}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${sub}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${lines}
        <text x="${(top.x+bl.x+br.x)/3}" y="${(top.y+bl.y+br.y)/3+4}" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">TRIÁNGULO</text>
        <text x="${(top.x+bl.x+br.x)/3}" y="${(top.y+bl.y+br.y)/3+18}" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">RSU</text>
        ${nodesSvg}
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Tres fuentes independientes. Cuando coinciden, la coincidencia es información.</text>
    </svg>`;
}

function triangle_confidence_scale() {
    const W=680, H=190;
    const rows=[
        {n:'1 de 3', label:'Puede ser ruido', action:'No operar', color:C.red, w:180},
        {n:'2 de 3', label:'Sesgo razonable', action:'Tamaño reducido', color:C.orange, w:400},
        {n:'3 de 3', label:'Confluencia real', action:'Tamaño completo', color:C.accent, w:620},
    ];
    let content='';
    let y=20;
    rows.forEach(({n,label,action,color,w})=>{
        content+=`<rect x="20" y="${y}" width="${w}" height="38" fill="${color}" opacity="0.12" rx="4" stroke="${color}" stroke-width="1.5"/>
        <text x="34" y="${y+16}" fill="${color}" font-size="11" font-family="monospace" font-weight="bold">${n}</text>
        <text x="34" y="${y+30}" fill="${C.textDim}" font-size="9" font-family="monospace">${label}</text>
        <text x="${20+w-10}" y="${y+23}" fill="${color}" font-size="10" font-family="monospace" text-anchor="end" font-weight="bold">${action}</text>`;
        y+=52;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="${H-6}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El tamaño de la posición sigue al número de señales confirmadas — nunca a la intuición</text>
    </svg>`;
}

function order_flow_signal_reading() {
    const W=680, H=180;
    const cols=[
        {label:'TICKER', x:20, w:70},
        {label:'PRIMA', x:95, w:110},
        {label:'VOL/OI', x:210, w:90},
        {label:'TIPO', x:305, w:100},
        {label:'SCORE', x:410, w:90},
        {label:'SEÑAL', x:505, w:150},
    ];
    const row=['XYZ','$742,000','8.4x','SWEEP','92','BULLISH FUERTE'];
    let header='', cell='';
    cols.forEach((c,i)=>{
        header+=`<text x="${c.x}" y="42" fill="${C.textDim}" font-size="9" font-family="monospace" font-weight="bold">${c.label}</text>`;
        cell+=`<text x="${c.x}" y="70" fill="${i===5?C.accent:C.text}" font-size="10" font-family="monospace" font-weight="${i===5?'bold':'normal'}">${row[i]}</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="20" y="20" fill="${C.text}" font-size="11" font-family="monospace" font-weight="bold">EJEMPLO — LECTURA DE UNA FILA EN OPTIONS FLOW</text>
        <line x1="10" y1="30" x2="${W-10}" y2="30" stroke="${C.border}" stroke-width="1"/>
        ${header}
        <line x1="10" y1="50" x2="${W-10}" y2="50" stroke="${C.border}" stroke-width="1"/>
        <rect x="10" y="55" width="${W-20}" height="30" fill="${C.accent}" opacity="0.05" rx="4"/>
        ${cell}
        <text x="20" y="115" fill="${C.textDim}" font-size="9" font-family="monospace">Prima alta + Vol/OI alto (posición nueva) + ejecución sweep (urgencia) → score alto</text>
        <text x="20" y="132" fill="${C.textDim}" font-size="9" font-family="monospace">Cualquiera de estos factores por separado dice poco. Juntos, describen convicción real.</text>
    </svg>`;
}

function order_flow_consistency_days() {
    const W=680, H=190;
    const daysWeak=[0,0,1,0,0];
    const daysStrong=[1,2,2,3,4];
    function row(label,days,y,color){
        let bars='';
        days.forEach((v,i)=>{
            const h=v*14;
            bars+=`<rect x="${140+i*90}" y="${y+40-h}" width="50" height="${h}" fill="${color}" opacity="${0.25+v*0.15}" rx="3"/>`;
        });
        return `<text x="20" y="${y+24}" fill="${C.textDim}" font-size="10" font-family="monospace">${label}</text>${bars}`;
    }
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="20" y="20" fill="${C.text}" font-size="11" font-family="monospace" font-weight="bold">SEÑAL AISLADA vs SEÑAL CONSISTENTE</text>
        ${row('Operación única', daysWeak, 40, C.red)}
        ${row('Flujo de varios días', daysStrong, 100, C.accent)}
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">La repetición en la misma dirección descarta la casualidad</text>
    </svg>`;
}

function positioning_three_signals() {
    const W=680, H=210;
    const boxes=[
        {label:'INSTITUCIONAL',desc:'% del float · 13F trimestral',color:C.cyan},
        {label:'INSIDERS',desc:'Form 4 · códigos P / S',color:C.accent},
        {label:'CORTO INTERÉS',desc:'Squeeze gauge',color:C.yellow},
    ];
    const bw=190, gap=25, startX=25;
    let content='';
    boxes.forEach(({label,desc,color},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="20" width="${bw}" height="90" fill="${color}" opacity="0.08" rx="6" stroke="${color}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="55" fill="${color}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${label}</text>
        <text x="${x+bw/2}" y="72" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">${desc}</text>
        <line x1="${x+bw/2}" y1="110" x2="340" y2="150" stroke="${color}" stroke-width="1.5" opacity="0.5"/>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <rect x="250" y="150" width="180" height="40" fill="${C.text}" opacity="0.06" rx="6" stroke="${C.text}" stroke-width="1"/>
        <text x="340" y="174" fill="${C.text}" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">POSICIONAMIENTO</text>
        <text x="${W/2}" y="${H-6}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">Ninguna fuente sola confirma el pilar — se lee el conjunto</text>
    </svg>`;
}

function positioning_dynamic_warning() {
    const W=680, H=170;
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        <text x="170" y="18" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">HACE 3 SEMANAS</text>
        <rect x="30" y="28" width="280" height="90" fill="${C.accent}" opacity="0.07" rx="6" stroke="${C.accent}" stroke-width="1"/>
        <text x="170" y="55" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">Insiders comprando</text>
        <text x="170" y="72" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">Institucional al alza</text>
        <text x="170" y="89" fill="${C.accent}" font-size="10" font-family="monospace" text-anchor="middle">→ Posicionamiento alcista</text>
        <text x="${W/2}" y="80" fill="${C.textDim}" font-size="16" text-anchor="middle">→</text>
        <text x="510" y="18" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">HOY (tras rebaja de guidance)</text>
        <rect x="370" y="28" width="280" height="90" fill="${C.red}" opacity="0.07" rx="6" stroke="${C.red}" stroke-width="1"/>
        <text x="510" y="55" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">Sin nueva compra insider</text>
        <text x="510" y="72" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">Guidance a la baja</text>
        <text x="510" y="89" fill="${C.red}" font-size="10" font-family="monospace" text-anchor="middle">→ Lectura ya no es fiable</text>
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">El posicionamiento es una fotografía — vuelve a comprobarlo antes de entrar</text>
    </svg>`;
}

function triangle_workflow_order() {
    const W=680, H=200;
    const steps=[
        {n:'1',label:'Escanear',sub:'Options Flow'},
        {n:'2',label:'Revisar',sub:'Técnica'},
        {n:'3',label:'Confirmar',sub:'Posicionamiento'},
        {n:'4',label:'Esperar',sub:'Ruptura confirmada'},
        {n:'5',label:'Entrar',sub:'Con plan y R:R'},
    ];
    const bw=110, gap=22, startX=15;
    let content='';
    steps.forEach(({n,label,sub},i)=>{
        const x=startX+i*(bw+gap);
        content+=`<rect x="${x}" y="70" width="${bw}" height="70" fill="${C.accent}" opacity="${0.06+i*0.03}" rx="6" stroke="${C.accent}" stroke-width="1.5"/>
        <text x="${x+bw/2}" y="92" fill="${C.accent}" font-size="13" font-family="monospace" text-anchor="middle" font-weight="bold">${n}</text>
        <text x="${x+bw/2}" y="110" fill="${C.text}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>
        <text x="${x+bw/2}" y="124" fill="${C.textDim}" font-size="8" font-family="monospace" text-anchor="middle">${sub}</text>`;
        if(i<steps.length-1) content+=`<text x="${x+bw+gap/2}" y="112" fill="${C.accent}" font-size="14" text-anchor="middle">→</text>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <rect width="${W}" height="${H}" fill="${C.bg}" rx="6"/>
        ${content}
        <text x="${W/2}" y="18" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">EL PILAR MÁS ESCASO PRIMERO — ORDER FLOW COMO FILTRO INICIAL</text>
        <text x="${W/2}" y="${H-8}" fill="${C.textDim}" font-size="10" font-family="monospace" text-anchor="middle">No hace falta revisar toda la técnica del mercado — empieza por donde ya hay dinero grande</text>
    </svg>`;
}

export const CHARTS = {
    // Módulo 0
    rsu_philosophy, rsu_community, rsu_for_who,
    rsu_topdown, rsu_three_pillars, rsu_risk_first, rsu_patience,
    tools_market_analysis, tools_stock_selection, tools_management, tools_academy,
    weekly_ritual_sunday, weekly_ritual_daily, weekly_ritual_wait, weekly_ritual_adapt,
    // Módulo 1
    monthly_why, monthly_structure, ma10_monthly, monthly_levels,
    weekly_trend, highs_lows_weekly, weekly_emas, weekly_momentum,
    daily_context, daily_setup, daily_mas, daily_exit,
    chart_messy_vs_clean, clean_chart_setup, candle_anatomy, candle_colors,
    // Módulo 2
    hh_definition, hh_psychology, hh_identification, hh_breakout,
    hl_definition, hh_hl_combined, hl_stop_loss, hl_failure,
    lh_definition, lh_psychology, lh_short_entry, lh_reversal,
    ll_definition, lh_ll_combined, ll_trailing_stop, full_structure_read,
    // Módulo 3
    uptrend_phases, uptrend_entries, uptrend_management, uptrend_exhaustion,
    downtrend_characteristics, downtrend_early_signs, downtrend_responses, downtrend_bounces,
    range_definition, range_identification, range_strategies, range_patience,
    trendline_valid, trendline_drawing, price_channel, trendline_break,
    // Módulo 4
    fresh_support_formation, fresh_support_formation_2, fresh_support_entry, fresh_vs_consolidated,
    resistance_why, resistance_types, resistance_trading, resistance_breakout,
    zone_vs_level, zone_types, zone_marking_process, zone_update,
    multiple_touches_strength, multiple_touches_paradox, multiple_touches_volume, multiple_touches_break,
    // Módulo 5
    supply_demand_basics, demand_zone_identification, demand_zone_types, demand_zone_entry,
    supply_zone_identification, supply_zone_types, supply_zone_entry, supply_becomes_demand,
    rejection_area_definition, rejection_types, rejection_realtime, rejection_multi_tf,
    base_formation_what, base_quality, base_types, base_breakout,
    // Módulo 6
    bullish_engulfing_anatomy, bullish_engulfing_context, bullish_engulfing_trade, bullish_engulfing_volume,
    bearish_engulfing_anatomy, bearish_engulfing_context, bearish_engulfing_trade, bearish_engulfing_vs_simple,
    pin_bar_anatomy, pin_bar_types, pin_bar_entry, pin_bar_confluence,
    inside_bar_definition, inside_bar_continuation, inside_bar_reversal, inside_bar_false_break,
    // Módulo 7
    range_breakout_energy, range_breakout_real_vs_false, range_breakout_entry, range_breakout_target,
    trendline_break_significance, uptrend_line_break, downtrend_line_break, accelerated_breakout,
    support_break_why, support_break_types, support_becomes_resistance, support_break_action,
    retest_why, retest_bullish, retest_bearish, retest_failed,
    // Módulo 8
    volume_confirms_price, breakout_volume_valid, pullback_low_volume, volume_candle_reading,
    healthy_pullback_volume, pullback_volume_measure, deep_pullback_low_volume, volume_context_trap,
    climax_volume_definition, selling_climax, buying_climax, climax_at_level,
    weak_participation, weak_participation_signals, volume_price_divergence, participation_recovery,
    // Módulo 9
    ascending_triangle_anatomy, ascending_triangle_valid, ascending_triangle_breakout, ascending_triangle_context,
    descending_triangle_anatomy, descending_triangle_breakdown, descending_triangle_trend, descending_triangle_management,
    rectangle_formation, rectangle_trading, rectangle_breakout, rectangle_longterm,
    flag_anatomy, flag_quality, flag_entry_target, bear_flag,
    // Módulo 10
    monthly_bias_definition, monthly_bias_how, monthly_bias_change, monthly_bias_sectors,
    weekly_structure_semaphore, weekly_vs_monthly, weekly_pivot_point, weekly_zones_planning,
    daily_setup_context, daily_setup_types, daily_setup_scaling, daily_intraday_timing,
    trigger_definition, trigger_by_timeframe, mtf_full_process, trigger_mistakes,
    // Módulo 11
    setup_definition, setup_five_elements, setup_types_context, setup_documentation,
    rr_calculation, rr_minimum, rr_position_size, rr_alignment,
    fixed_risk_principle, position_scaling, averaging_right_wrong, sizing_psychology,
    trade_plan_why, trade_plan_structure, trade_plan_scenarios, trade_plan_expiry,
    // Módulo 12
    fixed_risk_nonnegotiable, risk_percentage_how, risk_vs_exposure, risk_accumulation,
    stop_types, stop_placement, trailing_stop_how, mental_stop_danger,
    revenge_trading_what, revenge_trading_signs, losing_streak_protocol, loss_mindset,
    capital_protection_rules, drawdown_management, position_correlation, capital_recovery_math,
    // Módulo 13
    confirmation_definition, confirmation_types, patience_vs_fear, patience_training,
    premature_entry_anatomy, premature_entry_traps, premature_entry_stats, anti_impatience_protocol,
    why_abandon_plan, two_ways_abandon, when_deviate_legit, plan_following_habit,
    ego_sabotage, exit_loss_no_ego, exit_profit_no_ego, recognize_market_change,
    // Módulo 14
    fake_breakout_why, fake_breakout_anatomy, fake_breakout_protection, fake_breakout_trapped,
    late_entry_why, late_entry_signs, late_entry_alternatives, fomo_mechanism,
    overtrading_definition, overtrading_causes, overtrading_real_cost, overtrading_limits,
    why_ignore_volume, volume_signals_ignored, volume_integration_process, volume_final_filter,
    // Módulo 15
    memory_unreliable, what_to_capture, organize_screenshots, always_capture_discipline,
    loss_vs_error, error_categories, error_log_format, error_log_review,
    setup_quality_separate, setup_review_questions, identify_best_setups, specialize_setups,
    data_to_wisdom, lessons_document_structure, personal_rules_evidence, continuous_improvement_cycle,
    // Módulo 16
    four_stages_overview, stage1_anatomy, stage1_accumulation_process, stage1_identification_signals,
    stage2_breakout, stage2_confirmation_signs, stage2_higher_lows_rule, stage2_exit_signal,
    stage3_formation, stage3_trader_vs_investor, stage3_volume_ambiguity, stage3_vs_pullback,
    stage4_breakdown, stage4_ma_resistance, stage4_buying_trap, stage4_to_stage1_cycle,
    // Módulo 17
    discounting_machine_concept, discounting_horizon_types, already_priced_in, discounting_practical_implications,
    buy_rumour_anatomy, who_buys_rumour_first, identify_rumour_phase, late_rumour_risk,
    sell_news_mechanism, three_outcome_scenarios, sell_news_vs_real_change, trading_around_known_events,
    earnings_guidance_importance, post_earnings_reaction_timeline, fed_decision_discounting, pre_event_checklist,
    // Módulo 18
    no_mans_land_vs_demand_zone, stop_distance_by_entry_quality, rr_disparity_same_target, more_room_to_target,
    strong_demand_zone_anatomy, fresh_vs_tested_zones, fake_support_vs_real_demand, zone_as_range_not_line,
    anxiety_no_mans_land, comparing_trade_experience, fewer_losses_from_placement, conviction_from_preparation,
    correct_process_order, demand_zone_insufficient_rr, comparing_multiple_opportunities, module_summary_connection,
    // Módulo 19
    trendline_break_reversal_sequence, trendline_both_directions, wick_vs_close_break,
    support_resistance_multiple_touches, confirmation_at_level_touch, level_role_reversal,
    fibonacci_retracement_levels, fibonacci_correct_drawing, fibonacci_confluence,
    consolidation_within_trend, quality_consolidation_signs, consolidation_resolution_entry,
    three_gap_types, gap_context_identification, gap_fill_behavior,
    volume_trend_pattern, volume_climax_pattern, vt_vc_alternation,
    // Módulo 20
    rsu_score_breakdown, rsu_score_labels, piotroski_criteria, piotroski_scale, sector_comparison_example, research_workflow,
    // Módulo 21
    income_statement_quarters, margin_ladder, valuation_multiples_context, earnings_catalysts_timeline,
    // Módulo 8 (ampliación)
    climax_stacking,
    // Módulo 1 (ampliación — Lección 5, EMAs)
    ema_vs_sma_reaction, ema_entry_volume, ema_exit_signal, golden_death_cross,
    // Módulo 22
    triangle_three_pillars, triangle_confidence_scale, order_flow_signal_reading,
    order_flow_consistency_days, positioning_three_signals, positioning_dynamic_warning,
    triangle_workflow_order,
};