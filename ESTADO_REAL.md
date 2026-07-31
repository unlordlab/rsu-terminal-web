# ESTADO REAL — hallazgos pendientes de RSU Terminal

**Generado el 30/07/2026.** Consolida los 379 hallazgos de los 16
`AUDITORIA_<MODULO>.md` (que viven en el Escritorio, fuera del repo y sin
control de versiones) y marca el estado de cada uno **verificado contra el
código actual**, no copiado del documento original.

## Por qué este documento existe

Las auditorías son de julio de 2026 y **no saben nada de las ~15 sesiones de
trabajo posteriores**. Consultarlas directamente lleva a trabajar sobre cosas
ya resueltas, y —peor— a dar por buenas otras que fallan en silencio. Cuatro
casos reales, todos del 29/07/2026:

- Las **medianas sectoriales** figuraban como cerradas y llevaban 9 días sin
  llegar a Research: el job semanal escribía en un Gist y el backend leía otro.
  Salía en verde cada domingo.
- **"Retirar Alpha Vantage por uso marginal"** era falso por partida doble: ni
  era marginal (alimenta un gráfico visible) ni había que retirarlo, sino
  sustituirlo — su plan gratuito son 25 peticiones/día y el gráfico desaparecía
  a media mañana.
- El **apalancamiento de ANET** en el Piotroski: la conclusión correcta era la
  CONTRARIA a la reportada.
- De los 26 hallazgos de Research, varios ya estaban cerrados por sesiones
  anteriores.

Por eso cada línea lleva su estado y su evidencia. Un listado sin verificar
parecería completo y sería engañoso.

## Cobertura de esta versión — leer antes de usarlo

- **389 hallazgos**: 379 extraídos de los 16 documentos de auditoría, más 10
  encontrados después con el sistema ya en producción (RSU Algoritmo #14–#18,
  Newsfeed/briefing #27–#31).
- **64 son críticos (🔴)**: todos revisados en la primera pasada.
  33 cerrados · 11 abiertos ·
  1 ya no aplican ·
  19 pendientes de verificar.
- **Segunda pasada (30/07), parcial**: verificado además el tier ALTO/MEDIO de
  Research, RS/RW y Scanner. Los demás módulos siguen sin revisar en ese tier.
- **RS/RW cerrado del todo (30/07, `34a659f`)**: los 22 hallazgos del módulo
  revisados uno a uno, seis arreglados en esa sesión. Quedan 3 abiertos (#6
  festivos, #7 universo, #20 histórico de percentil) y 4 sin comprobar del
  tier UX/NUEVO.
- **RSU Algoritmo cerrado del todo (30-31/07)**: tercer módulo con el tier
  completo verificado. Aparecieron **5 hallazgos nuevos** que no estaban en la
  auditoría (#14–#18), tres de ellos encadenados y con efecto real sobre las
  señales: el backtest a 10 años pasa de 51 a 16 señales, con la ventaja a 60
  días de +1,51pp a +4,30pp. Del tier que quedaba sin comprobar, **4 de 7 ya
  estaban cerrados y 2 no aplicaban** — solo 2 eran trabajo real.
- Los **287 restantes** están extraídos y clasificados por
  severidad, pero marcados ❓ SIN VERIFICAR: aparecen aquí para no perderlos de
  vista, **no como lista de trabajo fiable**. Verificarlos es la segunda pasada.

**Fuentes que faltan por integrar** (tercera pasada): `ROADMAP_ESTRATEGICO.md`,
`TODO_RSU_TERMINAL.md`, `tareas terminal.md`, `DATOS_IRREPRODUCIBLES_PLAN.md`,
`PRECIOS_Y_APIS.md`, `ESTRATEGIA_CRECIMIENTO_REDES.md`, y sobre todo la memoria
del proyecto — 2.597 líneas que son la única fuente que sabe qué se cerró en
las últimas sesiones. Hay pendientes que SOLO viven ahí: el fallback `^ADV`/
`^DEC` de Market caído en silencio, el walk-forward del Algoritmo, la
reponderación 4.5 del RSU Score, la longitud del briefing diario.

| Marca | Significado |
|-------|-------------|
| ✅ | CERRADO — verificado en el código actual |
| ❌ | ABIERTO — verificado, sigue ahí |
| ⬜ | YA NO APLICA — el código al que se refería no existe |
| ❓ | SIN VERIFICAR — extraído del documento, no comprobado |

---

## Lo que hay que atacar, por orden

De los críticos verificados como abiertos:

1. **BTC_STRATUM #1** — El MVRV Z-Score no usa Realized Cap — y la alerta le dice al usuario que sí
   `btc_stratum_service.py:189 documenta que el Realized Cap es una aproximación por EMA365 del market cap. El proxy sigue ahí; queda comprobar si la UI lo declara`
1. **CARTERA #A2** — `auto_adjust=True` (default de yfinance) distorsiona el HOY % en días ex-dividendo
   `verificado 30/07: cero apariciones de auto_adjust en cartera_service.py, sigue el default de yfinance`
1. **CARTERA #A3** — El fallback FMP fabrica un "+0.00%" y lo cachea
   `verificado 30/07: cartera_service.py:207 sigue usando /stable/quote-short, que no devuelve la variación real`
1. **CARTERA #B1** — `clean_numeric` destroza importes con formato US de miles
   `PROBADO 30/07 ejecutando la función: clean_numeric('1,234.56') → 1.23456. Un importe en formato US con separador de miles se divide por ~1000 en silencio. Con formato europeo ('1.234,56' → 1234.56) sí funciona`
1. **INFRAESTRUCTURA_Y_VALORACION_GLOBAL #3** — Los endpoints de administración no tienen rate limiting: la clave maestra se puede probar a ciegas sin límite
   `main.py:90 include_router(auth.router) SIN dependencies=rl: los /admin/* no tienen rate limiting`
1. **OPTIONS_FLOW #3** — `POST /options/save` permite a cualquier usuario inyectar datos falsos en tu histórico
   `options.py:80 POST /save sigue con solo verify_token: cualquier usuario autenticado puede inyectar en el histórico`
1. **OPTIONS_FLOW #4** — `POST /options/scan-now` abierto a cualquier usuario, sin lock de concurrencia
   `options.py:56 POST /scan-now sin lock de concurrencia (ya lo dispara el cron, pero sigue abierto)`
1. **OPTIONS_FLOW #5** — `GET /options/flow` (legacy) ejecuta el escaneo completo en vivo por petición
   `options.py:72 GET /flow legacy sigue llamando a get_options_flow() en vivo por petición`
1. **PAGINAS_CONTENIDO #1** — No existe política de privacidad — y eso es un requisito legal, no una buena práctica
   `bloque legal Fase 1, nunca empezado. Bloquea la monetización`
1. **PAGINAS_CONTENIDO #2** — El JWT se guarda en `localStorage` cuando marcas "recordarme" — persistente e indefinido
   `mismo bloque legal`
1. **SPXL #4** — Ni `/live` ni `/backtest` tienen caché: cada visita descarga 17 años y ejecuta el motor completo
   `0 usos de cache.get en spxl_service.py: cada visita descarga 17 años y corre el motor`

Los dos de `PAGINAS_CONTENIDO` son el **bloque legal de la Fase 1**, que sigue
sin empezar y es lo único de toda la lista que no es deuda técnica sino
exposición: con ~100 usuarios reales, no hay política de privacidad.

---

## Btc Stratum  (16 hallazgos — ❌1 · ✅1 · ❓14)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ❌ | 1 | 🔴 | El MVRV Z-Score no usa Realized Cap — y la alerta le dice al usuario que sí | btc_stratum_service.py:189 documenta que el Realized Cap es una aproximación por EMA365 del market cap. El proxy sigue ahí; queda comprobar si la UI lo declara |
| ❓ | 2 | 🔴 | El AHR999 implementado no es el AHR999 | *sin comprobar* |
| ❓ | 3 | 🔴 | El defecto estructural: el score de cuatro factores es en realidad un factor contado tres veces | *sin comprobar* |
| ✅ | 4 | 🔴 | La MA200W probablemente no son 200 semanas — y nada lo comprueba | min_periods 200→1400 real + backtest truncado al periodo maduro (2807b34) |
| ❓ | 5 | 🔴 | El backtest usa un Puell distinto del que usa el dashboard | *sin comprobar* |
| ❓ | 6 | 🟠 | La alerta de "OPORTUNIDAD MÁXIMA" tiene la lógica invertida | *sin comprobar* |
| ❓ | 7 | 🟠 | `sampled=true` rompe el cálculo del Puell real | *sin comprobar* |
| ❓ | 8 | 🟠 | `liquidity_score` es prácticamente una constante | *sin comprobar* |
| ❓ | 9 | 🟠 | El fallback de macro fabrica datos con apariencia de reales | *sin comprobar* |
| ❓ | 10 | 🟠 | La fecha del próximo halving está fijada a mano | *sin comprobar* |
| ❓ | 11 | 🟠 | `_get_timestamp()` con CET fijo — decimocuarta aparición | *sin comprobar* |
| ❓ | 12 | 🟡 | El score se satura en los extremos, y eso invalida el backtest largo | *sin comprobar* |
| ❓ | 13 | 🟡 | Los stress tests publican probabilidades numéricas inventadas | *sin comprobar* |
| ❓ | 14 | 🟡 | El backtest compra una sola vez por ciclo | *sin comprobar* |
| ❓ | 15 | 🟡 | `ath = close.max()` sobre el histórico disponible | *sin comprobar* |
| ❓ | 16 | 🟡 | `_get_zone` es la salida más prescriptiva de toda la terminal | *sin comprobar* |

## Canslim  (24 hallazgos — ✅5 · ❓19)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | El RS Rating es un número inventado en el uso normal del módulo — y de él dependen el criterio "S" y el 35% del Composite | fallback 50+perf/2 eliminado y RS real desde el Gist de RS/RW |
| ✅ | 2 | 🔴 | La letra M está fijada a `True` — y es la letra que O'Neil consideraba la más importante | verificado 30/07: canslim_service.py:428 usa market_can_buy real, no True |
| ✅ | 3 | 🔴 | El botón "ESCANEAR S&P 500 (503)" dispara 503 descargas bajo demanda, sin caché ni lock, y está diseñado para pulsarse | scan movido a GitHub Actions + Gist; el frontend ya no dispara 503 descargas |
| ✅ | 4 | 🔴 | El universo está embebido aquí (503) y diverge del universo compartido (525) — la Fase 2.1 se dejó este fichero | universo unificado en shared/sp500_universe.py |
| ✅ | 5 | 🔴 | `inst_pct` puede leer 0,75 como "0,75%" en vez de "75%" — y el criterio I falla siempre | canslim_service.py:331 raw*100 desde major_holders, contrastado en el código contra AAPL 66.5% / JPM 76.1% / XOM 68.4% / TXN 94.7% |
| ❓ | 6 | 🟠 | El scan y el análisis individual usan definiciones distintas de "tendencia" y escalas distintas de "score" | *sin comprobar* |
| ❓ | 7 | 🟠 | `perf_12m` del scan no son 12 meses para todos los tickers — y contamina el percentil de todos | *sin comprobar* |
| ❓ | 8 | 🟠 | La etiqueta "A — Ventas **anuales** >25%" usa el crecimiento **trimestral | *sin comprobar* |
| ❓ | 9 | 🟠 | `traceback.format_exc()` se devuelve al usuario en la respuesta de error | *sin comprobar* |
| ❓ | 10 | 🟠 | El estado del mercado se calcula aquí por tercera vez, con criterios distintos | *sin comprobar* |
| ❓ | 11 | 🟠 | `_get_timestamp()` naive — décima aparición del bug de timezone | *sin comprobar* |
| ❓ | 12 | 🟡 | `universe_perfs` de depuración expuesto en la respuesta pública | *sin comprobar* |
| ❓ | 13 | 🟡 | Los fallos del scan son invisibles | *sin comprobar* |
| ❓ | 14 | 🟡 | `for future in futures` no usa `as_completed` | *sin comprobar* |
| ❓ | 15 | 🟡 | `spy_hist['Close'].iloc[-2]` sin validar longitud | *sin comprobar* |
| ❓ | 16 | 🟡 | Escapado en el frontend | *sin comprobar* |
| ❓ | 17 | 🟡 | Sin deep-link `?ticker=` | *sin comprobar* |
| ❓ | 18 | 🔵 | Conectar la M al widget que ya existe | *sin comprobar* |
| ❓ | 19 | 🔵 | Badge 💼/⭐ de Cartera y Watchlist | *sin comprobar* |
| ❓ | 20 | 🔵 | Enlace cruzado con Research y RS/RW | *sin comprobar* |
| ❓ | 21 | 🔵 | Explicar por qué falla cada letra | *sin comprobar* |
| ❓ | 22 | 🟢 | Histórico de candidatos | *sin comprobar* |
| ❓ | 23 | 🟢 | Detección de bases y pivot points | *sin comprobar* |
| ❓ | 24 | 🟢 | Cruce con Insider y Options Flow | *sin comprobar* |

## Cartera  (42 hallazgos — ❌3 · ✅1 · ❓38)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ❓ | A1 | 🔴 | El "cierre anterior" puede ser el de hace DOS días (frontera de sesión no validada) | *sin comprobar* |
| ❌ | A2 | 🔴 | `auto_adjust=True` (default de yfinance) distorsiona el HOY % en días ex-dividendo | verificado 30/07: cero apariciones de auto_adjust en cartera_service.py, sigue el default de yfinance |
| ❌ | A3 | 🔴 | El fallback FMP fabrica un "+0.00%" y lo cachea | verificado 30/07: cartera_service.py:207 sigue usando /stable/quote-short, que no devuelve la variación real |
| ❌ | B1 | 🔴 | `clean_numeric` destroza importes con formato US de miles | PROBADO 30/07 ejecutando la función: clean_numeric('1,234.56') → 1.23456. Un importe en formato US con separador de miles se divide por ~1000 en silencio. Con formato europeo ('1.234,56' → 1234.56) sí funciona |
| ❓ | B2 | 🔴 | Las comisiones de operaciones CERRADAS se restan al P&L de las ABIERTAS | *sin comprobar* |
| ✅ | B3 | 🔴 | "P&L Total Acum." es una suma de porcentajes — no es un P&L | avg_pnl ponderado por capital invertido |
| ❓ | B4 | 🔴 | `simulate_tier_capital` procesa el cierre en la fecha de APERTURA | *sin comprobar* |
| ❓ | A4 | 🟠 | Cripto en cartera: precio congelado 16 horas al día | *sin comprobar* |
| ❓ | A5 | 🟠 | El P&L en $ puede divergir entre la carga inicial y los updates en vivo | *sin comprobar* |
| ❓ | A6 | 🟠 | Cadencia real del "en vivo": hasta ~2 minutos de retraso, más los 15 min de Yahoo | *sin comprobar* |
| ❓ | A7 | 🟠 | Las métricas de cabecera se quedan congeladas mientras las filas se actualizan | *sin comprobar* |
| ❓ | A8 | 🟠 | Reordenar o filtrar la tabla revierte los precios al snapshot inicial | *sin comprobar* |
| ❓ | B5 | 🟠 | El Google Sheet se lee 3+ veces por carga de página (y cada 60s con el WS activo) | *sin comprobar* |
| ❓ | B6 | 🟠 | El WebSocket de cartera queda vivo para siempre al salir de la página | *sin comprobar* |
| ❓ | B7 | 🟠 | Token JWT en la query string del WebSocket | *sin comprobar* |
| ❓ | B8 | 🟠 | Sparklines cruzados entre tickers que son prefijo de otros | *sin comprobar* |
| ❓ | B9 | 🟠 | `/notificaciones/check` accesible a cualquier usuario autenticado | *sin comprobar* |
| ❓ | B10 | 🟠 | Gating de tier incoherente (relevante para la monetización) | *sin comprobar* |
| ❓ | B11 | 🟠 | `last_update` con hora del contenedor (UTC) | *sin comprobar* |
| ❓ | B12 | 🟠 | Límite silencioso de 30 tickers en el WS | *sin comprobar* |
| ❓ | B13 | 🟡 | Fechas ambiguas DD/MM vs MM/DD — riesgo silencioso permanente | *sin comprobar* |
| ❓ | B14 | 🟡 | Curva "Evolución del Valor" con sesgo de superviviente | *sin comprobar* |
| ❓ | B15 | 🟡 | Línea de invertido del gráfico con fallback engañoso | *sin comprobar* |
| ❓ | B16 | 🟡 | Export CSV: comillas sin escapar y sin BOM | *sin comprobar* |
| ❓ | B17 | 🟡 | Colisión de clave en notificaciones Telegram | *sin comprobar* |
| ❓ | B18 | 🟡 | Barra de peso saturada | *sin comprobar* |
| ❓ | 19 | 🔵 | P&L del DÍA agregado de la cartera | *sin comprobar* |
| ❓ | 20 | 🔵 | Asignación objetivo vs real | *sin comprobar* |
| ❓ | 21 | 🔵 | Columna P&L $ visible en la tabla | *sin comprobar* |
| ❓ | 22 | 🔵 | Días en posición | *sin comprobar* |
| ❓ | 23 | 🔵 | Responsive | *sin comprobar* |
| ❓ | 1 | 🟢 | A1 + A2 (validación de sesión por fecha + `auto_adjust=False`) | *sin comprobar* |
| ❓ | 3 | 🟢 | B1 (clean_numeric) + B2 (comisiones) + B3 (suma de %) | *sin comprobar* |
| ❓ | 4 | 🟢 | A5–A8 | *sin comprobar* |
| ❓ | 5 | 🟢 | B5 + B6 + B7 | *sin comprobar* |
| ❓ | 6 | 🟢 | B4 (simulación por eventos) | *sin comprobar* |
| ❓ | 24 | 🟢 | Snapshot diario del equity en SQLite | *sin comprobar* |
| ❓ | 25 | 🟢 | Feed de trades en tiempo real vía Finnhub WS | *sin comprobar* |
| ❓ | 26 | 🟢 | Alertas de posición | *sin comprobar* |
| ❓ | 27 | 🟢 | Cruce con Options Flow | *sin comprobar* |
| ❓ | 2 | ⚪ | Honestidad en la UI: | *sin comprobar* |
| ❓ | A9 | ⚪ | Pre/Post market: decisión no comunicada | *sin comprobar* |

## Infraestructura Y Valoracion Global  (18 hallazgos — ❌1 · ✅2 · ❓14 · ⬜1)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ⬜ | 1 | 🔴 | `docker-compose.prod.yml` es una trampa cargada: borra 4 bases de datos y reabre el agujero de UFW | verificado 30/07: docker-compose.prod.yml ya no existe en el repo |
| ✅ | 2 | 🔴 | Cualquier usuario registrado puede vaciar toda la caché de la terminal | verificado 30/07: no queda ningún endpoint de purga de caché en backend/routers/ |
| ❌ | 3 | 🔴 | Los endpoints de administración no tienen rate limiting: la clave maestra se puede probar a ciegas sin límite | main.py:90 include_router(auth.router) SIN dependencies=rl: los /admin/* no tienen rate limiting |
| ✅ | 4 | 🔴 | `deploy.sh` no hace copia de seguridad antes de desplegar, y no existe ninguna copia automática | backup pre-deploy en deploy.sh (a4507ae) + backup_dbs.sh |
| ❓ | 5 | 🟠 | El rate limiting por usuario en realidad es por IP | *sin comprobar* |
| ❓ | 6 | 🟠 | El estado del rate limiting y de la caché no sobrevive a varios workers | *sin comprobar* |
| ❓ | 7 | 🟠 | Nueve tareas de fondo sin supervisión: si una muere, muere en silencio | *sin comprobar* |
| ❓ | 8 | 🟠 | El pool compartido de yfinance solo lo usan 2 de 12 módulos | *sin comprobar* |
| ❓ | 9 | 🟠 | La caché abre y cierra una conexión SQLite en cada operación | *sin comprobar* |
| ❓ | 10 | 🟠 | `verify_token` consulta la base de datos en cada petición (y `require_tier`, otra vez) | *sin comprobar* |
| ❓ | 11 | 🟠 | `.env.example` está obsoleto y **rompe el arranque** si se usa | *sin comprobar* |
| ❓ | 12 | 🟠 | La configuración de Nginx no está en el repositorio | *sin comprobar* |
| ❓ | 13 | 🟠 | El health check de `deploy.sh` no comprueba que la aplicación responda | *sin comprobar* |
| ❓ | 14 | 🟠 | Solo se reconstruye la imagen si cambia `requirements.txt` | *sin comprobar* |
| ❓ | 15 | 🟡 | El parche del proxy de yfinance no cubre `yf.download()` | *sin comprobar* |
| ❓ | 16 | 🟡 | Las tareas se cancelan pero no se esperan al apagar | *sin comprobar* |
| ❓ | 17 | 🟡 | Los cinco workflows de GitHub Actions no avisan si fallan | *sin comprobar* |
| ❓ | 18 | 🟡 | `sector_medians.yml` existe pero su Gist no está configurado | *sin comprobar* |

## Insider Flow  (23 hallazgos — ❓23)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ❓ | 1 | 🔴 | Cada ciclo de 20 min re-descarga los mismos ~100 filings ya procesados (~200 requests a la SEC, el 90% desperdiciadas) | *sin comprobar* |
| ❓ | 2 | 🔴 | Cluster Buying cuenta transacciones, no personas — y solo mira el top 15 | *sin comprobar* |
| ❓ | 3 | 🔴 | Las filas sin fecha de transacción son inmortales y siempre encabezan el feed | *sin comprobar* |
| ❓ | 4 | 🔴 | Primera visita con BD vacía = ingesta síncrona de ~200 requests con el usuario esperando (y sin lock) | *sin comprobar* |
| ❓ | 5 | 🟠 | Petición muerta a EDGAR en cada búsqueda de ticker | *sin comprobar* |
| ❓ | 6 | 🟠 | El filtro "persona real" descarta a los fundadores 10%-owner sin cargo | *sin comprobar* |
| ❓ | 7 | 🟠 | "COMPRAS RECIENTES" ordenadas por tamaño, no por fecha | *sin comprobar* |
| ❓ | 8 | 🟠 | Form 4/A (enmiendas) crean duplicados en vez de corregir | *sin comprobar* |
| ❓ | 9 | 🟠 | Los directores sin cargo de officer salen con CARGO "—" | *sin comprobar* |
| ❓ | 10 | 🟠 | El diagnóstico de ingesta expone errores internos a todos los usuarios | *sin comprobar* |
| ❓ | 11 | 🟠 | `_get_timestamp` con CET fijo (UTC+1) | *sin comprobar* |
| ❓ | 12 | 🟠 | La vista de ticker ignora el histórico local ya acumulado | *sin comprobar* |
| ❓ | 13 | 🟡 | Escape de contenido EDGAR en el frontend | *sin comprobar* |
| ❓ | 14 | 🟡 | Pide 20 entries a EDGAR, procesa 10 | *sin comprobar* |
| ❓ | 15 | 🟡 | `except Exception: pass` en el loop de ws.py | *sin comprobar* |
| ❓ | 16 | 🟡 | `insider_history.db` en la lista de BDs sin backup | *sin comprobar* |
| ❓ | 17 | 🔵 | Columna "% desde la compra" | *sin comprobar* |
| ❓ | 18 | 🔵 | Badge 💼/⭐ de Cartera y Watchlist | *sin comprobar* |
| ❓ | 19 | 🔵 | Deep-link `?ticker=` | *sin comprobar* |
| ❓ | 20 | 🔵 | Filtro por tipo/cargo | *sin comprobar* |
| ❓ | 21 | 🟢 | Alerta Telegram de cluster | *sin comprobar* |
| ❓ | 22 | 🟢 | Efectividad del insider | *sin comprobar* |
| ❓ | 23 | 🟢 | Cruce Insider × Options Flow | *sin comprobar* |

## Market  (33 hallazgos — ✅3 · ❓30)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ❓ | 1 | 🔴 | Net Liquidity sobreestimada ~$0,7–0,9T (TGA sin convertir de unidades) | *sin comprobar* |
| ✅ | 2 | 🔴 | El yield a 2 años (y por tanto la "curva invertida") es un número fabricado | quitada la síntesis Y3M+0.47; sin dato real devuelve None |
| ✅ | 3 | 🔴 | Todos los "Actualizado: HH:MM:SS" van 1 hora atrasados en verano | shared/time_utils.py con ZoneInfo Europe/Madrid en los 14 servicios |
| ❓ | 4 | 🔴 | Crypto Fear & Greed: el fallback inventa un "Neutral 50" y el frontend lo pinta como real | *sin comprobar* |
| ✅ | 5 | 🔴 | Reddit Pulse: fallback con datos 100% inventados servido con `ok: True` | _reddit_fallback devuelve ok:False; los 8 tickers inventados eliminados |
| ❓ | 6 | 🔴 | Crypto RS: el filtro `price <= 1.0` excluye large caps legítimas (¡incluida ADA, que está en tu propio top-6!) | *sin comprobar* |
| ❓ | 7 | 🟠 | Reddit solo escanea 1 subreddit de los 5 listados | *sin comprobar* |
| ❓ | 8 | 🟠 | WS en vivo roto para cripto y petróleo + pierde el prefijo "$" | *sin comprobar* |
| ❓ | 9 | 🟠 | VIX Term Structure: spread no estándar, spot no garantizado y colores contradictorios | *sin comprobar* |
| ❓ | 10 | 🟠 | `get_fear_greed()` no cachea nada | *sin comprobar* |
| ❓ | 11 | 🟠 | `get_fed_macro()` cachea 30 min aunque todo venga vacío | *sin comprobar* |
| ❓ | 12 | 🟠 | Race condition: la sparkline del Balance Fed puede no renderizarse en la primera carga | *sin comprobar* |
| ❓ | 13 | 🟠 | `loadVix()` inyecta Chart.js SIEMPRE | *sin comprobar* |
| ❓ | 14 | 🟠 | Fuga de memoria: los charts no se destruyen al navegar | *sin comprobar* |
| ❓ | 15 | 🟠 | Listener de Escape huérfano en el modal del briefing | *sin comprobar* |
| ❓ | 16 | 🟠 | Earnings: precios solo en las primeras 50 filas de 100 + timestamps inconsistentes + sin caché en el detalle | *sin comprobar* |
| ❓ | 17 | 🟠 | Fear & Greed fallback (estimado por VIX) fabrica historial | *sin comprobar* |
| ❓ | 18 | 🟡 | `_fred_csv` triplicado + WALCL/WTREGEN/RRPONTSYD descargados dos veces | *sin comprobar* |
| ❓ | 19 | 🟡 | Índices / Forex / Commodities siguen yendo ticker a ticker | *sin comprobar* |
| ❓ | 20 | 🟡 | Gist del briefing sin token de GitHub | *sin comprobar* |
| ❓ | 21 | 🟡 | Cache stampede | *sin comprobar* |
| ❓ | 22 | 🟡 | Correlación Net Liquidity ↔ SPX sobre niveles = correlación espuria | *sin comprobar* |
| ❓ | 23 | 🔵 | Auto-refresh: | *sin comprobar* |
| ❓ | 24 | 🔵 | Indicadores FRED (IPC/PCE): | *sin comprobar* |
| ❓ | 25 | 🔵 | Earnings sin resultados = buscador desaparece: | *sin comprobar* |
| ❓ | 26 | 🔵 | Responsive: | *sin comprobar* |
| ❓ | 27 | 🔵 | Reddit: | *sin comprobar* |
| ❓ | 28 | 🔵 | Sector Performance: | *sin comprobar* |
| ❓ | 29 | 🟢 | Semáforo macro agregado | *sin comprobar* |
| ❓ | 30 | 🟢 | Histórico del Fear & Greed: | *sin comprobar* |
| ❓ | 31 | 🟢 | Put/Call ratio (CBOE): | *sin comprobar* |
| ❓ | 32 | 🟢 | Ratio VIX/VIX3M explícito | *sin comprobar* |
| ❓ | 33 | 🟢 | Alertas de umbral | *sin comprobar* |

## Modulos 2026-07-19  (10 hallazgos — ❓10)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ❓ | 1 | ⚪ | [Metodológico, real] `rs_momentum` compara magnitudes de horizontes distintos | *sin comprobar* |
| ❓ | 2 | ⚪ | [Mantenimiento, importante] El universo S&P 500 está copiado a mano en TRES sitios | *sin comprobar* |
| ❓ | 3 | ⚪ | [Menor] Sesgo de supervivencia suave: | *sin comprobar* |
| ❓ | A1 | ⚪ | Research — los tres errores, en profundidad | *sin comprobar* |
| ❓ | A2 | ⚪ | RSU Score — la doble contabilidad del sentimiento, con ejemplo | *sin comprobar* |
| ❓ | A3 | ⚪ | Futuro — el track record público, aterrizado | *sin comprobar* |
| ❓ | B1 | ⚪ | RS/RW — el mejor construido de los cuatro | *sin comprobar* |
| ❓ | B2 | ⚪ | Scanner — bien diseñado, con pesos discutibles | *sin comprobar* |
| ❓ | B3 | ⚪ | CANSLIM — los bugs se arreglaron hoy; queda la crítica metodológica | *sin comprobar* |
| ❓ | B4 | ⚪ | SPXL — el motor ya está sano; el riesgo ahora es epistemológico | *sin comprobar* |

## Newsfeed  (31 hallazgos — ❌1 · ✅5 · ❓25)

Los #27–#31 no vienen de la auditoría: salieron al fallar el briefing diario en
producción dos días seguidos (30 y 31/07), cada día por una causa distinta. Se agrupan aquí porque `scripts/daily_briefing.py`
alimenta el modal "Resumen de Mercado Diario", aunque sea un script aparte.

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | XSS almacenado explotable a través de los feeds (especialmente Reddit) | esc()/safeUrl() + segunda pasada de _strip_html contra doble codificación |
| ❓ | 2 | 🔴 | Clasificador de impacto/sector/sentimiento roto por substring matching | *sin comprobar* |
| ✅ | 3 | 🔴 | Los timers del auto-refresh siguen corriendo para siempre tras salir de la página | cleanup() en el router SPA + export en newsfeed.js |
| ❓ | 4 | 🔴 | `/newsfeed/prices`: 10 llamadas yfinance en vivo por cada carga, sin caché y fuera del pool global | *sin comprobar* |
| ❓ | 5 | 🟠 | Feed de Reuters muerto (y probablemente otros) | *sin comprobar* |
| ❓ | 6 | 🟠 | No hay botón "ALL" para sectores — un filtro de sector no se puede deshacer | *sin comprobar* |
| ❓ | 7 | 🟠 | Los filtros solo filtran los 80 items ya descargados | *sin comprobar* |
| ❓ | 8 | 🟠 | Auto-refresh destruye la lista y el scroll cada 5 minutos | *sin comprobar* |
| ❓ | 9 | 🟠 | `mins_ago = 999` se muestra como una edad falsa de "16h" | *sin comprobar* |
| ❓ | 10 | 🟠 | Timestamps con hora del contenedor (UTC) — misma familia que el bug #3 de Market | *sin comprobar* |
| ❓ | 11 | 🟠 | Fallo total de fuentes = sin caché = martilleo de 16 requests por usuario | *sin comprobar* |
| ❓ | 12 | 🟠 | Precios del ticker superior pierden precisión en forex | *sin comprobar* |
| ❓ | 13 | 🟠 | Parámetro muerto en la API | *sin comprobar* |
| ❓ | 14 | 🟡 | La latencia del endpoint = la fuente más lenta (hasta 8s) | *sin comprobar* |
| ❓ | 15 | 🟡 | Dedup solo por título, no por URL | *sin comprobar* |
| ❓ | 16 | 🟡 | Sin retry/backoff en las fuentes | *sin comprobar* |
| ❓ | 17 | 🔵 | Tickers clicables en titulares: | *sin comprobar* |
| ❓ | 18 | 🔵 | Filtro por fuente: | *sin comprobar* |
| ❓ | 19 | 🔵 | Búsqueda por texto | *sin comprobar* |
| ❓ | 20 | 🔵 | Responsive: | *sin comprobar* |
| ❓ | 21 | 🔵 | Titulares en español: | *sin comprobar* |
| ❓ | 22 | 🟢 | Sentimiento/impacto con LLM para los HIGH: | *sin comprobar* |
| ❓ | 23 | 🟢 | Histórico de noticias HIGH en SQLite: | *sin comprobar* |
| ❓ | 24 | 🟢 | Alertas de noticias HIGH | *sin comprobar* |
| ❓ | 25 | 🟢 | Push por WebSocket en vez de polling: | *sin comprobar* |
| ❓ | 26 | 🟢 | Feed de la SEC (EDGAR current events RSS) | *sin comprobar* |
| ✅ | 27 | 🔴 | **El briefing diario no se genera los días de calendario cargado** — el prompt desbordaba el límite de 8.000 TPM de Groq y el script abortaba, dejando a los ~100 usuarios sin briefing | 31/07: el 30/07 falló con ~6578 tok contra un techo de 6450, por un día con BOE + BOJ + Advance GDP + Core PCE (15 eventos de impacto alto/medio, frente a 4-5 de un día normal). Medido: **3471 tok (53%) eran INSTRUCCIONES FIJAS** y solo 2703 datos — el prompt llevaba meses al borde. Ahora recorte progresivo en 4 niveles hasta que quepa, en vez de abortar; el nivel 0 ya ahorra 533 tok (historial 3000→1800 chars, titulares 8+8→5+5) |
| ❌ | 28 | 🟠 | Las instrucciones fijas del prompt son el 53% de su tamaño | verificado 31/07: `_ESTILO_V2` solo son 2296 tok, con las 9 reglas anti-alucinación en prosa larga y bloques duplicados (`PROHIBIDO SONAR A TEXTO GENERADO` y `CONVICCIÓN CALIBRADA` aparecen dos veces con listas casi idénticas). Comprimir a lista telegráfica ahorraría ~600 tok, pero cambia el output: exige comparar un briefing antes/después |
| ❓ | 29 | 🟡 | ¿Hay margen de TPM sin recortar nada? | *sin comprobar* — los 8.000 TPM son del tier gratuito de Groq. Antes de comprimir el prompt (#28) conviene mirar si otro modelo del mismo tier tiene más margen, o el coste del siguiente escalón |
| ✅ | 30 | 🔴 | **El contador de tokens subestimaba un 13%**, así que el recorte automático dejaba pasar prompts que Groq rechazaba | 31/07: el briefing volvió a fallar, ahora con 413 pese a pasar la comprobación interna. Medición exacta: el script estimó 5.744 tok y Groq pidió 8.401 con `max_tokens=1800`, o sea **6.601 reales**. 20.104 chars / 6.601 = **3,046 chars/token**, no los 3,5 configurados. Recalibrado a 2,9 (por debajo de lo medido a propósito: sobrestimar cuesta contexto, subestimar cuesta el briefing entero) |
| ✅ | 31 | 🟠 | Un 413 de Groq mataba el proceso en vez de reintentar con menos contexto | 31/07: cualquier estimación por caracteres se desvía del tokenizador real, así que la única fuente de verdad es la respuesta de la API. Ahora el 413 se distingue del resto de errores (`PromptDemasiadoGrande`) y baja un nivel de recorte; construir y llamar viven en el mismo bucle. Verificado con un Groq simulado más estricto que la estimación: falla en 'normal', reintenta en 'medio' y genera |

## Options Flow  (25 hallazgos — ❌3 · ✅2 · ❓20)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | La clasificación Buy/Sell — el cimiento de todo el módulo — es `vol/OI >= 0.3` | dirección por bid/ask (Lee-Ready) en vez de vol/OI |
| ✅ | 2 | 🔴 | La hora del escaneo diario es la hora del último deploy — aleatoria respecto al mercado | cron fijo en options_scan.yml; eliminado el loop en proceso |
| ❌ | 3 | 🔴 | `POST /options/save` permite a cualquier usuario inyectar datos falsos en tu histórico | options.py:80 POST /save sigue con solo verify_token: cualquier usuario autenticado puede inyectar en el histórico |
| ❌ | 4 | 🔴 | `POST /options/scan-now` abierto a cualquier usuario, sin lock de concurrencia | options.py:56 POST /scan-now sin lock de concurrencia (ya lo dispara el cron, pero sigue abierto) |
| ❌ | 5 | 🔴 | `GET /options/flow` (legacy) ejecuta el escaneo completo en vivo por petición | options.py:72 GET /flow legacy sigue llamando a get_options_flow() en vivo por petición |
| ❓ | 6 | 🟠 | El dedupe de guardado omite `type` — calls y puts al mismo strike colisionan | *sin comprobar* |
| ❓ | 7 | 🟠 | Escaneos parciales invisibles: el "sesgo del día" puede calcularse sobre media muestra | *sin comprobar* |
| ❓ | 8 | 🟠 | Las small caps de tu propia cartera nunca pasarán el filtro | *sin comprobar* |
| ❓ | 9 | 🟠 | El baseline relativo penaliza progresivamente a los tickers con historial | *sin comprobar* |
| ❓ | 10 | 🟠 | `near_earnings` solo marca vencimientos POSTERIORES a earnings | *sin comprobar* |
| ❓ | 11 | 🟠 | `scan_date` con fecha UTC del contenedor — el histórico puede desplazarse un día | *sin comprobar* |
| ❓ | 12 | 🟠 | `_calc_sentiment_momentum` compara contra "ayer natural", no contra el último scan | *sin comprobar* |
| ❓ | 13 | 🟠 | `flow-simple` lee el Google Sheet de Cartera en cada carga de página | *sin comprobar* |
| ❓ | 14 | 🟡 | La "prima" es `volumen_total_día × último_precio` — un proxy, no órdenes reales | *sin comprobar* |
| ❓ | 15 | 🟡 | `Large OI Increase/Decrease` opera sobre un subconjunto sesgado | *sin comprobar* |
| ❓ | 16 | 🟡 | `get_ticker_history_summary` agrupa por MES pero todo se llama "weekly" | *sin comprobar* |
| ❓ | 17 | 🟡 | La BD crece sin límite ni retención | *sin comprobar* |
| ❓ | 18 | 🟡 | WATCHLIST con posibles tickers erróneos del export de TradingView | *sin comprobar* |
| ❓ | 19 | 🔵 | Deep-link y estado en URL | *sin comprobar* |
| ❓ | 20 | 🔵 | Gráfico de NPS diario en la vista de ticker | *sin comprobar* |
| ❓ | 21 | 🔵 | Badge de flow en Research | *sin comprobar* |
| ❓ | 22 | 🔵 | Responsive | *sin comprobar* |
| ❓ | 23 | 🟢 | Alerta Telegram de flow en Cartera/Watchlist | *sin comprobar* |
| ❓ | 24 | 🟢 | Put/Call ratio agregado del día | *sin comprobar* |
| ❓ | 25 | 🟢 | Seguimiento de aciertos del flow | *sin comprobar* |

## Paginas Contenido  (25 hallazgos — ❌2 · ✅2 · ❓21)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ❌ | 1 | 🔴 | No existe política de privacidad — y eso es un requisito legal, no una buena práctica | bloque legal Fase 1, nunca empezado. Bloquea la monetización |
| ❌ | 2 | 🔴 | El JWT se guarda en `localStorage` cuando marcas "recordarme" — persistente e indefinido | mismo bloque legal |
| ✅ | 3 | 🔴 | Dos páginas anuncian "ENCRYPTION: AES-256" en un sitio sin HTTPS | textos de AES-256 retirados |
| ✅ | 4 | 🔴 | Academy anuncia horas de vídeo que no existen | referencias a horas de vídeo retiradas de Academy |
| ❓ | 5 | 🟠 | Academy carga ~1,3 MB de JavaScript de golpe | *sin comprobar* |
| ❓ | 6 | 🟠 | La barra de progreso de Academy está fijada a 0% — no hay seguimiento | *sin comprobar* |
| ❓ | 7 | 🟠 | El Dashboard dispara el endpoint más pesado de la terminal en cada carga | *sin comprobar* |
| ❓ | 8 | 🟠 | Citas del Dashboard: varias son apócrifas o parafraseadas, y una "diaria" que no es diaria | *sin comprobar* |
| ❓ | 9 | 🟠 | El Roadmap 2026 es una previsión estática de la que ya ha pasado medio año | *sin comprobar* |
| ❓ | 10 | 🟠 | Roadmap contiene previsiones concretas de mercado sin disclaimer visible | *sin comprobar* |
| ❓ | 11 | 🟠 | `equipo.js` marca a Elia y Laia como "EN SERVICIO" cuando no están conectadas | *sin comprobar* |
| ❓ | 12 | 🟡 | Fotos de personas reales en el repositorio que no aparecen en la web | *sin comprobar* |
| ❓ | 13 | 🟡 | El Dashboard inyecta un `<style>` nuevo en cada render | *sin comprobar* |
| ❓ | 14 | 🟡 | El disclaimer aceptado no tiene versión | *sin comprobar* |
| ❓ | 15 | 🟡 | La sección 06 del disclaimer prohíbe algo que la propia terminal hace | *sin comprobar* |
| ❓ | 16 | 🟡 | Academy: `[STATUS: ALL MODULES UNLOCKED // ACCESS: FULL]` | *sin comprobar* |
| ❓ | 17 | 🟡 | `equipo.js` y `roadmap.js` no escapan nada, pero todo su contenido es estático | *sin comprobar* |
| ❓ | 18 | 🔵 | Academy: buscador de lecciones | *sin comprobar* |
| ❓ | 19 | 🔵 | Enlazar Academy desde los módulos | *sin comprobar* |
| ❓ | 20 | 🔵 | Dashboard: continuidad | *sin comprobar* |
| ❓ | 21 | 🔵 | Equipo: enlazar cada agente con su trabajo | *sin comprobar* |
| ❓ | 22 | 🔵 | Manifiesto: es tu mejor pieza de marca | *sin comprobar* |
| ❓ | 23 | 🟢 | Certificado de finalización de Academy | *sin comprobar* |
| ❓ | 24 | 🟢 | Roadmap con registro de aciertos | *sin comprobar* |
| ❓ | 25 | 🟢 | Página pública de landing | *sin comprobar* |

## Research  (26 hallazgos — ❌1 · ✅17 · ❓8)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | Cada research en frío = ~20 descargas a Yahoo, con datos repetidos hasta 6 veces, fuera del pool global | _info_de() comparte .info (3→1) + caché de precio/volumen (841b977) |
| ✅ | 2 | 🔴 | Alpha Vantage: 25 peticiones/día quemadas en horas | sustituido por yfinance.earnings_dates (0f10243) |
| ✅ | 3 | 🔴 | Traducción con Groq repetida infinitamente para el mismo texto estático | traducción cacheada 30 días por contenido (841b977) |
| ✅ | 4 | 🔴 | XSS reflejado vía `?ticker=` + contenido externo sin escapar (mismo patrón que Newsfeed) | esc() + validación de ticker con regex en el backend |
| ✅ | 5 | 🟠 | Los fallos no se cachean → un ticker inválido dispara la avalancha completa cada vez | caché negativa de 120s para ok:False (841b977) |
| ✅ | 6 | 🟠 | El RSU Score puede dar "COMPRA FUERTE" con una sola categoría de cinco | MIN_CATEGORIAS_RSU_SCORE=3; por debajo no se publica score (42ae09e) |
| ✅ | 7 | 🟠 | `_get_next_earnings` puede mostrar la fecha equivocada | earnings ordenados por fecha y filtrados a futuro (ffe16bd) |
| ✅ | 8 | 🟠 | Dos "máximos de 52 semanas" distintos en la misma página | Niveles Técnicos usa el mismo fiftyTwoWeekHigh que la tarjeta (ffe16bd) |
| ✅ | 9 | 🟠 | `short_pct` sin la defensa de formato que ya aplicaste al dividend yield | guarda fracción/porcentaje en short_pct (ffe16bd) |
| ✅ | 10 | 🟠 | El pipeline de medianas sectoriales reales está muerto por configurar | shared/gist_ids.py: mismo ID para quien escribe y quien lee (0555f15) |
| ✅ | 11 | 🟠 | Umbrales de absorción incoherentes entre Research y Scanner | shared/absorption.py compartido con Scanner, mismo umbral 0.75 |
| ❌ | 12 | 🟠 | Latencia de research en frío: 10-20 segundos con un "Cargando..." plano | el paquete de rendimiento (841b977) quitó descargas duplicadas, pero un research en frío sigue en ~11s medidos y el 'Cargando...' sigue siendo plano, sin progreso |
| ✅ | 13 | 🟠 | Instancias de Chart.js nunca destruidas | cleanup() + destrucción antes de repintar en research.js (a1a0931) |
| ✅ | 14 | 🟠 | `timestamp` con hora del contenedor (UTC) | shared/time_utils.py |
| ✅ | 15 | 🟡 | La URL no refleja las búsquedas manuales | history.replaceState al buscar (a1a0931) |
| ✅ | 16 | 🟡 | Turnover y absorción no comparten la descarga | _get_daily_turnover deriva de _get_price_volume_data, con caché (841b977) |
| ✅ | 17 | 🟡 | `_resolve_coingecko_id`: el fallback `coins[0]` puede elegir el token equivocado | desempate por market_cap_rank; sin match exacto no resuelve (ffe16bd) |
| ✅ | 18 | 🟡 | Estacionalidad con `auto_adjust` implícito | auto_adjust=True explícito y razonado (ffe16bd) |
| ❓ | 19 | 🔵 | Badge "en Cartera" / "en Watchlist" | *sin comprobar* |
| ❓ | 20 | 🔵 | Métricas del scan nocturno gratis: | *sin comprobar* |
| ❓ | 21 | 🔵 | Botón "Generar tesis con Gael" | *sin comprobar* |
| ❓ | 22 | 🔵 | Modo comparación | *sin comprobar* |
| ❓ | 23 | 🔵 | Pre-calentado de caché | *sin comprobar* |
| ❓ | 24 | 🟢 | Sección "Qué dice RSU" | *sin comprobar* |
| ❓ | 25 | 🟢 | Histórico del RSU Score | *sin comprobar* |
| ❓ | 26 | 🟢 | Alertas de cambio de fase | *sin comprobar* |

## Rsrw  (22 hallazgos — ❌3 · ✅15 · ❓4)

**Pasada completa el 30/07** (commit `34a659f`): los 22 hallazgos revisados uno
a uno contra el código, seis cerrados en esa sesión. Es, junto a Research, el
único módulo con el tier completo verificado.

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | El motor de cálculo está duplicado y YA HA DIVERGIDO — el bug corregido del `rs_momentum` sigue vivo en el backend | shared/rsrw_engine.py; el fix de rs_momentum llegó a los 4 sitios |
| ✅ | 2 | 🔴 | El Gist se pide a GitHub sin caché — con el límite de 60 req/hora por IP sin autenticar | 30/07: `_load_gist()` cacheado 10 min (el fallo, 60s). Medido: 9,79s → 1,95s en la segunda llamada |
| ✅ | 3 | 🔴 | El endpoint `/scan` on-demand sigue expuesto — y la propia UI dice que ya no existe | 30/07: `GET /rsrw/scan`, `get_rsrw_scan()` y `_run_scan_engine()` eliminados. Cero referencias en frontend/ antes de quitarlo |
| ✅ | 4 | 🔴 | `get_rsrw_ticker` devuelve un RS Score que no es comparable con el de las tablas, y `rs_pct` siempre es `None` | rs_pct real desde el Gist en get_rsrw_ticker() |
| ✅ | 5 | 🟠 | `max_tickers` recorta el universo alfabéticamente → percentiles sin sentido | 30/07: desaparece con #3 (vivía en `_run_scan_engine`). El `[:525]` gemelo de `rsrw_scan.py` no recorta nada — universo de 503 |
| ❌ | 6 | 🟠 | Los festivos del mercado US reescriben el Gist con datos del día anterior, y "freshness" los presenta como frescos | verificado 30/07: cero menciones de festivos/holiday/calendar en scripts/rsrw_scan.py. Necesita un calendario de mercado, no una línea |
| ❌ | 7 | 🟠 | El universo es solo S&P 500 — tu propia cartera queda fuera | verificado 30/07: `rsrw_scan.py:52` `tickers = list(SP500_SECTOR_MAP.keys())`, sin cruce con Cartera. Es decisión de producto (ampliar el universo cuesta descargas), no un bug |
| ✅ | 8 | 🟠 | `_rs_trend_slope` puede producir flechas espurias cuando la RS es muy estable | 30/07: `EPSILON_PENDIENTE = 1e-4`. Demostrado antes del fix: ruido con std 6,2e-09 daba 0,1612 — idéntico a una tendencia real del 5% por periodo |
| ✅ | 9 | 🟠 | Instancias de Chart.js nunca destruidas + Chart.js reinyectado | 30/07: registro de INSTANCIAS (no de ids: `getChart(id)` resuelve por DOM y el canvas ya no está al limpiar) + `export cleanup()`. Verificado en navegador: 3 análisis seguidos → 1 gráfico vivo, 0 huérfanos |
| ✅ | 10 | 🟠 | `timestamp` naive (novena aparición del bug de timezone) | shared/time_utils.py |
| ✅ | 11 | 🟠 | Si el workflow nocturno falla, nadie se entera | RS/RW corre dentro de nightly_scans.yml, que avisa por Telegram por paso |
| ✅ | 12 | 🟡 | El nombre del sector viaja en el campo `ticker` | 30/07: `_df_to_records` toma la clave del nombre del índice — `ticker` para acciones, `sector` para sectores. Confirmado con datos reales del Gist |
| ✅ | 13 | 🟡 | Las barras sectoriales se normalizan al máximo del día | 30/07: escala fija ±12, medida sobre el rango real (1,16–10,66 el 30/07) y declarada en la leyenda. El líder llena 88,8%, no el 100% |
| ✅ | 14 | 🟡 | `leaders`/`laggards` duplicados entre las dos funciones de salida | 30/07: desaparece con #3 — la copia duplicada vivía en `get_rsrw_scan()` |
| ✅ | 15 | 🟡 | Escapado en el frontend | esc()/safeUrl() aplicados en rsrw.js |
| ❓ | 16 | 🔵 | Amplitud RS del universo | *sin comprobar* |
| ✅ | 17 | 🔵 | Badge 💼/⭐ de Cartera y Watchlist | `_tag_cartera()` en el servicio + `in_watchlist` en el router (sesión 16) |
| ✅ | 18 | 🔵 | Deep-link `?ticker=` | `rsrw.js` lee `?ticker=` y auto-analiza (sesión 16) |
| ❓ | 19 | 🔵 | Columna de fase Weinstein | *sin comprobar* |
| ❌ | 20 | 🟢 | Histórico del percentil RS | verificado 30/07: la persistencia YA EXISTE — `snapshot_ticker` de `snapshots.db` guarda `rs_pct` de ~500 tickers a diario. Solo falta el lado de LECTURA (detección de cruces). Es el pendiente de RS/RW con mejor relación valor/coste |
| ❓ | 21 | 🟢 | Rotación sectorial en el tiempo | *sin comprobar* |
| ❓ | 22 | 🟢 | Alerta de entrada en el top decil | *sin comprobar* |

## Rsu Algoritmo  (18 hallazgos — ❌1 · ✅15 · ❓0 · ⬜2)

**Módulo con el tier completo verificado** — el tercero, tras Research y RS/RW.
Cero hallazgos sin comprobar.

**Auditoría de datos el 30/07** (commits `34efe61` y `bb8106f`), a raíz de que
el usuario recibiera tres avisos de semáforo en un día. Los valores en pantalla
resultaron todos correctos —contrastados uno a uno contra un recálculo
independiente desde yfinance— pero salieron cuatro hallazgos nuevos, tres de
ellos encadenados y con efecto real sobre las señales. Los #14–#18 no estaban
en la auditoría original.

**Barrido del 31/07**: de los 7 que quedaban sin comprobar, **cuatro ya estaban
cerrados** (#3, #7, #8 y de paso #4 y #9 en la pasada anterior) y **dos no
aplicaban** (#11 y #13 se refieren a código que ya no existe o a un límite que
no es el que creía la auditoría). Solo #6 y #10 eran reales, y se arreglaron.
Queda abierto #12, medido y descartado por marginal.

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | El backtest valida un sistema distinto del que corre en producción (McClellan) | PRIORIDAD 2: oscilador de amplitud sectorial con histórico desde 1998 |
| ✅ | 2 | 🔴 | `get_rsu_algoritmo()` no tiene caché — ~13 llamadas de red por carga de página, y una escritura en BD | caché de 10 min en get_rsu_algoritmo() |
| ✅ | 3 | 🔴 | El "limpiado de datos" por percentiles puede borrar barras legítimas justo en un crash | verificado 31/07: **ya estaba cerrado**. El filtro se eliminó el 21/07 y hay un comentario en su sitio explicando por qué (en una caída vertical las barras más bajas — las que definen el suelo — eran justo las candidatas a caerse, dejando huecos que contaminaban RSI/ATR/medias). Comprobado que tampoco existe en el backtest: solo `dropna`. Mal contado como pendiente |
| ✅ | 4 | 🟠 | El RVOL del día del mínimo se compara contra la media de volumen de HOY, no de aquel día | verificado 30/07: ya estaba cerrado desde el 21/07 — `_rvol_en_minimo` usa `rolling(20).mean().loc[idx_min]`, la media EN el día del mínimo. Estaba mal contado como pendiente |
| ✅ | 5 | 🟠 | El texto al usuario dice "/100" cuando el máximo real es 90 | 30/07: el backend ya enviaba `max_score: 90`, el frontend lo tenía a fuego en 4 sitios. Un 52 es el 58% de lo alcanzable, no el 52% |
| ✅ | 6 | 🟠 | Comentario de cabecera desactualizado sobre los umbrales | 31/07: la línea del bloque de Régimen de Mercado seguía diciendo "(60 alcista / 70 bajista)" desde antes de que la SMA200 saliera del score y el máximo bajara de 100 a 90. Ahora apunta a las constantes en vez de repetir los números, que es lo que hizo que divergieran |
| ✅ | 7 | 🟠 | La caché del backtest puede servir un resultado sin filtro de crédito como si fuera completo | verificado 31/07: **ya estaba cerrado por partida doble**. El TTL baja de 12h a 300s si `credit_spread_cobertura_completa` es falso, y el frontend pinta un aviso naranja (`algoritmo.js:395-399`) distinguiendo "FRED no respondió" de "el histórico no cubre todo el periodo" |
| ✅ | 8 | 🟠 | Sin `FRED_API_KEY`, el filtro de crédito es inoperante en el histórico y nadie lo ve claramente | verificado 31/07: el CSV anónimo se limita a ~3 años, lo que hace `cobertura_completa=False` en cualquier backtest de 10-20 años → salta el mismo aviso del #7. Además el backend loguea la instrucción exacta para conseguir la key gratis |
| ✅ | 9 | 🟠 | `timestamp` naive (duodécima aparición) | verificado 30/07: ya usa `shared/time_utils.get_timestamp()` (Europe/Madrid). Cerrado en la sesión 2, mal contado como pendiente |
| ✅ | 10 | 🟡 | `_descargar_sectores()` se ejecuta siempre aunque su resultado casi nunca se use | 31/07: era peor de lo que decía la auditoría — la sesión 44 cambió `period` de "1mo" a "max", así que el desperdicio pasó a ser el histórico COMPLETO de 9 ETFs. **Medido: 1,67s y 58.253 filas descargadas y tiradas** en cada cache-miss, porque la amplitud real (PRIORIDAD 1) gana y los descarta. Ahora solo se descargan si hacen falta: el cálculo en vivo baja de ~2,7s a 1,08s |
| ⬜ | 11 | 🟡 | `q10`/`q90` mal nombrados | verificado 31/07: cero apariciones en el fichero. Los nombres desaparecieron con el filtro de percentiles del #3 — el código al que se refería ya no existe |
| ❌ | 12 | 🟡 | El backtest recalcula el baseline completo en cada ejecución | verificado 31/07: cierto — bucle Python con `.iloc[]` escalar sobre ~4.500 posiciones × 4 horizontes. Real pero **marginal**: el backtest hace además ~4.500 llamadas a `_calcular_score_punto` (minutos) y se cachea 12h, así que corre como mucho dos veces al día. Vectorizarlo es trivial pero no compensa tocar el motor por esto |
| ⬜ | 13 | 🟡 | `df_vix` a 3 meses limita la ventana del VIX | verificado 31/07: **el hallazgo no aplica**. El factor VIX usa `df_vix['Close'].tail(VENTANA)` con `VENTANA = 10`, así que la ventana la fija esa constante, no la descarga. Los 3 meses (~63 sesiones) son 6× lo que se consume |
| ✅ | 14 | 🔴 | **La EMA200 semanal no había convergido**: se calculaba sobre 5 años (~262 semanas) para un span de 200, y con `adjust=True` el valor arrastra el arranque de la serie | 30/07: 5y → 584,99 (+24,7%) vs convergido → 563,45 (+29,5%). Casi 5pp de error, justo sobre un corte del 25% → el gatekeeper quedaba ACTIVO sin deber estarlo. Arreglado a 15y en vivo y `BUFFER_YEARS` 5→15 en el backtest, donde el sesgo afectaba a TODOS los días evaluados |
| ✅ | 15 | 🔴 | **El gatekeeper de la EMA200W era simétrico** (`abs(dist) ≤ 25%`): trataba igual estar 24% por encima de la media secular que 24% por debajo | 30/07: se encendía el 62,5% de las semanas y se APAGABA en 2002 (−27,5%) y 2009 (−41,7%), los dos suelos más profundos. Los 7 suelos reales estuvieron todos ≤ +6,9%. Ahora `dist ≤ +10%`: 7 de 7, activo el 26,8% |
| ✅ | 16 | 🔴 | **El semáforo se decidía con datos a medio refrescar**, y cada cambio notificaba y entraba en `senales_tracked` | 30/07: los 3 avisos del día llegaron de madrugada con el MISMO precio (729,46), score 51→55→52 — el scan nocturno reescribe la amplitud a las 22:15 UTC y FRED va por su cuenta. Decisión movida a una vez por sesión, atada a que la fecha de la amplitud coincida con la sesión, + histéresis de 3 puntos aplicada también en el backtest |
| ✅ | 17 | 🟡 | `?">ABI: 38.8%` en pantalla: `tt()` devuelve HTML y estaba dentro de un `title="..."` | 30/07: la comilla del `<span>` cerraba el atributo y el resto se derramaba como texto |
| ✅ | 18 | 🟠 | ¿Es correcto que estar sobre la SMA200 BAJE el umbral de VERDE a 54? Parece un sesgo optimista: es más fácil declarar un suelo con el mercado fuerte | **EVALUADO 31/07, la asimetría es correcta y se queda.** Cuatro configuraciones barridas con el backtest real en dos periodos. Ventaja a 60d: ACTUAL 54/63 → **+4,30pp (10a) y +4,76pp (máx)**; fijo 58/58 → +1,12 / +1,02; fijo 54/54 → +0,27 / +1,05; inverso 63/54 → +0,98 / +1,54. Mismo orden en ambos periodos. Matiz: a 10d el inverso rinde algo más y n=14-35, así que es direccional, no medición fina |

## Scanner  (20 hallazgos — ✅9 · ❓11)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🟠 | La columna "Absorción" muestra 0/10 para casi todo el universo — sabes que el umbral es provisional, pero el frontend lo presenta  | umbral 0.75 restaurado y unificado en shared/absorption.py |
| ✅ | 2 | 🟠 | `_fetch_batch` no reintenta lotes incompletos — a diferencia del scan de RS/RW, que sí lo hace | reintentos reales en _fetch_batch vía shared/yf_batch.py |
| ✅ | 3 | 🟠 | Si el scan nocturno falla, el Gist queda con datos rancios y solo `_freshness` lo delata | aviso Telegram en scanner_scan.yml / nightly_scans.yml |
| ✅ | 4 | 🟠 | La amplitud de mercado hereda tickers muertos del export de Russell 2000 | ABX eliminado + log de tickers muertos |
| ✅ | 5 | 🟠 | `new_high` con `>=` marca como "nuevo máximo" cualquier día lateral en máximos | new_high/new_low excluyen el día evaluado |
| ✅ | 6 | 🟠 | El percentil RS del Scanner y el de RS/RW son el mismo cálculo con dos códigos distintos | shared/rsrw_engine.py::rs_percentile, un solo cálculo |
| ✅ | 7 | 🟠 | `timestamp` naive en `run_filter` (undécima aparición del bug de timezone) | shared/time_utils.py |
| ✅ | 8 | 🟡 | El `score_tecnico` es puramente técnico pero se llama igual que el RSU Score fundamental | verificado 30/07: scanner_service.py:22 documenta explícitamente que el score_tecnico NO es el RSU Score fundamental |
| ❓ | 9 | 🟡 | El `rvol_pts` del score satura a RVOL=3x, pero RVOL extremos siguen siendo informativos | *sin comprobar* |
| ❓ | 10 | 🟡 | `run_filter` no valida coherencia entre criterios | *sin comprobar* |
| ❓ | 11 | 🟡 | `absorcion_min` filtra sobre un dato provisional (ligado al #1) | *sin comprobar* |
| ✅ | 12 | 🟡 | Escapado en el frontend | verificado 30/07: 11 usos de esc() en scanner.js |
| ❓ | 13 | 🔵 | Enriquecimiento on-demand con el RSU Score v2 | *sin comprobar* |
| ❓ | 14 | 🔵 | Badge 💼/⭐ de Cartera y Watchlist | *sin comprobar* |
| ❓ | 15 | 🔵 | Presets de filtros | *sin comprobar* |
| ❓ | 16 | 🔵 | Deep-link del estado de filtros en la URL | *sin comprobar* |
| ❓ | 17 | 🔵 | Fase semanal en la tabla | *sin comprobar* |
| ❓ | 18 | 🟢 | Histórico de transiciones de fase | *sin comprobar* |
| ❓ | 19 | 🟢 | Alerta de entrada en criterios para Watchlist | *sin comprobar* |
| ❓ | 20 | 🟢 | Divergencia S&P 500 vs Russell 2000 | *sin comprobar* |

## Spxl  (14 hallazgos — ❌1 · ✅3 · ❓10)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | Cuarto bug de la misma familia: en el Escenario A el objetivo del runner es inalcanzable por construcción | first_sell_px asignado en Escenario A (48422ff) |
| ✅ | 2 | 🔴 | El benchmark Buy & Hold está penalizado con un 10% de caja que la estrategia no reserva | B&H invierte el 100%; reserve_pct eliminado (48422ff) |
| ✅ | 3 | 🔴 | Los stops se evalúan contra cierres, no contra mínimos intradía — y el otro backtest de la casa sí lo hace bien | stops contra Low intradía con fill realista (48422ff) |
| ❌ | 4 | 🔴 | Ni `/live` ni `/backtest` tienen caché: cada visita descarga 17 años y ejecuta el motor completo | 0 usos de cache.get en spxl_service.py: cada visita descarga 17 años y corre el motor |
| ❓ | 5 | 🟠 | `_fetch_cds()` usa la serie que ya descubriste que está restringida por licencia | *sin comprobar* |
| ❓ | 6 | 🟠 | Sin costes de transacción, spread ni deslizamiento | *sin comprobar* |
| ❓ | 7 | 🟠 | `compute_stats` devuelve `{}` si no hay operaciones | *sin comprobar* |
| ❓ | 8 | 🟠 | `max_dd` se calcula dos veces con bases distintas | *sin comprobar* |
| ❓ | 9 | 🟠 | La ejecución en el mismo cierre que dispara la condición | *sin comprobar* |
| ❓ | 10 | 🟠 | `cycle_equity` tras `C-final` incluye un runner que en el Escenario C no existe | *sin comprobar* |
| ❓ | 11 | 🟡 | `phase_high = price` tras cada compra: conviene que la UI lo explique | *sin comprobar* |
| ❓ | 12 | 🟡 | Sin `Low`/`High` descargados, tampoco hay drawdown intradía real | *sin comprobar* |
| ❓ | 13 | 🟡 | Charts sin `destroy()` | *sin comprobar* |
| ❓ | 14 | 🟡 | `_is_market_open()` depende de `pytz` con fallback a UTC fijo | *sin comprobar* |

## Tesis Admin  (22 hallazgos — ✅1 · ❓21)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | Inyección de HTML/CSS en el PDF de tesis vía interpolación f-string sin escapar | html.escape() en generar_pdf_tesis() |
| ❓ | 2 | 🔴 | La clave de administrador se guarda en `sessionStorage` y viaja en una cabecera custom en cada request | *sin comprobar* |
| ❓ | 3 | 🔴 | XSS almacenado en el panel de admin desde contenido generado por agentes | *sin comprobar* |
| ❓ | 4 | 🔴 | `create_tesis` permite publicar directamente saltándose la cola de aprobación | *sin comprobar* |
| ❓ | 5 | 🟠 | `/track` de analytics es un endpoint de escritura sin autenticación ni límite | *sin comprobar* |
| ❓ | 6 | 🟠 | `get_tesis_list` pagina en Python tras traer TODAS las filas aprobadas | *sin comprobar* |
| ❓ | 7 | 🟠 | Timestamps naive en toda la capa de tesis | *sin comprobar* |
| ❓ | 8 | 🟠 | `search` en `get_tesis_list` se interpola con LIKE sin escapar comodines | *sin comprobar* |
| ❓ | 9 | 🟠 | `get_tesis_detail` hace una llamada a yfinance en vivo por cada apertura de tesis, sin caché | *sin comprobar* |
| ❓ | 10 | 🟠 | Meeting Room: los mensajes a agentes no conectados se acumulan como "pending" para siempre | *sin comprobar* |
| ❓ | 11 | 🟡 | `_normalize_doc_url` genera iframes de Google Drive/Docs — posible fuga de contexto | *sin comprobar* |
| ❓ | 12 | 🟡 | El PDF no lleva el `rating` ni el precio objetivo en la cabecera | *sin comprobar* |
| ❓ | 13 | 🟡 | Inconsistencia de escapado entre paneles del admin | *sin comprobar* |
| ❓ | 14 | 🟡 | `activeTab` es estado a nivel de módulo (global) | *sin comprobar* |
| ❓ | 15 | 🔵 | Vista previa del PDF antes de aprobar | *sin comprobar* |
| ❓ | 16 | 🔵 | Diff/edición antes de aprobar | *sin comprobar* |
| ❓ | 17 | 🔵 | Render markdown en el VER del panel | *sin comprobar* |
| ❓ | 18 | 🔵 | Confirmaciones con `confirm()` nativo | *sin comprobar* |
| ❓ | 19 | 🟢 | Audit log de acciones de admin | *sin comprobar* |
| ❓ | 20 | 🟢 | Métricas de tesis en el panel | *sin comprobar* |
| ❓ | 21 | 🟢 | Cola de aprobación unificada | *sin comprobar* |
| ❓ | 22 | 🟢 | Rotación de la ADMIN_KEY | *sin comprobar* |

## Watchlist Community  (20 hallazgos — ✅1 · ❓19)

| | # | Sev | Hallazgo | Estado / evidencia |
|-|---|-----|----------|--------------------|
| ✅ | 1 | 🔴 | Las alertas se disparan, se guardan… y nadie se entera | notificación Telegram por usuario + vinculación de cuenta |
| ❓ | 2 | 🟠 | La alerta de "toque de EMA" puede no ver el toque | *sin comprobar* |
| ❓ | 3 | 🟠 | Las alertas de RVOL solo pueden saltar a última hora de la sesión | *sin comprobar* |
| ❓ | 4 | 🟠 | No se valida el formato del ticker en ningún punto de entrada | *sin comprobar* |
| ❓ | 5 | 🟠 | `_rvol_cache` y `_ema_cache` crecen sin límite | *sin comprobar* |
| ❓ | 6 | 🟠 | `_get_ema_baseline` usa el día UTC para decidir "hoy" | *sin comprobar* |
| ❓ | 7 | 🟠 | Las alertas disparadas no se rearman nunca | *sin comprobar* |
| ❓ | 8 | 🟠 | El feedback de Community no notifica ni valida el contacto | *sin comprobar* |
| ❓ | 9 | 🟡 | `target_price` guarda el periodo de la EMA por compatibilidad de esquema | *sin comprobar* |
| ❓ | 10 | 🟡 | El chat no limita el gasto por usuario | *sin comprobar* |
| ❓ | 11 | 🟡 | `chat_historial.db` guarda conversaciones sin retención declarada | *sin comprobar* |
| ❓ | 12 | 🟡 | `alerts_check_loop` con `except Exception: pass` | *sin comprobar* |
| ❓ | 13 | 🟡 | La comprobación cada 90 s corre también con el mercado cerrado | *sin comprobar* |
| ❓ | 14 | 🔵 | Cruce Watchlist × módulos | *sin comprobar* |
| ❓ | 15 | 🔵 | Alerta directa desde cualquier módulo | *sin comprobar* |
| ❓ | 16 | 🔵 | Notas por ticker | *sin comprobar* |
| ❓ | 17 | 🔵 | Community: mostrar el estado del feedback enviado | *sin comprobar* |
| ❓ | 18 | 🟢 | Alertas sobre las señales de la propia terminal | *sin comprobar* |
| ❓ | 19 | 🟢 | Watchlists múltiples | *sin comprobar* |
| ❓ | 20 | 🟢 | Digest diario | *sin comprobar* |

