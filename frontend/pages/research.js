import { tt } from '/components/tooltip.js';

export async function render(container) {
    container.innerHTML = pageHeader();

    const input  = container.querySelector('#research-input');
    const btn    = container.querySelector('#research-btn');
    const result = container.querySelector('#research-result');

    async function doResearch() {
        const ticker = input.value.trim().toUpperCase();
        if (!ticker) return;
        btn.textContent   = 'ANALIZANDO...';
        btn.style.opacity = '0.7';
        result.innerHTML  = '<div style="color:var(--color-muted);font-size:12px;padding:1rem;">Cargando datos de ' + ticker + '...</div>';
        try {
            const token = sessionStorage.getItem('rsu_token');
            const res   = await fetch('/api/v1/research/' + ticker, {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data  = await res.json();
            if (!data.ok) throw new Error(data.error || 'Sin datos');
            result.innerHTML = renderResearch(data);
            renderSparkline(data);
            renderEarningsChart(data);
        } catch(e) {
            result.innerHTML = '<div style="padding:1rem;color:#f23645;font-size:12px;">✗ ' + e.message + '</div>';
        } finally {
            btn.textContent   = 'ANALIZAR';
            btn.style.opacity = '1';
        }
    }

    btn.addEventListener('click', doResearch);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doResearch(); });

    // Auto-cargar ticker si viene en la URL
    const urlTicker = new URLSearchParams(window.location.search).get('ticker');
    if (urlTicker) {
        input.value = urlTicker.toUpperCase();
        setTimeout(() => doResearch(), 100);
    } else {
        input.focus();
    }
}

function pageHeader() {
    return '<div style="margin-bottom:1.5rem;">'
        + '<div style="color:var(--color-accent);font-size:18px;letter-spacing:0.1em;text-shadow:var(--glow-text);margin-bottom:4px;">RESEARCH ' + tt('rsu-score') + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;">Análisis fundamental · yfinance · Finnhub · FMP · Alpha Vantage</div>'
        + '</div>'
        + '<div style="display:flex;gap:8px;margin-bottom:1.5rem;">'
        + '<input id="research-input" type="text" placeholder="AAPL, NVDA, TSLA..." style="flex:1;background:var(--color-bg,#0a0a0a);border:1px solid var(--color-border);border-radius:var(--radius);padding:10px 14px;color:var(--color-text);font-family:var(--font-mono);font-size:14px;outline:none;">'
        + '<button id="research-btn" style="background:var(--color-accent);color:#000;border:none;border-radius:var(--radius);padding:10px 20px;font-family:var(--font-mono);font-size:13px;cursor:pointer;letter-spacing:0.05em;font-weight:500;">ANALIZAR</button>'
        + '</div>'
        + '<div id="research-result"></div>';
}

function renderResearch(data) {
    const chgColor   = data.chg_pct >= 0 ? 'var(--color-accent)' : '#f23645';
    const chgStr     = (data.chg_pct >= 0 ? '+' : '') + data.chg_pct.toFixed(2) + '%';
    const score      = data.rsu_score;
    const scoreColor = score.color;

    return headerSection(data, chgColor, chgStr)
        + descriptionSection(data)
        + rsuScoreSection(score, scoreColor)
        + chartSection(data)
        + technicalSection(data)
        + metricsSection(data)
        + consensoSection(data)
        + analystChangesSection(data)
        + seasonalitySection(data)
        + insiderSection(data)
        + earningsSection(data)
        + suggestionsSection(data)
        + newsSection(data);
}

// ── SECCIONES ─────────────────────────────────────────────────────────────────

// ── SECCIONES ─────────────────────────────────────────────────────────────────

function headerSection(data, chgColor, chgStr) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">'
        + '<div>'
        + '<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px;">'
        + '<span onclick="goToResearch(\'' + data.ticker + '\')" class="ticker-link" style="color:var(--color-accent);font-size:24px;letter-spacing:0.1em;">' + data.ticker + '</span>'
        + '<span style="color:var(--color-muted);font-size:14px;">' + data.name + '</span>'
        + '</div>'
        + '<div style="color:var(--color-muted);font-size:12px;margin-bottom:4px;">' + data.sector + ' · ' + data.industry + ' · ' + data.country + '</div>'
        + (data.website ? '<a href="' + data.website + '" target="_blank" style="color:var(--color-secondary);font-size:11px;">' + data.website + '</a>' : '')
        + '</div>'
        + '<div style="text-align:right;">'
        + '<div style="color:var(--color-text);font-size:28px;font-weight:500;">$' + data.price.toLocaleString('en-US') + '</div>'
        + '<div style="color:' + chgColor + ';font-size:13px;">' + chgStr + ' hoy</div>'
        + '<div style="color:var(--color-muted);font-size:11px;margin-top:2px;">' + data.mktcap_fmt + ' market cap</div>'
        + '</div>'
        + '</div>'
        + '<div style="display:flex;gap:2rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--color-border);font-size:11px;flex-wrap:wrap;">'
        + (data.week52_low  ? '<span style="color:var(--color-muted);">52w Low: <b style="color:var(--color-text);">$' + data.week52_low.toFixed(2) + '</b></span>' : '')
        + (data.week52_high ? '<span style="color:var(--color-muted);">52w High: <b style="color:var(--color-text);">$' + data.week52_high.toFixed(2) + '</b></span>' : '')
        + (data.beta        ? '<span style="color:var(--color-muted);">Beta: <b style="color:var(--color-text);">' + data.beta.toFixed(2) + '</b></span>' : '')
        + (data.dividend_yield ? '<span style="color:var(--color-muted);">Dividendo: <b style="color:var(--color-accent);">' + (data.dividend_yield * 100).toFixed(2) + '%</b></span>' : '')
        + '</div>'
        + '</div>';
}

function descriptionSection(data) {
    if (!data.description) return '';
    const short = data.description.substring(0, 300);
    const full  = data.description;
    const hasMore = full.length > 300;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">DESCRIPCIÓN</div>'
        + '<div id="desc-short" style="color:var(--color-muted);font-size:12px;line-height:1.7;">' + short + (hasMore ? '...' : '') + '</div>'
        + (hasMore
            ? '<div id="desc-full" style="color:var(--color-muted);font-size:12px;line-height:1.7;display:none;">' + full + '</div>'
              + '<button onclick="toggleDesc()" id="desc-btn" style="background:none;border:none;color:var(--color-secondary);font-size:11px;cursor:pointer;margin-top:6px;font-family:var(--font-mono);">▼ Ver más</button>'
            : '')
        + '</div>';
}

function rsuScoreSection(score, scoreColor) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<span style="color:var(--color-muted);font-size:11px;letter-spacing:0.08em;">RSU SCORE ' + tt('rsu-score') + '</span>'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<span style="color:' + scoreColor + ';font-size:20px;font-weight:500;">' + score.score + '/100</span>'
        + '<span style="color:' + scoreColor + ';font-size:12px;padding:2px 10px;border:1px solid ' + scoreColor + '33;border-radius:4px;">' + score.label + '</span>'
        + '</div></div>'
        + '<div style="background:var(--color-bg,#0a0a0a);border-radius:4px;height:6px;margin-bottom:8px;">'
        + '<div style="height:100%;width:' + score.score + '%;background:' + scoreColor + ';border-radius:4px;transition:width 0.8s;"></div>'
        + '</div>'
        + '<div style="display:flex;gap:1rem;flex-wrap:wrap;">'
        + (score.breakdown || []).map(b => {
            const pct = b.max > 0 ? Math.round(b.pts / b.max * 100) : 0;
            return '<div style="font-size:10px;color:var(--color-muted);">'
                + b.label + ': <span style="color:' + (pct >= 75 ? 'var(--color-accent)' : pct >= 50 ? '#ffb800' : '#f23645') + ';">' + b.pts + '/' + b.max + '</span>'
                + ' <span style="color:var(--color-muted);">(' + b.val + ')</span>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

function chartSection(data) {
    const tvSymbol = data.ticker;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--color-border);">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">GRÁFICO · TRADINGVIEW</div>'
        + '<div style="color:var(--color-muted);font-size:11px;">Diario · 1 año</div>'
        + '</div>'
        + '<div style="height:400px;">'
        + '<iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tv_chart&symbol=' + tvSymbol
        + '&interval=D&hidesidetoolbar=1&hidetoptoolbar=0&symboledit=0&saveimage=0&toolbarbg=1a1a1a&theme=dark&style=1&timezone=Europe%2FMadrid&studies=[]&locale=es"'
        + ' style="width:100%;height:100%;border:none;" allowtransparency="true" frameborder="0" scrolling="no"></iframe>'
        + '</div>'
        + '</div>';
}

function metricsSection(data) {
    const m = data.metrics;
    const p = data.profitability;
    return '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">'
        + metricCard('VALORACIÓN', [
            ['P/E Trailing',  m.trailing_pe,    v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['P/E Forward',   m.forward_pe,     v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['P/S',           m.price_to_sales, v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['EV/EBITDA',     m.ev_ebitda,      v => v ? v.toFixed(1) + 'x' : 'N/A'],
            ['PEG',           m.peg_ratio,      v => v ? v.toFixed(2)        : 'N/A'],
            ['P/B',           m.price_to_book,  v => v ? v.toFixed(2) + 'x' : 'N/A'],
        ])
        + metricCard('RENTABILIDAD', [
            ['ROE',           p.roe,            v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['ROA',           p.roa,            v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Margen Neto',   p.net_margin,     v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Margen Op.',    p.op_margin,      v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Margen Bruto',  p.gross_margin,   v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['D/E Ratio',     p.debt_to_equity, v => v ? v.toFixed(0) + '%'       : 'N/A'],
        ])
        + metricCard('CRECIMIENTO', [
            ['Revenue Growth',  p.revenue_growth,  v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Earnings Growth', p.earnings_growth, v => v ? (v*100).toFixed(1) + '%' : 'N/A'],
            ['Current Ratio',   p.current_ratio,   v => v ? v.toFixed(2) + 'x'       : 'N/A'],
            ['Free Cash Flow',  p.free_cashflow,   v => v ? _fmtVal(v)                : 'N/A'],
            ['Div. Yield',      data.dividend_yield, v => v ? (v*100).toFixed(2) + '%' : 'N/A'],
            ['N. Analistas',    data.n_analysts,   v => v ? v + ' analistas'           : 'N/A'],
        ])
        + '</div>';
}

function consensoSection(data) {
    if (!data.recommendations || !data.recommendations.total) return '';
    const r     = data.recommendations;
    const total = r.total;
    const bars  = [
        ['Strong Buy',  r.strong_buy,  '#00ffad'],
        ['Buy',         r.buy,         '#90ee90'],
        ['Hold',        r.hold,        '#ffb800'],
        ['Sell',        r.sell,        '#ff8c00'],
        ['Strong Sell', r.strong_sell, '#f23645'],
    ];
    const buyPct = total > 0 ? Math.round((r.strong_buy + r.buy) / total * 100) : 0;
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">CONSENSO ANALISTAS</div>'
        + (data.target_data.mean ? '<div style="font-size:12px;color:var(--color-muted);">Objetivo: <span style="color:var(--color-text);">$' + data.target_data.mean.toFixed(2) + '</span> · <span style="color:' + (data.target_data.upside >= 0 ? 'var(--color-accent)' : '#f23645') + ';">' + (data.target_data.upside >= 0 ? '+' : '') + data.target_data.upside.toFixed(1) + '%</span></div>' : '')
        + '</div>'
        + '<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;">'
        + bars.map(([label, count, color]) => {
            const pct = total > 0 ? Math.round(count / total * 100) : 0;
            return '<div style="flex:1;min-width:70px;text-align:center;">'
                + '<div style="color:' + color + ';font-size:18px;font-weight:500;">' + count + '</div>'
                + '<div style="color:var(--color-muted);font-size:10px;margin-top:2px;">' + label + '</div>'
                + '<div style="background:var(--color-bg,#0a0a0a);border-radius:2px;height:4px;margin-top:4px;">'
                + '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:2px;"></div>'
                + '</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

function analystChangesSection(data) {
    const changes = data.analyst_changes || [];
    if (!changes.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">CAMBIOS DE RATING ANALISTAS</div>'
        + '<div style="display:grid;grid-template-columns:80px 1fr 100px 1fr;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>FIRMA</div><div>ACCIÓN</div><div>CAMBIO</div>'
        + '</div>'
        + changes.map(c => {
            const arrow = c.from_grade && c.to_grade ? c.from_grade + ' → ' + c.to_grade : c.to_grade || c.from_grade || '—';
            return '<div style="display:grid;grid-template-columns:80px 1fr 100px 1fr;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
                + '<div style="color:var(--color-muted);">' + c.date + '</div>'
                + '<div style="color:var(--color-text);">' + c.firm + '</div>'
                + '<div style="background:' + c.action_color + '22;color:' + c.action_color + ';border:1px solid ' + c.action_color + '44;border-radius:3px;padding:2px 8px;font-size:10px;text-align:center;">' + c.action + '</div>'
                + '<div style="color:var(--color-muted);">' + arrow + '</div>'
                + '</div>';
        }).join('')
        + '</div>';
}

function earningsSection(data) {
    if (!data.quarterly_earnings || !data.quarterly_earnings.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">EPS TRIMESTRAL · HISTÓRICO</div>'
        + '<div style="position:relative;height:140px;"><canvas id="earnings-chart"></canvas></div>'
        + '</div>';
}

function suggestionsSection(data) {
    if (!data.suggestions || !data.suggestions.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">ANÁLISIS RSU</div>'
        + data.suggestions.map(s => '<div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;color:var(--color-text);line-height:1.5;">' + s + '</div>').join('')
        + '</div>';
}

function newsSection(data) {
    if (!data.news || !data.news.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:0.75rem;">NOTICIAS RECIENTES</div>'
        + data.news.map(n => '<div style="padding:8px 0;border-bottom:1px solid var(--color-border);">'
            + '<a href="' + n.url + '" target="_blank" style="color:var(--color-text);font-size:12px;line-height:1.4;display:block;">' + n.headline + '</a>'
            + '<div style="color:var(--color-muted);font-size:10px;margin-top:3px;">' + n.source + '</div>'
            + '</div>').join('')
        + '</div>';
}

function technicalSection(data) {
    const t = data.technical_levels;
    const s = data.short_interest;
    const ne = data.next_earnings;
    if (!t || Object.keys(t).length === 0) return '';

    function vsColor(val) {
        if (val == null) return 'var(--color-muted)';
        return val >= 0 ? 'var(--color-accent)' : '#f23645';
    }
    function vsStr(val) {
        if (val == null) return 'N/A';
        return (val >= 0 ? '+' : '') + val + '%';
    }

    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">NIVELES TÉCNICOS · CORTO INTERÉS · PRÓXIMO EARNINGS</div>'
        + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">'

        // Niveles técnicos
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">MEDIAS MÓVILES</div>'
        + techRow('SMA 20',  t.sma20,  t.vs_sma20)
        + techRow('SMA 50',  t.sma50,  t.vs_sma50)
        + techRow('SMA 200', t.sma200, t.vs_sma200)
        + '</div>'

        // 52 semanas
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">RANGO 52 SEMANAS</div>'
        + techRow('Máx 52w', null, t.vs_52h)
        + techRow('Mín 52w', null, t.vs_52l)
        + (t.above_sma50 != null ? '<div style="font-size:11px;margin-top:8px;color:' + (t.above_sma50 ? 'var(--color-accent)' : '#f23645') + ';">' + (t.above_sma50 ? '✓ Sobre SMA50' : '✗ Bajo SMA50') + '</div>' : '')
        + (t.above_sma200 != null ? '<div style="font-size:11px;color:' + (t.above_sma200 ? 'var(--color-accent)' : '#f23645') + ';">' + (t.above_sma200 ? '✓ Sobre SMA200' : '✗ Bajo SMA200') + '</div>' : '')
        + '</div>'

        // Short interest + next earnings
        + '<div>'
        + '<div style="color:var(--color-muted);font-size:10px;margin-bottom:8px;letter-spacing:0.05em;">SHORT INTEREST</div>'
        + (s && s.short_pct != null
            ? '<div style="font-size:20px;color:' + (s.short_pct > 20 ? '#f23645' : s.short_pct > 10 ? '#ffb800' : 'var(--color-text)') + ';font-weight:500;">' + s.short_pct + '%</div>'
              + '<div style="color:var(--color-muted);font-size:10px;">del float · ' + (s.date || '') + '</div>'
            : '<div style="color:var(--color-muted);font-size:11px;">Sin datos</div>')
        + (ne && ne.date
            ? '<div style="margin-top:12px;"><div style="color:var(--color-muted);font-size:10px;margin-bottom:4px;letter-spacing:0.05em;">PRÓXIMO EARNINGS</div>'
              + '<div style="color:#ffb800;font-size:14px;font-weight:500;">📅 ' + ne.date + '</div>'
              + (ne.eps_est != null ? '<div style="color:var(--color-muted);font-size:11px;">EPS Est: $' + ne.eps_est.toFixed(2) + '</div>' : '')
              + (ne.hour ? '<div style="color:var(--color-muted);font-size:10px;">' + (ne.hour.toLowerCase().includes('bmo') ? 'BMO 🌅' : 'AMC 🌙') + '</div>' : '')
              + '</div>'
            : '')
        + '</div>'
        + '</div>'
        + '</div>';
}

function techRow(label, price, vs) {
    const color = vs == null ? 'var(--color-muted)' : vs >= 0 ? 'var(--color-accent)' : '#f23645';
    const vsStr = vs == null ? 'N/A' : (vs >= 0 ? '+' : '') + vs + '%';
    return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
        + '<span style="color:var(--color-muted);">' + label + (price ? ' $' + price : '') + '</span>'
        + '<span style="color:' + color + ';">' + vsStr + '</span>'
        + '</div>';
}

function seasonalitySection(data) {
    const season = data.seasonality;
    if (!season || !season.length) return '';
    const max = Math.max(...season.map(s => Math.abs(s.avg)));
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1.25rem;margin-bottom:1rem;">'
        + '<div style="color:var(--color-accent);font-size:12px;letter-spacing:0.08em;margin-bottom:1rem;">ESTACIONALIDAD · RENDIMIENTO MEDIO MENSUAL (5 AÑOS)</div>'
        + '<div style="display:grid;grid-template-columns:repeat(12,1fr);gap:4px;">'
        + season.map(s => {
            const h = max > 0 ? Math.round(Math.abs(s.avg) / max * 60) : 0;
            return '<div style="text-align:center;">'
                + '<div style="font-size:9px;color:var(--color-muted);margin-bottom:4px;">' + s.month + '</div>'
                + '<div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:70px;">'
                + '<div style="width:100%;background:' + s.color + ';height:' + h + 'px;border-radius:2px;min-height:3px;"></div>'
                + '</div>'
                + '<div style="font-size:9px;color:' + s.color + ';margin-top:4px;">' + (s.avg > 0 ? '+' : '') + s.avg + '%</div>'
                + '</div>';
        }).join('')
        + '</div>'
        + '</div>';
}

function insiderSection(data) {
    const insider = data.insider_trading;
    if (!insider || !insider.length) return '';
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);overflow:hidden;margin-bottom:1rem;">'
        + '<div style="padding:10px 14px;border-bottom:1px solid var(--color-border);color:var(--color-accent);font-size:12px;letter-spacing:0.08em;">INSIDER TRADING · TRANSACCIONES DIRECTIVOS</div>'
        + '<div style="display:grid;grid-template-columns:90px 1fr 120px 70px 80px 80px;gap:8px;padding:6px 14px;border-bottom:1px solid var(--color-border);font-size:10px;color:var(--color-muted);">'
        + '<div>FECHA</div><div>NOMBRE</div><div>CARGO</div><div>TIPO</div><div>ACCIONES</div><div>VALOR</div>'
        + '</div>'
        + insider.map(i => '<div style="display:grid;grid-template-columns:90px 1fr 120px 70px 80px 80px;gap:8px;padding:8px 14px;border-bottom:1px solid var(--color-border);font-size:11px;align-items:center;">'
            + '<div style="color:var(--color-muted);">' + i.date + '</div>'
            + '<div style="color:var(--color-text);">' + i.name + '</div>'
            + '<div style="color:var(--color-muted);font-size:10px;">' + i.title + '</div>'
            + '<div style="background:' + i.type_color + '22;color:' + i.type_color + ';border:1px solid ' + i.type_color + '44;border-radius:3px;padding:2px 6px;font-size:10px;text-align:center;">' + i.type + '</div>'
            + '<div style="color:var(--color-text);">' + i.shares.toLocaleString('en-US') + '</div>'
            + '<div style="color:var(--color-text);">' + i.value + '</div>'
            + '</div>').join('')
        + '</div>';
}
// ── HELPERS ───────────────────────────────────────────────────────────────────

function metricCard(title, rows) {
    return '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:1rem;">'
        + '<div style="color:var(--color-accent);font-size:11px;letter-spacing:0.08em;margin-bottom:0.75rem;">' + title + '</div>'
        + rows.map(([label, val, fmt]) => {
            const fmtVal = fmt(val);
            return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--color-border);font-size:11px;">'
                + '<span style="color:var(--color-muted);">' + label + '</span>'
                + '<span style="color:' + (fmtVal !== 'N/A' ? 'var(--color-text)' : 'var(--color-muted)') + ';">' + fmtVal + '</span>'
                + '</div>';
        }).join('')
        + '</div>';
}

function _fmtVal(val) {
    if (val == null) return 'N/A';
    try {
        const v = parseFloat(val);
        if (Math.abs(v) >= 1e12) return '$' + (v/1e12).toFixed(2) + 'T';
        if (Math.abs(v) >= 1e9)  return '$' + (v/1e9).toFixed(2) + 'B';
        if (Math.abs(v) >= 1e6)  return '$' + (v/1e6).toFixed(2) + 'M';
        return '$' + v.toFixed(2);
    } catch(e) { return 'N/A'; }
}

function renderSparkline(data) {
    if (!data.sparkline || data.sparkline.length < 2) return;
    const color = data.chg_pct >= 0 ? '#00ffad' : '#f23645';
    loadChartJs(() => {
        const ctx = document.getElementById('sparkline-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.sparkline.map((_, i) => i),
                datasets: [{ data: data.sparkline, borderColor: color, backgroundColor: color + '18', borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { display: false }, y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.04)' }, min: Math.min(...data.sparkline) * 0.995, max: Math.max(...data.sparkline) * 1.005 } }
            }
        });
    });
}

function renderEarningsChart(data) {
    if (!data.quarterly_earnings || !data.quarterly_earnings.length) return;
    const earnings = [...data.quarterly_earnings].reverse();
    loadChartJs(() => {
        const ctx = document.getElementById('earnings-chart');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: earnings.map(e => e.date.substring(0, 7)),
                datasets: [
                    { label: 'Reportado', data: earnings.map(e => e.reported), backgroundColor: earnings.map(e => e.reported >= (e.estimated || 0) ? '#00ffad88' : '#f2364588'), borderColor: earnings.map(e => e.reported >= (e.estimated || 0) ? '#00ffad' : '#f23645'), borderWidth: 1 },
                    { label: 'Estimado', data: earnings.map(e => e.estimated), backgroundColor: 'transparent', borderColor: '#ffb800', borderWidth: 1.5, type: 'line', pointRadius: 3, tension: 0.3 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#666', font: { size: 10 } } } },
                scales: { x: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } }, y: { ticks: { color: '#555', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } } }
            }
        });
    });
}

function loadChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = cb;
    document.head.appendChild(s);
}

// Toggle descripción
window.toggleDesc = function() {
    const short = document.getElementById('desc-short');
    const full  = document.getElementById('desc-full');
    const btn   = document.getElementById('desc-btn');
    if (!short || !full || !btn) return;
    const isShowing = full.style.display === 'none';
    short.style.display = isShowing ? 'none' : 'block';
    full.style.display  = isShowing ? 'block' : 'none';
    btn.textContent     = isShowing ? '▲ Ver menos' : '▼ Ver más';
};