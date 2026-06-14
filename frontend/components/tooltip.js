// Componente reutilizable de tooltips explicativos
// Uso: Tooltip.init() en cualquier página
// HTML: <span data-tooltip="key">?</span>

export const TOOLTIPS = {

    // ── MARKET ────────────────────────────────────────────────────────────────
    "fear-greed": {
        title: "Fear & Greed Index",
        short: "Mide el sentimiento del mercado de 0 (miedo extremo) a 100 (codicia extrema).",
        long: `El Fear & Greed Index de CNN mide el sentimiento del mercado combinando 7 indicadores:
        
▸ Momentum del mercado (SPX vs MA125)
▸ Fuerza del precio de las acciones (nuevos máximos vs mínimos)
▸ Amplitud del precio (volumen alcista vs bajista)
▸ Put/Call Ratio (opciones de venta vs compra)
▸ Demanda de bonos basura (spread HY vs IG)
▸ Volatilidad implícita (VIX)
▸ Demanda de refugio seguro (bonos vs acciones)

CÓMO USARLO:
- 0-25 → Miedo extremo → Históricamente zona de compra
- 25-45 → Miedo → Posible oportunidad
- 45-55 → Neutral → Sin señal clara
- 55-75 → Codicia → Precaución
- 75-100 → Codicia extrema → Posible techo de mercado

Warren Buffett: "Sé temeroso cuando otros son codiciosos, y codicioso cuando otros son temerosos."`
    },

    "vix": {
        title: "VIX — Índice de Volatilidad",
        short: "El 'índice del miedo'. Mide la volatilidad implícita esperada del S&P 500 a 30 días.",
        long: `El VIX (CBOE Volatility Index) mide cuánta volatilidad espera el mercado en los próximos 30 días, calculado a partir de los precios de opciones del S&P 500.

NIVELES CLAVE:
- < 15 → Complacencia. Mercado tranquilo. Ojo con la trampa.
- 15-20 → Normal. Sin señal clara.
- 20-25 → Precaución. Volatilidad elevándose.
- 25-30 → Estrés. Mercado nervioso.
- > 30 → Miedo. Zona histórica de oportunidad.
- > 40 → Pánico extremo. Máximas oportunidades históricas.

TERM STRUCTURE:
Cuando el VIX spot > futuros = BACKWARDATION → señal de pánico, posible suelo.
Cuando el VIX spot < futuros = CONTANGO → mercado tranquilo, normal.

El VIX y el SPX tienen correlación negativa de ~-0.7. Cuando el mercado cae, el VIX sube.`
    },

    "vix-term-structure": {
        title: "VIX Term Structure",
        short: "Curva de futuros del VIX. Contango = normal. Backwardation = estrés/oportunidad.",
        long: `La Term Structure del VIX muestra los precios de los futuros del VIX a distintos vencimientos.

CONTANGO (curva ascendente):
Los futuros cotizan más caro que el spot. Situación normal. El mercado espera que la volatilidad aumente con el tiempo, lo cual es estadísticamente habitual.

BACKWARDATION (curva descendente):
El spot cotiza más caro que los futuros. Situación de estrés agudo. El mercado tiene miedo AHORA pero espera que se calme. Históricamente, la backwardation pronunciada coincide con suelos de mercado importantes.

SPREAD SPOT-ÚLTIMO:
La diferencia entre el VIX spot y el futuro más lejano. 
- Spread positivo alto → contango pronunciado → complacencia
- Spread negativo → backwardation → oportunidad potencial

Los traders profesionales monitorean esta curva para timing de entradas en volatilidad.`
    },

    "credit-spreads": {
        title: "Credit Spreads (OAS)",
        short: "Diferencial de rentabilidad entre bonos corporativos y bonos del Tesoro. Mide el riesgo de crédito.",
        long: `Los Credit Spreads miden cuánto extra de rentabilidad exigen los inversores por asumir riesgo crediticio corporativo vs la seguridad del bono del Tesoro americano.

HY OAS (High Yield Option-Adjusted Spread):
Diferencial de bonos basura (calificación BB o inferior) vs Tesoro.
- < 3% → Complacencia extrema. Mercado ignora riesgos.
- 3-5% → Normal.
- 5-8% → Estrés. Mercado pricing deterioro económico.
- > 8% → Crisis. Zona de oportunidad histórica en renta variable.

IG OAS (Investment Grade):
Diferencial de bonos de alta calidad vs Tesoro. Menos volátil.

POR QUÉ IMPORTA PARA ACCIONES:
Los credit spreads se amplían ANTES de que el mercado de renta variable lo refleje. Son un indicador adelantado de recesión o crisis. Cuando los spreads se disparan, prepárate.

La correlación entre spreads HY y el VIX es muy alta en momentos de estrés.`
    },

    "ad-line": {
        title: "AD Line — Advance/Decline Line",
        short: "Número de acciones que suben menos las que bajan, acumulado. Mide la amplitud real del mercado.",
        long: `La Advance/Decline Line es el indicador de amplitud de mercado más importante. Muestra si el rally del índice está siendo participado por la mayoría de acciones o solo por unas pocas.

CÁLCULO:
Cada día: (Acciones que suben) - (Acciones que bajan) + valor anterior.

DIVERGENCIAS — LO MÁS IMPORTANTE:
▸ Mercado sube pero AD Line baja → DIVERGENCIA BAJISTA. El rally se está estrechando. Señal de techo potencial.
▸ Mercado cae pero AD Line sube → DIVERGENCIA ALCISTA. La caída no tiene participación. Posible suelo.

EJEMPLOS HISTÓRICOS:
- 2007: AD Line divergió negativamente meses antes del crash de 2008.
- 2020: AD Line confirmó el rally post-COVID rápidamente → señal de salud.
- 2021-2022: AD Line divergió negativamente mientras el SPX marcaba máximos → predijo la corrección.

Un mercado sano tiene AD Line confirmando los máximos del índice.`
    },
// ── OPTIONS FLOW ──────────────────────────────────────────────────────────
    "options-flow": {
        title: "Options Flow — Flujo de Opciones",
        short: "Registro de operaciones inusuales en opciones. Prima alta + Vol/OI elevado = posible posicionamiento institucional.",
        long: `El flujo de opciones inusual rastrea operaciones donde el volumen y la prima pagada superan significativamente lo habitual para ese contrato.

POR QUÉ IMPORTA:
Las instituciones no pueden ocultar sus operaciones en opciones. Cuando alguien paga $3M en calls de HOOD a 60 días, eso deja huella en el volumen — y nosotros la vemos.

LO QUE BUSCAMOS:
▸ Prima alta (>$100K) → tamaño institucional
▸ Vol/OI ratio alto (>2x) → posición completamente nueva
▸ Strike OTM 5-25% → el sweet spot táctico institucional
▸ Vencimiento 14-60 días → timing direccional, no especulativo

LIMITACIÓN IMPORTANTE:
Estos datos son EOD (end of day) — del cierre del día anterior. Para opciones a corto plazo (0-5 días) el retraso importa mucho. Para posiciones a semanas o meses, el retraso es irrelevante — la señal sigue siendo válida.`
    },

    "vol-oi-ratio": {
        title: "Vol/OI Ratio — Volumen vs Open Interest",
        short: "Cuánto volumen nuevo se ha negociado respecto al OI existente. >1x = posición nueva. >2x = señal fuerte.",
        long: `El ratio Vol/OI es uno de los indicadores más importantes para distinguir flujo institucional nuevo del ruido de trading habitual.

OPEN INTEREST (OI):
Número total de contratos abiertos en ese strike/vencimiento. Es la posición acumulada de todos los participantes.

VOLUMEN:
Contratos negociados HOY en ese strike/vencimiento.

INTERPRETACIÓN:
- Vol/OI < 0.1 → Actividad mínima, ruido
- Vol/OI 0.1-0.5 → Actividad normal
- Vol/OI 0.5-1.0 → Interés elevado
- Vol/OI 1.0-2.0 → Posición nueva significativa
- Vol/OI > 2.0 → SEÑAL FUERTE — alguien está abriendo posición grande nueva

EJEMPLO:
Strike $85 con OI = 5.000 y Vol = 12.000 → Vol/OI = 2.4x
Esto significa que se han negociado más contratos hoy que todos los que existían ayer. Es posición nueva, no cierre de existentes.`
    },

    "options-score": {
        title: "Score — Puntuación de Señal",
        short: "Score 0-10 que combina prima, Vol/OI, IV, strike OTM y vencimiento. ≥7 = señal HIGH.",
        long: `El Score es un sistema propio RSU que combina múltiples factores para priorizar las señales más relevantes.

COMPONENTES DEL SCORE:

Prima (máx 3pts):
- >$1M → 3pts
- >$500K → 2pts
- >$100K → 1pt

Vol/OI Ratio (máx 2pts):
- >2.0x → 2pts
- >0.5x → 1pt

Implied Volatility (máx 2pts):
- IV >80% → 2pts (pagan caro = alta convicción)
- IV >40% → 1pt

Strike OTM (máx 2pts):
- 5-25% OTM → 2pts (sweet spot institucional)
- 0-5% OTM → 1pt

Vencimiento (máx 1pt):
- 14-60 días → 1pt (timing táctico)

NIVELES:
- Score 8-10 → HIGH ⚡ Señal de alta convicción
- Score 5-7  → MEDIUM 📊 Señal a seguir
- Score <5   → LOW Ruido filtrado`
    },

    "calls-bought": {
        title: "Calls Bought — Compra de Calls",
        short: "Compras de opciones call. Señal alcista — el comprador apuesta a que el precio sube.",
        long: `Una Call comprada da al comprador el derecho (no la obligación) de comprar el activo al precio strike antes del vencimiento.

SEÑAL ALCISTA:
Quien compra una call está apostando a que el precio del subyacente supera el strike antes del vencimiento. Cuanto más OTM el strike y mayor la prima pagada, mayor es la convicción del comprador.

EJEMPLO:
NVDA Call $250 vencimiento 45 días, prima $2M
→ Alguien paga $2M apostando a que NVDA supera $250 en 45 días
→ Si NVDA está en $220, necesita subir +13.6%

CALLS BOUGHT vs CALLS SOLD:
- Calls Bought → Alcista (apuesta a subida)
- Calls Sold (Covered/Naked) → Neutral/Bajista (apuesta a que NO sube)`
    },

    "puts-bought": {
        title: "Puts Bought — Compra de Puts",
        short: "Compras de opciones put. Señal bajista — el comprador se protege o apuesta a caída.",
        long: `Una Put comprada da al comprador el derecho de vender el activo al precio strike. Es la cobertura o apuesta bajista más directa.

DOS INTERPRETACIONES:

1. COBERTURA (Hedge):
Un fondo que tiene 1M de acciones de MSFT compra puts para protegerse de una caída. No es necesariamente bajista en la acción, solo se cubre.

2. APUESTA BAJISTA PURA:
Comprar puts OTM con vencimiento corto/medio sin posición en el subyacente es apostar a que el precio cae.

CÓMO DISTINGUIRLAS:
- Puts muy OTM (>20%) con vencimiento largo → probablemente cobertura de cartera
- Puts cerca del precio actual con vencimiento corto → apuesta bajista táctica

SEÑAL MÁS RELEVANTE:
Puts compradas en tickers individuales (no ETFs como SPY/QQQ) son más significativas como señal bajista.`
    },

    "puts-sold": {
        title: "Puts Sold — Venta de Puts",
        short: "Venta de opciones put. Señal alcista — el vendedor apuesta a que el precio NO baja.",
        long: `Vender una put obliga al vendedor a comprar el activo al precio strike si el comprador ejerce. Es una estrategia alcista o neutral.

SEÑAL ALCISTA:
Quien vende puts está diciendo "estoy dispuesto a comprar este activo a este precio" o simplemente cree que el precio no caerá hasta ese nivel.

ESTRATEGIAS COMUNES:
- Sell Put para generar ingreso (premium selling)
- Sell Put como forma de comprar acciones a precio deseado
- Wheel strategy: vender puts, si te asignan vender calls

INTERPRETACIÓN EN OPCIONES FLOW:
Puts vendidas masivas en un ticker = la "smart money" cree que NO va a bajar. Es una señal alcista implícita.

EJEMPLO:
SPY Sell Put $500, 30 días, prima $1.5M
→ Alguien recibe $1.5M apostando a que SPY no cae por debajo de $500 en 30 días`
    },

    "calls-sold": {
        title: "Calls Sold — Venta de Calls",
        short: "Venta de opciones call. Señal bajista o neutral — apuesta a que el precio NO sube.",
        long: `Vender una call obliga al vendedor a entregar el activo al precio strike si se ejerce. Es bajista o neutral.

DOS TIPOS:

COVERED CALL (Cubierta):
El vendedor ya tiene las acciones y vende calls para generar ingreso extra. Es una estrategia neutral — cree que el precio no subirá mucho más.

NAKED CALL (Descubierta):
El vendedor NO tiene las acciones. Es extremadamente arriesgado y señal bajista fuerte — apuesta a que el precio NO sube.

SEÑAL EN OPTIONS FLOW:
Calls vendidas masivas = la smart money cree que el precio tiene techo en ese strike.

DIFERENCIA CON BUY CALL:
- Buy Call → quiero que suba → ALCISTA
- Sell Call → creo que NO sube → BAJISTA/NEUTRAL`
    },

    "net-score-options": {
        title: "Net Score — Puntuación Neta",
        short: "Calls Bought - Puts Bought. Positivo = flujo alcista neto. Negativo = flujo bajista neto.",
        long: `El Net Score es un indicador resumen del sesgo direccional del flujo de opciones para un ticker específico.

CÁLCULO:
Net Score = (nº señales alcistas) - (nº señales bajistas)
Donde alcistas = Calls Bought + Puts Sold
Y bajistas = Puts Bought + Calls Sold

INTERPRETACIÓN:
- Score muy positivo (+5 o más) → Acumulación alcista sistemática
- Score ligeramente positivo (+1 a +4) → Ligero sesgo alcista
- Score neutro (0) → Sin sesgo claro
- Score negativo → Distribución o cobertura bajista

LIMITACIONES:
El Net Score no pondera por prima — una señal de $5M pesa igual que una de $100K. En próximas versiones se ponderará por prima total para dar más peso a las señales de mayor tamaño.

MÁS ÚTIL CON HISTORIAL:
Un Net Score de +7 en una semana es más significativo que un +7 puntual — si aparece repetido en varios días, hay acumulación sistemática.`
    },

    "high-signal": {
        title: "Señal HIGH — Alta Convicción",
        short: "Score ≥7. Combina prima grande, Vol/OI alto, IV elevada y strike OTM en rango óptimo.",
        long: `Las señales HIGH son las más relevantes del scanner. Requieren cumplir simultáneamente varios criterios estrictos.

CRITERIOS PARA HIGH (Score ≥7):
✓ Prima típicamente >$500K
✓ Vol/OI ratio >2x (posición completamente nueva)
✓ IV elevada (pagan caro = tienen convicción)
✓ Strike en sweet spot OTM (5-25%)
✓ Vencimiento táctico (14-60 días)

POR QUÉ SON RELEVANTES:
Para que una señal alcance score 7+ tiene que cumplir casi todos los criterios simultáneamente. Eso filtra casi todo el ruido retail y deja solo operaciones de tamaño y convicción.

CÓMO USARLAS:
1. Anota el ticker y el strike cuando aparece la señal
2. Revisa la tesis fundamental del activo
3. Compara con tu análisis técnico (¿confirma o contradice?)
4. Si la misma señal aparece 2-3 días seguidos → señal de acumulación

IMPORTANTE:
Una señal HIGH no garantiza movimiento. Es información, no señal de trading automático. Siempre combina con análisis propio.`
    },

    "otm-strike": {
        title: "Strike OTM — Out of the Money",
        short: "Strike fuera del precio actual. Call OTM = strike > precio. Put OTM = strike < precio.",
        long: `Un strike OTM (Out of The Money) es aquel que está fuera del precio actual del subyacente.

CALL OTM:
Strike > Precio actual
Ejemplo: NVDA a $220, Call $250 = OTM +13.6%
Para ganar dinero, NVDA debe superar $250 antes del vencimiento.

PUT OTM:
Strike < Precio actual
Ejemplo: NVDA a $220, Put $180 = OTM -18.2%
Para ganar dinero, NVDA debe caer por debajo de $180 antes del vencimiento.

POR QUÉ EL SWEET SPOT ES 5-25% OTM:
- <5% OTM (near the money): puede ser cobertura rutinaria, mucho ruido
- 5-25% OTM: requiere movimiento significativo = convicción real
- >25% OTM: especulación pura tipo "lotto ticket", baja probabilidad

SEÑAL DE ACUMULACIÓN:
Compras repetidas de calls 10-20% OTM con vencimiento a 30-60 días = alguien espera movimiento fuerte y tiene información o convicción alta.`
    },

    "implied-volatility": {
        title: "IV — Implied Volatility (Volatilidad Implícita)",
        short: "La volatilidad que el mercado está descontando en el precio de la opción. IV alta = opciones caras.",
        long: `La Volatilidad Implícita (IV) es la expectativa del mercado sobre cuánto se moverá el subyacente hasta el vencimiento.

CÓMO FUNCIONA:
El precio de una opción se deriva de varios factores. La IV es el único que no se observa directamente — se calcula a partir del precio de mercado de la opción.

INTERPRETACIÓN:
- IV baja (20-30%): mercado tranquilo, opciones baratas
- IV media (30-60%): actividad normal
- IV alta (60-100%): incertidumbre alta, opciones caras
- IV muy alta (>100%): evento inminente (earnings, merger)

POR QUÉ IMPORTA PARA EL FLOW:
Si alguien compra opciones con IV alta, está pagando una prima elevada. Eso significa que tienen alta convicción — no esperan a que la IV baje para entrar.

IV alta en una señal de compra = señal más fuerte, porque el coste de equivocarse es mayor.

IV RANK:
Compara la IV actual con el rango histórico del último año. IV Rank 80% = la IV está en el percentil 80 de los últimos 12 meses — inusualmente cara.`
    },
    // ── ALGORITMO RSU ─────────────────────────────────────────────────────────

    "rsu-algoritmo": {
        title: "RSU Algoritmo — Detector de Fondos",
        short: "Sistema multi-factor que detecta condiciones de fondo de mercado. Score 0-100.",
        long: `El RSU Algoritmo analiza 6 factores simultáneamente para determinar si el mercado está creando un fondo comprable.

LOS 6 FACTORES:

1. DIVERGENCIA ALCISTA (15pts)
Precio marcando mínimos pero RSI no los confirma. Señal clásica de agotamiento vendedor.

2. FOLLOW THROUGH DAY (35pts)
Concepto IBD. Día de rally en volumen alto tras una corrección. Históricamente marca el inicio de nuevas tendencias alcistas. El más importante del algoritmo.

3. RSI OVERSOLD (15pts)
RSI mínimo en ventana de 10 días. < 25 = extremo, máxima puntuación.

4. VIX SPIKE (20pts)
Pico de volatilidad. El miedo extremo históricamente = oportunidad. VIX > 35 = máxima puntuación.

5. McCLELLAN OSCILLATOR (20pts)
Amplitud del mercado. Valores extremadamente negativos = mayoría de acciones sobrevendidas = suelo potencial.

6. VOLUMEN (10pts)
Confirmación con volumen elevado. Sin volumen, no hay convicción.

INTERPRETACIÓN:
- > 70 + volumen → VERDE → Fondo probable. Entrada gradual.
- 50-70 → ÁMBAR → Condiciones desarrollándose. Preparar lista.
- < 30 → ROJO → Sin condiciones. Preservar capital.`
    },

    "ftd": {
        title: "Follow Through Day (FTD)",
        short: "Día de rally en alto volumen que confirma el inicio de una nueva tendencia alcista.",
        long: `El Follow Through Day es el concepto más importante de la metodología IBD (Investor's Business Daily) de William O'Neil.

DEFINICIÓN:
Un día en que un índice principal (SPX, Nasdaq) sube ≥1.7% en volumen mayor al día anterior, ocurriendo entre el día 4 y 10 de un intento de rally desde un mínimo.

POR QUÉ FUNCIONA:
Tras una corrección, el mercado necesita confirmar que hay demanda institucional real. Los grandes fondos no pueden disimular sus compras — dejan huella en el volumen. El FTD es esa huella.

ESTADÍSTICAS HISTÓRICAS:
- Todo gran mercado alcista desde 1900 comenzó con un FTD.
- ~75% de los FTDs llevan a mercados alcistas sostenidos.
- ~25% fallan (mercado vuelve a mínimos tras el FTD).

ADVERTENCIAS:
- FTD bajo la EMA21 → posible trampa alcista
- FTD en volumen solo moderado → menos convicción
- Múltiples FTDs fallidos seguidos → mercado muy débil

Sin FTD, no hay confirmación de fondo. Con FTD, empieza la acción.`
    },

    // ── CANSLIM ───────────────────────────────────────────────────────────────

    "canslim": {
        title: "CAN SLIM — Metodología IBD",
        short: "Sistema de selección de acciones de William O'Neil basado en 7 criterios fundamentales y técnicos.",
        long: `CAN SLIM es la metodología desarrollada por William O'Neil, fundador de Investor's Business Daily. Estudió los 600 mejores valores del mercado americano desde 1953 para identificar sus características comunes ANTES de grandes movimientos.

C — Current Earnings: EPS trimestral +25% o más vs año anterior.
A — Annual Earnings: Crecimiento anual consistente últimos 3-5 años.
N — New: Nuevo producto, servicio, management o máximo de 52 semanas.
S — Supply & Demand: Float bajo + volumen en ruptura = demanda institucional.
L — Leader: RS Rating > 80. Comprar líderes, no rezagados.
I — Institutional Sponsorship: Fondos de calidad acumulando.
M — Market Direction: Solo comprar en mercado alcista confirmado.

RS RATING:
Compara el rendimiento de una acción vs el universo de acciones en los últimos 12 meses. 99 = mejor rendimiento. O'Neil decía "nunca compres una acción con RS < 80".

EPS RATING:
Calidad y consistencia del crecimiento de beneficios vs el universo. Combina crecimiento trimestral y anual.

La metodología completa está en el libro "How to Make Money in Stocks" de William O'Neil.`
    },

    "trend-template": {
        title: "Trend Template — Minervini",
        short: "7 condiciones técnicas que definen una acción en etapa 2 alcista según Mark Minervini.",
        long: `El Trend Template es el filtro técnico de Mark Minervini (US Investing Champion 1997) para identificar acciones en Etapa 2 — la única etapa donde hay que comprar.

LAS 7 CONDICIONES:
1. Precio > MA150 Y MA200
2. MA150 > MA200
3. MA200 en tendencia alcista (subiendo al menos 1 mes)
4. MA50 > MA150 Y MA200
5. Precio > MA50
6. Precio ≥ 25% sobre mínimo de 52 semanas
7. Precio dentro del 25% del máximo de 52 semanas

ETAPAS DE MERCADO (Stan Weinstein):
- Etapa 1: Base/acumulación → lateral
- Etapa 2: Avance → AQUÍ SE COMPRA
- Etapa 3: Distribución → lateral en máximos → SALIR
- Etapa 4: Declive → bajista → NUNCA COMPRAR

Una acción que cumple las 7 condiciones está en Etapa 2 confirmada.
5-6 condiciones → probable Etapa 2.
< 4 condiciones → no cumple, no actuar.

Minervini ganó el US Investing Championship con +155% en 1997 usando este sistema.`
    },

    "rs-rating": {
        title: "RS Rating — Relative Strength",
        short: "Compara el rendimiento de la acción vs el universo completo. 99 = top 1%.",
        long: `El RS Rating de IBD mide el rendimiento relativo de una acción frente al universo completo de acciones americanas en los últimos 12 meses (con mayor peso en los últimos 3 meses).

CÁLCULO:
Se ordena el rendimiento de todas las acciones y se asigna un percentil del 1 al 99.
- RS 99 → Top 1% del mercado
- RS 80 → Mejor que el 80% de las acciones
- RS 50 → Rendimiento promedio del mercado

REGLA DE O'NEIL:
"Nunca compres una acción con RS Rating inferior a 80."

RS LÍNEA:
La línea de RS (precio relativo vs SPX) es igual de importante que el RS Rating. Lo que buscas:
▸ RS línea marcando nuevos máximos ANTES o CON la ruptura del precio → señal muy alcista.
▸ RS línea divergiendo negativamente mientras el precio sube → señal de debilidad.

LAS MEJORES ACCIONES tienen RS > 90 y la línea de RS marcando máximos históricos justo antes de la gran ruptura.`
    },

    // ── SPXL ──────────────────────────────────────────────────────────────────

    "spxl": {
        title: "SPXL — Direxion Daily S&P 500 Bull 3X",
        short: "ETF apalancado 3x del S&P 500. Triplica las ganancias Y las pérdidas diarias.",
        long: `SPXL es un ETF de Direxion que replica el 3x del rendimiento DIARIO del S&P 500.

CÓMO FUNCIONA:
Si el S&P 500 sube +1% en un día, SPXL sube ~+3%.
Si el S&P 500 baja -1% en un día, SPXL baja ~-3%.

DECAY POR VOLATILIDAD (el riesgo principal):
El apalancamiento se aplica DIARIAMENTE, no acumulativamente. En mercados laterales con alta volatilidad, SPXL pierde valor aunque el índice no se mueva. Se llama "volatility decay" o "beta slippage".

Ejemplo: SPX baja -10% y luego sube +11.1% → SPX breakeven. SPXL baja -30% y sube +33.3% → SPXL pierde ~6%.

POR QUÉ LA ESTRATEGIA DCA EN 6 FASES:
Comprar SPXL de golpe es muy arriesgado. La estrategia RSU escala posiciones en caídas progresivas, reduciendo el coste medio y aprovechando el rebote. Al comprar en pánico y vender en recuperación, el decay trabaja A FAVOR.

HORIZONTE TEMPORAL:
SPXL NO es para mantener indefinidamente. Es una herramienta táctica para ciclos de corrección-recuperación bien definidos.`
    },

    "spxl-phases": {
        title: "Fases DCA — Estrategia SPXL",
        short: "6 niveles de entrada escalonados según la caída desde máximos de SPXL.",
        long: `La estrategia RSU divide el capital disponible en 6 tramos que se despliegan progresivamente según SPXL cae desde su máximo histórico.

LÓGICA:
No intentamos adivinar el mínimo. Compramos a medida que cae, reduciendo el coste medio. Si el mercado continúa cayendo, tenemos capital reservado para niveles más bajos.

LAS 6 FASES:
- Fase 1: -15% desde máximo → 20% del capital
- Fase 2: -24% desde máximo → 15% del capital
- Fase 3: -29% desde máximo → 20% del capital
- Fase 4: -36% desde máximo → 20% del capital
- Fase 5: -43% desde máximo → 15% del capital
- Fase 6: -49% desde máximo → 10% del capital

RESERVA: 10% del capital nunca se invierte → liquidez de emergencia.

ESCENARIOS DE SALIDA (A, B, C):
- Escenario A (≤3 fases): Entrada en caída moderada. Salida rápida en +20%.
- Escenario B (4-5 fases): Caída seria. Venta parcial en +10%, runner con trailing.
- Escenario C (6 fases): Capitulación total. Salida escalonada en 3 tramos.

La disciplina de seguir el plan sin improvisaciones es la clave del sistema.`
    },

    // ── RESEARCH ──────────────────────────────────────────────────────────────

    "rsu-score": {
        title: "RSU Score — Valoración Integral",
        short: "Score 0-100 que combina crecimiento, rentabilidad, consenso y potencial de precio objetivo.",
        long: `El RSU Score es un sistema de valoración propio que combina 5 dimensiones para dar una puntuación global de 0 a 100 a cualquier acción.

LOS 5 COMPONENTES (20 puntos cada uno):

1. CRECIMIENTO DE INGRESOS (20pts)
> 25% → 20pts | > 15% → 15pts | > 5% → 10pts | < 5% → 0pts

2. ROE — Return on Equity (20pts)
> 25% → 20pts | > 15% → 15pts | > 8% → 10pts | < 8% → 0pts

3. MARGEN NETO (20pts)
> 20% → 20pts | > 10% → 15pts | > 2% → 10pts | < 2% → 0pts

4. CONSENSO ANALISTAS (20pts)
> 75% alcistas → 20pts | > 60% → 15pts | > 40% → 10pts | < 40% → 0pts

5. POTENCIAL PRECIO OBJETIVO (20pts)
Upside > 25% → 20pts | > 15% → 15pts | > 5% → 10pts | < 5% → 0pts

INTERPRETACIÓN:
- 80-100 → COMPRA FUERTE → Todos los factores alineados
- 65-79 → COMPRA → Mayoría de factores positivos
- 50-64 → NEUTRAL → Mix de señales
- 35-49 → PRECAUCIÓN → Debilidades importantes
- 0-34 → EVITAR → Fundamentales débiles

Es una herramienta de filtrado, no una recomendación de inversión.`
    },

    // ── RS/RW ─────────────────────────────────────────────────────────────────

    "rsrw": {
        title: "RS/RW Scanner — Relative Strength/Weakness",
        short: "Identifica las acciones con mayor fortaleza y debilidad relativa vs el mercado.",
        long: `El RS/RW Scanner identifica qué acciones están liderando (RS) y cuáles están rezagadas (RW) respecto al mercado en múltiples marcos temporales.

METODOLOGÍA:
Comparamos el rendimiento de cada acción vs el SPX en 3 períodos:
- 21 días (~1 mes)
- 63 días (~3 meses)
- 126 días (~6 meses)

Cada período tiene un peso distinto. El resultado es un percentil del 1 al 99.

POR QUÉ IMPORTA:
Las acciones con RS más alto tienden a seguir superando al mercado en el corto-medio plazo. Es el momentum del mercado. Las acciones con RW más bajo tienden a seguir cayendo.

RS LINE vs RS RATING:
- RS Rating: número estático comparando vs universo
- RS Line: línea dinámica que muestra la evolución relativa día a día

SEÑALES CLAVE:
▸ RS Line en nuevo máximo antes que el precio → acción líder, entrada de alta probabilidad
▸ RS Line cayendo mientras precio sube → divergencia bajista, evitar
▸ Clusters de RS alto en un sector → rotación sectorial en marcha

EMA SMOOTHING:
Aplicamos media móvil exponencial para eliminar el ruido de corto plazo y ver la tendencia real de la fortaleza relativa.`
    },

    // ── GENERAL ───────────────────────────────────────────────────────────────

    "market-cap": {
        title: "Market Cap — Capitalización bursátil",
        short: "Precio de la acción × número de acciones en circulación. Tamaño total de la empresa en bolsa.",
        long: `La capitalización bursátil es el valor total de mercado de una empresa.

FÓRMULA: Precio × Acciones en circulación

CATEGORÍAS:
- Mega Cap: > $200B (Apple, Microsoft, NVDA)
- Large Cap: $10B - $200B
- Mid Cap: $2B - $10B
- Small Cap: $300M - $2B
- Micro Cap: < $300M

POR QUÉ IMPORTA PARA EL TRADING:
Las Small y Mid Caps tienen mayor potencial de crecimiento pero también mayor riesgo y menor liquidez. Las Mega Caps son más estables pero difícilmente multiplican.

Para estrategias de crecimiento tipo CAN SLIM, O'Neil recomendaba acciones entre $500M y $10B de market cap — suficientemente grandes para que los institucionales puedan entrar, suficientemente pequeñas para que haya recorrido.`
    },

    "pe-ratio": {
        title: "P/E Ratio — Price to Earnings",
        short: "Precio dividido entre beneficio por acción. Cuánto pagas por cada euro de beneficio.",
        long: `El P/E Ratio (Price-to-Earnings) es el múltiplo de valoración más utilizado. Indica cuánto está dispuesto a pagar el mercado por cada unidad de beneficio.

TIPOS:
- Trailing P/E: usa beneficios de los últimos 12 meses (real)
- Forward P/E: usa beneficios estimados próximos 12 meses (estimado)

INTERPRETACIÓN BÁSICA:
- P/E bajo → acción "barata" vs beneficios → posible valor
- P/E alto → acción "cara" vs beneficios → el mercado espera crecimiento

PERO OJO — EL CONTEXTO LO ES TODO:
Un P/E de 50x puede ser barato para una empresa creciendo al 80% anual.
Un P/E de 10x puede ser caro para una empresa en declive.

PEG RATIO = P/E ÷ Tasa de crecimiento
Si PEG < 1 → acción potencialmente barata respecto a su crecimiento.
Si PEG > 2 → valoración exigente.

Para acciones de crecimiento tipo CAN SLIM, el P/E absoluto importa menos que el crecimiento. Una acción con P/E 40x creciendo al 50% es más interesante que una con P/E 10x sin crecimiento.`
    },
};

// ── ENGINE ────────────────────────────────────────────────────────────────────

export const Tooltip = {

    init() {
        this._injectStyles();
        this._createModal();
        this._bindAll();
    },

    _injectStyles() {
        if (document.getElementById('tooltip-styles')) return;
        const style = document.createElement('style');
        style.id = 'tooltip-styles';
        style.textContent = `
            .tt-trigger {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: rgba(0,217,255,0.1);
                border: 1px solid rgba(0,217,255,0.3);
                color: var(--color-secondary);
                font-size: 10px;
                cursor: pointer;
                font-style: normal;
                font-family: var(--font-mono);
                vertical-align: middle;
                margin-left: 6px;
                transition: all 0.2s;
                user-select: none;
                flex-shrink: 0;
            }
            .tt-trigger:hover {
                background: rgba(0,217,255,0.2);
                border-color: var(--color-secondary);
                transform: scale(1.1);
            }

            /* Tooltip flotante pequeño */
            .tt-popup {
                position: fixed;
                z-index: 9000;
                background: var(--color-surface);
                border: 1px solid var(--color-secondary);
                border-radius: var(--radius);
                padding: 8px 12px;
                font-size: 11px;
                color: var(--color-muted);
                max-width: 260px;
                line-height: 1.5;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.15s;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            }
            .tt-popup.visible { opacity: 1; }
            .tt-popup strong { color: var(--color-secondary); display: block; margin-bottom: 3px; font-size: 12px; }

            /* Modal detallado */
            .tt-overlay {
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.75);
                z-index: 9998;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1.5rem;
                opacity: 0;
                transition: opacity 0.2s;
                pointer-events: none;
            }
            .tt-overlay.visible {
                opacity: 1;
                pointer-events: all;
            }
            .tt-modal {
                background: var(--color-surface);
                border: 1px solid var(--color-secondary);
                border-radius: var(--radius-lg, 10px);
                padding: 1.5rem;
                max-width: 580px;
                width: 100%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 0 40px rgba(0,217,255,0.15);
                transform: scale(0.95);
                transition: transform 0.2s;
            }
            .tt-overlay.visible .tt-modal { transform: scale(1); }
            .tt-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 1rem;
                padding-bottom: 0.75rem;
                border-bottom: 1px solid var(--color-border);
            }
            .tt-modal-title {
                color: var(--color-secondary);
                font-size: 15px;
                letter-spacing: 0.08em;
                font-family: var(--font-mono);
            }
            .tt-modal-close {
                background: none;
                border: 1px solid var(--color-border);
                color: var(--color-muted);
                width: 28px;
                height: 28px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                transition: all 0.2s;
            }
            .tt-modal-close:hover {
                border-color: var(--color-accent);
                color: var(--color-accent);
            }
            .tt-modal-body {
                color: var(--color-muted);
                font-size: 13px;
                line-height: 1.8;
                white-space: pre-line;
                font-family: var(--font-mono);
            }
            .tt-modal-body b, .tt-modal-body strong {
                color: var(--color-accent);
            }
        `;
        document.head.appendChild(style);
    },

    _createModal() {
        if (document.getElementById('tt-overlay')) return;
        const overlay = document.createElement('div');
        overlay.id        = 'tt-overlay';
        overlay.className = 'tt-overlay';
        overlay.innerHTML = '<div class="tt-modal">'
            + '<div class="tt-modal-header">'
            + '<div class="tt-modal-title" id="tt-modal-title"></div>'
            + '<button class="tt-modal-close" id="tt-modal-close">✕</button>'
            + '</div>'
            + '<div class="tt-modal-body" id="tt-modal-body"></div>'
            + '</div>';
        document.body.appendChild(overlay);

        document.getElementById('tt-modal-close').addEventListener('click', () => this.closeModal());
        overlay.addEventListener('click', e => { if (e.target === overlay) this.closeModal(); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') this.closeModal(); });

        // Popup flotante
        const popup = document.createElement('div');
        popup.id        = 'tt-popup';
        popup.className = 'tt-popup';
        document.body.appendChild(popup);
    },

    _bindAll() {
        document.addEventListener('mouseover', e => {
            const trigger = e.target.closest('.tt-trigger');
            if (!trigger) return;
            const key  = trigger.getAttribute('data-tooltip');
            const data = TOOLTIPS[key];
            if (!data) return;
            this._showPopup(trigger, data);
        });

        document.addEventListener('mouseout', e => {
            if (!e.target.closest('.tt-trigger')) return;
            this._hidePopup();
        });

        document.addEventListener('click', e => {
            const trigger = e.target.closest('.tt-trigger');
            if (!trigger) return;
            const key  = trigger.getAttribute('data-tooltip');
            const data = TOOLTIPS[key];
            if (!data) return;
            this._hidePopup();
            this.openModal(data);
        });
    },

    _showPopup(trigger, data) {
        const popup = document.getElementById('tt-popup');
        if (!popup) return;
        popup.innerHTML = '<strong>' + data.title + '</strong>' + data.short;
        const rect = trigger.getBoundingClientRect();
        let top  = rect.bottom + 8;
        let left = rect.left;
        if (left + 260 > window.innerWidth) left = window.innerWidth - 270;
        if (top + 80 > window.innerHeight) top = rect.top - 88;
        popup.style.top  = top + 'px';
        popup.style.left = left + 'px';
        popup.classList.add('visible');
    },

    _hidePopup() {
        const popup = document.getElementById('tt-popup');
        if (popup) popup.classList.remove('visible');
    },

    openModal(data) {
        const overlay = document.getElementById('tt-overlay');
        const title   = document.getElementById('tt-modal-title');
        const body    = document.getElementById('tt-modal-body');
        if (!overlay || !title || !body) return;
        title.textContent = data.title;
        body.innerHTML    = data.long.replace(/\n/g, '<br>');
        overlay.classList.add('visible');
        document.body.style.overflow = 'hidden';
    },

    closeModal() {
        const overlay = document.getElementById('tt-overlay');
        if (overlay) overlay.classList.remove('visible');
        document.body.style.overflow = '';
    },
};

// Función helper para crear el trigger HTML
export function tt(key) {
    return '<span class="tt-trigger" data-tooltip="' + key + '" title="¿Qué es esto?">?</span>';
}