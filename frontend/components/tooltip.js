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

    "fear-greed-components": {
        title: "Los 7 Componentes",
        short: "Cada uno de los 7 indicadores que CNN combina para formar el score compuesto, con su propia lectura 0-100.",
        long: `El score compuesto del Fear & Greed Index es la media de estos 7 indicadores independientes, cada uno con su propia escala 0 (miedo extremo) a 100 (codicia extrema):

▸ Momentum del Mercado: compara el S&P 500 con su media móvil de 125 sesiones.
▸ Fortaleza del Precio: número de acciones en nuevos máximos de 52 semanas en la NYSE frente a nuevos mínimos.
▸ Amplitud del Precio: volumen negociado en acciones que suben frente al volumen en acciones que bajan (McClellan Volume Summation Index).
▸ Ratio Put/Call: volumen de opciones put frente a calls — más puts relativos indica más cobertura/miedo.
▸ Demanda de Bonos Basura: diferencial de rendimiento entre bonos high yield e investment grade — un spread que se estrecha indica apetito por riesgo.
▸ Volatilidad (VIX): el VIX comparado con su media móvil de 50 sesiones.
▸ Demanda de Refugio: rendimiento de las acciones frente a los bonos del Tesoro en las últimas 20 sesiones.

POR QUÉ MIRARLOS POR SEPARADO:
El score compuesto puede estar en "Neutral" mientras algún componente individual ya está en zona extrema — por ejemplo, la volatilidad puede estar tranquila mientras la amplitud del precio ya muestra señales de codicia extrema. Los componentes por separado dan una lectura más rica que el número único.`
    },

    "watchlist": {
        title: "Watchlist",
        short: "Tus tickers seguidos con precio en vivo, y punto de partida para crear alertas de precio.",
        long: `La Watchlist guarda los tickers que quieres tener siempre a mano, con precio y variación diaria en vivo (mismo caché de 60s que usa Cartera).

QUÉ PUEDES HACER:
▸ Añadir cualquier ticker escribiéndolo arriba.
▸ Clic en el nombre del ticker para ir directo a su ficha en Research.
▸ Botón "＋ alerta" en cada fila para crear una alerta de precio sobre ese ticker sin tener que volver a escribirlo.
▸ Quitar un ticker con la ✕.

LÍMITE: hasta 50 tickers por usuario. Es una lista personal — no se comparte con el resto de la comunidad.`
    },

    "price-alerts": {
        title: "Alertas",
        short: "Avisa cuando un ticker cruza un umbral de precio o de RVOL, o toca una de sus EMAs (10/20/50/200). Se comprueban cada ~90 segundos.",
        long: `Cada alerta compara un valor en vivo del ticker contra el objetivo que fijaste. Tres métricas disponibles:

▸ PRECIO: compara el precio actual contra un precio objetivo en $, con la condición "por encima de" o "por debajo de".
▸ RVOL: compara el volumen relativo actual (volumen de hoy / media de 20 sesiones) contra un múltiplo objetivo — p.ej. "RVOL por encima de 2.5" avisa cuando el ticker negocia 2,5 veces su volumen medio, señal típica de entrada de dinero grande.
▸ TOQUE DE EMA: avisa cuando el precio se acerca a menos de un 0,5% de la EMA que elijas (10, 20, 50 o 200 sesiones) — útil para vigilar posibles retrocesos a una media móvil clave sin tener que mirar el gráfico constantemente. A diferencia de precio/RVOL, no tiene "por encima" o "por debajo": es un aviso de proximidad, en cualquier dirección.

CÓMO SE COMPRUEBAN:
Un proceso en segundo plano revisa todas las alertas activas de todos los usuarios cada ~90 segundos (agrupando por ticker, así que no importa cuánta gente tenga una alerta en el mismo nombre — el dato se pide una sola vez por ticker y métrica). Para las alertas de EMA, el valor de la media de las sesiones ya cerradas se calcula una vez al día (no tiene sentido recalcularlo cada 90 segundos si los cierres de ayer no cambian) y se combina con el precio en vivo de hoy en cada ciclo. En cuanto se cumple la condición, la alerta pasa a "DISPARADA" y aparece un aviso (número rojo) junto a Watchlist en el menú lateral.

IMPORTANTE — SOLO DENTRO DE LA TERMINAL:
Por ahora el aviso es únicamente dentro de la app (campanita + listado en Watchlist). Todavía no hay notificación por email, Discord o Telegram — si cierras la pestaña, la alerta se sigue comprobando en el servidor y la verás marcada como disparada la próxima vez que entres, pero no recibirás ningún aviso fuera de la terminal.

LÍMITE: hasta 30 alertas activas por usuario. Una alerta disparada no vuelve a comprobarse ni se repite — si quieres seguir vigilando el mismo nivel, crea una nueva. Puedes limpiar en bloque las ya disparadas con el botón "Limpiar disparadas".`
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

    "fed-balance": {
        title: "Balance de la Reserva Federal",
        short: "Tamaño del balance de la Fed (WALCL) y liquidez neta del sistema. QE expande, QT contrae.",
        long: `El balance de la Reserva Federal (serie WALCL en FRED) refleja el total de activos que la Fed tiene en su hoja de balance — principalmente bonos del Tesoro y MBS comprados durante programas de expansión cuantitativa (QE).

QE vs QT:
- Quantitative Easing (QE): la Fed compra activos, expandiendo el balance e inyectando liquidez al sistema.
- Quantitative Tightening (QT): la Fed deja vencer activos sin reinvertir (o vende), contrayendo el balance y retirando liquidez.

LIQUIDEZ NETA (Balance − TGA − RRP):
Esta es la métrica que muchos consideran más relevante que el balance bruto, porque resta dos "aparcamientos" de liquidez que no circulan en el mercado:
▸ TGA (Treasury General Account): la cuenta del Tesoro en la Fed. Cuando sube, retira liquidez del sistema; cuando baja, la inyecta.
▸ RRP (Reverse Repo Facility): liquidez que fondos money market depositan en la Fed a cambio de un interés, efectivamente "aparcada" fuera del mercado.

POR QUÉ IMPORTA PARA LOS MERCADOS:
La liquidez neta tiende a correlacionar con el apetito de riesgo en activos como acciones y cripto — más liquidez neta circulando suele coincidir con entornos más favorables para activos de riesgo, y viceversa durante fases de contracción.`
    },

    "fed-macro-chart": {
        title: "Gráfico Histórico TradingView",
        short: "Evolución histórica de cada serie FRED (Fed Funds, IPC, Desempleo, PCE) vía TradingView, con pestañas para cambiar de serie.",
        long: `Las tarjetas de arriba muestran el último valor publicado de cada indicador. Este gráfico añade el contexto histórico — cómo ha evolucionado esa serie a lo largo del tiempo — usando el mismo motor de gráficos de TradingView que ya ves en Credit Spreads y en el Calendario Económico.

SERIES DISPONIBLES:
▸ FED FUNDS (FRED:FEDFUNDS): tipo de interés efectivo de la Reserva Federal.
▸ IPC (FRED:CPIAUCSL): Índice de Precios al Consumo, nivel general.
▸ DESEMPLEO (FRED:UNRATE): tasa de paro de EE.UU.
▸ PCE (FRED:PCEPI): Índice de Precios de Gasto en Consumo Personal — la medida de inflación que más sigue la Fed.

Cambia de pestaña para ver la serie que te interese; el gráfico usa velas mensuales, coherente con la frecuencia de publicación de estos datos.`
    },

    "fed-balance-total": {
        title: "Balance Total — WALCL",
        short: "Tamaño bruto del balance de la Fed en dólares. La serie base detrás de todo el análisis de liquidez.",
        long: `WALCL es el código de la serie en FRED para el balance total de activos de la Reserva Federal — la cifra bruta antes de restar TGA y RRP.

QUÉ INCLUYE:
Principalmente bonos del Tesoro americano y MBS (mortgage-backed securities) que la Fed ha comprado a lo largo de sus distintos programas de expansión cuantitativa desde 2008, y especialmente desde 2020.

CÓMO LEER EL CAMBIO SEMANAL:
▸ Δ Semanal positivo → la Fed está expandiendo el balance (QE activo o reinversión de vencimientos)
▸ Δ Semanal negativo → la Fed está contrayendo el balance (QT — deja vencer activos sin reinvertir)

Esta cifra bruta es el punto de partida, pero la Liquidez Neta (que resta TGA y RRP) suele ser más relevante para entender cuánta liquidez circula realmente en el mercado.`
    },

    "fed-net-liquidity": {
        title: "Liquidez Neta (Balance − TGA − RRP)",
        short: "El balance de la Fed menos los dos 'aparcamientos' de liquidez que no circulan en el mercado.",
        long: `La Liquidez Neta resta del balance bruto de la Fed dos partidas que, aunque forman parte del sistema financiero, no están circulando activamente en los mercados de riesgo:

TGA (Treasury General Account):
La cuenta corriente del Tesoro de EE.UU. en la Fed. Cuando el Tesoro acumula efectivo ahí (por ejemplo, tras emitir deuda), retira esa liquidez del sistema. Cuando el Tesoro gasta ese efectivo, lo devuelve al mercado.

RRP (Reverse Repo Facility):
Liquidez que fondos del mercado monetario depositan voluntariamente en la Fed a cambio de un interés garantizado, en lugar de prestarla en el mercado. Es liquidez "aparcada" de forma segura pero inactiva para activos de riesgo.

POR QUÉ ESTA MÉTRICA IMPORTA MÁS QUE EL BALANCE BRUTO:
Dos periodos con el mismo balance bruto pueden tener condiciones de liquidez muy distintas si el TGA o el RRP varían. La Liquidez Neta intenta capturar cuánto dinero está realmente disponible para fluir hacia acciones, bonos y otros activos de riesgo.`
    },

    "liquidity-overview": {
        title: "Módulo de Liquidez",
        short: "Sigue el dinero disponible en el sistema con dos métricas complementarias, superpuestas contra el SPX.",
        long: `Seguir la liquidez del sistema financiero es, para muchos inversores macro, uno de los factores más determinantes de la dirección de fondo del mercado — más incluso que los fundamentales de empresas individuales en ciertos entornos.

DOS MÉTRICAS, DOS VELOCIDADES:
▸ Net Liquidity (WALCL − TGA − RRP): táctica, se actualiza semanalmente, captura movimientos de liquidez de semanas a pocos meses. Es la que más rápido reacciona a decisiones de la Fed y del Tesoro.
▸ M2 Money Supply: estructural, se actualiza semanalmente (serie WM2NS), representa el contexto de fondo de varios trimestres o años. Aunque su frecuencia de publicación es semanal, cambia mucho más lento que la Net Liquidity porque agrega depósitos de toda la economía, no movimientos tácticos de la Fed.

POR QUÉ SE MUESTRAN JUNTAS Y CONTRA EL SPX:
Ninguna de las dos predice el mercado por sí sola con precisión de timing exacto, pero ambas han mostrado correlación histórica relevante con el apetito de riesgo. Superponerlas contra el SPX permite ver visualmente si la liquidez está expandiéndose o contrayéndose en paralelo al movimiento del índice, o si están divergiendo — una divergencia sostenida suele ser una señal de alerta digna de investigar más a fondo.

Ninguna métrica de liquidez sustituye al análisis técnico o fundamental — es una capa adicional de contexto macro sobre la "marea" en la que se mueven todos los activos de riesgo.`
    },

    "m2-money-supply": {
        title: "M2 Money Supply",
        short: "Cantidad agregada de dinero amplio en la economía: efectivo, depósitos y fondos monetarios minoristas.",
        long: `M2 es uno de los agregados monetarios más seguidos para entender cuánto dinero "ancho" existe en la economía en un momento dado — no solo efectivo y depósitos a la vista (eso sería M1), sino también depósitos a plazo de menor cuantía y fondos del mercado monetario minoristas.

DIFERENCIA CLAVE CON NET LIQUIDITY:
La serie WM2NS que se usa aquí se publica semanalmente, pero aun así M2 es un indicador mucho más estructural — no reacciona a movimientos tácticos del TGA o del RRP de un día para otro. Refleja más bien la política monetaria de fondo (expansiva o restrictiva) acumulada a lo largo de meses y años, ya que agrega el total de depósitos y efectivo en circulación en toda la economía.

POR QUÉ IMPORTA EL DATO YoY (interanual):
El crecimiento o contracción de M2 respecto al año anterior es la forma más habitual de leer esta serie. Periodos de fuerte expansión de M2 (como 2020-2021) han coincidido históricamente con entornos muy favorables para activos de riesgo; periodos de contracción histórica de M2 (como 2022-2023) coincidieron con uno de los ciclos de ajuste más duros para acciones y cripto en décadas recientes.

A diferencia del balance de la Fed, M2 incluye también el efecto de la actividad bancaria comercial (créditos, depósitos), no solo las decisiones directas de la Reserva Federal — por eso aporta una perspectiva complementaria, no redundante, a la Net Liquidity.`
    },

    "liquidity-correlation": {
        title: "Correlación Net Liquidity ↔ SPX",
        short: "Coeficiente de correlación entre la Liquidez Neta y el S&P 500 en los últimos ~2 años (semanal).",
        long: `Este coeficiente mide, de forma puramente estadística, cuánto se han movido en la misma dirección la Liquidez Neta y el S&P 500 a lo largo del periodo mostrado, usando datos semanales.

CÓMO LEER EL NÚMERO (rango de -1 a +1):
▸ Cercano a +1 → fuerte correlación positiva. Cuando la liquidez sube, el SPX tiende a subir también, y viceversa.
▸ Cercano a 0 → poca relación lineal aparente en el periodo medido.
▸ Cercano a -1 → correlación negativa. Movimientos en direcciones opuestas.

LIMITACIONES IMPORTANTES A TENER EN CUENTA:
Correlación no implica causalidad directa ni constante en el tiempo — la relación entre liquidez y mercados ha sido más fuerte en algunos periodos (2020-2022) que en otros, y puede debilitarse cuando otros factores (beneficios empresariales, geopolítica, valoración) dominan el movimiento del mercado en una ventana de tiempo concreta.

Este número es una foto del periodo mostrado, no una constante universal — conviene observar cómo evoluciona con el tiempo más que fijarse en un valor puntual aislado.`
    },

    "fed-monthly-change": {
        title: "Cambio Mensual del Balance",
        short: "Variación del balance total de la Fed en las últimas ~5 semanas. Confirma si la tendencia reciente es QE o QT.",
        long: `Esta cifra compara el balance actual con el de hace aproximadamente 5 semanas, dando una lectura de tendencia más estable que el cambio semanal aislado (que puede ser ruidoso por operaciones técnicas puntuales).

CÓMO USARLA:
▸ Varias semanas consecutivas de cambio mensual positivo → confirma una fase de expansión (QE) sostenida, no solo un repunte puntual.
▸ Varias semanas consecutivas de cambio mensual negativo → confirma una fase de contracción (QT) sostenida.

Un solo dato semanal puede estar distorsionado por vencimientos de deuda, operaciones de financiación a corto plazo, u otros factores técnicos. El cambio mensual filtra parte de ese ruido y refleja mejor la dirección de fondo de la política de balance de la Fed.`
    },

    "yield-curve": {
        title: "Curva de Tipos US Treasury",
        short: "Rentabilidades de bonos del Tesoro en distintos plazos (3M a 30Y). Su forma anticipa expectativas económicas.",
        long: `La curva de tipos muestra la rentabilidad (yield) que exige el mercado por prestar dinero al gobierno de EE.UU. en distintos plazos: 3 meses, 2, 5, 10 y 30 años.

FORMA NORMAL (curva ascendente):
Plazos más largos pagan más rentabilidad que los cortos — compensación lógica por asumir más riesgo de inflación y de tipo de interés a largo plazo. Refleja expectativas de crecimiento económico saludable.

FORMA INVERTIDA:
Cuando los plazos cortos pagan más que los largos, el mercado está señalando que espera que la economía se debilite y que la Fed tenga que bajar tipos en el futuro. Es una de las señales adelantadas de recesión más estudiadas históricamente.

POR QUÉ SE MIRA PLAZO A PLAZO:
La forma completa de la curva (no solo el spread 10Y-2Y) puede revelar matices — por ejemplo, una inversión solo en el tramo corto cuenta una historia distinta a una inversión en toda la curva.`
    },

    "treasury-spread": {
        title: "Spread 10Y − 2Y",
        short: "Diferencia entre el bono a 10 años y el de 2 años. El indicador de inversión de curva más seguido.",
        long: `El spread 10Y-2Y es la diferencia entre la rentabilidad del bono del Tesoro a 10 años y la del bono a 2 años. Es probablemente el indicador de forma de curva más citado en medios financieros.

LECTURA:
▸ Spread positivo (curva normal) → el bono a 10 años paga más que el de 2 años, como es habitual en un entorno de crecimiento esperado.
▸ Spread negativo (curva invertida) → el bono a 2 años paga más que el de 10 años. Señal histórica de alerta de recesión.

DATO HISTÓRICO IMPORTANTE:
Cada recesión en EE.UU. desde los años 1970 ha sido precedida por una inversión de este spread, normalmente entre 6 y 18 meses antes del inicio de la recesión. Sin embargo, no toda inversión ha sido seguida de recesión inmediata — el indicador señala riesgo elevado, no certeza ni timing exacto.

La normalización del spread (vuelta a positivo) tras un periodo invertido históricamente ha coincidido, en varios ciclos, con el inicio efectivo de la fase recesiva — no con su descarte.`
    },

    "fed-funds-rate": {
        title: "Fed Funds Rate",
        short: "Tipo de interés de referencia que fija la Reserva Federal. La palanca principal de política monetaria.",
        long: `El Fed Funds Rate es el tipo de interés objetivo que la Reserva Federal fija para los préstamos interbancarios a un día. Es la herramienta principal de política monetaria de EE.UU. e influye, directa o indirectamente, en casi todos los demás tipos de interés de la economía.

CLASIFICACIÓN DE POSTURA (según el nivel mostrado en este widget):
▸ RESTRICTIVA (≥ 4.5%) → tipos altos, política diseñada para enfriar la inflación y la actividad económica.
▸ NEUTRAL (3% – 4.5%) → nivel que ni estimula ni frena significativamente la economía.
▸ EXPANSIVA (&lt; 3%) → tipos bajos, política diseñada para estimular crecimiento y empleo.

POR QUÉ NO ES "SUBIDA = MALO" DE FORMA AUTOMÁTICA:
A diferencia de otros indicadores macro de este panel, una subida de tipos no siempre es negativa para los mercados — depende de si responde a una economía que necesita enfriarse (a menudo visto como manejable) o a una inflación fuera de control (a menudo visto como más preocupante). El contexto que la acompaña importa tanto como la cifra en sí.`
    },

    "cpi-yoy": {
        title: "IPC YoY — Inflación interanual",
        short: "Variación de precios al consumo respecto al mismo mes del año anterior. El termómetro de inflación más seguido.",
        long: `El IPC (Índice de Precios al Consumo) YoY mide cuánto han subido los precios de una cesta representativa de bienes y servicios respecto al mismo mes hace un año.

POR QUÉ ES EL DATO MACRO MÁS OBSERVADO:
La inflación es uno de los dos mandatos principales de la Reserva Federal (junto al pleno empleo). Datos de IPC por encima de lo esperado suelen interpretarse como presión para que la Fed mantenga o suba tipos; datos por debajo de lo esperado abren la puerta a posibles bajadas.

LECTURA EN ESTE WIDGET:
La flecha y el color reflejan si la cifra ha subido o bajado respecto al periodo anterior — en el contexto de inflación, una subida (▲) generalmente se interpreta como menos favorable para los mercados, ya que reduce el margen de la Fed para flexibilizar política monetaria.

El IPC general puede diferir significativamente del PCE Core, que la Fed sigue de cerca con más peso para sus decisiones.`
    },

    "unemployment-rate": {
        title: "Tasa de Desempleo",
        short: "Porcentaje de la población activa sin empleo y buscando trabajo. El otro mandato clave de la Fed.",
        long: `La tasa de desempleo mide qué porcentaje de la fuerza laboral disponible (personas que quieren y pueden trabajar) no tiene empleo actualmente.

EL DOBLE MANDATO DE LA FED:
Junto a la estabilidad de precios (inflación), el pleno empleo es el segundo objetivo legal explícito de la Reserva Federal. Un desempleo muy bajo puede generar presión salarial e inflacionaria; un desempleo en aumento suele preceder o acompañar fases de debilidad económica.

CÓMO SE INTERPRETA EN ESTE WIDGET:
Una subida de la tasa de desempleo generalmente se considera una señal de debilitamiento económico — por eso, igual que con el IPC, una subida (▲) se marca como menos favorable en el color del indicador.

DATO A TENER EN CUENTA:
El desempleo es un indicador retrasado (lagging) — tiende a confirmar fases económicas que ya están en marcha, más que anticiparlas. Otros indicadores de este panel, como la curva de tipos, tienden a adelantarse más en el ciclo.`
    },

    "core-pce": {
        title: "PCE Core",
        short: "Medida de inflación preferida por la Fed, excluyendo alimentos y energía por su volatilidad.",
        long: `El PCE Core (Personal Consumption Expenditures, excluyendo alimentos y energía) es la medida de inflación que la Reserva Federal ha declarado explícitamente como su referencia preferida para sus decisiones de política monetaria — por encima incluso del IPC, que es el dato más conocido públicamente.

POR QUÉ EXCLUYE ALIMENTOS Y ENERGÍA:
Estos dos componentes son altamente volátiles por factores externos (clima, geopolítica, oferta puntual) que no reflejan necesariamente presión inflacionaria de fondo en la economía. Excluirlos da una lectura más "limpia" de la tendencia subyacente.

POR QUÉ SE SIGUE MENOS QUE EL IPC EN MEDIOS GENERALISTAS:
A pesar de ser el indicador que más pesa en las decisiones reales de la Fed, el PCE Core recibe menos cobertura mediática que el IPC porque se publica con algo más de retraso y es menos intuitivo para el público general. Para entender hacia dónde se inclina la política monetaria, el PCE Core suele ser más informativo que el IPC.`
    },

    "vix-levels": {
        title: "VIX Niveles",
        short: "Gauge de 5 zonas del VIX spot con histórico diario de 6 meses.",
        long: `Este gauge clasifica el VIX spot actual en 5 zonas según su nivel absoluto, complementando la lectura de la Term Structure (que compara spot vs futuros).

ZONAS:
- &lt; 12 → Complacencia. Volatilidad muy baja, posible exceso de confianza del mercado.
- 12-20 → Normal. Rango habitual de un mercado sin estrés.
- 20-25 → Precaución. Volatilidad por encima de lo normal, vigilar.
- 25-35 → Miedo. Estrés de mercado elevado, movimientos amplios.
- &gt; 35 → Pánico. Capitulación, históricamente cerca de suelos de mercado importantes.

DIFERENCIA CON LA TERM STRUCTURE:
El gauge de niveles te dice CUÁNTO miedo hay ahora mismo en términos absolutos. La Term Structure te dice si el mercado espera que ese miedo aumente (contango) o ya está descontando que se calme (backwardation). Usar ambos juntos da una lectura más completa que cualquiera de los dos por separado.`
    },

    "crypto-prices": {
        title: "Criptomonedas",
        short: "Precios en tiempo casi real de las 6 principales criptomonedas por capitalización.",
        long: `Seguimiento de las 6 criptomonedas más relevantes por capitalización de mercado: Bitcoin, Ethereum, BNB, Solana, XRP y Cardano.

POR QUÉ SEGUIR CRIPTO EN UNA TERMINAL DE ACCIONES:
Bitcoin en particular ha mostrado periodos de correlación creciente con activos de riesgo tradicionales (Nasdaq, growth stocks), especialmente en entornos de liquidez monetaria expansiva o restrictiva. Monitorizar el sentimiento cripto puede dar una lectura adicional sobre el apetito de riesgo global, complementaria a los indicadores de renta variable tradicional.

Los datos se actualizan con la misma frecuencia que el resto de activos de mercado de la terminal.`
    },

    "crypto-fear-greed": {
        title: "Crypto Fear & Greed Index",
        short: "Sentimiento del mercado cripto de 0 (miedo extremo) a 100 (codicia extrema). Fuente: alternative.me",
        long: `El Crypto Fear & Greed Index es un indicador independiente del Fear & Greed de acciones (CNN), específico para el mercado de criptomonedas. Lo calcula alternative.me combinando:

▸ Volatilidad de Bitcoin comparada con sus promedios históricos
▸ Momentum y volumen de mercado
▸ Sentimiento en redes sociales relacionado con cripto
▸ Dominancia de Bitcoin sobre el resto del mercado cripto
▸ Tendencias de búsqueda relacionadas con criptomonedas

CÓMO INTERPRETARLO:
- 0-25 → Miedo extremo → Posible zona de capitulación / oportunidad
- 25-45 → Miedo → Sentimiento negativo dominante
- 45-55 → Neutral → Sin sesgo claro
- 55-75 → Codicia → Optimismo elevado
- 75-100 → Codicia extrema → Riesgo de sobrecalentamiento

El mercado cripto tiende a moverse en ciclos de sentimiento más extremos y rápidos que el mercado de acciones, por lo que este índice puede ser más volátil que su equivalente de renta variable.`
    },

    "trump-truth-social": {
        title: "Trump · Truth Social (archivo público)",
        short: "Posts recientes de Donald Trump en Truth Social, vía trumpstruth.org. Etiquetados por impacto en mercado.",
        long: `Trump es actualmente uno de los activos macro más volátiles del mercado — un post sobre aranceles, la Fed, o geopolítica puede mover el S&P 500 1-2% en minutos, antes de que esa información aparezca en ningún RSS financiero convencional.

FUENTE:
Los posts proceden de trumpstruth.org, un archivo público de Truth Social gestionado por Defending Democracy Together. No es la fuente oficial de Truth Social (que no tiene API pública) — es un archivo de acceso libre que archiva los posts públicos de Trump con RSS nativo.

CLASIFICACIÓN DE IMPACTO:
Igual que en el feed principal, los posts se clasifican automáticamente por keywords:
▸ HIGH (rojo) → mención de aranceles, Fed, recesión, crash, guerra, sanción, emergencia
▸ MED (ámbar) → earnings, fusiones, PIB, inflación, tipos de interés
▸ Sin badge → posts de contenido político/personal sin impacto directo inmediato en mercados

CÓMO USARLO:
No todos los posts de Trump mueven mercados — muchos son de contenido político o personal. Los que históricamente han causado más movimiento son los relacionados con aranceles (en particular contra China), comentarios sobre la Fed o sobre tipos de interés, y anuncios de política exterior. El badge HIGH intenta destacarlos, pero el juicio final es siempre del trader.

El panel se actualiza automáticamente cada 5 minutos junto al feed principal.`
    },

    "reddit-pulse": {
        title: "Reddit Pulse — Social Buzz",
        short: "Tickers con mayor actividad y mención en Reddit y StockTwits, ordenados por nivel de conversación social.",
        long: `Reddit Pulse rastrea qué acciones están generando más conversación en comunidades de inversión retail como Reddit (r/wallstreetbets, r/stocks, etc.) y StockTwits, combinando ambas fuentes en un ranking único.

QUÉ MIDE Y QUÉ NO MIDE:
Este indicador mide volumen de conversación social, no calidad del análisis ni dirección "correcta" del mercado. Una acción puede aparecer arriba en el ranking tanto por entusiasmo alcista genuino como por pánico, controversia, o simple curiosidad mediática.

CÓMO USARLO CON CRITERIO:
El sentimiento retail extremo (en cualquier dirección) ha demostrado históricamente ser, en ocasiones, un indicador contrario útil — picos de euforia social coincidiendo con techos locales, y picos de pánico social coincidiendo con suelos locales. No es una señal de entrada por sí sola, sino un dato de contexto sobre el sentimiento retail dominante en un momento dado.

Este tipo de actividad social ganó notoriedad especialmente desde el episodio de GameStop en enero de 2021, cuando el volumen de conversación en Reddit precedió movimientos de precio extraordinarios en varios tickers.`
    },

    "social-buzz": {
        title: "Buzz — Volumen de Conversación",
        short: "Medida relativa (0-100) de cuánta actividad social está generando un ticker en este momento.",
        long: `El "Buzz" es una puntuación relativa de 0 a 100 que refleja el volumen de menciones y conversación que un ticker está generando en las fuentes sociales rastreadas, comparado con el resto de tickers del ranking en ese mismo momento.

NO ES UN INDICADOR DE DIRECCIÓN:
Un Buzz alto solo indica que se está hablando mucho de ese ticker — no indica si la conversación dominante es alcista o bajista. Para eso está la columna de Señal, que sí intenta capturar el tono del sentimiento.

CÓMO LEERLO:
Picos repentinos de Buzz en un ticker que normalmente no aparece en el ranking suelen coincidir con alguna noticia, catalizador, o movimiento de precio reciente que ha captado la atención retail — vale la pena investigar qué lo está causando antes de actuar.`
    },

    "social-signal": {
        title: "Señal — Tono del Sentimiento Social",
        short: "Clasificación cualitativa del tono dominante (alcista, bajista, mixto) en la conversación sobre ese ticker.",
        long: `La columna de Señal resume, de forma simplificada, si el tono general de la conversación social sobre un ticker se inclina alcista, bajista, o está mixto/dividido en un momento dado.

LIMITACIONES A TENER EN CUENTA:
La clasificación de tono en redes sociales es inherentemente imperfecta — el sarcasmo, el humor interno de ciertas comunidades, y la jerga específica de foros como r/wallstreetbets pueden generar lecturas que no siempre capturan el matiz real de la conversación.

CÓMO INTEGRARLO EN EL ANÁLISIS:
Esta señal funciona mejor como una pieza adicional de contexto sobre el sentimiento retail, combinada con el resto de herramientas de la terminal (estructura técnica, fundamentales, flujo institucional), no como una señal aislada para tomar decisiones de entrada o salida.`
    },

    "economic-calendar": {
        title: "Calendario Económico",
        short: "Próximos eventos macroeconómicos relevantes de la semana, con su nivel de impacto esperado.",
        long: `El Calendario Económico recoge las publicaciones de datos macro y eventos de política monetaria programados para la semana en curso, ordenados cronológicamente.

QUÉ INCLUYE TÍPICAMENTE:
Decisiones de tipos de interés, publicaciones de inflación (IPC, PCE), datos de empleo, PIB, índices de confianza del consumidor, y otros indicadores que el mercado sigue de cerca por su capacidad de mover precios en el corto plazo.

CÓMO USAR LAS COLUMNAS:
▸ Actual: el dato ya publicado (si el evento ya ocurrió)
▸ Previo: el dato del periodo anterior, para comparar la tendencia
▸ Estimado: la expectativa de consenso del mercado antes de la publicación

LA SORPRESA IMPORTA MÁS QUE EL DATO EN SÍ:
Los mercados suelen reaccionar más a la diferencia entre el dato Actual y el Estimado (la "sorpresa") que al valor absoluto del dato. Un dato "malo" pero mejor de lo esperado puede generar una reacción alcista, y viceversa.

Las horas mostradas están en horario de Madrid (CET/CEST) para facilitar la planificación.`
    },

    "event-impact": {
        title: "Nivel de Impacto del Evento",
        short: "Indicador visual (●●●/●●○/●○○) de cuánto puede mover los mercados cada publicación económica.",
        long: `Cada evento del calendario se clasifica en uno de tres niveles de impacto esperado sobre los mercados:

▸ ●●● ALTO (rojo): eventos con histórico de generar movimientos significativos y volátiles — decisiones de tipos de la Fed, IPC, informe de empleo (Nonfarm Payrolls).
▸ ●●○ MEDIO (ámbar): eventos relevantes pero con impacto históricamente más moderado o contenido a sectores específicos.
▸ ●○○ BAJO (gris): publicaciones de seguimiento rutinario, con impacto de mercado típicamente limitado salvo sorpresas importantes.

CÓMO USARLO PARA PLANIFICAR:
Antes de eventos de impacto Alto, muchos traders reducen tamaño de posición, evitan abrir nuevas operaciones justo antes de la publicación, o amplían stops para evitar ser expulsados por el ruido de volatilidad puntual que suele acompañar a estos datos.`
    },

    "shiller-cape": {
        title: "CAPE de Shiller",
        short: "P/E del S&P 500 ajustado por ciclo — precio dividido entre el beneficio medio real de los últimos 10 años. Mide si el mercado está caro o barato a largo plazo, no sirve para el corto plazo.",
        long: `El CAPE (Cyclically Adjusted P/E, también llamado Shiller P/E) es un ratio de valoración creado por el economista Robert Shiller (Premio Nobel 2013) para medir si el mercado americano está caro o barato en términos históricos.

LA DIFERENCIA CON UN P/E NORMAL:
Un P/E normal divide el precio entre el beneficio del último año — un solo año puede estar artificialmente alto (boom) o bajo (recesión), distorsionando la foto. El CAPE divide el precio entre el beneficio medio REAL (ajustado por inflación) de los últimos 10 años, suavizando un ciclo económico completo. Es más lento de reaccionar, pero más difícil de engañar por un trimestre puntual.

NIVELES CRÍTICOS (marcados en el gráfico):
▸ Por debajo de 15 → Barato en términos históricos.
▸ 15-25 → Rango normal (la mediana histórica desde 1871 está en torno a 17).
▸ 25-30 → Elevado (línea amarilla) — el mercado empieza a cotizar con prima frente a su media histórica.
▸ Por encima de 30 → Muy alto (línea roja) — nivel que ha coincidido con los picos previos a las caídas de 1929 (~33) y de la burbuja punto-com de 1999-2000 (superó 40).

LO QUE NO ES — MUY IMPORTANTE:
El CAPE NO es una señal de entrada o salida a corto plazo. Puede quedarse "caro" durante años sin que eso sirva para operar mañana — de hecho, en 2020-2025 el mercado estuvo casi todo el tiempo con el CAPE muy por encima de 30 y siguió subiendo. Es contexto de valoración a largo plazo (años, no días), útil para calibrar expectativas de rentabilidad futura, no para decidir el timing de una operación concreta.

FUENTE:
Fichero de datos público que el propio Robert Shiller publica y actualiza mensualmente (Yale University), con histórico mensual desde enero de 1871.`
    },

    "credit-spreads": {
        title: "Credit Spreads (OAS)",
        short: "Diferencial de rentabilidad entre bonos corporativos y bonos del Tesoro. Mide el riesgo de crédito. Los niveles críticos se marcan como líneas discontinuas en el propio gráfico.",
        long: `Los Credit Spreads miden cuánto extra de rentabilidad exigen los inversores por asumir riesgo crediticio corporativo vs la seguridad del bono del Tesoro americano.

HY OAS (High Yield Option-Adjusted Spread):
Diferencial de bonos basura (calificación BB o inferior) vs Tesoro — el indicador de estrés crediticio más seguido del mercado.
- < 3,5% → Complacencia. Compensación mínima por riesgo de impago, típico de fases tardías de ciclo alcista.
- 3,5-5% → Normal.
- 5-8% → Elevado (línea amarilla en el gráfico). Mercado empezando a descontar deterioro económico.
- > 8% → Alto (línea roja en el gráfico). Niveles que históricamente han coincidido o precedido recesión en EE.UU. de forma consistente desde los 90 — y también, paradójicamente, zona de oportunidad histórica en renta variable para quien tenga horizonte largo.

IG OAS (Investment Grade):
Diferencial de bonos de alta calidad (BBB o superior) vs Tesoro — mucho menos volátil que el HY, así que sus umbrales son distintos y bastante más bajos:
- < 1% → Complacencia (media histórica a 10 años ronda 1,3%, así que estar por debajo del 1% es una zona relativamente ajustada).
- 1-1,5% → Normal.
- 1,5-2,5% → Elevado (línea amarilla).
- > 2,5% → Alto (línea roja) — zona que se ha acercado a picos de estrés como el de la crisis del Covid en 2020 (~3,5%).

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

Un mercado sano tiene AD Line confirmando los máximos del índice.

FUENTE DE LOS DATOS:
La etiqueta junto al gráfico indica de dónde sale el recuento de avances/declives: [S&P 500 + RUSSELL 2000 REAL] usa ~2.480 valores (scan nocturno propio, las 500 grandes más las ~1.960 del Russell 2000 — pensado específicamente para detectar cuándo el rally del S&P 500 no tiene participación real de las empresas más pequeñas). [S&P 500 REAL] es la misma fuente pero solo con las 500 grandes (aparece si el Russell 2000 aún no se ha cargado). [NYSE REAL] usa ^ADV/^DEC de Yahoo, NYSE de verdad pero con datos que llevan tiempo siendo poco fiables. [PROXY SPY] es un sustituto sintético cuando ninguna fuente real está disponible. Sigue sin ser NYSE completo (~2.800 valores incluyendo ETFs, preferentes y ADRs) — deliberadamente, esa mezcla diluye la señal más de lo que aporta.`
    },

    "market-indices": {
        title: "Índices Principales",
        short: "S&P 500, Nasdaq 100, Dow Jones, Russell 2000 y VIX — la foto rápida del mercado americano.",
        long: `Este widget muestra los cinco índices/indicadores de referencia más seguidos del mercado americano, cada uno con un enfoque distinto:

▸ S&P 500 (SPX): las 500 mayores empresas cotizadas de EE.UU. El índice de referencia general del mercado.
▸ Nasdaq 100 (NDX): las 100 mayores empresas no financieras del Nasdaq, con fuerte sesgo tecnológico y de crecimiento.
▸ Dow Jones (DJI): 30 empresas industriales de gran capitalización. El índice más antiguo, aunque menos representativo por su reducido número de componentes.
▸ Russell 2000 (RUT): referencia de small caps — empresas de menor capitalización, más sensibles al ciclo económico doméstico.
▸ VIX: el "índice del miedo", mide la volatilidad implícita esperada del S&P 500. No es un índice de precio sino de expectativa de movimiento.

POR QUÉ MIRARLOS JUNTOS:
Comparar el comportamiento relativo entre ellos da contexto adicional — por ejemplo, si el Nasdaq lidera al alza mientras el Russell 2000 se queda atrás, sugiere un mercado impulsado por grandes tecnológicas más que por una recuperación económica amplia.`
    },

    "market-breadth": {
        title: "Amplitud de Mercado",
        short: "Salud interna del mercado: SMA50/200, Golden/Death Cross, RSI, McClellan real, % real del S&P 500 y Línea A/D.",
        long: `Amplitud de Mercado combina varios indicadores de amplitud y técnica del SPY para dar una lectura compuesta de la salud interna del mercado, más allá del precio del índice en sí.

COMPONENTES:
▸ SMA50/SMA200: medias móviles de referencia. Precio sobre ambas = tendencia alcista de fondo.
▸ Golden Cross / Death Cross: SMA50 cruzando por encima (Golden) o por debajo (Death) de la SMA200. Señal de cambio de régimen de medio-largo plazo.
▸ RSI(14): momentum de corto plazo. &gt;70 sobrecompra, &lt;30 sobreventa.
▸ Oscilador McClellan: calculado con datos reales de avance/declive del NYSE (^ADV/^DEC), no un proxy del propio índice.
▸ % del S&amp;P 500 sobre SMA50: calculado sobre las ~500 acciones del índice (scan nocturno), no una muestra de 11 ETFs sectoriales.
▸ Línea A/D: avance/declive acumulado del NYSE, con su gráfico histórico frente al SPY.

CÓMO LEERLO:
Si el SPY sube pero el % del S&P 500 sobre SMA50 cae o la Línea A/D diverge a la baja, el rally se está estrechando — señal de alerta. Cuantos más componentes confirmen la misma dirección, más sólida es la tendencia.`
    },

    "breadth-pct-sma50": {
        title: "% S&P 500 sobre SMA50",
        short: "Porcentaje de las ~500 acciones del S&P 500 que cotizan por encima de su media móvil de 50 sesiones. Amplitud real, no una muestra de ETFs.",
        long: `Este dato se calcula sobre el universo completo del scan nocturno de RSU Terminal (~500 tickers del S&P 500), comprobando para cada uno si el precio actual está por encima o por debajo de su propia SMA de 50 sesiones.

POR QUÉ IMPORTA:
Es la definición estándar de amplitud "% por encima de la media" — mide si la subida del índice está siendo respaldada por la mayoría de acciones o solo por un puñado de grandes valores.

LECTURA:
▸ &gt; 60%: participación amplia, tendencia alcista sana.
▸ 40-60%: zona mixta, sin sesgo claro.
▸ &lt; 40%: participación débil — el índice puede estar sostenido por pocos valores.

FUENTE Y FALLBACK:
El dato marcado [S&amp;P 500 REAL] viene del scan nocturno completo. Si ese scan aún no ha corrido (por ejemplo, justo tras un despliegue nuevo) o el Gist no está disponible, el widget cae automáticamente a un proxy basado en 11 ETFs sectoriales, marcado como [PROXY 11 ETFs] — una aproximación razonable pero con mucha menos resolución que el dato real.`
    },


    "new-high-52w": {
        title: "Máximos de 52 Semanas",
        short: "Tickers cuyo precio actual es el más alto de los últimos ~12 meses. Aproximación a ATH, no el máximo histórico real de toda la vida del activo.",
        long: `Este filtro marca los tickers cuyo precio de hoy es el máximo de toda la ventana de histórico que el Scanner tiene cargada (hasta 260 sesiones ≈ 52 semanas).

POR QUÉ NO ES UN ATH REAL:
Un ATH (All-Time High) real requeriría el histórico completo desde que cada empresa cotiza — algunas llevan más de 50 años en bolsa. El Scanner solo descarga 260 sesiones por ticker cada noche (necesario para RS/RVOL/Fase), así que "máximo de 52 semanas" es lo más parecido que se puede calcular sin añadir una descarga de histórico mucho más larga para las 500 acciones cada noche.

EN LA PRÁCTICA:
Para la inmensa mayoría de setups de ruptura que te interesan como trader (una acción rompiendo su rango del último año), esta aproximación es exactamente la señal que buscas — muy pocas veces el máximo real de 52 semanas y el máximo histórico real difieren en el momento de una ruptura genuina. La diferencia solo importa para valores muy antiguos que llevan años en tendencia bajista de muy largo plazo.`
    },

    "nh-nl": {
        title: "New Highs − New Lows (NH-NL)",
        short: "Nuevos máximos de 52 semanas menos nuevos mínimos, sobre S&P 500 + Russell 2000 real. Mide la calidad del liderazgo del mercado.",
        long: `NH-NL cuenta, sobre las ~2.480 acciones de S&P 500 + Russell 2000 (scan nocturno), cuántas están marcando un nuevo máximo de las últimas ~52 semanas frente a cuántas marcan un nuevo mínimo, y resta ambas cifras.

POR QUÉ IMPORTA:
A diferencia de la Línea A/D (que solo mira si sube o baja cada día) o el McClellan (que mira la aceleración), NH-NL mide la CALIDAD del liderazgo: cuántas acciones están realmente marcando terreno nuevo, no solo participando en el movimiento del día.

LA DIVERGENCIA CLÁSICA:
Si el índice sigue haciendo máximos pero NH-NL empieza a caer (cada vez menos acciones hacen nuevo máximo), es una señal de agotamiento del rally — el liderazgo se está estrechando aunque el precio del índice todavía no lo refleje. Es una de las divergencias de amplitud más citadas antes de techos de mercado importantes.

LECTURA:
▸ NH-NL muy positivo y creciente: liderazgo amplio y sano.
▸ NH-NL cayendo con el índice en máximos: divergencia de alerta.
▸ NH-NL muy negativo: presión bajista amplia, muchas acciones en mínimos de 52 semanas a la vez.`
    },


    "mcclellan-oscillator": {
        title: "Oscilador McClellan",
        short: "Mide la aceleración de la amplitud real del mercado (EMA19-EMA39 sobre avance/declive neto del propio S&P 500). Extremos anticipan giros de corto plazo.",
        long: `El Oscilador McClellan es un indicador de amplitud que mide la diferencia entre dos medias exponenciales del avance/declive neto diario — cuántas acciones del S&P 500 suben menos cuántas bajan cada día, no el precio de un índice.

CÁLCULO Y FUENTE:
EMA(19) − EMA(39) del avance/declive neto diario, calculado directamente sobre el histórico de precios de las ~2.480 acciones (S&P 500 + Russell 2000) que ya descarga el Scanner cada noche — no depende de tickers compuestos externos (como ^ADV/^DEC de Yahoo, que llevan tiempo dando datos poco fiables). Ampliar más allá del S&P 500 fue deliberado: captura mejor los momentos en que solo las megacaps sostienen el rally mientras el resto del mercado ya está débil. Si el Scanner todavía no tiene suficiente histórico acumulado (hacen falta 40+ sesiones), se muestra como [PROXY SPY] usando una fuente de respaldo en vez de un dato a medias.

VARIACIÓN SEMANAL:
Junto al valor actual se muestra la variación frente a hace ~5 sesiones (una semana de mercado) — útil para ver si la amplitud se está acelerando o frenando, no solo su nivel absoluto en este momento.

INTERPRETACIÓN:
▸ &gt; +70: sobrecompra de amplitud — el mercado puede estar extendido a corto plazo.
▸ Entre -70 y +70: zona neutra, sin señal direccional clara.
▸ &lt; -70: sobreventa de amplitud — posible zona de rebote técnico.

DIFERENCIA CON EL RSI:
El RSI mide momentum de PRECIO de un solo activo. El McClellan mide momentum de PARTICIPACIÓN — cuántas acciones están detrás del movimiento. Un McClellan muy negativo con precio estable puede anticipar un rebote técnico de corto plazo aunque el contexto de fondo siga siendo bajista.`
    },

    "abi-absolute-breadth": {
        title: "Absolute Breadth Index (ABI)",
        short: "Mide cuánta dispersión/actividad hay en el mercado, sin decir hacia dónde — |avances-declives| sobre el total. Lecturas extremas suelen coincidir con capitulación o cambios de régimen.",
        long: `El Absolute Breadth Index (ABI), creado por Norman Fosback, es distinto a casi todos los demás indicadores de amplitud: NO es direccional. No dice si el mercado va a subir o bajar — dice cuánto está pasando internamente, sea cual sea el sentido.

CÁLCULO:
ABI = |avances − declives| / (avances + declives) × 100, usando el mismo recuento real de las ~2.480 acciones (S&P 500 + Russell 2000) que ya calcula el Scanner cada noche (el mismo dato que alimenta el McClellan real y la Línea A/D de aquí arriba).

CÓMO LEERLO:
▸ ABI alto (≥40%): mucha dispersión — un número inusualmente grande de acciones moviéndose con fuerza, sean cuales sean. Suele coincidir con capitulación, pánico vendedor o el arranque de un cambio de régimen — no con un día tranquilo.
▸ ABI bajo (≤15%): mercado apagado, sin convicción clara en ningún sentido — ni fuerte presión compradora ni vendedora.
▸ Fosback documentó en su investigación original que lecturas extremas de ABI han tendido a preceder subidas de precio en horizontes de 3 a 12 meses — no como señal de entrada inmediata, sino como contexto de que "algo se está moviendo" que merece la pena vigilar.

POR QUÉ NO ES REDUNDANTE CON EL McCLELLAN:
El McClellan de arriba es direccional (positivo = más avances, negativo = más declives). El ABI ignora esa dirección a propósito — un día con 400 acciones subiendo y 100 bajando da un ABI parecido a un día con 400 bajando y 100 subiendo. Son complementarios: el McClellan dice "hacia dónde", el ABI dice "con cuánta fuerza/dispersión", independientemente del sentido.`
    },

    // ── OPTIONS FLOW ──────────────────────────────────────────────────────────
    "options-flow": {
        title: "Options Flow — Flujo de Opciones",
        short: "Registro de operaciones inusuales en opciones. Prima alta + Vol/OI elevado = posible posicionamiento institucional.",
        long: `El flujo de opciones inusual rastrea operaciones donde el volumen y la prima pagada superan significativamente lo habitual para ese contrato.

POR QUÉ IMPORTA:
Las instituciones no pueden ocultar sus operaciones en opciones. Cuando alguien paga $3M en calls de HOOD a 60 días, eso deja huella en el volumen — y nosotros la vemos.

LO QUE BUSCAMOS (actualizado tras el ajuste de criterios de 14/07/2026):
▸ Volumen mínimo 200 contratos y Open Interest mínimo 100 → filtra contratos ilíquidos donde cualquier ratio es ruido, no señal
▸ Vol/OI ratio alto (≥2x) → posición completamente nueva, no ajuste de una posición existente
▸ Prima MUY POR ENCIMA de la media propia del ticker (cuando hay 5+ días de histórico guardado) → un trade de $500K en una small-cap no es lo mismo que en NVDA, así que se compara cada ticker contra sí mismo, no contra un umbral fijo igual para todos. Sin histórico suficiente todavía, cae a un umbral absoluto (>$100K) como red de seguridad
▸ IV en percentil alto DENTRO del histórico propio del ticker (mismo criterio que la prima) — 60% de IV es raro en una utility y rutinario en una biotecnológica
▸ Strike OTM 5-25% → el sweet spot táctico institucional
▸ Vencimiento 14-60 días → timing direccional, no especulativo

ICONOS EN CADA ENTRADA:
📅 = el vencimiento cae cerca de la próxima fecha de earnings — contexto, no necesariamente más "inusual" (el volumen sube de forma rutinaria antes de resultados en casi cualquier ticker)
💼 = ya tienes esa acción en posición abierta en Cartera
🔁 = el mismo contrato exacto (ticker+strike+vencimiento+tipo) ya apareció en un día de escaneo anterior — actividad repetida en la misma dirección es una señal más fuerte que una entrada puntual de un solo día

LIMITACIÓN IMPORTANTE:
Estos datos son EOD (end of day) — del cierre del día anterior. Para opciones a corto plazo (0-5 días) el retraso importa mucho. Para posiciones a semanas o meses, el retraso es irrelevante — la señal sigue siendo válida.

NO ES TIEMPO REAL, Y ESO ES A PROPÓSITO:
El escaneo corre 1 vez al día (no continuamente) y cada resultado se guarda de forma permanente en base de datos — por eso puedes buscar un ticker y ver su histórico de semanas o meses, no solo el día de hoy. La "fecha" que ves en cada entrada es el día en que el escaneo detectó la señal, no el instante exacto de la operación.`
    },

    "options-categories": {
        title: "Calls Bought / Puts Sold / Puts Bought / Calls Sold",
        short: "Las 4 categorías de flujo — las dos primeras son alcistas, las dos últimas bajistas. Buy/Sell se infiere del volumen frente al Open Interest, no es un dato directo.",
        long: `Cada entrada de opciones se clasifica en una de estas 4 categorías, combinando el tipo de contrato (call/put) con si es apertura de posición nueva (buy) o cierre/venta (sell):

▸ CALLS BOUGHT (alcista): alguien compra calls — apuesta a que el precio suba.
▸ PUTS SOLD (alcista): alguien vende puts — apuesta a que el precio NO caiga por debajo del strike (cobra la prima sin obligación si el precio se mantiene).
▸ PUTS BOUGHT (bajista): alguien compra puts — apuesta a que el precio baje, o cobertura de una posición larga.
▸ CALLS SOLD (bajista): alguien vende calls — apuesta a que el precio no suba por encima del strike.

CÓMO SE INFIERE BUY VS SELL:
yfinance no dice directamente "esto fue una compra" o "esto fue una venta" — se infiere comparando el volumen negociado hoy contra el Open Interest ya existente (Vol/OI ≥ 0.3 sugiere posición nueva = compra). Es una aproximación razonable, no una certeza absoluta — así funciona cualquier herramienta de flujo de opciones basada en datos públicos, no solo esta.`
    },

    "options-large-oi": {
        title: "Large OI Increase / Decrease",
        short: "Contratos donde el Open Interest cambió mucho de un día al siguiente — sube o baja más del 1%. Necesita al menos 2 días de histórico guardado para poder compararse.",
        long: `Compara el Open Interest (contratos abiertos) de cada contrato HOY contra el mismo contrato AYER (mismo ticker, strike, vencimiento y tipo).

POR QUÉ IMPORTA:
Un aumento grande de OI en un contrato concreto significa que se están abriendo muchas posiciones NUEVAS en ese strike/vencimiento exacto — más señal de convicción que un simple pico de volumen de un solo día, porque implica que la posición se mantiene, no que se cerró en el mismo día.

LIMITACIÓN:
Solo puede calcularse a partir del segundo día de escaneo guardado — con un único día de histórico no hay nada contra lo que comparar, y esta sección aparecerá vacía hasta entonces.`
    },

    "options-net-score": {
        title: "Net Score",
        short: "Recuento simple: +1 por cada entrada alcista (Buy Call / Sell Put) del periodo, -1 por cada bajista (Buy Put / Sell Call). No pondera por prima.",
        long: `El Net Score de un ticker es la suma de todas sus entradas guardadas en el periodo seleccionado (1 semana a 4 meses): +1 si la entrada es alcista (Buy Call o Sell Put), -1 si es bajista (Buy Put o Sell Call).

DELIBERADAMENTE SIMPLE:
Es un recuento, no una media ponderada por prima — dos entradas alcistas de $200K pesan lo mismo que una de $5M. Esto es intencional para mantener la sección legible de un vistazo; si necesitas ver el tamaño real de cada operación, la prima de cada entrada está en la tabla justo debajo.`
    },

    "options-dia-bias": {
        title: "Sesgo del día",
        short: "% de la prima total del último escaneo que es alcista (Calls Bought + Puts Sold) frente a bajista (Puts Bought + Calls Sold). Un único número, sin gráficos.",
        long: `Suma toda la prima de las 4 categorías del último escaneo guardado y calcula qué proporción es alcista:

ALCISTA = Calls Bought + Puts Sold
BAJISTA = Puts Bought + Calls Sold

Sesgo % = prima alcista / (prima alcista + prima bajista) × 100

INTERPRETACIÓN:
▸ ≥60% → ALCISTA
▸ ≤40% → BAJISTA
▸ Entre ambos → NEUTRAL

QUÉ NO ES:
No es un indicador de todo el mercado, es la agregación de los ~570 tickers de vuestra propia watchlist de escaneo — un día con mucha actividad concentrada en 2-3 tickers grandes puede mover este número igual que un día con actividad repartida entre 50 tickers. Sirve como contexto rápido de apertura, no como señal por sí sola.`
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
        short: "Sistema multi-factor que detecta condiciones de fondo de mercado. Score 0-100. No busca el mínimo exacto, busca el punto de empezar a construir posición.",
        long: `FILOSOFÍA — LEER ESTO PRIMERO:
Este sistema NO intenta acertar el mínimo exacto — nadie lo hace de forma consistente. El objetivo es distinto: detectar el momento en que ya hay evidencia suficiente para EMPEZAR a construir posición de forma gradual, con gestión de riesgo (stop, tramos), no de una sola vez.

Por eso el semáforo se usa así:
▸ VERDE → arranca la construcción de posición (primer tramo, ~25%, con stop). No es "aquí está el suelo", es "aquí ya compensa empezar a entrar".
▸ ÁMBAR → fase de watchlist, no de entrada. El trabajo en ámbar es tener claros y priorizados los candidatos de interés, para no improvisar si llega el VERDE.
▸ ROJO → sin condiciones de fondo. Preservar capital y esperar.

El propio backtest existe justamente para esto — antes de fiarte de la filosofía "construir gradualmente", pulsa el botón de Backtest y mira la ventaja real por horizonte (5/10/20/60 días) en el histórico actual. Esa ventaja puede cambiar con el tiempo y con mejoras al algoritmo (ya ha pasado: un bug en el proxy de McClellan hacía que ese factor no aportara nunca, y arreglarlo cambió sustancialmente los resultados) — por eso esta guía no fija un número concreto aquí, consulta siempre el backtest en vivo.

LOS 6 FACTORES DEL SCORE (0-100):

1. RSI SOBREVENDIDO — DIARIO + SEMANAL (18pts)
RSI(14) mínimo reciente en ambas temporalidades. Mide agotamiento del momentum vendedor.

2. VIX — SPIKE DE MIEDO + CURVA VIX/VIX3M (22pts)
Pico de volatilidad reciente, más la curva de futuros VIX/VIX3M. La curva en backwardation (VIX de corto por encima del de medio plazo) es señal de capitulación real, no un motivo de exclusión.

3. McCLELLAN — AMPLITUD DE MERCADO (18pts)
En el cálculo EN VIVO, usa amplitud real de las ~2.480 acciones de S&P 500 + Russell 2000 (el mismo dato que ya calcula el Scanner cada noche, ver Amplitud de Mercado en la página de Mercado) cuando hay suficiente histórico acumulado. Si no, cae al proxy basado en el percentil móvil (últimos ~2 años) del diferencial de momentum de SPY — se auto-calibra a cualquier régimen de volatilidad en vez de usar una escala absoluta fija. El backtest de 20 años siempre usa el proxy (no hay 20 años de amplitud real de las 500 acciones guardados). Valores muy negativos sugieren sobreventa generalizada.

ABI — ABSOLUTE BREADTH INDEX (contexto, no puntúa):
Se muestra junto a los gatekeepers cuando hay amplitud real disponible. A diferencia del McClellan, el ABI no dice hacia dónde va el mercado — mide cuánta dispersión/actividad interna hay, sea cual sea el sentido. Lecturas altas (≥40%) suelen coincidir con capitulación o cambios de régimen. Solo disponible en vivo, por la misma razón que el McClellan real — ver el tooltip del ABI en la página de Mercado para más detalle.

4. VOLUMEN — CONFIRMACIÓN (12pts)
Volumen elevado como evidencia de convicción institucional real detrás del movimiento.

5. EMA200 SEMANAL (20pts)
Precio dentro de un margen razonable de la media de largo plazo — contexto de que no está excesivamente extendido.

6. RÉGIMEN SMA200 (umbral, no puntúa)
Sobre la SMA200 diaria = régimen alcista de fondo (listón de VERDE más bajo, 60/100). Bajo la SMA200 = régimen bajista (listón sube a 70/100, más exigente). No suma puntos aparte al score — antes sí lo hacía, pero eso significaba que "estar sobre la SMA200" contaba dos veces a favor de lo mismo (los puntos Y el listón más bajo). Ahora solo cumple su función original: decidir el umbral.

GATEKEEPERS — el filtro que evita falsos verdes:
Un score alto por sí solo NO enciende VERDE. Hace falta además al menos una condición estructural real: precio cerca de la EMA200 semanal, o RVOL extremo en el día del mínimo. El Follow-Through Day (FTD) ya no puntúa como factor del score — actúa como confirmación posterior: si llega, refuerza la convicción del VERDE, pero su ausencia no bloquea la señal (solo indica vigilar los próximos días).

FILTRO DE ESTRÉS DE CRÉDITO (BAA10Y):
Añadido tras revisar el backtest de 2008: las señales de sep-oct 2008 (ya con el crédito roto, post-Lehman) fueron las peores de toda la muestra, mientras que las de ene-jul 2008 (crisis en curso pero crédito aún no en pánico sistémico) funcionaron razonablemente. Se probó primero con el HY OAS de ICE BofA, pero FRED solo distribuye programáticamente los últimos ~3 años de esa serie por licencia (aunque su gráfico web muestre más) — así que se usa BAA10Y (diferencial entre el bono corporativo Baa de Moody's y el Treasury a 10 años), que mide el mismo tipo de estrés de crédito con histórico público completo desde 1986. Si está "elevado" (≥3%) se añade un aviso, sin más — SALVO que además esté empeorando (subiendo en los últimos 10 días), en cuyo caso se trata igual que "crítico". Si está en nivel "crítico" (≥4%), cualquier VERDE se degrada automáticamente a VERDE-VOL (entrada muy reducida) — pero deliberadamente NO se bloquea del todo, porque los suelos reales de 2008-09 y COVID ocurrieron con el spread todavía cerca de su pico.

Por qué importa la tendencia y no solo el nivel: confirmado con el propio backtest, dos señales "elevado" en sep-2008 (crédito rompiéndose activamente) fueron un desastre (-18% a -26% a 60d), mientras que otras igual de "elevado" pero con el crédito ya sanando (jul-2009, sep-2011, tras la fase aguda de sus crisis) fueron excelentes (+12% a +20%). Bloquear TODO "elevado" sin distinguir mejoraba las cifras agregadas del backtest, pero a costa de descartar esas recuperaciones reales — de ahí el filtro de tendencia en vez de un corte plano por nivel.

IMPORTANTE: este es un sistema de heurísticas de análisis técnico clásico, no una estrategia con ventaja estadística garantizada. Usa el botón de Backtest para ver cómo se ha comportado realmente sobre 10 años de histórico de SPY antes de darle un peso desproporcionado en tus decisiones.`
    },

    "algoritmo-historial-real": {
        title: "Señales Reales (en vivo)",
        short: "Señales disparadas desde que se activó el seguimiento, con su resultado real — distinto del backtest, que reanaliza histórico ya conocido.",
        long: `POR QUÉ EXISTE ESTO, APARTE DEL BACKTEST:
El backtest de arriba reanaliza el mismo histórico fijo de 20 años una y otra vez. Cada mejora al algoritmo viene de mirar mejor esos mismos datos — no de datos genuinamente nuevos. Eso es útil para depurar bugs, pero tiene un límite: nunca puede decirte con certeza si un ajuste concreto va a funcionar en el futuro, solo si habría funcionado en el pasado que ya conocemos.

Este panel es la otra pata: cada vez que el semáforo cambia de estado, queda registrado — y si es un VERDE o VERDE-VOL, se guarda su desglose completo de factores. 5, 10, 20 y 60 días después, se rellena automáticamente qué pasó de verdad con SPY desde ese momento.

Con el tiempo (meses, años), esto construye un historial de resultados que nadie pudo ver de antemano al diseñar las reglas — la validación más honesta posible de si el algoritmo funciona, sin el riesgo de sobreajuste que tiene cualquier backtest sobre datos ya conocidos.

Empieza vacío. Es normal y esperado — se irá llenando solo, sin que haga falta hacer nada.`
    },

    "algoritmo-gatekeepers": {
        title: "Gatekeepers",
        short: "Condiciones estructurales que deben cumplirse para que el algoritmo pueda encender VERDE, aunque el score ya sea alto.",
        long: `Un score alto por sí solo no enciende el semáforo en VERDE — hace falta que, además, se cumpla al menos uno de los "gatekeepers" (condiciones de guardia):

▸ Cerca de la EMA200 semanal — el precio está dentro de un margen razonable de la media de largo plazo, no muy extendido.
▸ RVOL extremo en el mínimo — el volumen del día del mínimo de precio fue anormalmente alto, señal de capitulación real, no de un mínimo silencioso.
▸ FTD confirmado — Follow-Through Day, una sesión de fuerza posterior al mínimo que confirma que la reversión tiene volumen detrás, no es solo un rebote técnico.

POR QUÉ EXISTEN:
Sin estos filtros, un score alto podría encenderse simplemente porque varios indicadores de momentum coinciden en un rebote débil, sin que haya ninguna evidencia estructural de que sea un giro real. Los gatekeepers son la diferencia entre "los números dicen que esto pinta bien" y "hay señales de que dinero grande está actuando", que es justo la misma filosofía que verás en el Módulo 22 de la Academia (El Triángulo RSU) aplicada aquí a la detección de fondos de mercado.

También verás el Drawdown de 52 semanas junto a los gatekeepers — no es un gatekeeper en sí, es contexto: cuanto mayor la caída previa, más significativo es que se cumplan estas condiciones de giro.

BAA10Y (diferencial de crédito corporativo Baa vs Treasury 10y) también aparece aquí, pero funciona al revés que los demás: los gatekeepers de arriba son permisivos (basta con que se cumpla UNO). El BAA10Y es un filtro de cautela — si está en nivel crítico (≥4%), degrada un VERDE que de otro modo sería pleno a VERDE-VOL, porque señala que el problema puede ser de crédito real, no solo de precio de las acciones (ver tooltip principal del algoritmo para el porqué, con el ejemplo real de 2008).`
    },

    "algoritmo-importancia": {
        title: "Importancia de Variables",
        short: "Correlación histórica entre cada factor del algoritmo y el retorno real a 20 días — para ver qué variables aportan señal de verdad y cuáles son ruido.",
        long: `Esta tabla responde a una pregunta distinta a la del backtest general: de los 6 factores que componen el score (RSI, VIX, McClellan, RVOL en mínimo, EMA200 semanal, régimen SMA200), ¿cuáles han pesado de verdad en el resultado y cuáles apenas han importado?

CÓMO SE CALCULA:
Para cada factor, se ordenan las señales históricas por el valor de ESE factor concreto y se dividen en dos grupos para comparar su retorno medio a 20 días. Factores discretos con pocos valores posibles (p.ej. Régimen SMA200, que solo vale 0 o 10) se agrupan por su valor real ("alto" = valor máximo observado, "bajo" = el resto); factores con variación más continua (RSI, VIX, RVOL) se dividen por ranking (mitad superior vs inferior). Si un factor con score alto obtuvo sistemáticamente mejor retorno que con score bajo, ese factor tiene correlación real con el resultado.

LA COLUMNA "CORR":
Correlación entre el valor del factor y el retorno a 20 días — más cercana a +1 indica que ese factor anticipa bien subidas, cercana a 0 indica que no aporta señal por sí solo, y cercana a -1 indica que el factor se ha correlacionado con RETORNOS PEORES en esta muestra (vale la pena vigilarlo, aunque con pocas señales puede ser ruido).

SIN VARIACIÓN:
Si un factor tuvo exactamente el mismo valor en TODAS las señales de la muestra (p.ej. si siempre estuvo al máximo), no hay nada que comparar — se marca como "sin variación" en vez de forzar un split artificial.

MUESTRA PEQUEÑA:
Con menos de 2 señales en algún grupo (alto o bajo), la comparación no es estadísticamente fiable y se marca explícitamente — no la trates como concluyente si ves ese aviso.

INESTABILIDAD CONOCIDA — NO REPONDERAR SOBRE UN SOLO SNAPSHOT:
Estas correlaciones pueden cambiar de signo por completo entre una corrida del backtest y otra, simplemente porque cambia qué señales entran en la muestra (ej. arreglar un bug que añade más señales de 2008 cambia la composición, no el mercado). Ya ha pasado: RSI, RVOL en mínimo y Régimen SMA200 invirtieron su signo entre dos corridas del mismo algoritmo. Trata estos números como diagnóstico exploratorio, no como base para tocar pesos del score — hace falta que un factor se mantenga estable en su signo a través de varias corridas y ventanas temporales distintas antes de considerar recalibrarlo.

REQUISITO MÍNIMO:
Hacen falta al menos 8 señales históricas con retorno ya calculado (necesitan 60 días desde que se dispararon para tener el dato a 60d) para que este análisis tenga sentido mínimo — con menos, se muestra un aviso en vez de forzar una conclusión sobre una muestra demasiado pequeña.`
    },

    "algoritmo-backtest": {
        title: "Backtest del Algoritmo",
        short: "Recalcula el algoritmo día a día sobre 10 años de histórico de SPY y compara contra el rendimiento base del índice.",
        long: `Este backtest responde a la pregunta más importante sobre cualquier indicador: ¿aporta una ventaja real, o es ruido que parece útil en retrospectiva?

METODOLOGÍA:
- Se recalcula el score exacto del algoritmo (la misma lógica que ves en vivo) para cada día de los últimos 10 años de SPY.
- Una "señal" se registra cuando el semáforo se enciende en VERDE puro (score sobre umbral dinámico 60/70 + gatekeeper estructural cumplido + volumen o cercanía a EMA200 semanal) tras no estarlo el día anterior — el momento exacto de encendido, no cada día que permanece encendido.
- Para cada señal, se mide el retorno real de SPY en los siguientes 5, 10, 20 y 60 días de trading.

LA COMPARACIÓN CLAVE — BASELINE:
El "Baseline SPY" es el retorno medio que habría dado SPY en esos mismos horizontes calculado sobre TODOS los días del periodo, no solo los días de señal. Esta es la comparación honesta: si el retorno medio tras una señal VERDE no supera claramente al baseline, el algoritmo no está aportando ventaja real sobre estar simplemente invertido siempre — solo está coincidiendo con un mercado que en general tiende a subir con el tiempo.

LIMITACIÓN CONOCIDA:
El McClellan Oscillator se calcula con el proxy basado en SPY de forma consistente en todo el periodo (no datos sectoriales reales), ya que recalcular 9 ETFs sectoriales en miles de días históricos sería excesivamente costoso. Esto hace que el backtest sea fiel al comportamiento real del sistema en producción cuando los datos sectoriales no están disponibles, pero no representa el McClellan "ideal" con amplitud real de mercado.

"N SEÑALES" VS "EPISODIOS":
Varias señales seguidas (a pocos días de trading entre sí) suelen corresponder al mismo evento de mercado, no a pruebas independientes — p.ej. 4 señales en 2 semanas durante un mismo crash cuentan como 1 episodio real, no 4. Por eso se muestra también el número de episodios independientes (señales agrupadas cuando caen a ≤15 días de trading de la anterior): es la medida más honesta del tamaño de muestra real. Amplía el rango a 15-20 años para incluir más episodios genuinamente distintos (2008, 2011, 2015, 2018) antes de sacar conclusiones fuertes sobre pesos o umbrales.

Un número de episodios bajo (algo esperable, ya que un fondo de mercado real no ocurre con frecuencia) limita la significancia estadística de las conclusiones — interpreta los resultados con esa cautela.`
    },

    "ftd": {
        title: "Follow Through Day (FTD)",
        short: "Día de rally en alto volumen que confirma el inicio de una nueva tendencia alcista.",
        long: `El Follow Through Day es el concepto más importante de la metodología IBD (Investor's Business Daily) de William O'Neil.

DEFINICIÓN:
Un día en que un índice principal (SPX, Nasdaq) sube ≥1.7% en volumen mayor al día anterior, ocurriendo entre el día 4 y 10 de un intento de rally desde un mínimo.

POR QUÉ FUNCIONA:
Tras una corrección, el mercado necesita confirmar que hay demanda institucional real. Los grandes fondos no pueden disimular sus compras — dejan huella en el volumen. El FTD es esa huella.

ESTADÍSTICAS HISTÓRICAS — IMPORTANTE LEER:
IBD afirma públicamente una tasa de éxito del 70-80% para los FTDs. Sin embargo, estudios cuantitativos independientes que reprodujeron la metodología con los criterios más generosos posibles encontraron una tasa real de éxito de aproximadamente 55% desde 1971 — apenas mejor que el azar en términos de predicción aislada.

Esto no invalida el concepto (sigue siendo uno de los pilares más estudiados del análisis técnico de mercado), pero sí significa que un FTD por sí solo es una señal de probabilidad moderadamente favorable, no una confirmación fuerte. Combinarlo con otros factores (volumen, contexto de tendencia, amplitud) — como hace el RSU Algoritmo — es más razonable que confiar en el FTD de forma aislada.

ADVERTENCIAS:
- FTD bajo la EMA21 → posible trampa alcista
- FTD en volumen solo moderado → menos convicción
- Múltiples FTDs fallidos seguidos → mercado muy débil

Sin FTD, no hay confirmación de fondo. Con FTD, aumenta la probabilidad, pero no la garantiza.`
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

    "ibd-composite": {
        title: "IBD Composite Rating",
        short: "Rating combinado de 1 a 99 que resume RS Rating, EPS Rating, SMR y Acc/Dis en una sola cifra.",
        long: `El Composite Rating de IBD combina en una sola métrica los principales ratings individuales que IBD calcula para cada acción:

▸ RS Rating (fuerza relativa de precio vs el mercado)
▸ EPS Rating (calidad y consistencia del crecimiento de beneficios)
▸ SMR Rating (ventas, margen y retorno sobre capital)
▸ Acc/Dis Rating (acumulación o distribución institucional reciente)

ESCALA:
Va de 1 a 99, igual que el RS Rating. Cuanto más alto, mejor se posiciona la acción frente al resto del universo en el conjunto de estos factores combinados.

CÓMO USARLO:
Un Composite alto (90+) sugiere que la acción destaca de forma consistente en varios frentes a la vez, no solo en uno. Es un filtro rápido para descartar candidatos antes de revisar el detalle de cada rating individual.

No sustituye al análisis del setup técnico ni del contexto de mercado — es un filtro de calidad fundamental-técnica combinada, no una señal de entrada por sí sola.`
    },

    "canslim-i": {
        title: "I — Institutional Sponsorship",
        short: "El factor 'I' de CAN SLIM: porcentaje de la acción en manos de fondos e instituciones de calidad.",
        long: `La "I" de CAN SLIM representa el respaldo institucional — qué proporción de las acciones en circulación está en manos de fondos de inversión, gestoras y otros inversores institucionales.

POR QUÉ IMPORTA:
Las instituciones mueven el volumen suficiente para sostener tendencias duraderas. Una acción con poco o nulo respaldo institucional puede subir, pero suele carecer del combustible necesario para sostener un movimiento de varios meses.

EL EQUILIBRIO CORRECTO:
▸ Demasiado bajo → falta de demanda institucional real detrás del movimiento
▸ Demasiado alto (sobre-poseída) → poco margen para nuevas compras institucionales que empujen el precio, y mayor riesgo de ventas masivas si el sentimiento cambia

QUÉ BUSCAR:
O'Neil recomendaba buscar acciones con un número creciente de fondos de calidad acumulando posición trimestre a trimestre — no necesariamente el porcentaje más alto posible, sino una tendencia de acumulación reciente y de gestoras con buen histórico.`
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

LAS MEJORES ACCIONES tienen RS > 90 y la línea de RS marcando máximos históricos justo antes de la gran ruptura.

NOTA: este concepto se usa en varios módulos de la terminal (CANSLIM, Scanner, RS/RW) — el percentil final es comparable, pero cada módulo calcula el rendimiento subyacente con su propia combinación de ventanas temporales. Para el detalle exacto de RS/RW, consulta su propio tooltip.`
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
    "relative-strength": {
        title: "Fuerza Relativa vs SPY y vs Sector",
        short: "Compara el rendimiento del activo contra el S&P 500 (SPY) y contra el ETF de su propio sector, en 1, 3 y 6 meses ponderados.",
        long: `Esta métrica responde a una pregunta distinta de la tendencia técnica: no "¿está subiendo el precio?", sino "¿está subiendo MÁS o MENOS que el mercado y que su propio sector?". Una acción puede estar en tendencia alcista (Fase 2) y aun así tener fuerza relativa débil si el resto del mercado sube todavía más rápido.

METODOLOGÍA — MISMA LÓGICA QUE EL MÓDULO RS/RW SCANNER:
Se calcula el rendimiento del activo, del SPY (proxy del S&P 500) y de un ETF de referencia sectorial, en 3 marcos temporales: 1 mes (21 sesiones), 3 meses (63 sesiones) y 6 meses (126 sesiones).

QUÉ ETF SE USA COMO REFERENCIA — INDUSTRIA ANTES QUE SECTOR:
El sector GICS (ej. "Industrials") agrupa negocios muy distintos entre sí — desde aeroespacial/defensa hasta maquinaria pesada o transporte — por lo que comparar una empresa de defensa contra el ETF de todo el sector Industrial (XLI) diluye la comparación. Por eso, cuando la industria específica del ticker tiene un ETF más preciso disponible (ej. Aerospace & Defense → ITA, Semiconductors → SOXX, Biotechnology → IBB), se usa ese en vez del ETF de sector genérico. La badge indica "INDUSTRIA" o "SECTOR" según cuál se haya usado, y debajo aparece el nombre de la industria/sector concreto.

PONDERACIÓN:
▸ 1 mes → 50% del peso (más reciente, más relevante para el momentum actual)
▸ 3 meses → 30% del peso
▸ 6 meses → 20% del peso

CÁLCULO:
Fuerza Relativa = rendimiento del activo − rendimiento del benchmark (SPY o ETF sectorial), en cada periodo, luego promediado con los pesos anteriores. El resultado se expresa en puntos porcentuales (pp) de diferencia.

NIVELES:
▸ &gt; +5pp → FUERTE → El activo lidera claramente sobre el benchmark
▸ +1.5 a +5pp → LIGERAMENTE FUERTE
▸ -1.5 a +1.5pp → NEUTRAL → Se mueve prácticamente igual que el benchmark
▸ -5 a -1.5pp → LIGERAMENTE DÉBIL
▸ &lt; -5pp → DÉBIL → El activo está rezagado claramente frente al benchmark

POR QUÉ DOS COMPARACIONES (SPY Y SECTOR) EN VEZ DE UNA:
Un activo puede ganarle al mercado general simplemente porque todo su sector está en racha (ej. todo el sector Energy sube por una subida del petróleo) sin que la empresa concreta esté haciendo nada especial dentro de su propio grupo — eso lo revela la comparación vs sector. Y al revés: un activo puede perderle a su sector pero seguir ganándole al mercado general, lo cual sigue siendo una señal relativamente positiva. Las dos lecturas juntas dan más contexto que cualquiera de las dos por separado.

RELACIÓN CON EL MÓDULO RS/RW SCANNER:
Este cálculo usa la misma filosofía de ponderación por periodos que el RS/RW Scanner de la terminal, pero aplicada de forma puntual a un solo ticker dentro de Research, en vez de rankear todo el universo de ~500 acciones. Si quieres ver cómo se posiciona este ticker frente a TODO el mercado en percentil (no solo frente a SPY/sector), el RS/RW Scanner es la herramienta más completa para eso.

LIMITACIÓN:
Esta fuerza relativa es de precio puro — no incorpora volumen, amplitud ni el RS Rating oficial estilo IBD. Es un proxy rápido y útil, no un sustituto exacto del RS Rating de 1-99 que sí calcula el módulo RS/RW sobre el universo completo.`
    },

    "fcf-yield": {
        title: "FCF Yield — Rentabilidad por Flujo de Caja Libre",
        short: "Free Cash Flow ÷ Capitalización de mercado. Mide cuánto efectivo real genera la empresa por cada euro/dólar de valoración.",
        long: `El FCF Yield divide el Free Cash Flow (efectivo que genera el negocio tras cubrir su propio capex, antes de dividendos o recompras) entre la capitalización bursátil actual.

FÓRMULA:
FCF Yield = Free Cash Flow / Market Cap × 100

POR QUÉ ES MÁS FIABLE QUE EL P/E EN ALGUNOS CASOS:
El beneficio contable (el que usa el P/E) puede distorsionarse por partidas no monetarias: amortizaciones aceleradas, cargos únicos, cambios contables, stock-based compensation no descontado, etc. El FCF es dinero real entrando en caja — mucho más difícil de maquillar de forma sostenida.

INTERPRETACIÓN:
▸ &gt; 8% → Generación de caja muy fuerte en relación al precio, terreno de "value"
▸ 4-8% → Rango razonable para la mayoría de empresas maduras y rentables
▸ 0-4% → Empresa cara en términos de caja, o todavía invirtiendo fuerte en crecimiento (normal en growth/tech temprano)
▸ Negativo → La empresa está quemando caja; no es necesariamente malo si es fase de inversión agresiva, pero exige vigilar la pista de aterrizaje (runway) de efectivo

LIMITACIÓN:
El FCF puede ser muy volátil trimestre a trimestre (proyectos de capex puntuales, cambios de working capital), así que un único dato trimestral puede no representar la tendencia real — siempre que sea posible, contrástalo con varios años.`
    },

    "payout-ratio": {
        title: "Payout Ratio — Ratio de Reparto de Dividendo",
        short: "Porcentaje del beneficio por acción (EPS) que la empresa reparte como dividendo. Mide la sostenibilidad del dividendo.",
        long: `El Payout Ratio indica qué proporción del beneficio neto por acción se destina a pagar dividendos, dejando el resto para reinversión, reducción de deuda o recompras.

FÓRMULA:
Payout Ratio = Dividendo anual por acción / EPS (beneficio por acción) × 100

INTERPRETACIÓN:
▸ &lt; 40% → Margen amplio, dividendo muy sostenible y con espacio para crecer
▸ 40-80% → Rango normal para la mayoría de empresas maduras que reparten dividendo
▸ 80-100% → Zona de vigilancia: poco margen de seguridad, un mal trimestre puede forzar un recorte
▸ &gt; 100% → La empresa reparte más de lo que gana — solo sostenible un tiempo limitado, financiado con caja acumulada o deuda, salida en rojo en esta terminal

POR QUÉ ESTE DATO IMPORTA TANTO TRAS EL FIX DEL DIVIDEND YIELD:
Un yield "real" alto (ej. 6-7%) acompañado de un payout ratio superior al 100% es exactamente el patrón de aviso que precede a recortes de dividendo — el mercado a veces ya está descontando ese riesgo en forma de precio bajo, que es lo que infla el yield artificialmente.

EXCEPCIÓN A TENER EN CUENTA — REITs:
Los REITs (fondos inmobiliarios cotizados) están obligados por ley a repartir ≥90% de su beneficio imponible, así que un payout alto en ese sector es estructural y normal, no una señal de alarma como en una empresa industrial o tecnológica.`
    },

    "n-analysts": {
        title: "Número de Analistas",
        short: "Cuántas casas de análisis cubren activamente este valor con una recomendación vigente, con la fecha del rating individual más reciente.",
        long: `Este dato indica cuántos analistas de bancos/casas de inversión tienen actualmente una recomendación publicada sobre el valor.

DE DÓNDE SALE EL NÚMERO:
Se prioriza el recuento real sumando todas las recomendaciones individuales (Strong Buy + Buy + Hold + Sell + Strong Sell) del periodo más reciente, en vez del campo agregado de Yahoo, que en ocasiones queda desactualizado respecto al consenso real.

POR QUÉ SE MUESTRA LA FECHA DEL ÚLTIMO RATING:
El número total de analistas (ej. "20 analistas") puede sonar a dato fresco, pero el consenso de precio objetivo que lo acompaña puede arrastrar valoraciones de hace semanas o meses sin que ningún analista haya actualizado su postura recientemente. La fecha del último rating individual te dice cuándo fue la última vez que alguien realmente revisó su opinión sobre el valor — un consenso "vivo" tiene rating recientes; un consenso "dormido" puede llevar tiempo sin que nadie lo toque, aunque el número de analistas siga siendo alto.

CÓMO USARLO:
Pocos analistas (&lt;5) implica un consenso poco robusto, más sensible a que un solo analista mueva la media con su cambio de opinión. Muchos analistas con rating reciente es la situación más fiable para apoyarte en el consenso de precio objetivo.`
    },

    "institutional-ref-price": {
        title: "Precio al Cierre del Trimestre (13F)",
        short: "Precio al que cotizaba la acción cuando se cerró el trimestre que reportan estos 13F, comparado con el precio actual.",
        long: `Los informes 13F que presentan las instituciones ante la SEC declaran sus posiciones a CIERRE DE TRIMESTRE, no la fecha real en la que compraron. Por eso todas las instituciones de la tabla reportan a la misma fecha de corte — es una norma regulatoria, no una coincidencia.

QUÉ MUESTRA ESTE DATO:
El precio de cierre real de la acción en esa fecha de corte trimestral, y cuánto se ha movido el precio desde entonces hasta hoy.

LIMITACIÓN IMPORTANTE:
Con datos de 13F es imposible saber el precio de entrada real de cada institución — solo cuántas acciones tenían a cierre de trimestre. Si una institución construyó su posición en varios tramos, su coste medio real puede diferir bastante de este precio de referencia trimestral. Para precios de transacción reales y por insider concreto, mirad la sección de Insider Trading (eso sí usa Form 4, que sí declara precio y fecha exactos).`
    },

    "insider-monthly-volume": {
        title: "Volumen Mensual Insider",
        short: "Acciones compradas vs vendidas por insiders cada mes, en los últimos 12 meses (solo transacciones discrecionales).",
        long: `Este gráfico agrega, mes a mes, el número de acciones que los insiders (directivos, consejeros, accionistas significativos) han comprado o vendido en mercado abierto durante el último año.

QUÉ SE INCLUYE:
Igual que el resumen de sentimiento, solo cuenta transacciones discrecionales reales (códigos P de compra y S de venta), excluyendo movimientos rutinarios como ejercicios de opciones, donaciones o liquidaciones fiscales automáticas.

CÓMO USARLO:
Permite ver si la actividad insider es puntual (un mes con mucho volumen y el resto vacío) o sostenida en el tiempo, y si el patrón de compras/ventas se ha invertido recientemente respecto a meses anteriores — algo que el resumen de 6 meses por sí solo no muestra.`
    },

    "income-statement": {
        title: "Cuenta de Resultados Trimestral",
        short: "Evolución de Ingresos, Beneficio Bruto, Operativo y Neto trimestre a trimestre.",
        long: `Muestra la evolución de las cuatro líneas principales de la cuenta de resultados de la empresa en los últimos trimestres disponibles, según los datos reportados por la propia compañía.

LAS 4 LÍNEAS:
▸ Ingresos: ventas totales del trimestre
▸ Beneficio Bruto: ingresos menos coste de los bienes vendidos (COGS)
▸ Beneficio Operativo: beneficio bruto menos gastos operativos (I+D, marketing, administración)
▸ Beneficio Neto: lo que queda tras impuestos, intereses y partidas extraordinarias

CÓMO USARLO:
Si Ingresos crece pero Beneficio Neto se queda plano o cae, la empresa está perdiendo eficiencia (márgenes comprimidos) aunque las ventas vayan bien. Si las cuatro líneas crecen en paralelo, es una señal de fortaleza fundamental sostenida.`
    },

    "insider-summary": {
        title: "Sentimiento Insider (6 meses)",
        short: "Resumen neto de compras vs ventas discrecionales de directivos/insiders en los últimos 6 meses.",
        long: `Este resumen agrega todas las transacciones de insiders (directivos, consejeros, accionistas significativos) de los últimos 6 meses en un único indicador de sentimiento neto.

QUÉ SE INCLUYE Y QUÉ SE EXCLUYE:
Solo se cuentan transacciones DISCRECIONALES de mercado real — compras y ventas donde el insider toma una decisión activa. Se excluyen explícitamente movimientos rutinarios y no discrecionales (ejercicios de stock options programados, donaciones, conversiones de valores, liquidaciones fiscales automáticas), que no reflejan una opinión real del insider sobre la valoración del activo.

CÓMO SE CALCULA EL SENTIMIENTO:
Se compara el valor en $ comprado vs vendido en ese periodo. Si la diferencia neta (compras − ventas) supera el 30% del volumen total transaccionado, se etiqueta COMPRADOR o VENDEDOR; si está más equilibrado, queda NEUTRAL.

POR QUÉ LAS COMPRAS PESAN MÁS QUE LAS VENTAS COMO SEÑAL:
Los insiders venden por mil motivos no relacionados con su opinión sobre la empresa (diversificación, compra de una casa, divorcio, impuestos, plan de venta automático 10b5-1 programado meses atrás). Pero casi nunca COMPRAN en el mercado abierto con su propio dinero salvo que crean genuinamente que el precio está barato — por eso, históricamente, las compras de insiders son una señal bastante más informativa que las ventas.

LIMITACIÓN:
6 meses es una ventana corta. Un solo insider con una compra grande puede inclinar el sentimiento sin que represente una visión colectiva del equipo directivo — revisa siempre la tabla detallada debajo para ver quién está detrás del número.`
    },

    "ema-slope": {
        title: "EMAs y su Pendiente",
        short: "Medias móviles exponenciales (10/20/50/200) con su pendiente reciente: alcista ↗, bajista ↘, o plana →.",
        long: `Las EMAs (medias móviles exponenciales) dan más peso a los precios recientes que las SMA clásicas, por lo que reaccionan más rápido a cambios de tendencia — útil sobre todo en la EMA10/20 para timing de corto plazo.

LAS 4 EMAs Y SU USO TÍPICO:
▸ EMA 10: la más reactiva, sigue el pulso de muy corto plazo (días/1-2 semanas)
▸ EMA 20: referencia de swing trading de corto plazo (2-4 semanas)
▸ EMA 50: tendencia de medio plazo (1-3 meses), la más vigilada por gestores
▸ EMA 200: tendencia de largo plazo (6-12 meses), la línea divisoria clásica entre mercado alcista y bajista de fondo

CÓMO SE CALCULA LA PENDIENTE:
Se compara el valor actual de cada EMA contra su propio valor unas sesiones atrás (más sesiones cuanto más lenta la EMA, para evitar ruido). Si la variación supera un umbral mínimo se marca como ↗ alcista o ↘ bajista; si está dentro del umbral, se marca → plana (la EMA se está aplanando, señal de posible cambio de fase).

DOS NÚMEROS DISTINTOS QUE NO HAY QUE CONFUNDIR:
Cada fila de EMA muestra dos porcentajes con significados diferentes:
▸ "% vs precio" (arriba, número grande) → cuánto se aleja el precio ACTUAL de esa media. Ej. si el precio está en $13.14 y la EMA200 en $14.34, la distancia es -8.4% — esto responde "¿qué tan lejos está el precio de esta media?".
▸ "EMA pendiente" (abajo, número pequeño con flecha) → cuánto ha cambiado el VALOR de la propia EMA en las últimas sesiones, no su relación con el precio. Responde "¿está esta media subiendo o bajando?", independientemente de dónde esté el precio respecto a ella.
Un precio puede estar muy lejos de una EMA (distancia grande) mientras esa EMA tiene una pendiente pequeña porque se mueve despacio — son lecturas independientes, no la misma cosa medida de dos formas.

POR QUÉ LA PENDIENTE IMPORTA MÁS QUE EL VALOR ABSOLUTO:
Dos activos pueden cotizar ambos por encima de su EMA50, pero si en uno la EMA50 sigue subiendo con fuerza y en el otro se está aplanando, el segundo está mostrando primeras señales de agotamiento de tendencia mucho antes de que el precio lo confirme.`
    },

    "asset-trend": {
        title: "Tendencia del Activo",
        short: "Clasificación ALCISTA / BAJISTA / RANGO según la alineación y pendiente de las EMAs.",
        long: `Esta clasificación resume en una sola etiqueta si el activo está en tendencia alcista, bajista, o sin dirección clara (rango/lateral), combinando 5 condiciones de alineación de EMAs:

1. Precio por encima de la EMA20
2. EMA20 por encima de la EMA50
3. EMA50 por encima de la EMA200
4. EMA50 con pendiente alcista
5. EMA200 con pendiente alcista o plana (no bajista)

CÓMO SE DECIDE LA ETIQUETA:
▸ 4-5 condiciones cumplidas → ALCISTA: alineación limpia, EMAs ordenadas de corto a largo plazo y subiendo
▸ 0-1 condiciones cumplidas → BAJISTA: alineación invertida, EMAs ordenadas a la baja
▸ 2-3 condiciones → RANGO: alineación mixta, sin un sesgo dominante claro — el activo está lateral, en transición entre fases, o las EMAs están entrelazadas

POR QUÉ "RANGO" NO ES UN FALLO DEL SISTEMA:
Los activos no están siempre en tendencia clara — pasan buena parte del tiempo en fases de transición o consolidación. Detectar correctamente el "RANGO" es tan útil como detectar la tendencia: evita forzar una lectura direccional donde el activo simplemente no la tiene todavía.`
    },

    "market-phase": {
        title: "Fase de Mercado (1-4)",
        short: "Clasificación de las 4 fases clásicas de Stan Weinstein: Acumulación, Avance, Distribución, Declive. Fase diaria (rápida) + fase semanal (lenta, confirmación estructural).",
        long: `Este sistema de 4 fases, popularizado por Stan Weinstein en "Secrets for Profiting in Bull and Bear Markets", describe el ciclo natural por el que pasa cualquier activo a lo largo del tiempo.

DOS TEMPORALIDADES, NO UNA:
▸ FASE DIARIA: calculada sobre cierres diarios (EMA10/20/50/200 diarias) — rápida y táctica, pero más sensible al ruido de corto plazo. Es la que verás primero en pantalla.
▸ FASE SEMANAL: calculada sobre velas semanales (mismos indicadores, resampleados) — la temporalidad ORIGINAL del método de Weinstein, mucho más lenta pero mucho más limpia. Se muestra al lado como confirmación estructural, no como sustituta de la diaria.
Cuando ambas coinciden, la lectura es más fiable. Cuando discrepan (p.ej. diaria ya en Fase 3 pero semanal todavía en Fase 2), el desacuerdo en sí es información: suele significar que un movimiento reciente todavía no tiene entidad suficiente para cambiar el cuadro de fondo.

DEBOUNCE — "SIN CONFIRMAR AÚN":
La fase diaria exige que la clasificación se mantenga 3 sesiones seguidas antes de darse por buena. Si ves el aviso "cambio reciente, sin confirmar aún", significa que la fase acaba de cambiar y todavía no lleva las 3 sesiones seguidas necesarias — puede estabilizarse en la nueva fase o volver a la anterior. Esto reduce el "parpadeo" entre fases por ruido de un solo día, sin cambiar la fórmula de clasificación en sí.

LAS 4 FASES:
▸ FASE 1 — ACUMULACIÓN: el activo lleva tiempo lateral tras una caída previa, las EMAs están entrelazadas sin pendiente clara, normalmente cerca o por debajo de la EMA200. Los inversores informados empiezan a acumular en silencio antes de que el precio confirme nada.
▸ FASE 2 — AVANCE (Markup): tendencia alcista confirmada y limpia — EMAs ordenadas (10>20>50>200) y con pendiente ascendente. Es la única fase que O'Neil, Minervini y Weinstein coinciden en señalar como la fase para comprar.
▸ FASE 3 — DISTRIBUCIÓN: el activo cotiza todavía por encima de la EMA200 (herencia de una Fase 2 previa) pero la alineación de EMAs se ha roto — empieza a moverse lateral en zona alta. Los que compraron en Fase 1-2 comienzan a vender posición a quien compra tarde.
▸ FASE 4 — DECLIVE / CORRECCIÓN: tendencia bajista confirmada y limpia, EMAs ordenadas a la baja. Fase de salida o de espera, nunca de compra según esta metodología.

CÓMO SE DISTINGUEN 1 Y 3 EN ESTE SISTEMA (ambas son técnicamente "rango"):
La diferencia clave es la posición respecto a la EMA200: si el precio está por debajo o pegado a ella tras un periodo lateral, se interpreta como acumulación temprana (Fase 1); si está por encima tras un periodo lateral, se interpreta como distribución tras una subida previa (Fase 3).

SUBESTADOS ESPECIALES — GIROS TEMPRANOS (alcista y bajista):
Existen dos casos intermedios que el sistema trata de forma diferenciada, uno espejo del otro:
▸ "FASE 1 · POSIBLE GIRO TEMPRANO": las EMAs cortas (10 y 20) ya giran al alza y el precio cotiza por encima de la EMA20, pero las EMAs largas (50 y 200) siguen con pendiente bajista — un rebote real desde mínimos siempre empieza así.
▸ "FASE 3 · POSIBLE GIRO BAJISTA TEMPRANO": el caso simétrico — las EMAs cortas ya giran a la baja con fuerza y el precio cotiza por debajo de la EMA20, pero las EMAs largas todavía no han terminado de confirmarlo. Sin este matiz, un activo cayendo con fuerza desde un techo reciente podía quedar clasificado como "Fase 1 · Acumulación" tranquila — justo lo contrario de lo que está pasando.
En ambos casos sigue siendo una fase de cautela, no de confirmación.

LIMITACIÓN A TENER EN CUENTA:
Esta clasificación se basa puramente en el comportamiento de precio y EMAs (sin datos de volumen institucional real ni acumulación/distribución verificada), por lo que es una aproximación técnica razonable, no una confirmación de manual de Weinstein al 100%. Combínala con el resto de herramientas de la terminal antes de actuar.

USO EN EL SCANNER:
El módulo Scanner reutiliza exactamente esta misma lógica (misma fórmula diaria, mismo debounce, misma fase semanal) para clasificar las ~500 acciones del S&P 500 en el scan nocturno, sin llamadas de red adicionales por ticker — así el criterio "Fase" del Scanner y la Fase que ves aquí en Research son siempre coherentes entre sí.`
    },

    "short-interest-pct": {
        title: "Short Interest — % del Float",
        short: "Porcentaje de las acciones disponibles para negociar (float) que están actualmente vendidas en corto.",
        long: `El % de Short Interest sobre el float mide cuántas acciones, de las que realmente circulan en el mercado libre (excluyendo las retenidas por insiders o bloqueadas), están prestadas y vendidas en corto en este momento.

POR QUÉ SE USA EL FLOAT Y NO EL TOTAL DE ACCIONES:
El float es la cifra relevante porque es la oferta REAL disponible para comprar/vender. Un short interest del 20% sobre un float pequeño es mucho más significativo que el mismo 20% sobre un float gigante — hay menos acciones físicas para que los cortos las recompren si el precio se dispara.

RANGOS ORIENTATIVOS:
▸ &lt; 5% → Interés corto bajo, sin presión relevante
▸ 5-10% → Interés corto normal, vigilar si sube
▸ 10-20% → Interés corto elevado, candidato a movimientos bruscos
▸ &gt; 20% → Interés corto extremo, zona histórica de squeezes conocidos (GME, AMC superaron el 100% en sus picos)

LIMITACIÓN IMPORTANTE:
Este dato se reporta con retraso (normalmente con datos de mediados o finales de cada quincena bursátil en EE.UU.), no es en tiempo real. Un short interest alto no garantiza un squeeze — necesita además un catalizador (noticia, earnings, compra coordinada) que fuerce a los cortos a cerrar posiciones.`
    },

    "days-to-cover": {
        title: "Days to Cover — Días para Cubrir",
        short: "Cuántos días de volumen medio de negociación necesitarían los vendedores en corto para recomprar todas sus posiciones.",
        long: `Days to Cover (también llamado Short Ratio) divide el número total de acciones vendidas en corto entre el volumen medio diario de negociación.

FÓRMULA:
Days to Cover = Acciones en corto / Volumen medio diario

QUÉ MIDE REALMENTE:
No es un plazo que los cortos deban cumplir obligatoriamente — es una medida de LIQUIDEZ. Indica cuánto tardaría el mercado en "absorber" toda la recompra de cortos si todos intentaran cerrar posición al mismo tiempo, dado el volumen habitual que se negocia.

INTERPRETACIÓN:
▸ &lt; 2 días → Liquidez amplia, los cortos podrían salir rápido sin mover mucho el precio
▸ 2-5 días → Liquidez moderada
▸ 5-10 días → Liquidez ajustada, una recompra forzada movería el precio de forma notable
▸ &gt; 10 días → Liquidez muy ajustada, ingrediente clave de un short squeeze severo

POR QUÉ IMPORTA COMBINADO CON EL % DE FLOAT:
Un % de float corto alto con Days to Cover bajo significa que, aunque hay mucho interés corto, hay suficiente volumen para que se deshaga sin drama. La combinación de AMBOS altos a la vez es la que históricamente ha precedido los squeezes más violentos (GME enero 2021 llegó a tener Days to Cover de varios días con un float muy reducido).`
    },

    "squeeze-gauge": {
        title: "Squeeze Gauge — Potencial de Short Squeeze",
        short: "Score 0-100 propio RSU que combina % de float en corto y días para cubrir en una sola lectura visual.",
        long: `El Squeeze Gauge combina dos métricas de short interest en un único score de 0 a 100 para facilitar una lectura rápida del riesgo/oportunidad de un short squeeze.

CÁLCULO:
▸ Componente % Float en corto (peso 60 pts): escala hasta 30% de float corto → máximo de puntos
▸ Componente Days to Cover (peso 40 pts): escala hasta 10 días → máximo de puntos

Score = min(%float/30 × 60, 60) + min(DTC/10 × 40, 40)

NIVELES:
▸ 0-25 → BAJO → Sin presión de cortos relevante
▸ 25-50 → MODERADO → Interés corto a vigilar, sin condiciones extremas todavía
▸ 50-75 → ALTO → Combinación de % float y liquidez ajustada que históricamente precede movimientos bruscos
▸ 75-100 → EXTREMO → Condiciones similares a los squeezes más conocidos del mercado (GME, AMC 2021)

QUÉ NO TE DICE EL SCORE — MUY IMPORTANTE:
Un score alto NO predice que el squeeze vaya a ocurrir, ni cuándo. Mide CONDICIONES NECESARIAS (mucho interés corto + poca liquidez para cubrir), no el catalizador que dispararía el evento — eso requiere un detonante externo (noticia, compra coordinada retail, earnings sorpresa) que ningún indicador cuantitativo puede anticipar con fiabilidad. Trátalo como un mapa de "dónde hay leña apilada", no de "cuándo se va a prender fuego".`
    },

    "rsu-score": {
        title: "RSU Score — Valoración Integral Unificada",
        short: "Score 0-100 que combina calidad fundamental, salud financiera (Piotroski), valoración vs sector, sentimiento de mercado y fase técnica en un único número.",
        long: `El RSU Score es un sistema de valoración propio que combina 5 dimensiones independientes para dar una puntuación global de 0 a 100 a cualquier acción.

LOS 5 COMPONENTES (20 puntos cada uno):

1. CALIDAD FUNDAMENTAL (20pts)
Promedio de crecimiento de ingresos, ROE y margen neto — niveles ABSOLUTOS de rentabilidad actual.

2. SALUD FINANCIERA · PIOTROSKI (20pts)
El Piotroski F-Score (0-9 criterios, ver tooltip propio) escalado a 20 puntos. A diferencia de la Calidad Fundamental, esto mide la TENDENCIA interanual de la salud financiera, no el nivel absoluto — por eso es un componente separado, no redundante.

3. VALORACIÓN VS SECTOR (20pts)
Compara P/E, EV/EBITDA, PEG y P/B contra la mediana del sector. Si no hay benchmark sectorial disponible, usa el PEG absoluto como respaldo.

4. SENTIMIENTO DE MERCADO (20pts)
Consenso de analistas + potencial de precio objetivo, ajustado ±3pts según si los insiders están comprando o vendiendo discrecionalmente en los últimos 6 meses.

5. FASE TÉCNICA (20pts)
Usa la Fase de Mercado (1-4) de Niveles Técnicos: Fase 2 (Markup) = 20pts, Fase 1 (Acumulación) = 13pts, Fase 3 (Distribución) = 7pts, Fase 4 (Declive) = 0pts.

POR QUÉ SE REDISEÑÓ — INTEGRACIÓN DE PIOTROSKI:
Antes, el RSU Score y el Piotroski F-Score eran dos sistemas totalmente independientes que medían cosas distintas (niveles absolutos vs tendencia interanual) y podían dar lecturas aparentemente contradictorias sin explicación — una empresa con buenos márgenes actuales pero salud financiera deteriorándose podía mostrar RSU alto y Piotroski bajo a la vez. Ahora Piotroski es literalmente el 20% del RSU Score, así que su efecto sobre la puntuación final es explícito y visible en el desglose, no una contradicción aparte que hay que reconciliar mentalmente.

SI FALTA ALGÚN DATO:
Si una categoría no tiene datos disponibles para el ticker, el score se recalcula sobre las categorías sí disponibles (no se penaliza por ausencia de datos, pero el score será menos representativo cuantas menos categorías tenga detrás — revisa siempre el desglose).

INTERPRETACIÓN:
- 80-100 → COMPRA FUERTE → Las 5 dimensiones mayormente alineadas
- 65-79 → COMPRA → Mayoría de dimensiones positivas
- 50-64 → NEUTRAL → Mix de señales entre dimensiones
- 35-49 → PRECAUCIÓN → Varias dimensiones débiles
- 0-34 → EVITAR → Fundamentales, técnico y/o sentimiento débiles

Es una herramienta de filtrado y contexto, no una recomendación de inversión.

DIFERENCIA CON EL "SCORE TÉCNICO" DEL SCANNER:
El módulo Scanner muestra un "Score Técnico" distinto de este RSU Score — ese solo usa datos de precio/volumen (RS Percentile, Fase, RVOL), sin componente fundamental, porque calcular el RSU Score completo para las ~500 acciones del S&P 500 cada noche sería demasiado costoso en llamadas a datos. Si el Scanner te señala un candidato interesante, este RSU Score (con Piotroski, valoración y sentimiento incluidos) es el siguiente paso lógico para confirmarlo con la pata fundamental.`
    },

    "piotroski-score": {
        title: "Piotroski F-Score — Salud Financiera Fundamental",
        short: "Puntuación 0-9 ideada por Joseph Piotroski que mide la solidez fundamental de una empresa comparando su último ejercicio fiscal contra el anterior. Es el 20% del RSU Score.",
        long: `El Piotroski F-Score evalúa 9 criterios contables binarios (1 punto si se cumple, 0 si no) repartidos en 3 bloques. Cuanto más alto, más sólida es la TENDENCIA interanual de los fundamentales de la empresa — a diferencia de otras métricas que miran el nivel absoluto, este score mira si las cosas están mejorando o empeorando respecto al ejercicio anterior.

RELACIÓN CON EL RSU SCORE:
Este score ya no vive de forma aislada — es uno de los 5 componentes que forman el RSU Score (20% del total, ver tooltip "RSU Score"). Eso significa que un Piotroski bajo siempre va a pesar a la baja en el score global, y uno alto siempre suma — ya no pueden contradecirse entre sí porque uno está dentro del otro.

RENTABILIDAD (4 puntos):
1. ROA positivo en el último ejercicio
2. Flujo de caja operativo (CFO) positivo
3. ROA superior al del ejercicio anterior
4. CFO superior al beneficio neto (calidad del beneficio, pocos "ajustes contables")

APALANCAMIENTO Y LIQUIDEZ (3 puntos):
5. Deuda a largo plazo sobre activos estable o decreciente
6. Ratio de liquidez (current ratio) en mejora
7. Sin emisión de nuevas acciones (sin dilución)

EFICIENCIA OPERATIVA (2 puntos):
8. Margen bruto en mejora
9. Rotación de activos (ventas/activos) en mejora

INTERPRETACIÓN:
- 8-9 → EXCELENTE → Fundamentales en clara mejora
- 6-7 → SÓLIDO → Mayoría de factores positivos
- 4-5 → NEUTRAL → Mix de señales
- 0-3 → DÉBIL → Deterioro fundamental, requiere cautela

Es un score de "momentum fundamental" interanual, complementario al RSU Score (que es más bien una foto del momento actual). Funciona mejor en empresas con histórico de varios años — en compañías muy jóvenes o con datos incompletos puede no calcularse.`
    },

    "sector-valuation": {
        title: "Valoración vs Sector",
        short: "Múltiplos de valoración coloreados según si la empresa cotiza más cara o más barata que la mediana de su sector.",
        long: `Cada múltiplo de valoración (P/E, P/S, EV/EBITDA, PEG, P/B) se compara contra una mediana de referencia del sector GICS al que pertenece la empresa.

CÓMO LEER LOS COLORES:
- Verde → la empresa cotiza más barata que su sector en ese múltiplo (potencialmente infravalorada en términos relativos)
- Rojo → la empresa cotiza más cara que su sector en ese múltiplo (prima de valoración frente a sus comparables)

El porcentaje entre paréntesis indica cuánto se desvía el valor de la empresa respecto a esa mediana sectorial.

IMPORTANTE:
Una valoración "cara" frente al sector no es automáticamente mala — puede estar justificada por crecimiento superior, mejor rentabilidad, o ventajas competitivas. Esta comparación es un punto de partida para preguntar "¿por qué?", no una conclusión en sí misma. Las medianas usadas son de referencia general del mercado US, no datos de un proveedor en tiempo real.`
    },

    "analyst-ratings-history": {
        title: "Histórico de Ratings de Analistas",
        short: "Cambios de calificación reales por firma de Wall Street (Morgan Stanley, Goldman Sachs, etc.), con grado anterior y nuevo.",
        long: `Esta tabla muestra el historial real de cambios de calificación (rating) emitidos por firmas de análisis de Wall Street para esta empresa — quién lo emitió, cuándo, y qué cambio exacto de grado representó.

TIPOS DE ACCIÓN:
▸ UPGRADE → la firma mejora su calificación (ej. de Hold a Buy)
▸ DOWNGRADE → la firma empeora su calificación (ej. de Buy a Hold)
▸ INICIA COBERTURA → la firma empieza a cubrir esta empresa por primera vez
▸ REITERA / MANTIENE → la firma confirma su calificación anterior sin cambios

POR QUÉ ESTO ES DIFERENTE A UN CONSENSO AGREGADO:
A diferencia de un simple recuento de "cuántos analistas dicen comprar/mantener/vender", aquí ves la trazabilidad real: qué firma específica cambió de opinión, cuándo, y en qué dirección exacta. Esto permite detectar patrones — por ejemplo, varias downgrades seguidas en pocos días suele ser una señal más fuerte que una sola opinión aislada.

LIMITACIONES A TENER EN CUENTA:
Los cambios de rating de analistas tienden a llegar después de que el mercado ya haya movido el precio en esa dirección (son reactivos, no siempre predictivos). Además, distintas firmas usan escalas de calificación diferentes entre sí (lo que un banco llama "Neutral" otro lo llama "Hold"), así que comparar grados entre firmas distintas requiere cierta cautela.`
    },

    "sector-profitability": {
        title: "Rentabilidad vs Sector",
        short: "ROE, márgenes y apalancamiento comparados contra la mediana del sector de la empresa.",
        long: `Las métricas de rentabilidad (ROE, ROA, márgenes neto/operativo/bruto) y de apalancamiento (D/E Ratio) se comparan contra la mediana típica del sector GICS de la empresa.

CÓMO LEER LOS COLORES:
- Verde → la empresa es más rentable o tiene menos deuda relativa que su sector
- Rojo → la empresa es menos rentable o tiene más deuda relativa que su sector

Para ROE, ROA y los tres márgenes, más alto siempre es mejor. Para el D/E Ratio, menos deuda relativa al patrimonio se considera más favorable, por lo que el color se invierte respecto a las demás métricas de esta tarjeta.

Comparar rentabilidad dentro del mismo sector es más significativo que comparar entre sectores distintos — un margen neto del 8% puede ser excelente en retail y mediocre en software, por eso el contexto sectorial importa.`
    },

    "sector-growth": {
        title: "Crecimiento vs Sector",
        short: "Crecimiento de ingresos y beneficios comparado contra la mediana de crecimiento del sector.",
        long: `Revenue Growth y Earnings Growth se comparan contra el ritmo de crecimiento típico del sector GICS de la empresa.

CÓMO LEER LOS COLORES:
- Verde → la empresa crece por encima del ritmo habitual de su sector
- Rojo → la empresa crece por debajo del ritmo habitual de su sector

Sectores como Tecnología o Consumo Discrecional tienden a tener medianas de crecimiento más altas que sectores maduros como Utilities o Consumo Básico — por eso un 8% de crecimiento puede ser sobresaliente en un sector y decepcionante en otro.

Current Ratio, Free Cash Flow, Dividend Yield y número de analistas no tienen una comparación sectorial aplicada, ya que dependen más de la estructura de capital específica de cada empresa que de su sector.`
    },

    // ── RS/RW ─────────────────────────────────────────────────────────────────
    "rsrw": {
        title: "RS/RW Scanner — Relative Strength/Weakness",
        short: "Identifica las acciones con mayor fortaleza y debilidad relativa vs el mercado, sobre el universo completo del S&P 500 (525 tickers), actualizado cada noche.",
        long: `El RS/RW Scanner identifica qué acciones están liderando (RS) y cuáles están rezagadas (RW) respecto al mercado en múltiples marcos temporales.

UNIVERSO Y ACTUALIZACIÓN:
Escanea el S&P 500 completo (525 tickers) una vez por noche vía GitHub Actions — no hay scan "on-demand" desde el navegador, así que no depende de que un usuario lo dispare ni arriesga rate limits de Yahoo en horario de mercado. Los datos que ves siempre vienen de ese scan nocturno.

METODOLOGÍA:
Comparamos el rendimiento de cada acción vs el SPY en 3 períodos:
- 21 días (~1 mes) — peso 20%
- 63 días (~3 meses) — peso 35%
- 126 días (~6 meses) — peso 45%

La métrica base no es un ratio de precios, sino el DIFERENCIAL de rendimiento porcentual (rendimiento de la acción menos rendimiento del SPY en esa ventana), suavizado con una media móvil exponencial para reducir ruido. El resultado combinado se convierte en un percentil del 1 al 99 sobre todo el universo.

POR QUÉ IMPORTA:
Las acciones con RS más alto tienden a seguir superando al mercado en el corto-medio plazo. Es el momentum del mercado. Las acciones con RW más bajo tienden a seguir cayendo.

SEÑALES CLAVE:
▸ RS Percentile ≥ 80 con tendencia de RS al alza → acción líder, entrada de alta probabilidad
▸ RS cayendo mientras el precio sube → divergencia bajista, evitar
▸ Clusters de RS alto en un mismo sector → rotación sectorial en marcha (ver Rotación Sectorial)`
    },

    "rsrw-sector-rotation": {
        title: "Rotación Sectorial",
        short: "RS de cada sector (ETF sectorial vs SPY), combinando 1/3/6 meses igual que las acciones — la barra es el nivel actual, la flecha es si esa RS mejora o empeora en las últimas ~4 semanas. Son dos cosas distintas.",
        long: `Compara el ETF representativo de cada sector (XLK, XLF, XLE...) contra el SPY, con la misma fórmula que el resto del módulo: diferencial de rendimiento porcentual en 3 ventanas temporales, combinadas.

DOS MÉTRICAS INDEPENDIENTES — NO CONFUNDIR:
▸ La BARRA y el NÚMERO son el NIVEL: RS combinada de 21, 63 y 126 sesiones (20%/35%/45%) — igual ponderación que se usa para acciones individuales en este mismo módulo. Es una foto del presente a varios plazos a la vez.
▸ La FLECHA es la TENDENCIA: si la componente de 63 sesiones (~3 meses) de esa RS ha estado subiendo (▲) o bajando (▼) en las últimas ~4 semanas — no dice nada sobre si el nivel combinado es positivo o negativo, solo hacia dónde se mueve.

Por eso puedes ver un sector en ROJO con flecha ▲: el combinado sigue por debajo del SPY, pero la componente de 3 meses ha empezado a mejorar recientemente. Es la señal de "posible rotación temprana" — un sector que empieza a despertar antes de que el nivel combinado lo confirme. Al revés, un sector en VERDE con flecha ▼ está perdiendo fuelle aunque de momento siga ganando al mercado.

METODOLOGÍA — POR QUÉ COMBINAR 3 VENTANAS EN VEZ DE UNA SOLA:
Antes esta sección usaba solo una ventana fija de 63 sesiones, mientras que las acciones individuales del mismo módulo ya combinaban 21/63/126 — una asimetría metodológica sin motivo de diseño, solo porque se añadieron en momentos distintos. Ahora ambas partes hablan el mismo idioma.

LA TEORÍA DETRÁS — JEGADEESH & TITMAN (1993):
El paper seminal de momentum de Narasimhan Jegadeesh y Sheridan Titman, "Returns to Buying Winners and Selling Losers", encontró que las acciones (y por extensión, cestas como sectores) que superaron al mercado en los últimos 3 a 12 meses tienden a seguir superándolo en los meses siguientes — el efecto "momentum" clásico. Algunos matices relevantes de ese trabajo y de la literatura posterior:

▸ Ventanas de formación muy cortas (menos de 1 mes) tienden a mostrar REVERSIÓN, no continuación — comprar lo que subió ayer no funciona igual que comprar lo que lleva subiendo 3-6 meses.
▸ El rango de 3 a 12 meses es el que consistentemente muestra el efecto momentum más robusto en el estudio original y en réplicas posteriores.
▸ El efecto tiende a revertirse en horizontes muy largos (2-5 años) — momentum de corto-medio plazo y reversión de largo plazo coexisten en el mismo activo, en ventanas distintas.

Combinar 21/63/126 días en vez de usar una sola ventana es, en esencia, una forma simple de capturar el momentum de corto plazo sin depender de una única ventana arbitraria — con más peso en 126d (45%) precisamente porque esa es la ventana que la literatura señala como más robusta, y menos peso en 21d (20%) porque ahí el ruido y la reversión de corto plazo son más frecuentes.

Esto NO es garantía de nada — es una tendencia estadística observada en datos históricos de mercados desarrollados, no una ley física. Trátalo como una probabilidad a favor, no como una certeza.`
    },

    "sector-composition": {
        title: "Composición Sectorial — Breadth por Sector",
        short: "Cuántos nombres de cada sector lideran el mercado ahora mismo, sobre el universo S&P 500 del módulo RS/RW.",
        long: `Este panel agrupa por sector GICS el mismo universo de ~500 acciones que ya analiza el RS/RW Scanner, para responder una pregunta distinta: no "qué acciones lideran", sino "qué sectores tienen más nombres liderando".

CESTA:
Número de acciones del universo que pertenecen a ese sector.

EN TOP 20%:
De esos nombres, cuántos tienen RS Percentile ≥ 80 (están en el 20% superior de fortaleza relativa del mercado) y qué porcentaje representa sobre el total del sector. Un sector con muchos nombres en este percentil tiene "amplitud" real, no solo 1-2 acciones tirando del carro.

AVG SCORE:
Media del RS Percentile de todas las acciones del sector. Es la versión "sector" del RS Rating individual — cuanto más alto, más fuerte está el sector en conjunto frente al resto del mercado.

MOMENTUM:
Media del RS Momentum (ya calculado por el RS/RW Scanner) de las acciones del sector. Es una señal de aceleración/desaceleración basada en el dato de HOY, no en un histórico de varios días — un sector con momentum medio muy positivo tiene más acciones acelerando su fortaleza relativa en este momento, no necesariamente que lo haya hecho de forma sostenida en el tiempo.

DIFERENCIA CON "SECTOR PERFORMANCE":
El widget de Sector Performance (arriba) mide el rendimiento en precio de los 11 ETFs sectoriales (XLK, XLF...). Este panel mide algo distinto y complementario: la amplitud interna de cada sector — cuántos nombres individuales respaldan ese movimiento, no solo el índice del sector en su conjunto.

LIMITACIÓN A TENER EN CUENTA:
Los datos dependen de la frescura del último scan del RS/RW (visible en "Actualizado"). No hay histórico de streak ni de variación a 5/10/30 días por sector — solo la foto actual del universo.`
    },

    // ── SCANNER ───────────────────────────────────────────────────────────────
    "scanner": {
        title: "Scanner — Filtros Configurables S&P 500",
        short: "Combina RVOL, RS Percentile, Fase Weinstein y Score Técnico sobre las ~500 acciones del S&P 500. Los criterios activados se combinan con AND; el resultado se ordena por Score Técnico.",
        long: `El Scanner recorre cada noche (vía GitHub Action, tras el cierre de mercado US) el universo completo del S&P 500 y precalcula 4 métricas para cada ticker: RVOL, RS Percentile, Fase Weinstein y Score Técnico. El resultado se guarda en un Gist y se lee desde ahí — ninguna petición tuya al abrir la página dispara llamadas nuevas a Yahoo Finance.

CÓMO SE COMBINAN LOS CRITERIOS — GATEKEEPER + SCORE:
Cada criterio que actives (RVOL, RS%, Score, Fase, Sector) actúa como filtro obligatorio: un ticker solo aparece en los resultados si cumple TODOS los criterios activados a la vez (lógica AND). Si no activas ninguno, ves el universo completo. De los tickers que pasan el filtro, se ordenan por Score Técnico de mayor a menor — el mismo principio de "gatekeeper primero, score después" que ya usa el RSU Algoritmo y el RSU Score en Research: un score alto nunca compensa no cumplir un requisito estructural que hayas marcado como obligatorio.

POR QUÉ ES DISTINTO DEL RS/RW SCANNER:
El módulo RS/RW se centra en fuerza/debilidad relativa pura, con líderes y rezagados fijos (top/bottom 20%). El Scanner es más flexible: tú decides qué combinación de condiciones técnicas define tu "setup" (ej. solo acciones en Fase 2 con RVOL alto, o solo un sector concreto por encima de cierto RS), replicando el proceso real de filtrar "buenos activos, a buen precio, con rastro de liquidez" en vez de un ranking fijo de dos categorías.

LIMITACIÓN DE ALCANCE — v1:
De momento el Scanner cubre RVOL, RS Percentile, Fase Weinstein y Score Técnico. VCP (contracción de volatilidad) e insider buying reciente están planeados para versiones posteriores (v1.1/v1.2) una vez se valide el motor base en producción — ver tooltips "rvol" y "score-tecnico" para el detalle de cada métrica individual.`
    },

    "rsrw-trend": {
        title: "Flecha de Tendencia RS",
        short: "▲/▼ indica si la RS de 3 meses ha subido o bajado en las últimas ~4 semanas — no es el nivel actual, es hacia dónde se mueve.",
        long: `La flecha es la pendiente de la componente de RS a 63 sesiones (~3 meses) durante las últimas 21 sesiones (~4 semanas) — un indicador independiente del nivel actual.

▲ = la RS ha estado mejorando recientemente (aunque el nivel siga siendo negativo).
▼ = la RS ha estado empeorando recientemente (aunque el nivel siga siendo positivo).
→ = sin cambio significativo en las últimas semanas.

Combínalo con el nivel (RS%, o la barra de Rotación Sectorial): lo más interesante suele ser un nivel bajo con flecha ▲ (posible giro temprano) o un nivel alto con flecha ▼ (posible pérdida de fuelle antes de que se note en el precio).`
    },

    "rvol": {
        title: "RVOL — Volumen Relativo",
        short: "Volumen de la última sesión cerrada dividido entre la media de volumen de los últimos 20 días. RVOL > 1.5x-2x suele indicar interés inusual (institucional o noticia).",
        long: `RVOL (Relative Volume) mide si el volumen negociado en una sesión es normal o inusualmente alto/bajo comparado con el comportamiento reciente del propio activo.

FÓRMULA:
RVOL = Volumen de la última sesión cerrada / Media de volumen de los últimos 20 días (excluyendo el día actual del cálculo de la media)

POR QUÉ 20 DÍAS Y NO 14 O 50:
20 días es el estándar más extendido en herramientas como IBD, Finviz o TradingView — lo bastante corto para reflejar el ritmo de negociación reciente sin diluir el dato en meses de histórico, y lo bastante largo para no ser inflado o desinflado de forma artificial por un solo día extremo. Se eligió específicamente para que el RVOL del Scanner sea coherente con el mismo cálculo ya usado en el RSU Algoritmo y en RS/RW Scanner — mismo número, mismo significado, en toda la terminal.

INTERPRETACIÓN:
▸ RVOL &lt; 1x → volumen por debajo de lo habitual, poco interés
▸ RVOL 1x-1.5x → volumen normal
▸ RVOL 1.5x-2x → interés por encima de lo habitual, empieza a ser relevante
▸ RVOL &gt; 2x-3x → interés inusual, candidato a movimiento institucional o catalizador (noticia, earnings, ruptura técnica)

POR QUÉ IMPORTA PARA "SEGUIR EL RASTRO DE LIQUIDEZ":
Las instituciones no pueden ocultar el volumen que mueven — cuando entra dinero grande, deja huella. Un RVOL alto por sí solo no dice si el movimiento es alcista o bajista (para eso hace falta ver el precio y la Fase), pero sí confirma que hay actividad fuera de lo normal detrás del ticker en ese momento.

LIMITACIÓN:
El scan se calcula 1x/día, con el dato de la última sesión cerrada — no es RVOL intradía en tiempo real. Para movimientos de volumen dentro de la sesión actual, esta cifra no los refleja hasta el scan de la noche siguiente.`
    },

    "score-tecnico": {
        title: "Score Técnico (Scanner)",
        short: "Score 0-100 exclusivo del Scanner: RS Percentile (50%) + Fase Weinstein (30%) + RVOL (20%, satura en 3x). No es el RSU Score de Research.",
        long: `El Score Técnico es la métrica que usa el Scanner para ordenar los resultados que pasan el filtro de criterios activados. Se calcula únicamente con datos de precio y volumen que ya se descargan en el mismo scan nocturno, sin llamadas adicionales por ticker.

CÁLCULO:
▸ RS Percentile × 50% (fuerza relativa vs el universo, ver tooltip "RS Rating")
▸ Fase Weinstein × 30% — Fase 2 (Avance) = 30pts, Fase 1 (Acumulación/Giro) = 18pts, Fase 3 (Distribución) = 10pts, Fase 4 (Declive) = 0pts
▸ RVOL × 20%, saturando en RVOL = 3x (a partir de ahí no suma más puntos)

POR QUÉ NO ES EL RSU SCORE:
El RSU Score de Research (ver tooltip propio) incorpora 5 dimensiones incluyendo fundamentales — calidad, Piotroski, valoración vs sector y sentimiento de analistas — que requieren varias llamadas de datos POR TICKER. Ejecutar eso sobre las ~500 acciones del S&P 500 cada noche multiplicaría el riesgo de rate-limit y el tiempo del scan de forma desproporcionada. El Score Técnico es intencionadamente una versión "solo precio/volumen" del mismo espíritu (gatekeeper + score), pensada para rankear rápido un universo grande, no para sustituir el análisis fundamental completo.

CÓMO USARLO EN LA PRÁCTICA:
Un Score Técnico alto (70+) te dice que el ticker combina fuerza relativa alta, buena fase técnica y volumen por encima de lo normal — es una señal de "vale la pena mirarlo de cerca", no una recomendación de compra. El paso lógico siguiente para un candidato que destaque aquí es abrirlo en Research y revisar su RSU Score completo antes de tomar cualquier decisión.`
    },

    // ── CARTERA ───────────────────────────────────────────────────────────────
    "cartera-concentracion-sector": {
        title: "Concentración por Sector (HHI)",
        short: "Índice de concentración 0-100% de tu cartera por sectores. No es '% en el sector top' — mide qué tan repartida está toda la cartera.",
        long: `Se calcula con el Índice Herfindahl-Hirschman (HHI), un estándar en finanzas para medir concentración: se suma el peso% de cada sector al cuadrado, y se divide entre 100.

FÓRMULA: (peso₁² + peso₂² + peso₃² + ...) / 100

Cuanto más concentrada esté la cartera en pocos sectores, más alto sale el número — porque elevar al cuadrado penaliza mucho más los pesos grandes que los pequeños.

CÓMO LEERLO:
- 0-15% → Baja concentración → cartera bien repartida entre sectores
- 15-25% → Concentración moderada → un par de sectores dominan, pero sin exceso
- 25%+ → Alta concentración → gran parte del riesgo depende de pocos sectores

DIFERENCIA CON "EXPOSICIÓN POR SECTOR":
El bloque de al lado (Exposición por Sector) te dice el % exacto en cada sector individual — por ejemplo, "Technology 25.4%". La Concentración (HHI) es un resumen de TODOS los sectores a la vez en un solo número, para que no tengas que sumar mentalmente cuánto "peso combinado" tienen tus 2-3 sectores más grandes.

Una cartera con 5 sectores al 20% cada uno tiene HHI = 20% (bien repartida). Una cartera con un sector al 60% y el resto repartido tiene un HHI mucho más alto, aunque el "Exposición por Sector" solo muestre ese 60% como dato individual.`
    },

    "cartera-nivel": {
        title: "Nivel de Convicción (CORE / HIGH / LOTTERY)",
        short: "No es solo una etiqueta — determina el tamaño real de la posición como % fijo de tu capital total.",
        long: `Cada posición se etiqueta con un nivel de convicción, y ese nivel fija directamente cuánto capital se asigna, como % de tu capital total:

▸ CORE → 5% del capital total
▸ HIGH → 3% del capital total
▸ LOTTERY → 1% del capital total

CÓMO FUNCIONA:
En vez de decidir manualmente cuántas acciones comprar de cada posición, se etiqueta la convicción que tienes en la idea y el sistema deriva el tamaño en $ aplicando ese % fijo sobre el capital total configurado. Así el tamaño de cada posición es consistente con tu nivel de convicción real, no con cuánto "te apetece" comprar en el momento.

CÓMO LEERLO EN LA TABLA:
- CORE → tus mejores ideas, mayor convicción, mayor tamaño
- HIGH → convicción media-alta, tamaño intermedio
- LOTTERY → apuestas especulativas de alto riesgo/alta recompensa, tamaño deliberadamente pequeño para limitar el daño si sale mal

Si una fila no tiene un nivel válido, el sistema cae al cálculo antiguo (a partir de Cantidad/Inversión de la hoja), para no romper posiciones ya registradas de otra forma.`
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

    // ── BTC STRATUM ───────────────────────────────────────────────────────────
    "btc-stratum": {
        title: "BTC Stratum — Modelo de Acumulación",
        short: "Modelo de acumulación BTC basado en MA200W, MVRV Z-Score, Puell Multiple y AHR999. Genera señales de compra ponderadas.",
        long: `El BTC Stratum es un modelo propio RSU que combina 4 indicadores on-chain (aproximados) para detectar zonas históricas de acumulación en Bitcoin.

IMPORTANTE: Los indicadores son proxies basados en precio/MA200W. Los valores reales requieren datos on-chain de Glassnode.

COMPONENTES:
- MA200W (40%): Soporte histórico más importante de BTC
- MVRV Z-Score (30%): Proxy de valor de mercado vs valor realizado
- Puell Multiple (20%): Proxy de ingresos de mineros
- AHR999 (10%): Índice de acumulación específico

RSU SCORE BTC 0-100:
- < 20 → Oportunidad extrema → 25% asignación
- 20-40 → Acumulación fuerte → 20% asignación
- 40-60 → Acumulación moderada → 10% asignación
- 60-80 → Neutral/espera → 0% asignación
- > 80 → Sobrecompra/riesgo → 0% asignación

No es asesoramiento financiero. Bitcoin es un activo de alto riesgo.`
    },

    "ma200w": {
        title: "MA200W — Media Móvil 200 Semanas",
        short: "El soporte histórico más importante de Bitcoin. Precios bajo esta línea han sido oportunidades históricas de compra.",
        long: `La Media Móvil de 200 Semanas (MA200W) equivale a ~1400 días de precio de cierre promedio. Es el indicador técnico de largo plazo más respetado en Bitcoin.

HISTORIAL:
Desde 2013, el precio de BTC NUNCA ha cerrado una semana por debajo de la MA200W durante más de unos pocos meses. Cada vez que ha tocado o caído bajo esta línea, ha representado una zona de acumulación histórica.

ZONAS BASADAS EN MA200W:
- Precio < MA200W × 0.5 → Oportunidad máxima (capitulación total)
- Precio < MA200W × 0.75 → Compra agresiva
- Precio < MA200W → Compra fuerte
- Precio < MA200W × 1.25 → Buena compra
- Precio < MA200W × 1.5 → Zona DCA
- Precio > MA200W × 1.5 → Esperar

CURVATURA:
La pendiente y aceleración de la MA200W revelan la salud de la tendencia de largo plazo. Pendiente positiva + acelerando = bull market confirmado.`
    },

    "mvrv-z": {
        title: "MVRV Z-Score (Proxy)",
        short: "Market Value to Realized Value Z-Score — mide si BTC está sobrevalorado o infravalorado. <0 = zona de acumulación extrema.",
        long: `El MVRV Z-Score compara el valor de mercado total de BTC con el "valor realizado" (el precio al que cada BTC cambió de manos por última vez).

IMPORTANTE: Este módulo usa una APROXIMACIÓN basada en desviación del precio vs MA200W. El MVRV real requiere datos on-chain de Glassnode.

INTERPRETACIÓN DEL MVRV REAL:
- Z-Score < 0 → Valor realizado > Valor mercado → Inversores en pérdidas → Zona de suelo histórica
- Z-Score 0-2 → Zona neutra
- Z-Score 2-7 → Zona de distribución
- Z-Score > 7 → Zona de techo histórica (euforia extrema)

SEÑALES HISTÓRICAS:
- Noviembre 2018: MVRV < 0 → Suelo en $3,200
- Marzo 2020: MVRV < 0 → Suelo en $3,800
- Noviembre 2022: MVRV < 0 → Suelo en $15,500

Para datos reales: glassnode.com (requiere suscripción)`
    },

    "puell-multiple": {
        title: "Puell Multiple (Proxy)",
        short: "Ratio entre ingresos diarios de mineros y su media anual. <0.5 indica mineros en stress, históricamente zona de suelo.",
        long: `El Puell Multiple mide los ingresos de los mineros de Bitcoin en relación con su media histórica anual.

IMPORTANTE: Este módulo usa una APROXIMACIÓN basada en precio actual vs SMA365. El Puell real requiere datos de emisión on-chain.

FÓRMULA APROXIMADA:
Puell = Precio actual / SMA365

INTERPRETACIÓN:
- Puell < 0.5 → Mineros en stress severo. Históricamente zona de suelo.
- Puell 0.5-1.0 → Mineros bajo presión moderada
- Puell 1.0-4.0 → Zona normal
- Puell > 4.0 → Mineros muy rentables → Zona de distribución

POR QUÉ IMPORTA:
Cuando los mineros están en pérdidas, venden BTC para sobrevivir, creando presión bajista. Pero también reduce la oferta disponible. Los suelos históricos coinciden con Puell < 0.5.

Los mineros son los "productores" de BTC — cuando sufren, el mercado suele estar en capitulación.`
    },

    "ahr999": {
        title: "AHR999 (Proxy)",
        short: "Índice de acumulación específico de BTC. <0.45 señala zona de compra fuerte según datos históricos.",
        long: `El AHR999 es un índice desarrollado por el usuario "ahr999" de la comunidad china de Bitcoin, diseñado específicamente para identificar zonas de DCA (Dollar Cost Averaging).

IMPORTANTE: Este módulo usa una APROXIMACIÓN. El AHR999 real combina precio actual, MA200 y coste de minería.

FÓRMULA APROXIMADA:
AHR999 ≈ (Precio / MA200W) / log(MA200W)

ZONAS HISTÓRICAS:
- AHR999 < 0.45 → Zona de compra agresiva (DCA fuerte)
- AHR999 0.45-1.2 → Zona de DCA normal
- AHR999 > 1.2 → Esperar mejor oportunidad

COMPLEMENTARIEDAD:
El AHR999 es útil porque penaliza las compras cuando tanto el precio como la MA200W son muy altas, evitando comprar en topping de ciclo aunque el precio parezca "normal" vs la MA.`
    },

    "halving-cycle": {
        title: "Ciclo de Halving — Bitcoin",
        short: "Bitcoin reduce a la mitad su emisión cada ~4 años. Los precios históricamente siguen patrones cíclicos alrededor de estos eventos.",
        long: `El Halving de Bitcoin es un evento programado en el código que reduce a la mitad la recompensa que reciben los mineros por cada bloque minado.

HALVINGS HISTÓRICOS:
- Nov 2012: 50 → 25 BTC/bloque. Precio pasó de $12 a $1,100 en 12 meses.
- Jul 2016: 25 → 12.5 BTC/bloque. Precio pasó de $650 a $20,000 en 18 meses.
- May 2020: 12.5 → 6.25 BTC/bloque. Precio pasó de $8,700 a $69,000 en 18 meses.
- Abr 2024: 6.25 → 3.125 BTC/bloque. Ciclo actual en desarrollo.

FASES DEL CICLO (~4 años):
1. ACUMULACIÓN (0-20% del ciclo): Precio bajo, inversores acumulan
2. BULL TEMPRANO (20-40%): Rally inicial, euforia moderada
3. BULL AVANZADO (40-60%): Máximos históricos, euforia alta
4. DISTRIBUCIÓN (60-80%): Techos, institucionales distribuyendo
5. MERCADO BAJISTA (80-100%): Corrección severa, reset

ADVERTENCIA:
Los patrones históricos son informativos pero no garantizan repetición. "Esta vez podría ser diferente" — aunque hasta ahora no lo ha sido.`
    },

    "rsu-btc-score": {
        title: "RSU BTC Score — Score de Acumulación",
        short: "Score compuesto 0-100: MA200W (40%) + MVRV (30%) + Puell (20%) + AHR999 (10%). Menor score = mayor oportunidad de acumulación.",
        long: `El RSU BTC Score es un indicador compuesto que combina 4 proxies de indicadores on-chain para generar una señal de acumulación en Bitcoin.

PONDERACIONES:
- MA200W (40%): El indicador más importante. Desviación del precio vs media de largo plazo.
- MVRV Z-Score (30%): Valoración relativa al valor realizado.
- Puell Multiple (20%): Stress de mineros como proxy de capitulación.
- AHR999 (10%): Índice específico de oportunidad de DCA.

INTERPRETACIÓN (INVERTIDO — menor = mejor oportunidad):
- Score 0-20 → OPORTUNIDAD EXTREMA → Todos los indicadores en zona de suelo
- Score 20-40 → ACUMULACIÓN FUERTE → Mayoría en zona de oportunidad
- Score 40-60 → ACUMULACIÓN MODERADA → Mix de señales
- Score 60-80 → NEUTRAL/ESPERA → Sin señal clara de oportunidad
- Score 80-100 → SOBRECOMPRA/RIESGO → Mercado caro, evitar entradas

ASIGNACIÓN SUGERIDA:
Varía según score y perfil de riesgo. Los porcentajes mostrados son orientativos para un inversor con tolerancia al riesgo media-alta.

DISCLAIMER: Estos son proxies, no los indicadores on-chain reales. Para análisis más preciso usar Glassnode.`
    },

    "btc-backtest": {
        title: "Backtest Histórico — BTC Stratum",
        short: "Simulación histórica de la estrategia: qué habría pasado si hubieras comprado cada vez que el RSU Score cruzó umbrales clave.",
        long: `El backtest simula la estrategia RSU BTC Stratum sobre datos históricos de los últimos 10 años para evaluar su efectividad histórica.

METODOLOGÍA:
- Capital inicial: $10,000
- Señal de compra: RSU Score cae por debajo del umbral (20, 40 o 60)
- Acción: Invertir 50% del capital disponible en BTC
- Señal de venta: RSU Score supera 80
- Datos: Cierre diario BTC/USD desde yfinance

MÉTRICAS:
- Retorno total: % de ganancia sobre capital inicial
- Capital final: valor en $ al final del período
- Alpha: diferencia vs Buy & Hold puro de BTC
- Operaciones: número de compras y ventas ejecutadas

LIMITACIONES IMPORTANTES:
1. Sin costes de transacción ni slippage
2. Ejecución perfecta al precio de cierre (imposible en la práctica)
3. Sin considerar impuestos
4. Datos históricos no garantizan resultados futuros
5. El backtest usa proxies, no indicadores on-chain reales

USE CASE:
El backtest sirve para validar conceptualmente la estrategia. Los resultados reales diferirán significativamente. Es una herramienta educativa, no una garantía de rentabilidad.`
    },

    "stress-test": {
        title: "Stress Test — Escenarios Adversos",
        short: "Escenarios adversos extremos para gestión de expectativas. Las probabilidades son estimaciones subjetivas, no predicciones.",
        long: `El Stress Test simula escenarios extremos adversos para que el inversor pueda prepararse mentalmente y definir su estrategia de gestión de riesgo.

ESCENARIOS INCLUIDOS:
1. Colapso de Exchange (FTX 2.0): -50% en precio. Pánico sistémico temporal.
2. Ban Regulatorio G7: -35%. Prohibición coordinada en economías desarrolladas.
3. Estanflación 5+ años: -60%. Macro muy adverso prolongado.
4. Ruptura Criptográfica: -90%. Vulnerabilidad SHA256 o ataque cuántico.

IMPORTANTE SOBRE LAS PROBABILIDADES:
Las probabilidades son ESTIMACIONES SUBJETIVAS del equipo RSU. No tienen base estadística rigurosa. Son aproximaciones para dar contexto, no predicciones científicas.

CÓMO USAR ESTA INFORMACIÓN:
1. Define tu pérdida máxima tolerable ANTES de invertir
2. Asegúrate de que tu posición sobrevive el peor escenario
3. Ten un plan para cada escenario (¿compro más? ¿vendo? ¿hold?)
4. Nunca inviertas más de lo que puedes permitirte perder completamente

El objetivo no es asustar sino preparar. Un inversor con plan sobrevive las crisis. Uno sin plan entra en pánico y vende en el peor momento.`
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