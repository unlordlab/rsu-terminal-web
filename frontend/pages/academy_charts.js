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
    const top    = Math.min(y_open, y_close);
    const bottom = Math.max(y_open, y_close);
    const color  = bullish ? C.accent : C.red;
    return `<line x1="${cx}" y1="${y_high}" x2="${cx}" y2="${y_low}" stroke="${color}" stroke-width="1.5"/>
            <rect x="${cx - w/2}" y="${top}" width="${w}" height="${Math.max(bottom-top,2)}" fill="${bullish ? color : 'none'}" stroke="${color}" stroke-width="1.5" rx="1"/>`;
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

    function drawCandle(cx, yH, yO, yC, yL, bull, label, labelColor, annotations) {
        const color = bull ? C.accent : C.red;
        const top = Math.min(yO,yC), bottom = Math.max(yO,yC);
        let out=`<line x1="${cx}" y1="${yH}" x2="${cx}" y2="${yL}" stroke="${color}" stroke-width="2"/>
        <rect x="${cx-18}" y="${top}" width="36" height="${Math.max(bottom-top,4)}" fill="${bull?color:'none'}" stroke="${color}" stroke-width="2" rx="2"/>
        <text x="${cx}" y="${yL+20}" fill="${labelColor}" font-size="10" font-family="monospace" text-anchor="middle">${label}</text>`;
        annotations.forEach(({y,txt,side})=>{
            const lx = side==='right' ? cx+28 : cx-28;
            const anchor = side==='right' ? 'start' : 'end';
            out+=`<line x1="${cx+(side==='right'?18:-18)}" y1="${y}" x2="${lx}" y2="${y}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="3,2"/>
            <text x="${lx+(side==='right'?4:-4)}" y="${y+4}" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="${anchor}">${txt}</text>`;
        });
        return out;
    }

    // Vela alcista grande
    let svg=drawCandle(90,30,120,80,160,'bull',true,'ALCISTA',C.accent,[
        {y:30,txt:'Máximo',side:'left'},
        {y:80,txt:'Cierre',side:'left'},
        {y:120,txt:'Apertura',side:'left'},
        {y:160,txt:'Mínimo',side:'left'},
    ]);
    // Etiquetas
    svg+=`<text x="90" y="195" fill="${C.textDim}" font-size="9" font-family="monospace" text-anchor="middle">Shadow sup.</text>
    <text x="90" y="205" fill="${C.accent}" font-size="8" font-family="monospace" text-anchor="middle">(Mecha)</text>
    <line x1="90" y1="30" x2="90" y2="80" stroke="${C.accent}" stroke-width="2"/>
    <text x="115" y="100" fill="${C.accent}" font-size="9" font-family="monospace">Cuerpo</text>
    <line x1="90" y1="120" x2="90" y2="160" stroke="${C.accent}" stroke-width="2"/>`;

    // Vela bajista
    svg+=drawCandle(230,35,75,125,165,'bear',false,'BAJISTA',C.red,[]);
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

// ─── REGISTRO ─────────────────────────────────────────────────────────────────
export const CHARTS = {
    monthly_why,
    monthly_structure,
    ma10_monthly,
    monthly_levels,
    weekly_trend,
    highs_lows_weekly,
    weekly_emas,
    weekly_momentum,
    daily_context,
    daily_setup,
    daily_mas,
    daily_exit,
    chart_messy_vs_clean,
    clean_chart_setup,
    candle_anatomy,
    candle_colors,
};
