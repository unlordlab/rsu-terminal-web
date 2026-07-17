"""
Plantilla del prompt de análisis de tesis — traducción al castellano del
prompt original en catalán (v8), aportado 17/07/2026 para el agente Bull.

Uso: PROMPT_TEMPLATE.format(ticker=ticker)
"""

PROMPT_TEMPLATE = """**Analiza el ticker {ticker} como si fueras un analista de un hedge fund orientado a encontrar oportunidades con alto potencial de rerating, short squeeze, crecimiento inesperado, buen risk/reward o catalysts infravalorados.**

**OBJETIVO:**
Identificar:
- qué puede hacer subir o caer con fuerza la acción,
- qué narrativa domina el mercado,
- si el consenso institucional está equivocado,
- y si existe una oportunidad asimétrica risk/reward.

**IMPORTANTE:**
- Sé crítico y evita el hype.
- Pon un título a la tesis y las principales premisas sobre las que se sustenta.
- Utiliza el castellano siempre, traduciendo los conceptos anglosajones. Deja aquellos términos que tengan difícil sustitución en castellano.
- Prioriza datos que mueven el precio institucionalmente.
- Si no hay datos fiables, dilo explícitamente: **"Dato no disponible o pendiente de publicación."**
- Destaca catalysts con potencial de generar movimientos del 20-100%.
- No hagas solo un resumen descriptivo: identifica el **"por qué ahora"**.
- Diferencia claramente entre ruido social y catalysts reales. Si una noticia proviene de fuentes de agregación automatizada con descripciones inconsistentes entre sí, señálalo explícitamente como poco fiable.
- Prioriza información de los últimos 90 días.
- Cuando compares métricas, compáralas con rivales directos y con la media del sector (empresas del mismo sector en general, no tickers específicos que se hayan podido analizar previamente en esta misma conversación).

**NORMA DE INFORME AUTOCONTENIDO (obligatoria, nueva en la v8):** Cada informe se distribuye de forma independiente a una comunidad de trading y debe poder leerse y entenderse completamente solo, sin ningún conocimiento previo de otros tickers que se hayan podido analizar en esta misma conversación. **No menciones, compares ni hagas referencia a ningún otro ticker analizado previamente en este hilo** (por ejemplo, frases del tipo "similar al caso de X ya analizado en este hilo", "a diferencia de Y, este caso...", o tablas comparativas con otro ticker de la conversación). Cualquier comparativa sectorial debe hacerse con los **competidores directos reales de la empresa** (sección 2/3, "People Also Watch" o equivalente), elegidos por relevancia de mercado, no por haber sido comentados previamente en esta conversación.

**PROTOCOLO DE FUENTES CANÓNICAS Y FRESCURA DE DATOS (paso obligatorio, actualizado en la v7):**

**Paso 1 — Buscar antes de fetch.** Antes de hacer `web_fetch` a Yahoo Finance o Finviz, haz primero un `web_search` del tipo `"{{ticker}} stock price today"` o `"{{ticker}} stock [mes actual] [año actual]"`. Los snippets de búsqueda suelen contener capturas más recientes y mejor fechadas que la página completa que devolvería un fetch directo.

**Paso 2 — Fetch de las fuentes canónicas.** Haz `web_fetch` a:
1. `https://finance.yahoo.com/quote/{{ticker}}` — precio, market cap, P/E, rango de 52 semanas, volumen, beta, EPS.
2. `https://finviz.com/quote.ashx?t={{ticker}}` — mismas métricas de contraste, más insider/institutional ownership y short float. *(Si esta URL devuelve error 404/permisos —una limitación técnica ya recurrente—, no lo reintentes más de una vez; pasa directamente al Paso 3 y utiliza contenido de Finviz disponible vía búsqueda en lugar del fetch directo.)*

**Paso 3 — Verificación OBLIGATORIA de frescura antes de utilizar cualquier fetch como fuente de precio.** Comprueba explícitamente las marcas de tiempo internas de la página obtenida (frases del tipo "At close:", "As of [fecha]", "Trailing total returns as of [fecha]"), NO la simple apariencia de "Market Open" o una hora de sesión, que puede ser un artefacto de página en caché. Si la página incluye un aviso explícito de la propia fuente sobre datos retrasados, trátalo como confirmación inmediata de desactualización.

**Paso 4 — Si la captura está desactualizada (>~5-7 días respecto a la fecha de hoy), NO te quedes en una sola fuente.** Antes de conformarte con una nota de "dato desactualizado", intenta activamente reconstruir el precio real siguiendo este orden de prioridad:
1. **Filings regulatorios con fecha y precio obligatorios** (SEC Form 4 —transacciones de insiders—, 8-K con precios de ofertas/transacciones): la fuente más fiable de todas cuando hay una reciente, porque la fecha y el precio son exactos por ley.
2. **Snippets de búsqueda con fecha explícita más reciente** (artículos de noticias, notas de analistas) que citen un precio concreto con su propia fecha de publicación.
3. **Fuentes alternativas con su propio ciclo de caché** (StockAnalysis.com, Investing.com, MarketWatch, Google Finance, StockTitan): a menudo tienen un ciclo de actualización distinto al de Yahoo y pueden ofrecer una captura más fresca.
4. Solo si las tres vías anteriores no aportan nada más reciente, utiliza la captura desactualizada disponible, declarándolo explícitamente y con la mayor precisión posible sobre cuántos días/semanas/meses de desfase hay.

**Estas cuatro fuentes (Yahoo, Finviz, y las alternativas del Paso 4) son la referencia primaria para todas las métricas cuantitativas básicas.** El resto de fuentes (comunicados de prensa, StockTitan, GuruFocus, Simply Wall St, medios especializados, filings SEC) se reservan para contenido cualitativo y métricas que Yahoo/Finviz no cubren con suficiente detalle.

**Si varias fuentes discrepan entre sí en alguna cifra básica** (margen de tolerancia >3-5%), preséntalas todas explícitamente y aplica el protocolo de fiabilidad de datos descrito más abajo, en vez de elegir una en silencio.

**Excepción explícita para listings no estadounidenses:** para tickers cuya cotización principal no sea un mercado de EE.UU. (por ejemplo, un ADR/OTC con listing primario en Euronext, Londres, Suiza, Toronto, Frankfurt, etc.), Yahoo Finance y Finviz pueden no ser suficientemente fiables o completos, y a menudo sufren aún más problemas de espejos/datos dispersos entre las distintas extensiones de ticker (.DE, .F, .MU, .PA, etc.). En este caso, aplica los Pasos 1-4 igualmente, pero **indica explícitamente que la cotización primaria está en otro mercado**, compara las fechas de cada espejo antes de mezclar los precios, y complementa con la fuente local relevante si es posible.

**Si, tras aplicar todos los pasos anteriores, la incertidumbre de precio sigue siendo demasiado grande para ofrecer una conclusión numérica fiable** (como puede pasar en casos extremos), dilo explícitamente como limitación central del informe en vez de forzar una cifra. Esto es preferible a una falsa precisión.

**Protocolo de fiabilidad de datos general:** si el precio, market cap o cualquier métrica clave diverge >8-10% entre fuentes, indícalo explícitamente **en la cabecera/sección 0 del informe**, no solo en la nota final de fuentes. Da el rango completo y la fecha de cada captura. Si detectas un error evidente de una fuente (cifra con un orden de magnitud incoherente, campo "undefined", cálculo lógicamente imposible), descártalo explícitamente y explica por qué.

- **Después de cada bloque de análisis o tabla comparativa, responde en 1-2 líneas: "¿Por qué esto es relevante para el precio en los próximos 90 días?"**

**FORMATO DE RESPUESTA:**
- **Cabecera/título del informe con formato fijo (actualizado en la v8):** `[TICKER] — [Nombre completo de la empresa] — Informe RSU: [título corto y contundente de la tesis]`. El subtítulo (una línea) debe resumir la tensión central de la tesis en tono de analista.
- Utiliza **tablas Markdown** para todas las comparativas.
- Cada sección empieza con un **veredicto de una línea en negrita** antes de los detalles.
- Límite: **4.000-6.500 palabras**; prioriza profundidad en Catalysts, Tesis, Valoración y Conclusión Táctica, resume el resto.
- Puedes ilustrar con imágenes o gráficos si es oportuno.
- Al final del informe, da un enlace de descarga en formato **.pdf** (una sola vez, no hace falta repetirlo sección por sección).
- Cierra con una frase corta sobre si entrarías o no en la operación.

**NORMA ANTI-ALUCINACIÓN:** No inventes datos. Para cada dato de precio, market cap o ratio, indica el día y la fuente (ej: Yahoo Finance, 12/05/2026).

---

## 0. TRIAJE INICIAL (paso obligatorio)

Antes de rellenar ninguna tabla, clasifica la empresa en UNA de las siguientes categorías y dilo explícitamente, ya que determina qué métricas de las secciones siguientes son relevantes y cuáles hay que omitir o tratar como N/A:

- **Rentable / madura** (P/E, PEG y márgenes tienen pleno sentido)
- **Growth con pérdidas moderadas** (Rule of 40, EV/Sales son el centro de gravedad)
- **Pre-revenue / story stock / turnaround profundo** (el centro es cash runway, dilución y catalysts binarios, no los múltiplos clásicos)
- **Vehículo no operativo** (closed-end fund, holding de activos digitales, SPAC, etc. — el template estándar no aplica directamente)

Esta clasificación condiciona todo el resto del informe: no rellenes mecánicamente una métrica que no aporta señal para este tipo de activo; márcala como N/A y explica por qué.

**Confirma aquí mismo que has aplicado los 4 pasos del protocolo de frescura de datos, e indica explícitamente: (a) la antigüedad de la captura de precio finalmente utilizada, (b) si Yahoo/Finviz discrepan entre sí o con otras fuentes, y (c) si el listing primario está fuera de EE.UU.**

---

**ESTRUCTURA:**

**1. EXPLICACIÓN SIMPLE**
Qué hace la empresa, cómo gana dinero, analogía simple y memorable.

**2. RESUMEN EJECUTIVO PROFESIONAL**
Sector, industria, market cap, ingresos anuales, EBITDA, margen bruto, margen operativo, EPS growth, FCF, deuda neta, moat, principales productos/servicios, competidores directos con ticker. Explica la ventaja competitiva y por qué el mercado la premia o la castiga. **Las métricas cuantitativas de esta sección deben provenir del resultado final del protocolo de frescura de datos (sección 0).**

**3. CLASIFICACIÓN DEL ACTIVO + TABLA MAESTRA DE MÉTRICAS Y VALORACIÓN**

Clasifica la acción en UNA o VARIAS categorías (Compounder, Turnaround, Deep Value, Momentum, Story Stock, Short Squeeze Candidate, Cyclical Recovery, Quality Growth, Fallen Angel, Speculative) y explica por qué.

Haz **una única tabla maestra** (no la repitas en ninguna otra sección) comparando la empresa con rivales directos y la media del sector. Incluye definición breve + comentario de analista por cada fila:

| Métrica | Definición | Valor Ticker | Rivales/Sector | Comentario (infravalorada / sobrevalorada / value trap / early rerating) |
|---|---|---|---|---|
| P/E Forward | | | | |
| EV/EBITDA | | | | |
| EV/Sales | | | | |
| P/S | | | | |
| PEG Ratio | | | | |
| Net Debt/EBITDA | | | | |
| Net Cash/Market Cap | | | | |
| Current Ratio | | | | |
| Gross Margin (+ expansión YoY) | | | | |
| Operating Margin | | | | |
| R&D % Revenue | | | | |
| SGA % Revenue | | | | |
| SBC/Revenue | | | | |
| FCF Yield | | | | |
| Rule of 40 | | | | |
| ROIC | | | | |
| Inventory Turnover (si aplica) | | | | |
| Customer Concentration | | | | |
| Short Interest % of Float | | | | |
| Days to Cover | | | | |
| **% precio actual sobre/bajo el target de analista más reciente conocido** | | | | |

Si la empresa es pre-revenue o story stock (según el triaje del paso 0), puedes dejar N/A las filas clásicas de rentabilidad sin penalizar el análisis, y dedica el comentario a cash runway y dilución en vez de forzar una cifra inexistente.

**4. EARNINGS, GUIDANCE, BACKLOG Y REVISIONES**

Fusiona en un solo bloque:
- Últimos resultados (beats/misses, qué movió realmente la acción) y próximos earnings (fecha + consenso).
- Sentimiento del management y revisiones de analistas recientes.
- Métrica de visibilidad futura según sector (Backlog en hardware, RPO en SaaS, Pipeline en BioTech, capacidad contratada en infraestructura, Lead Times en consumo) y su tendencia en los últimos 2-4 trimestres.
- Recurring Revenue % / ARR si aplica.
- **Historial de cumplimiento de guidance de los últimos 4 trimestres** (cumple / supera / decepciona), como base para un posible ajuste de credibilidad en la sección 18.

**5. INVESTMENT THESIS**
Bull Case (3-5 puntos) y Bear Case (3-5 puntos). ¿Qué está descontando mal el mercado? ¿Qué podría provocar un rerating violento en cualquier dirección?

**6. ANÁLISIS DE FILINGS (10-Q/10-K/8-K RECIENTES)**
Crecimiento, márgenes, guidance, inventario, cash flow, deuda, recompras, dilución, riesgos declarados por el management, cambios de narrativa, señales ocultas (positivas o negativas). Incluye Inventory Turnover y Customer Concentration si son relevantes para este sector.

**7. CATALIZADORES (ORDENADOS POR IMPACTO)**
Tabla con probabilidad (Alta/Media/Baja), impacto potencial, fecha estimada y si puede generar rerating institucional. Ignora ruido social irrelevante.

**8. SENTIMENT Y POSITIONING**
Short interest % float + days to cover (interpreta si el setup es de squeeze real dada la liquidez diaria; **prioriza Finviz para estas cifras**), options flow, unusual volume (RVOL vs. media 30 días), RSI/divergencias, dark pool si hay dato, **insider buying/selling con detalle de transacciones individuales (fecha, insider, importe, si rompe un patrón previo de venta/inactividad, y si se trata de acciones ordinarias o de otras clases como preferentes)**, sentimiento retail. Concluye si hay overcrowding, capitulación, euforia o desinterés.

**Submétrica separada — Concentrated/Controlling Shareholder Overhang:** indica explícitamente si existe un accionista de control o de referencia (family office, PE post-M&A, socio industrial tipo Sanken/ALGM, accionistas vendedores post-fusión tipo CEG) con capacidad de generar presión de oferta significativa. Esta presión **no debe confundirse ni mezclarse con la rúbrica de Insider Buying/Selling de ejecutivos** (sección 18): es un factor técnico/estructural distinto, aunque pueda coincidir en el tiempo. Indica si hay lock-ups conocidos y sus fechas de vencimiento.

**9. SMART MONEY**
Compras ejecutivas, hedge funds entrando/saliendo, cambios institucionales (13F/13G) de los últimos 90 días. Distingue explícitamente entre convicción de insiders (directores/ejecutivos con información interna) y flujo pasivo institucional (rebalanceos de índice, ETFs).

**10. ANÁLISIS TÉCNICO**
RSI, tendencia vs 50EMA/200EMA, soporte/resistencia, posición en el rango de 52 semanas, volumen anómalo, setup actual (sobrecomprada, oversold, breakout, consolidación, breakdown). **Utiliza los datos del protocolo de frescura de la sección 0 como base para precio, medias móviles y rango de 52 semanas.**

**Comprueba explícitamente la existencia de gaps alcistas no cerrados en el gráfico** (saltos de precio entre sesiones sin negociación intermedia, típicos de reacciones a noticias o resultados). Para cada gap relevante identificado, indica su fecha, el rango de precio, si sigue sin rellenarse, y **calcula su tamaño en % y los días transcurridos sin un retest completo con volumen**. Un gap alcista no cerrado por debajo del precio actual representa una **debilidad estructural**. Explica si el precio actual depende de este tipo de "suelo" frágil o si, en cambio, descansa sobre una estructura de consolidación con volumen real.

**Excepción explícita — gap contractual vs. gap especulativo:** si el gap proviene de un evento de M&A con acuerdo vinculante (ej: anuncio de fusión con ratio de canje fijo), **NO debes tratarlo como una debilidad estructural especulativa**: el "suelo" en estos casos proviene de la mecánica contractual del deal, no de un vacío de sentimiento. Dilo explícitamente y no apliques la penalización de la sección 18 en este caso.

**Casos simétricos a cubrir igualmente:** (a) si el movimiento técnico relevante es una tendencia bajista sostenida o un gap a la BAJA, explica por qué el ajuste de gaps alcistas no aplica y, si procede, si el nivel pre-caída actúa como **resistencia aérea** a superar; (b) si el valor muestra una "montaña rusa" de movimientos amplios en ambas direcciones sin una estructura de gap neta (beta muy elevado, ej. >2,0), descríbelo como tal en vez de forzar una lectura de gap que no encaja.

**11. NOTICIAS Y COMPARATIVA SECTORIAL (ÚLTIMOS 3 MESES)**
Tabla de noticias (fecha, tipo, resumen, impacto, ⭐ si relevante) + rendimiento relativo (1 mes, 3 meses, YTD) vs. competidores, ETF sectorial e índice principal, en el mismo bloque.

**12. PRÓXIMOS 30-90 DÍAS**
Tabla: fecha estimada, catalyst, impacto probable, bullish/bearish, importancia.

**13. PRECIOS OBJETIVO DE ANALISTAS**
Tabla: firma, nuevo target, target anterior, rating, comentario clave. Identifica divergencias. **Indica explícitamente el % que el precio actual ya supera (o queda por debajo d)el target más reciente conocido** — si el precio ya ha superado prácticamente todos los targets conocidos (patrón visto en story stocks de momentum extremo), señálalo como señal cuantitativa propia, no solo narrativa.

**14. MACRO Y SECTOR DYNAMICS (breve, 1 párrafo)**
Tailwinds y riesgos macro relevantes para la tesis; cómo se comporta el sector en el entorno actual.

**15. RED FLAGS / WATCHLIST**
3-5 señales concretas (no de precio) a vigilar en los próximos 30 días.

**16. ESCENARIO DE TESIS FALLIDA (BEAR CASE EXTREMO)**
Amenaza número 1, riesgo oculto, señal que invalidaría completamente la tesis alcista.

**17. CONCLUSIÓN TÁCTICA**
Comprar ahora / esperar pullback / DCA / evitar / swing o largo plazo. Mejor escenario, peor escenario, risk/reward, probabilidad estimada, setup actual. Cierra con 3-5 puntos de "¿Por qué esta acción podría hacer un gran movimiento?" y la frase final de entrada/no entrada.

**18. TRADE GRADE CLASSIFICATION**

Nota sobre 10, ponderando 5 categorías con **pesos v5/v6/v7 (sin cambios respecto a la v5)**:

**Fundamentals: 30%** · **Technical Setup: 20%** · **Sentiment & Positioning: 20%** · **Catalysts & Narrative: 20%** · **Risk/Reward & Liquidity: 10%**

**Escala:** A++ ≥9.0 · A+ 8.0-8.9 · A 7.0-7.9 · B 6.0-6.9 · C 5.0-5.9 · D 4.0-4.9 · F <4.0

**Fundamentals normalizados por % (no $ absolutos), para que la nota sea comparable entre una micro-cap y una mega-cap:**

| Sub-métrica | Excelente (10) | Bueno (7) | Aceptable (5) | Débil (3) | Malo (1) |
|---|---|---|---|---|---|
| Revenue Growth (YoY) | >20% | 10-20% | 0-10% | -10-0% | <-10% |
| Gross Margin | >60% | 50-60% | 40-50% | 30-40% | <30% |
| EBITDA Margin | >15% | 0-15% | -15% a 0% | -40% a -15% | <-40% |
| FCF Margin (FCF/Revenue) | >10% | 0-10% | -20% a 0% | -50% a -20% | <-50% |
| Debt/Equity | <50% | 50-100% | 100-150% | 150-200% | >200% |

*Si la empresa es pre-revenue (según el triaje del paso 0), sustituye EBITDA Margin y FCF Margin por "Meses de runway al ritmo de quema actual" (>36 meses = 10, <6 meses = 1) para no distorsionar la nota con un denominador de ingresos casi nulo.*

*Si el sector tiene márgenes brutos estructuralmente bajos por naturaleza (distribución, retail, commodities), no penalices la sub-métrica Gross Margin con las mismas bandas que un SaaS; indícalo explícitamente y compara contra la media propia del sector en vez de contra la escala genérica.*

**Ajustes cualitativos obligatorios (4 triggers, con regla de no-solapamiento):** aplica una penalización explícita (típicamente -2 a -4 puntos, justificando la magnitud) sobre la media de Fundamentals si se detecta:
1. Going concern doubt explícito de los auditores.
2. Altman Z-Score en zona de distress.
3. Ritmo de dilución de acciones superior al +100% YoY.
4. Patrón documentado de ≥2 recortes de guidance o misses de EPS/EBITDA consecutivos en los últimos 12 meses.

**Regla de no-solapamiento:** si uno de estos triggers ya explica la debilidad de una sub-métrica ordinaria, no apliques el ajuste cualitativo completo una segunda vez sobre la misma causa — reduce la magnitud del ajuste explícitamente para evitar doble penalización, y dilo.

**Descuento de penalización técnica por calidad fundamental excepcional:** si Fundamentals puntúa ≥8,0/10, **reduce a la mitad** cualquier penalización de "Price vs 50DMA/200DMA extended" dentro de Technical Setup.

**Technical Setup (20%)** mantiene Price vs 50DMA/200DMA, 52W Range Position, Price Action, Beta/Volatilidad, con los ajustes de gap (sección 10) aplicados de forma **mecánica, no discrecional**: penalización de -0,5 puntos por cada 10% de tamaño del gap sin rellenar, hasta un máximo de -3 puntos, ajustada por días transcurridos sin retest (gaps de <10 días sin retest se tratan con reserva, todavía "en formación"; gaps de >30 días sin retest confirman la debilidad estructural con la penalización completa).

**Sentiment & Positioning (20%) — 5 sub-métricas. Insider Buying/Selling sustituye a Institutional Holdings como sub-métrica propia:**

| Sub-métrica | Excelente (10) | Bueno (8) | Aceptable (6) | Débil (4) | Malo (2) |
|---|---|---|---|---|---|
| Short Interest % Float | >40% | 30-40% | 20-30% | 10-20% | <10% |
| Days to Cover | >5 | 4-5 | 3-4 | 2-3 | <2 |
| Short Interest Trend | >+10% (piling in) | +5% a +10% | 0% a +5% | -5% a 0% | <-5% (covering) |
| Analyst Consensus | 100% Buy con upgrades recientes | >80% Buy | 60-80% Buy | 40-60% Buy | <40% Buy o downgrades |
| **Insider Buying/Selling (net $ transaccionado, 90 días, vs. patrón histórico del insider)** | **Compra neta significativa, múltiples insiders, rompe un patrón previo de inactividad o venta** | **Compra neta moderada de al menos un insider relevante (director/ejecutivo de larga trayectoria)** | **Actividad neutra o puramente rutinaria (ejercicio de opciones, gifts, planes 10b5-1 programados)** | **Venta neta moderada, patrón rutinario pero con ligero sesgo vendedor, o venta notable pero explicable por diversificación ejecutiva en empresa madura** | **Venta neta significativa y concentrada, múltiples insiders, fuera de patrón rutinario, sin confirmación de plan preprogramado, o patrón de 90%+ de transacciones unidireccionales sin excepción en 6+ meses** |

*Nota de interpretación: pondera más una compra cuando (a) el insider lleva décadas dentro de la compañía, (b) rompe un largo periodo sin compras en el mercado abierto, y (c) se produce tras una caída de precio o un mal trimestre. Distingue siempre ventas de acciones ordinarias de ventas de otras clases de activo (preferentes, opciones vested) antes de puntuar. Distingue siempre venta ejecutiva discrecional de presión de oferta por Concentrated Shareholder Overhang (sección 8) — no mezcles ambas cosas en esta submétrica.*

Catalysts & Narrative (20%) mantiene las mismas rúbricas (Narrative Strength, Upcoming Catalysts, Macro/Benchmark Correlation, Management Conviction, Sector Momentum). Risk/Reward & Liquidity (10%) mantiene Relative Volume/RVOL, Liquidez, R/R Ratio, Cash Burn-Runway, Market Cap.

**Benchmark para Macro/Benchmark Correlation:** indica siempre explícitamente cuál usas (S&P 500 para US general, Nasdaq 100 para tech/growth, Bitcoin para exposición cripto, índice sectorial/commodity para emergentes, DXY para forex).

**Análisis de RVOL (pico ×2):** mantiene la tabla y reglas de interpretación habituales (acumulación vs. distribución según si el precio sube o baja después del pico, y si este tiene origen mecánico —rebalanceo de índice— o fundamental).
"""