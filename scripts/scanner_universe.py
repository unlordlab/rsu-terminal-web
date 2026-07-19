#!/usr/bin/env python3
"""
RSU Terminal — Scanner Universo S&P 500
Calcula, para cada ticker del S&P 500, un set fijo de métricas técnicas
(RVOL, RS Percentile, Fase Weinstein, Score Técnico) y sube el resultado a un
GitHub Gist. Pensado para ejecutarse 1x/día vía GitHub Actions, después del
cierre de mercado — mismo patrón que scripts/thematic_scan.py y
scripts/rsrw_scan (motor embebido en rsrw_service.py).

IMPORTANTE — alcance de "Score Técnico" en v1:
Este script NO calcula el RSU Score v2 (backend/services/research_service.py
:_compute_rsu_score), porque ese score depende de datos FUNDAMENTALES por
ticker (estados financieros, Piotroski, insider trading, comparación
sectorial) que requieren 1 o más llamadas de red POR TICKER. Ejecutar eso
para 500 tickers cada noche multiplicaría por 5-10x el riesgo de rate-limit
y el tiempo de ejecución del workflow, algo que ya es un problema conocido
en scans grandes (ver comentarios de reintento en rsrw_service.py).

En su lugar, v1 calcula un "Score Técnico" (0-100) compuesto solo con datos
de precio/volumen que YA se descargan en este mismo scan (sin llamadas
adicionales): RS Percentile (50%) + Fase Weinstein (30%) + RVOL (20%).
Es intencionadamente parecido en espíritu al RSU Score (gatekeeper + score),
pero solo con la pata técnica. La pata fundamental (RSU Score v2 real) se
puede añadir en el frontend como enriquecimiento on-demand SOLO sobre los
pocos tickers que pasen el filtro (llamando a /api/v1/research/{ticker}),
nunca sobre el universo completo — así evitamos el problema de escala.

Script standalone (no importa nada de backend/), mismo motivo que
thematic_scan.py: correr en el runner de GitHub Actions sin depender del
entorno de FastAPI.
"""

import os
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import yfinance as yf

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("SCANNER_GIST_ID", "")
GIST_FILE  = "scanner_scan.json"

BENCHMARK    = "SPY"
PERIODS      = [21, 63, 126]
WEIGHTS      = {21: 0.20, 63: 0.35, 126: 0.45}
EMA_SMOOTH   = 10
RVOL_WINDOW  = 20   # media de volumen — ver hilo de decisión: 20d, no 14d (sin base estándar) ni 50d (menos reactivo)
BATCH_SIZE   = 40
BATCH_SLEEP  = 1.8

# ── UNIVERSO S&P 500 (mismo diccionario embebido que rsrw_service.py — única
# fuente de verdad para el universo: si actualizas constituyentes, actualiza
# AMBOS archivos, o mejor, considera extraer a un JSON compartido más adelante) ──
SP500_SECTOR_MAP = {
    "AAPL":"Information Technology","MSFT":"Information Technology","NVDA":"Information Technology",
    "AMZN":"Consumer Discretionary","GOOGL":"Communication Services","GOOG":"Communication Services",
    "META":"Communication Services","TSLA":"Consumer Discretionary","AVGO":"Information Technology",
    "JPM":"Financials","LLY":"Health Care","V":"Financials","UNH":"Health Care","XOM":"Energy",
    "MA":"Financials","JNJ":"Health Care","PG":"Consumer Staples","HD":"Consumer Discretionary",
    "MRK":"Health Care","COST":"Consumer Staples","ABBV":"Health Care","CVX":"Energy","BAC":"Financials",
    "KO":"Consumer Staples","CRM":"Information Technology","PEP":"Consumer Staples","TMO":"Health Care",
    "WFC":"Financials","NFLX":"Communication Services","ORCL":"Information Technology","AMD":"Information Technology",
    "ACN":"Information Technology","ADBE":"Information Technology","LIN":"Materials","MCD":"Consumer Discretionary",
    "WMT":"Consumer Staples","CSCO":"Information Technology","IBM":"Information Technology","GS":"Financials",
    "GE":"Industrials","HON":"Industrials","DIS":"Communication Services","CAT":"Industrials","RTX":"Industrials",
    "AMGN":"Health Care","VZ":"Communication Services","T":"Communication Services","CMCSA":"Communication Services",
    "PFE":"Health Care","ABT":"Health Care","TXN":"Information Technology","MS":"Financials","NEE":"Utilities",
    "BMY":"Health Care","SPGI":"Financials","DHR":"Health Care","UNP":"Industrials","LOW":"Consumer Discretionary",
    "BLK":"Financials","ISRG":"Health Care","GILD":"Health Care","SYK":"Health Care","CI":"Health Care",
    "BSX":"Health Care","ELV":"Health Care","ITW":"Industrials","DE":"Industrials","LMT":"Industrials",
    "COP":"Energy","EOG":"Energy","SLB":"Energy","OXY":"Energy","FCX":"Materials","PLD":"Real Estate",
    "AMT":"Real Estate","CCI":"Real Estate","EQIX":"Real Estate","PSA":"Real Estate","CRWD":"Information Technology",
    "PANW":"Information Technology","SNOW":"Information Technology","PLTR":"Information Technology","NET":"Information Technology",
    "UBER":"Industrials","ABNB":"Consumer Discretionary","DXCM":"Health Care","ZTS":"Health Care","BIIB":"Health Care",
    "MRNA":"Health Care","NKE":"Consumer Discretionary","LULU":"Consumer Discretionary","TGT":"Consumer Staples",
    "TJX":"Consumer Discretionary","UPS":"Industrials","FDX":"Industrials","NSC":"Industrials","CSX":"Industrials",
    "DAL":"Industrials","INTC":"Information Technology","QCOM":"Information Technology","MU":"Information Technology",
    "KLAC":"Information Technology","LRCX":"Information Technology","AMAT":"Information Technology","SNPS":"Information Technology",
    "CDNS":"Information Technology","ADI":"Information Technology","MCHP":"Information Technology","AXP":"Financials",
    "C":"Financials","SCHW":"Financials","PGR":"Financials","CB":"Financials","MMC":"Financials","AON":"Financials",
    "ICE":"Financials","CME":"Financials","USB":"Financials","PNC":"Financials","TFC":"Financials","COF":"Financials",
    "AIG":"Financials","MET":"Financials","PRU":"Financials","TRV":"Financials","ALL":"Financials","AFL":"Financials",
    "AJG":"Financials","FIS":"Financials","FI":"Financials","BK":"Financials","STT":"Financials","NTRS":"Financials",
    "MTB":"Financials","HBAN":"Financials","RF":"Financials","FITB":"Financials","KEY":"Financials","CFG":"Financials",
    "WTW":"Financials","BRO":"Financials","ACGL":"Financials","CINF":"Financials","L":"Financials","GL":"Financials",
    "PFG":"Financials","RJF":"Financials","NDAQ":"Financials","MCO":"Financials","MSCI":"Financials","IVZ":"Financials",
    "BEN":"Financials","SYF":"Financials","DFS":"Financials","PYPL":"Financials","WU":"Financials","COIN":"Financials",
    "PEG":"Utilities","DUK":"Utilities","SO":"Utilities","D":"Utilities","AEP":"Utilities","EXC":"Utilities",
    "SRE":"Utilities","XEL":"Utilities","ED":"Utilities","WEC":"Utilities","ES":"Utilities","FE":"Utilities",
    "ETR":"Utilities","AEE":"Utilities","CMS":"Utilities","CNP":"Utilities","ATO":"Utilities","NI":"Utilities",
    "LNT":"Utilities","EVRG":"Utilities","PNW":"Utilities","NRG":"Utilities","AES":"Utilities","PPL":"Utilities",
    "DTE":"Utilities","AWK":"Utilities","AVB":"Real Estate","EQR":"Real Estate","AEM":"Materials","AMH":"Real Estate",
    "INVH":"Real Estate","ESS":"Real Estate","MAA":"Real Estate","UDR":"Real Estate","CPT":"Real Estate",
    "EXR":"Real Estate","DLR":"Real Estate","O":"Real Estate","WELL":"Real Estate","VTR":"Real Estate",
    "ARE":"Real Estate","BXP":"Real Estate","SPG":"Real Estate","REG":"Real Estate","FRT":"Real Estate",
    "KIM":"Real Estate","HST":"Real Estate","VICI":"Real Estate","IRM":"Real Estate","SBAC":"Real Estate",
    "WY":"Real Estate","CBRE":"Real Estate","JLL":"Real Estate","NVR":"Consumer Discretionary","PHM":"Consumer Discretionary",
    "DHI":"Consumer Discretionary","LEN":"Consumer Discretionary","KBH":"Consumer Discretionary","BLDR":"Industrials",
    "MAS":"Industrials","VMC":"Materials","MLM":"Materials","NUE":"Materials","STLD":"Materials","X":"Materials",
    "CLF":"Materials","AA":"Materials","ALB":"Materials","FMC":"Materials","CE":"Materials","DOW":"Materials",
    "DD":"Materials","LYB":"Materials","PPG":"Materials","SHW":"Materials","ECL":"Materials","IFF":"Materials",
    "APD":"Materials","CTVA":"Materials","MOS":"Materials","EMN":"Materials","AVY":"Materials","PKG":"Materials",
    "IP":"Materials","SEE":"Materials","BALL":"Materials","CCK":"Materials","WRK":"Materials","NEM":"Materials",
    "GOLD":"Materials","SCCO":"Materials","FCX2":"Materials","BG":"Consumer Staples","ADM":"Consumer Staples",
    "TSN":"Consumer Staples","HRL":"Consumer Staples","CAG":"Consumer Staples","CPB":"Consumer Staples",
    "K":"Consumer Staples","GIS":"Consumer Staples","SJM":"Consumer Staples","MKC":"Consumer Staples",
    "HSY":"Consumer Staples","MDLZ":"Consumer Staples","KHC":"Consumer Staples","STZ":"Consumer Staples",
    "BF.B":"Consumer Staples","TAP":"Consumer Staples","MNST":"Consumer Staples","KDP":"Consumer Staples",
    "PM":"Consumer Staples","MO":"Consumer Staples","CL":"Consumer Staples","KMB":"Consumer Staples",
    "CHD":"Consumer Staples","CLX":"Consumer Staples","CASY":"Consumer Staples","CHRW":"Industrials","CTAS":"Industrials",
    "EXPD":"Industrials","JBHT":"Industrials","ODFL":"Industrials","LDOS":"Industrials","HII":"Industrials",
    "GD":"Industrials","NOC":"Industrials","TXT":"Industrials","TDY":"Industrials","HWM":"Industrials",
    "PH":"Industrials","DOV":"Industrials","ROK":"Industrials","EMR":"Industrials","ETN":"Industrials",
    "AME":"Industrials","XYL":"Industrials","IEX":"Industrials","PWR":"Industrials","FAST":"Industrials",
    "PCAR":"Industrials","CMI":"Industrials","WAB":"Industrials","ALLE":"Industrials","JCI":"Industrials",
    "CARR":"Industrials","OTIS":"Industrials","SWK":"Industrials","SNA":"Industrials","GWW":"Industrials",
    "URI":"Industrials","WM":"Industrials","RSG":"Industrials","NDSN":"Industrials","IR":"Industrials",
    "GNRC":"Industrials","PAYX":"Industrials","ADP":"Industrials","BR":"Industrials","VRSK":"Industrials",
    "EFX":"Industrials","ROL":"Industrials","CTSH":"Information Technology","ACN2":"Information Technology",
    "INTU":"Information Technology","NOW":"Information Technology","ADSK":"Information Technology",
    "WDAY":"Information Technology","TEAM":"Information Technology","HUBS":"Information Technology",
    "DDOG":"Information Technology","ZS":"Information Technology","FTNT":"Information Technology",
    "GEN":"Information Technology","AKAM":"Information Technology","JNPR":"Information Technology",
    "FFIV":"Information Technology","GDDY":"Information Technology","EPAM":"Information Technology",
    "PTC":"Information Technology","ANSS":"Information Technology","KEYS":"Information Technology",
    "TER":"Information Technology","TYL":"Information Technology","TRMB":"Information Technology",
    "ZBRA":"Information Technology","NTAP":"Information Technology","WDC":"Information Technology",
    "STX":"Information Technology","HPQ":"Information Technology","DELL":"Information Technology",
    "HPE":"Information Technology","ON":"Information Technology","SWKS":"Information Technology",
    "QRVO":"Information Technology","MPWR":"Information Technology","ENPH":"Information Technology",
    "SEDG":"Information Technology","FSLR":"Information Technology","TXN2":"Information Technology",
    "APH":"Information Technology","TEL":"Information Technology","GLW":"Information Technology",
    "VRSN":"Information Technology","PAYC":"Information Technology","MSI":"Information Technology",
    "CDW":"Information Technology","JBL":"Information Technology","NXPI":"Information Technology",
    "ASML":"Information Technology","MRVL":"Information Technology","SMCI":"Information Technology",
    "ANET":"Information Technology","CSGP":"Real Estate","FDS":"Financials","MKTX":"Financials",
    "CBOE":"Financials","NWSA":"Communication Services","NWS":"Communication Services","FOXA":"Communication Services",
    "FOX":"Communication Services","PARA":"Communication Services","WBD":"Communication Services",
    "LYV":"Communication Services","TTWO":"Communication Services","EA":"Communication Services",
    "OMC":"Communication Services","IPG":"Communication Services","MTCH":"Communication Services",
    "TMUS":"Communication Services","CHTR":"Communication Services","DISH":"Communication Services",
    "EBAY":"Consumer Discretionary","ETSY":"Consumer Discretionary","BKNG":"Consumer Discretionary",
    "EXPE":"Consumer Discretionary","MAR":"Consumer Discretionary","HLT":"Consumer Discretionary",
    "RCL":"Consumer Discretionary","CCL":"Consumer Discretionary","NCLH":"Consumer Discretionary",
    "MGM":"Consumer Discretionary","WYNN":"Consumer Discretionary","LVS":"Consumer Discretionary",
    "DRI":"Consumer Discretionary","YUM":"Consumer Discretionary","CMG":"Consumer Discretionary",
    "SBUX":"Consumer Discretionary","DPZ":"Consumer Discretionary","QSR":"Consumer Discretionary",
    "ORLY":"Consumer Discretionary","AZO":"Consumer Discretionary","AAP":"Consumer Discretionary",
    "GPC":"Consumer Discretionary","BBY":"Consumer Discretionary","ULTA":"Consumer Discretionary",
    "ROST":"Consumer Discretionary","GPS":"Consumer Discretionary","TPR":"Consumer Discretionary",
    "RL":"Consumer Discretionary","VFC":"Consumer Discretionary","PVH":"Consumer Discretionary",
    "DECK":"Consumer Discretionary","CROX":"Consumer Discretionary","KMX":"Consumer Discretionary",
    "F":"Consumer Discretionary","GM":"Consumer Discretionary","APTV":"Consumer Discretionary",
    "BWA":"Consumer Discretionary","LKQ":"Consumer Discretionary","DPZ2":"Consumer Discretionary",
    "POOL":"Consumer Discretionary","WHR":"Consumer Discretionary","NWL":"Consumer Discretionary",
    "HAS":"Consumer Discretionary","MAT":"Consumer Discretionary","TPX":"Consumer Discretionary",
    "LEG":"Consumer Discretionary","CZR":"Consumer Discretionary","PENN":"Consumer Discretionary",
    "BBWI":"Consumer Discretionary","KSS":"Consumer Discretionary","M":"Consumer Discretionary",
    "JWN":"Consumer Discretionary","DG":"Consumer Discretionary","DLTR":"Consumer Discretionary",
    "BJ":"Consumer Staples","KR":"Consumer Staples","SYY":"Consumer Staples","USFD":"Consumer Staples",
    "WBA":"Consumer Staples","CVS":"Health Care","CAH":"Health Care","MCK":"Health Care","COR":"Health Care",
    "HCA":"Health Care","UHS":"Health Care","DVA":"Health Care","CNC":"Health Care","MOH":"Health Care",
    "HUM":"Health Care","CNC2":"Health Care","ALGN":"Health Care","IDXX":"Health Care","IQV":"Health Care",
    "A":"Health Care","WAT":"Health Care","MTD":"Health Care","RMD":"Health Care","ZBH":"Health Care",
    "EW":"Health Care","BAX":"Health Care","BDX":"Health Care","COO":"Health Care","HOLX":"Health Care",
    "PODD":"Health Care","DXC":"Information Technology","VTRS":"Health Care","ORG":"Health Care",
    "REGN":"Health Care","VRTX":"Health Care","INCY":"Health Care","SGEN":"Health Care","ALNY":"Health Care",
    "BMRN":"Health Care","TECH":"Health Care","CRL":"Health Care","CTLT":"Health Care","RVTY":"Health Care",
    "PFE2":"Health Care","JNJ2":"Health Care","ABC":"Health Care","XRAY":"Health Care","SOLV":"Health Care",
    "EOG2":"Energy","MPC":"Energy","PSX":"Energy","VLO":"Energy","HES":"Energy","DVN":"Energy",
    "FANG":"Energy","CTRA":"Energy","APA":"Energy","MRO":"Energy","BKR":"Energy","HAL":"Energy",
    "WMB":"Energy","KMI":"Energy","OKE":"Energy","TRGP":"Energy","EQT":"Energy","NOV":"Energy",
    "AAL":"Industrials","UAL":"Industrials","LUV":"Industrials","ALK":"Industrials","SAVE":"Industrials",
    "EXC2":"Utilities","PCG":"Utilities","EIX":"Utilities","EMN2":"Materials","DOC":"Real Estate",
    "EQH":"Financials","GEHC":"Health Care","KVUE":"Consumer Staples","VLTO":"Industrials","GEV":"Industrials",
    "SW":"Materials","SOLV2":"Health Care",
}
# Eliminar entradas placeholder erróneas (tickers duplicados por error al construir
# la lista a mano, con sufijo numérico añadido para evitar colisión de claves).
# El ticker real correspondiente ya existe en el diccionario con el sector correcto.
_PLACEHOLDER_KEYS = ["FCX2", "ACN2", "TXN2", "DPZ2", "CNC2", "PFE2", "JNJ2", "EOG2", "EXC2", "EMN2", "SOLV2",
                      "ABC"]  # ABC = ticker antiguo de Cencora, renombrado a COR en 2023
for _k in _PLACEHOLDER_KEYS:
    SP500_SECTOR_MAP.pop(_k, None)
del _PLACEHOLDER_KEYS, _k

# ── RUSSELL 2000 — SOLO PARA AMPLITUD, NO PARA RS/FASE/TEMÁTICO ─────────────
# Extiende el universo usado para McClellan/ABI/A-D/NH-NL (ver _compute_breadth_history
# más abajo, y run_scan) más allá de las 500 grandes del S&P 500 — el motivo real:
# NYSE completo (~2.800 valores) fue descartado por estar contaminado con ETFs,
# preferentes y ADRs extranjeros que diluyen la señal (Yahoo ^ADV/^DEC ya lo
# demostraba, ver comentario en market_service.py). El Russell 2000 es el
# benchmark estándar de "participación small-cap" — cuando el S&P 500 sube solo
# por unas pocas megacaps mientras el Russell se queda atrás, es la señal
# clásica de liderazgo estrecho que el universo de solo 525 tickers no puede ver.
#
# DELIBERADAMENTE NO se mezcla con SP500_SECTOR_MAP ni se usa en el bucle de
# scoring RS/fase/temático — eso cambiaría los rankings existentes del Scanner
# (percentiles de RS relativos al universo, clasificación de fases, etc.), que
# ahora mismo dependen de comparar solo dentro de las 500 grandes. Amplitud y
# scoring son necesidades distintas con universos distintos a propósito.
#
# Fuente: export de TradingView Screener (filtro Index = Russell 2000),
# 1.961 tickers, capturado 2026-07-14. Como cualquier lista estática de
# constituyentes de índice, se desactualizará con el tiempo según el Russell
# reconstituya — igual que ya pasa con SP500_SECTOR_MAP, hace falta refrescarla
# de vez en cuando a mano, no cada noche.

RUSSELL2000_TICKERS = [
    "AAMI", "AAP", "AAT", "ABAT", "ABCB", "ABEO", "ABG", "ABM", "ABOS", "ABR",
    "ABSI", "ABUS", "ABX", "ACA", "ACAD", "ACCO", "ACDC", "ACEL", "ACH", "ACHC",
    "ACHR", "ACHV", "ACIC", "ACIW", "ACLS", "ACMR", "ACNB", "ACR", "ACRE", "ACRS",
    "ACT", "ACTG", "ACTU", "ACU", "ACVA", "ADAM", "ADCT", "ADEA", "ADMA", "ADNT",
    "ADPT", "ADTN", "ADUS", "ADV", "AEBI", "AEHR", "AEO", "AESI", "AEVA", "AEYE",
    "AFRI", "AGEN", "AGIO", "AGL", "AGM", "AGNT", "AGX", "AGYS", "AHCO", "AHRT",
    "AI", "AII", "AIN", "AIOT", "AIP", "AIR", "AIRJ", "AIRO", "AIRS", "AKBA",
    "AKR", "AKTS", "ALCO", "ALEC", "ALG", "ALGT", "ALH", "ALHC", "ALKS", "ALKT",
    "ALLO", "ALMR", "ALMS", "ALMU", "ALNT", "ALOY", "ALRM", "ALRS", "ALT", "ALTG",
    "ALTI", "ALTO", "ALX", "ALXO", "AMAL", "AMBA", "AMBP", "AMBQ", "AMC", "AMCX",
    "AMLX", "AMN", "AMPH", "AMPL", "AMPX", "AMPY", "AMR", "AMRC", "AMRX", "AMSC",
    "AMSF", "AMTB", "AMTX", "ANAB", "ANDE", "ANF", "ANGI", "ANGO", "ANIK", "ANIP",
    "ANNX", "ANRO", "ANTX", "AOMR", "AORT", "AOSL", "AOUT", "AP", "APAM", "APC",
    "APEI", "APGE", "APLE", "APOG", "APPN", "APPS", "AQST", "ARAY", "ARCB", "ARCT",
    "ARDT", "ARDX", "AREC", "AREN", "ARHS", "ARI", "ARKO", "ARL", "ARLO", "ARMP",
    "AROC", "AROW", "ARQT", "ARR", "ARRY", "ARTV", "ARVN", "ARX", "ASAN", "ASB",
    "ASC", "ASH", "ASIC", "ASIX", "ASLE", "ASMB", "ASO", "ASPI", "ASPN", "ASST",
    "ASTE", "ASTH", "ASUR", "ASYS", "ATAI", "ATEC", "ATEN", "ATEX", "ATKR", "ATLC",
    "ATLO", "ATMU", "ATNI", "ATOM", "ATRC", "ATRO", "AUB", "AUPH", "AURA", "AVA",
    "AVAH", "AVBC", "AVBH", "AVBP", "AVEX", "AVIR", "AVLN", "AVNS", "AVNT", "AVNW",
    "AVO", "AVPT", "AVR", "AVTX", "AVXL", "AWR", "AX", "AXGN", "AXTI", "AZTA",
    "AZZ", "BALY", "BANC", "BAND", "BANF", "BANR", "BATRA", "BBAI", "BBBY", "BBCP",
    "BBNX", "BBSI", "BBT", "BBW", "BCAL", "BCAX", "BCBP", "BCC", "BCML", "BCO",
    "BCPC", "BCRX", "BDC", "BDN", "BDTX", "BEAM", "BEEP", "BELFA", "BETA", "BETR",
    "BFC", "BFH", "BFLY", "BFS", "BFST", "BGC", "BGS", "BH", "BHB", "BHE",
    "BHR", "BHRB", "BHVN", "BIOA", "BJRI", "BKD", "BKE", "BKH", "BKKT", "BKSY",
    "BKTI", "BKU", "BKV", "BL", "BLBD", "BLFS", "BLKB", "BLMN", "BLND", "BLX",
    "BLZE", "BMBL", "BMI", "BMRC", "BNAI", "BNED", "BNL", "BNTC", "BOBS", "BOC",
    "BOH", "BOOT", "BORR", "BOW", "BOX", "BPRN", "BRBR", "BRBS", "BRCB", "BRCC",
    "BRSL", "BRSP", "BRT", "BRZE", "BSRR", "BSVN", "BTBT", "BTDR", "BTSG", "BTU",
    "BULL", "BUSE", "BV", "BVFL", "BVS", "BW", "BWB", "BWFG", "BWIN", "BWMN",
    "BXC", "BXMT", "BY", "BZAI", "BZH", "CABA", "CABO", "CAC", "CADL", "CAKE",
    "CAL", "CALM", "CALX", "CALY", "CAMP", "CAPR", "CARE", "CARG", "CARL", "CARS",
    "CASH", "CASS", "CATX", "CATY", "CBAN", "CBFV", "CBIO", "CBK", "CBL", "CBLL",
    "CBNA", "CBNK", "CBRL", "CBT", "CBU", "CBZ", "CC", "CCB", "CCBG", "CCCC",
    "CCNE", "CCO", "CCOI", "CCRN", "CCS", "CCSI", "CD", "CDNA", "CDNL", "CDP",
    "CDRE", "CDXS", "CDZI", "CECO", "CELC", "CENT", "CENX", "CERS", "CERT", "CEVA",
    "CFBK", "CFFI", "CFFN", "CGEM", "CGON", "CHCI", "CHCO", "CHCT", "CHEF", "CHMG",
    "CHPT", "CHRS", "CIA", "CIFR", "CIM", "CIVB", "CIX", "CLB", "CLBK", "CLDT",
    "CLDX", "CLFD", "CLMB", "CLMT", "CLNE", "CLOV", "CLPT", "CLSK", "CLVT", "CLW",
    "CLYM", "CMC", "CMCL", "CMCO", "CMDB", "CMP", "CMPR", "CMPX", "CMRC", "CMRE",
    "CMT", "CMTG", "CMTV", "CNDT", "CNK", "CNMD", "CNNE", "CNO", "CNOB", "CNR",
    "CNS", "CNTB", "CNTN", "CNTX", "CNX", "CNXC", "CNXN", "COCO", "CODI", "COFS",
    "COGT", "COHU", "COLL", "COMP", "CON", "CORZ", "COSO", "COTY", "COUR", "CPF",
    "CPK", "CPRI", "CPRX", "CPS", "CPSS", "CRAI", "CRBP", "CRBU", "CRC", "CRCT",
    "CRD-A", "CRGY", "CRI", "CRK", "CRMD", "CRML", "CRNC", "CRNX", "CRSP", "CRSR",
    "CRVL", "CRVS", "CSIQ", "CSPI", "CSR", "CSTL", "CSTM", "CSV", "CSW", "CTBI",
    "CTEV", "CTGO", "CTKB", "CTMX", "CTNM", "CTO", "CTOS", "CTRE", "CTRI", "CTRN",
    "CTS", "CUBI", "CURB", "CURI", "CURV", "CV", "CVBF", "CVCO", "CVEO", "CVGI",
    "CVI", "CVLG", "CVLT", "CVRX", "CVSA", "CWBC", "CWCO", "CWH", "CWK", "CWST",
    "CWT", "CXDO", "CXM", "CXT", "CXW", "CYH", "CYRX", "CYTK", "CZFS", "CZNC",
    "CZWI", "DAKT", "DAN", "DAVE", "DBD", "DBI", "DBRG", "DC", "DCH", "DCO",
    "DCOM", "DCTH", "DDD", "DEA", "DEC", "DEI", "DFH", "DFIN", "DFTX", "DGICA",
    "DGII", "DHC", "DHT", "DIBS", "DIN", "DIOD", "DJCO", "DJT", "DK", "DLO",
    "DLX", "DMAC", "DMC", "DMRA", "DMRC", "DNA", "DNLI", "DNOW", "DNTH", "DNUT",
    "DOLE", "DOMO", "DORM", "DOUG", "DRH", "DRVN", "DSGN", "DSGR", "DSP", "DTIL",
    "DUOT", "DV", "DX", "DXC", "DXPE", "DYN", "EAF", "EAT", "EBC", "EBF",
    "EBMT", "EBS", "ECBK", "ECPG", "ECVT", "EDIT", "EE", "EFC", "EFOR", "EFSC",
    "EFSI", "EGAN", "EGBN", "EGHT", "EGY", "EIG", "EIKN", "ELA", "ELDN", "ELMD",
    "ELMT", "ELTX", "ELVN", "EMBC", "ENOV", "ENR", "ENS", "ENTA", "ENVA", "ENVX",
    "EOLS", "EOSE", "EPAC", "EPC", "EPM", "EPRT", "EPSN", "EQBK", "ERAS", "ERII",
    "ESCA", "ESE", "ESNT", "ESOA", "ESP", "ESQ", "ESRT", "ESTA", "ETD", "ETON",
    "EVC", "EVCM", "EVER", "EVEX", "EVGO", "EVH", "EVI", "EVLV", "EVMN", "EVTC",
    "EWTX", "EXPO", "EXTR", "EYE", "EYPT", "FA", "FBIZ", "FBK", "FBLA", "FBNC",
    "FBP", "FBRT", "FBRX", "FBYD", "FC", "FCAP", "FCBC", "FCCO", "FCEL", "FCF",
    "FCFS", "FCPT", "FDBC", "FDMT", "FEIM", "FELE", "FENC", "FET", "FF", "FFBC",
    "FFIN", "FG", "FGBI", "FHTX", "FIBK", "FIGS", "FINW", "FIP", "FISI", "FIVN",
    "FIZZ", "FJET", "FLG", "FLGT", "FLNC", "FLNG", "FLO", "FLOC", "FLR", "FLWS",
    "FLXS", "FLY", "FLYW", "FLYX", "FMAO", "FMBH", "FMC", "FMNB", "FNKO", "FNLC",
    "FNRN", "FOA", "FOR", "FOSL", "FOXF", "FPI", "FRAF", "FRBA", "FRD", "FRME",
    "FROG", "FRPH", "FRSH", "FRST", "FSBC", "FSBW", "FSLY", "FSS", "FSTR", "FSUN",
    "FTDR", "FTK", "FTLF", "FTRE", "FUBO", "FUL", "FULC", "FULT", "FUN", "FUNC",
    "FVCB", "FVR", "FWDI", "FWRD", "FWRG", "FXNC", "GABC", "GALT", "GATX", "GBCI",
    "GBFH", "GBTG", "GBX", "GCBC", "GCMG", "GCO", "GCT", "GDOT", "GDYN", "GEF",
    "GEMI", "GENB", "GENC", "GENI", "GEO", "GERN", "GEVO", "GFF", "GHC", "GHM",
    "GIC", "GIII", "GKOS", "GLIBA", "GLNG", "GLOB", "GLRE", "GLSI", "GLUE", "GNE",
    "GNK", "GNL", "GNW", "GO", "GOGO", "GOLD", "GOLF", "GOOD", "GORO", "GPGI",
    "GPI", "GPOR", "GPRE", "GPRO", "GRAL", "GRBK", "GRC", "GRDN", "GRND", "GRNT",
    "GRPN", "GSBC", "GSHD", "GSIT", "GSM", "GT", "GTM", "GTN", "GTX", "GTY",
    "GVA", "GWRS", "GYRE", "HAE", "HAFC", "HAPN", "HASI", "HBB", "HBCP", "HBNC",
    "HBT", "HCC", "HCI", "HCKT", "HCSG", "HDSN", "HE", "HELE", "HFFG", "HFWA",
    "HG", "HGV", "HIFS", "HIMS", "HIPO", "HIW", "HLF", "HLIO", "HLIT", "HLLY",
    "HLMN", "HLX", "HMH", "HMN", "HNGE", "HNI", "HNRG", "HNST", "HNVR", "HOG",
    "HOMB", "HOPE", "HOV", "HP", "HPK", "HPP", "HQI", "HQY", "HRI", "HRMY",
    "HROW", "HRTG", "HRTX", "HSTM", "HTB", "HTFL", "HTH", "HTLD", "HTO", "HTZ",
    "HUBG", "HUN", "HURN", "HUT", "HVT", "HWBK", "HWC", "HWKN", "HY", "HYLN",
    "HYMC", "HYPR", "HZO", "IART", "IBCP", "IBEX", "IBOC", "IBP", "IBRX", "IBTA",
    "ICFI", "ICHR", "ICUI", "IDCC", "IDN", "IDR", "IDT", "IDYA", "IE", "IHRT",
    "III", "IIIN", "IIIV", "IIPR", "IKT", "ILPT", "IMAX", "IMKTA", "IMMR", "IMMX",
    "IMNM", "IMRX", "IMVT", "IMXI", "INBK", "INBX", "INDB", "INDI", "INDV", "INFQ",
    "INFU", "INGN", "INN", "INNV", "INOD", "INR", "INSE", "INSG", "INSP", "INSW",
    "INTA", "INTT", "INV", "INVA", "INVX", "IOSP", "IOVA", "IPAR", "IPI", "IPSC",
    "IRD", "IRMD", "IRON", "IRT", "IRTC", "IRWD", "ISBA", "ISPR", "ISSC", "ISTR",
    "ITGR", "ITIC", "ITRI", "IVR", "IVT", "IVVD", "JACK", "JAKK", "JANX", "JBGS",
    "JBI", "JBIO", "JBLU", "JBSS", "JBTM", "JCAP", "JILL", "JJSF", "JMSB", "JOBY",
    "JOE", "JOUT", "JRVR", "JXN", "KAI", "KALU", "KBH", "KE", "KEEL", "KELYA",
    "KFRC", "KFY", "KG", "KGS", "KIDS", "KINS", "KLC", "KLIC", "KLRA", "KLTR",
    "KMPR", "KMT", "KMTS", "KN", "KNF", "KNSA", "KNTK", "KOD", "KODK", "KOP",
    "KOPN", "KORE", "KOS", "KPTI", "KREF", "KRG", "KRMD", "KRNY", "KRO", "KROS",
    "KRRO", "KRT", "KRUS", "KRYS", "KSS", "KTB", "KURA", "KVHI", "KWR", "KWY",
    "KYMR", "KYTX", "LADR", "LAND", "LARK", "LASR", "LAUR", "LAW", "LBRT", "LBRX",
    "LCID", "LCII", "LCNB", "LCTX", "LCUT", "LDI", "LE", "LEE", "LEG", "LEGH",
    "LENZ", "LEU", "LFCR", "LFMD", "LFST", "LFT", "LGIH", "LGN", "LGND", "LIF",
    "LILA", "LINC", "LIND", "LION", "LIVN", "LKFN", "LMAT", "LMB", "LMND", "LMNR",
    "LMRI", "LNN", "LNSR", "LNTH", "LOB", "LOCO", "LODE", "LOVE", "LPG", "LPRO",
    "LPTH", "LQDA", "LQDT", "LRMR", "LRN", "LTBR", "LTC", "LTH", "LTRX", "LUCD",
    "LUMN", "LUNR", "LVWR", "LWAY", "LWLG", "LXEO", "LXFR", "LXP", "LXRX", "LXU",
    "LYEL", "LYTS", "LZ", "LZB", "LZM", "MAC", "MAGN", "MAMA", "MAN", "MANE",
    "MARA", "MASS", "MATV", "MATW", "MATX", "MAX", "MAZE", "MBC", "MBI", "MBIN",
    "MBUU", "MBWM", "MBX", "MC", "MCB", "MCBS", "MCFT", "MCHB", "MCRI", "MCS",
    "MCY", "MD", "MDV", "MDWD", "MDXG", "MEC", "MEI", "METC", "MFA", "MFIN",
    "MG", "MGEE", "MGNI", "MGNX", "MGPI", "MGRC", "MGTX", "MGY", "MH", "MHO",
    "MIAX", "MIR", "MIRM", "MITK", "MITT", "MKTW", "MLAB", "MLKN", "MLP", "MLR",
    "MLYS", "MMED", "MMI", "MMS", "MMSI", "MNKD", "MNPR", "MNRO", "MNSB", "MNTK",
    "MNTN", "MOG-A", "MOV", "MPAA", "MPB", "MPLT", "MPTI", "MQ", "MRAM", "MRBK",
    "MRCY", "MRTN", "MRVI", "MRX", "MSBI", "MSEX", "MSGE", "MTH", "MTRN", "MTRX",
    "MTUS", "MTW", "MTX", "MUR", "MUX", "MVBF", "MVST", "MWA", "MXL", "MYE",
    "MYFW", "MYGN", "MYRG", "MZTI", "NABL", "NAGE", "NAT", "NATH", "NATL", "NATR",
    "NAUT", "NAVI", "NAVN", "NB", "NBBK", "NBHC", "NBN", "NBR", "NBTB", "NC",
    "NCMI", "NCNO", "NE", "NECB", "NEO", "NEOG", "NERV", "NESR", "NEWT", "NEXN",
    "NEXT", "NFBK", "NG", "NGNE", "NGS", "NGVC", "NGVT", "NHC", "NHI", "NHP",
    "NIC", "NJR", "NKSH", "NKTR", "NKTX", "NL", "NLOP", "NMAX", "NMIH", "NMRA",
    "NMRK", "NN", "NNE", "NNI", "NODK", "NOG", "NOVT", "NP", "NPB", "NPCE",
    "NPK", "NPKI", "NPO", "NPWR", "NRC", "NRDS", "NREF", "NRGV", "NRIM", "NRIX",
    "NSIT", "NSP", "NSSC", "NTB", "NTCT", "NTGR", "NTLA", "NTST", "NUAI", "NUS",
    "NUTX", "NUVB", "NUVL", "NVAX", "NVCR", "NVCT", "NVEC", "NVGS", "NVRI", "NVTS",
    "NWBI", "NWE", "NWFL", "NWL", "NWN", "NWPX", "NX", "NXDR", "NXDT", "NXRT",
    "OABI", "OBIO", "OBK", "OBT", "OCFC", "OCGN", "OCUL", "ODC", "ODD", "OEC",
    "OFG", "OFIX", "OFLX", "OFRM", "OGS", "OI", "OII", "OIS", "OKUR", "OLMA",
    "OLP", "OMCL", "OMDA", "OMER", "ONB", "ONDS", "ONEW", "ONIT", "ONL", "ONT",
    "OOMA", "OPAL", "OPBK", "OPCH", "OPEN", "OPFI", "OPK", "OPLN", "OPRT", "OPTU",
    "OPTX", "ORA", "ORC", "ORGO", "ORIC", "ORKA", "ORMP", "ORN", "ORRF", "OSBC",
    "OSCR", "OSG", "OSIS", "OSPN", "OSS", "OSUR", "OSW", "OTTR", "OUST", "OUT",
    "OVBC", "OVID", "OVLY", "OXM", "PACB", "PACK", "PACS", "PAGS", "PAHC", "PAL",
    "PALI", "PAMT", "PANL", "PAR", "PARR", "PATK", "PAX", "PAY", "PAYO", "PAYS",
    "PBF", "PBFS", "PBH", "PBI", "PBYI", "PCB", "PCRX", "PCT", "PCVX", "PCYO",
    "PD", "PDEX", "PDFS", "PDLB", "PDM", "PDYN", "PEB", "PEBK", "PEBO", "PECO",
    "PENG", "PENN", "PESI", "PFBC", "PFIS", "PFS", "PFSI", "PGC", "PGEN", "PGNY",
    "PHAT", "PHIN", "PHR", "PI", "PII", "PINE", "PIPR", "PJT", "PK", "PKBK",
    "PKE", "PKOH", "PLAB", "PLAY", "PLBC", "PLBY", "PLGO", "PLMR", "PLOW", "PLPC",
    "PLSE", "PLTK", "PLUG", "PLUS", "PLX", "PLXS", "PMT", "PMTS", "PNBK", "PNRG",
    "PNTG", "POR", "POWI", "POWW", "PPIH", "PRAA", "PRAX", "PRCH", "PRCT", "PRDO",
    "PRG", "PRGO", "PRGS", "PRK", "PRKS", "PRLB", "PRLD", "PRM", "PRME", "PROK",
    "PRSU", "PRTA", "PRTH", "PRVA", "PSFE", "PSIX", "PSMT", "PSNL", "PSTL", "PTCT",
    "PTEN", "PTGX", "PTLO", "PTON", "PTRN", "PUBM", "PUMP", "PURR", "PVLA", "PWP",
    "PXED", "PZZA", "QBTS", "QCRH", "QDEL", "QLYS", "QNST", "QTRX", "QTWO", "QUAD",
    "QUBT", "QUIK", "RAIL", "RAMP", "RAPP", "RARE", "RBB", "RBBN", "RBCAA", "RBKB",
    "RC", "RCAT", "RCKT", "RCKY", "RCMT", "RCUS", "RDN", "RDNT", "RDNW", "RDVT",
    "RDW", "RDZN", "REAL", "REAX", "REFI", "REI", "RELL", "RELY", "RENT", "REPL",
    "REPX", "RES", "REX", "REZI", "RFIL", "RGCO", "RGNX", "RGR", "RGTI", "RH",
    "RHLD", "RHP", "RICK", "RIG", "RIGL", "RILY", "RIOT", "RJET", "RLAY", "RLGT",
    "RLJ", "RLMD", "RM", "RMAX", "RMBI", "RMNI", "RMR", "RNA", "RNAC", "RNGR",
    "RNST", "ROAD", "ROCK", "ROG", "ROOT", "RPAY", "RPC", "RPD", "RR", "RRBI",
    "RRR", "RSI", "RSVR", "RUM", "RUN", "RUSHA", "RVLV", "RWT", "RXO", "RXRX",
    "RXST", "RXT", "RYAM", "RYTM", "RYZ", "RZLT", "SABR", "SABS", "SAFE", "SAFT",
    "SAH", "SAM", "SAMG", "SANA", "SATL", "SB", "SBC", "SBCF", "SBET", "SBGI",
    "SBH", "SBMT", "SBRA", "SBSI", "SCHL", "SCL", "SCSC", "SD", "SDGR", "SDRL",
    "SEG", "SEI", "SENEA", "SENS", "SEPN", "SERV", "SES", "SEVN", "SEZL", "SFBS",
    "SFIX", "SFL", "SFNC", "SFST", "SG", "SGC", "SGHC", "SGHT", "SGMT", "SGP",
    "SGRY", "SHAK", "SHAZ", "SHBI", "SHEN", "SHLS", "SHO", "SHOE", "SHOO", "SI",
    "SIBN", "SIDU", "SIG", "SIGA", "SIGI", "SION", "SITC", "SKIL", "SKT", "SKWD",
    "SKY", "SKYH", "SKYT", "SKYW", "SLAB", "SLDB", "SLDE", "SLDP", "SLG", "SLND",
    "SLNH", "SLP", "SLS", "SLSN", "SLVM", "SM", "SMA", "SMBC", "SMBK", "SMC",
    "SMHI", "SMID", "SMP", "SMPL", "SMR", "SMRT", "SMTI", "SND", "SNDA", "SNDX",
    "SNEX", "SNFCA", "SOC", "SONO", "SOUN", "SPB", "SPCE", "SPFI", "SPHR", "SPIR",
    "SPNT", "SPOK", "SPRB", "SPRY", "SPSC", "SPT", "SR", "SRBK", "SRCE", "SRI",
    "SRPT", "SRRK", "SRTA", "SRZN", "SSP", "SSRM", "SSTK", "STAA", "STBA", "STC",
    "STEP", "STGW", "STNE", "STNG", "STOK", "STRA", "STRO", "STRT", "STRW", "STRZ",
    "STTK", "STUB", "STXS", "SUPN", "SVC", "SVCO", "SVRA", "SVV", "SWBI", "SWIM",
    "SWMR", "SWX", "SXC", "SXI", "SXT", "SYBT", "SYNA", "SYRE", "TALK", "TALO",
    "TARA", "TARS", "TATT", "TAYD", "TBBK", "TBCH", "TBI", "TBLA", "TBPH", "TCBI",
    "TCBK", "TCBX", "TCI", "TCMD", "TCX", "TDAY", "TDC", "TDOC", "TDS", "TDUP",
    "TDW", "TE", "TEAD", "TECX", "TENB", "TENX", "TEX", "TFIN", "TG", "TGLS",
    "TGTX", "TH", "THFF", "THRM", "THRY", "TIC", "TILE", "TIPT", "TITN", "TK",
    "TKNO", "TLS", "TLSI", "TMDX", "TMHC", "TMP", "TNC", "TNDM", "TNET", "TNGX",
    "TNK", "TNXP", "TOI", "TOWN", "TOYO", "TPB", "TPC", "TRAK", "TRAX", "TRC",
    "TRDA", "TREE", "TRIP", "TRMK", "TRN", "TRNO", "TRNS", "TRON", "TROX", "TRS",
    "TRST", "TRTX", "TRUP", "TRVI", "TSBK", "TSHA", "TSSI", "TTAM", "TTAN", "TTGT",
    "TTI", "TVTX", "TWI", "TWIN", "TWO", "TWST", "TXG", "TXNM", "TYGO", "TYRA",
    "UA", "UAMY", "UBSI", "UCB", "UCTT", "UE", "UEC", "UFCS", "UFPI", "UFPT",
    "UHT", "UIS", "ULCC", "ULH", "UMAC", "UMBF", "UMH", "UNCY", "UNF", "UNFI",
    "UNIT", "UNTY", "UP", "UPB", "UPBD", "UPST", "UPWK", "URBN", "URGN", "USAR",
    "USAU", "USCB", "USGO", "USLM", "USNA", "USPH", "UTI", "UTL", "UTMD", "UTZ",
    "UVE", "UVSP", "UVV", "VABK", "VAC", "VAL", "VALU", "VATE", "VC", "VCEL",
    "VCTR", "VCYT", "VECO", "VEL", "VELO", "VENU", "VERA", "VERI", "VERX", "VGAS",
    "VGNT", "VGZ", "VHI", "VIA", "VIR", "VIRC", "VISN", "VITL", "VLGEA", "VLY",
    "VMD", "VNDA", "VOR", "VOYG", "VPG", "VRDN", "VREX", "VRNS", "VRRM", "VRTS",
    "VSAT", "VSEC", "VSH", "VSTM", "VSTS", "VSXY", "VTOL", "VTS", "VUZI", "VVX",
    "VYGR", "VYX", "WABC", "WAFD", "WASH", "WATT", "WAY", "WBTN", "WD", "WDFC",
    "WEAV", "WEN", "WERN", "WEST", "WEYS", "WGO", "WGS", "WHD", "WHG", "WHWK",
    "WINA", "WK", "WKC", "WLDN", "WLFC", "WLTH", "WLY", "WMK", "WNC", "WNEB",
    "WOLF", "WOOF", "WOR", "WRBY", "WRLD", "WS", "WSBC", "WSBF", "WSFS", "WT",
    "WTBA", "WTI", "WTTR", "WVE", "WWW", "WYFI", "XENE", "XERS", "XFOR", "XHR",
    "XMAX", "XMTR", "XNCR", "XOMA", "XPEL", "XPER", "XPOF", "XPRO", "XRAY", "XRN",
    "XRX", "XZO", "YELP", "YEXT", "YORW", "YOU", "YSS", "YSWY", "ZBIO", "ZD",
    "ZENA", "ZETA", "ZGN", "ZIP", "ZNTL", "ZSQR", "ZUMZ", "ZURA", "ZVRA", "ZWS",
    "ZYME",
]



def _ema_slope(series: pd.Series, lookback: int, threshold: float):
    """Idéntica lógica que research_service._ema_slope — pendiente de una EMA
    comparando valor actual vs hace `lookback` sesiones."""
    if len(series) <= lookback:
        return None, None
    now  = float(series.iloc[-1])
    prev = float(series.iloc[-1 - lookback])
    if prev == 0:
        return None, None
    pct = round((now - prev) / prev * 100, 2)
    if pct > threshold:  return "alcista", pct
    if pct < -threshold: return "bajista", pct
    return "plana", pct


def _classify_phase(close: pd.Series) -> dict:
    """Fase Weinstein (1-4), idéntica metodología que
    research_service._get_technical_levels — reimplementada aquí sobre datos
    ya descargados en batch (sin llamada de red extra por ticker)."""
    if len(close) < 50:
        return {"phase": None, "phase_label": "Sin datos suficientes", "trend": None}

    price    = float(close.iloc[-1])
    ema10_s  = close.ewm(span=10,  adjust=False).mean()
    ema20_s  = close.ewm(span=20,  adjust=False).mean()
    ema50_s  = close.ewm(span=50,  adjust=False).mean()
    ema200_s = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else None

    ema20  = float(ema20_s.iloc[-1])
    ema50  = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1]) if ema200_s is not None else None

    slope10_dir,  _ = _ema_slope(ema10_s,  3,  0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  5,  0.4)
    slope50_dir,  _ = _ema_slope(ema50_s,  10, 0.6)
    slope200_dir, _ = _ema_slope(ema200_s, 20, 0.8) if ema200_s is not None else (None, None)

    bull_conditions = [
        price > ema20,
        ema20 > ema50,
        (ema50 > ema200) if ema200 else True,
        slope50_dir == "alcista",
        (slope200_dir in ("alcista", "plana")) if slope200_dir else True,
    ]
    bull_score = sum(1 for c in bull_conditions if c)

    early_reversal = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
    # Espejo del caso anterior — ver comentario detallado en research_service.py
    # (caso real AMPX: momentum corto plazo claramente bajista mal etiquetado
    # como "Fase 1 Acumulación" antes de este arreglo).
    early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

    if bull_score >= 4:
        trend = "ALCISTA"
    elif bull_score <= 1 and not early_reversal:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    elif early_reversal and bull_score <= 1:
        phase, label = 1, "Fase 1 · Posible Giro Temprano"
    elif early_breakdown:
        phase, label = 3, "Fase 3 · Posible Giro Bajista Temprano"
    elif ema200 and price >= ema200:
        phase, label = 3, "Fase 3 · Distribución"
    else:
        phase, label = 1, "Fase 1 · Acumulación"

    return {"phase": phase, "phase_label": label, "trend": trend}


def _classify_phase_debounced(close: pd.Series, confirm_sessions: int = 3) -> dict:
    """Exige que la fase se mantenga `confirm_sessions` sesiones seguidas
    antes de darla por "confirmada" — si la fase de hoy no coincide con la de
    hace 1 y 2 sesiones, se marca phase_confirmed=False y se añade
    "(sin confirmar)" a la etiqueta, en vez de reportar el cambio el primer
    día que aparece. No toca la fórmula de clasificación en sí — cada fase
    individual se calcula exactamente igual, solo se exige que se repita
    varias veces antes de confiar en un cambio. Reduce el parpadeo entre
    fases por ruido de un solo día."""
    today_result = _classify_phase(close)
    if today_result["phase"] is None:
        today_result["phase_confirmed"] = None
        return today_result

    recent_phases = [today_result["phase"]]
    for i in range(1, confirm_sessions):
        cutoff = len(close) - i
        if cutoff < 50:
            break
        sub = _classify_phase(close.iloc[:cutoff])
        if sub["phase"] is None:
            break
        recent_phases.append(sub["phase"])

    if len(recent_phases) < confirm_sessions:
        # Histórico insuficiente para confirmar del todo (ticker con poco
        # recorrido) — se sirve el resultado de hoy, sin marcar ni confirmar
        # ni desconfirmar.
        today_result["phase_confirmed"] = None
        return today_result

    confirmed = len(set(recent_phases)) == 1
    result = dict(today_result)
    result["phase_confirmed"] = confirmed
    if not confirmed:
        result["phase_label"] = result["phase_label"] + " (sin confirmar)"
    return result


def _resample_weekly_close(close: pd.Series):
    """Reagrupa una serie de cierres diarios en cierres semanales (viernes) —
    misma técnica que ya usa rsu_algoritmo_service._resample_semanal, aplicada
    aquí solo a la serie de cierre (todo lo que necesita _classify_phase)."""
    if len(close) < 14:
        return None
    try:
        weekly = close.resample('W-FRI').last().dropna()
        return weekly if len(weekly) >= 10 else None
    except Exception:
        return None


def _classify_phase_weekly(close_daily: pd.Series) -> dict:
    """Fase Weinstein sobre velas SEMANALES — la temporalidad original del
    método (el libro de Weinstein usa gráficos semanales, no diarios). Mucho
    más lenta a reaccionar que _classify_phase (diaria), pero con muchísimo
    menos ruido — pensada como CONFIRMACIÓN estructural junto a la fase
    diaria (más rápida y táctica), no como sustituta.

    Los lookbacks de pendiente se reescalan de sesiones diarias a semanas
    (÷5 aprox.) manteniendo los mismos umbrales porcentuales. La EMA200
    semanal necesita 200 semanas (~4 años) para estar "completa" — con los 2
    años de histórico diario disponibles (~104 semanas) se queda corta, así
    que se usa min_periods=20 (igual que ya hace
    rsu_algoritmo_service._ema200_semanal) para que dé un valor utilizable
    antes, aceptando que está menos "asentada" que con histórico completo."""
    weekly = _resample_weekly_close(close_daily)
    if weekly is None or len(weekly) < 30:
        return {"phase": None, "phase_label": "Sin histórico semanal suficiente", "trend": None}

    price    = float(weekly.iloc[-1])
    ema10_s  = weekly.ewm(span=10,  adjust=False, min_periods=5).mean()
    ema20_s  = weekly.ewm(span=20,  adjust=False, min_periods=10).mean()
    ema50_s  = weekly.ewm(span=50,  adjust=False, min_periods=20).mean()
    ema200_s = weekly.ewm(span=200, adjust=False, min_periods=20).mean() if len(weekly) >= 20 else None

    ema20  = float(ema20_s.iloc[-1])
    ema50  = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1]) if ema200_s is not None else None

    slope10_dir,  _ = _ema_slope(ema10_s,  1, 0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  2, 0.4)
    slope50_dir,  _ = _ema_slope(ema50_s,  3, 0.6)
    slope200_dir, _ = _ema_slope(ema200_s, 4, 0.8) if ema200_s is not None else (None, None)

    bull_conditions = [
        price > ema20,
        ema20 > ema50,
        (ema50 > ema200) if ema200 else True,
        slope50_dir == "alcista",
        (slope200_dir in ("alcista", "plana")) if slope200_dir else True,
    ]
    bull_score = sum(1 for c in bull_conditions if c)

    early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
    early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

    if bull_score >= 4:
        trend = "ALCISTA"
    elif bull_score <= 1 and not early_reversal:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    elif early_reversal and bull_score <= 1:
        phase, label = 1, "Fase 1 · Posible Giro Temprano"
    elif early_breakdown:
        phase, label = 3, "Fase 3 · Posible Giro Bajista Temprano"
    elif ema200 and price >= ema200:
        phase, label = 3, "Fase 3 · Distribución"
    else:
        phase, label = 1, "Fase 1 · Acumulación"

    return {"phase": phase, "phase_label": label, "trend": trend}


def _rs_smooth(prices: pd.Series, spy: pd.Series, period: int) -> pd.Series:
    rs = prices.pct_change(period) - spy.pct_change(period)
    return rs.ewm(span=EMA_SMOOTH, min_periods=3).mean()


def _fetch_batch(all_syms: list) -> tuple:
    close_d, vol_d = {}, {}
    batches = [all_syms[i:i + BATCH_SIZE] for i in range(0, len(all_syms), BATCH_SIZE)]
    n = len(batches)
    for i, batch in enumerate(batches):
        print(f"📦 Lote {i+1}/{n} ({len(batch)} símbolos)...")
        try:
            raw = yf.download(batch, period="2y", auto_adjust=True, progress=False, threads=True)
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw["Close"]  if "Close"  in raw.columns.get_level_values(0) else pd.DataFrame()
                vols   = raw["Volume"] if "Volume" in raw.columns.get_level_values(0) else pd.DataFrame()
            else:
                closes = raw[["Close"]]  if "Close"  in raw.columns else pd.DataFrame()
                vols   = raw[["Volume"]] if "Volume" in raw.columns else pd.DataFrame()
            for sym in batch:
                if sym in closes.columns:
                    series = closes[sym].dropna()
                    if len(series) >= 130:
                        close_d[sym] = series
                        vol_d[sym]   = vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)
        except Exception as e:
            print(f"⚠️  Lote {i+1}/{n} falló: {e}")
        if i < n - 1:
            time.sleep(BATCH_SLEEP)
    return close_d, vol_d


def _technical_score(rs_pct: float, phase: int, rvol: float) -> float:
    """Score Técnico 0-100 — ver docstring del módulo para el porqué de este
    alcance (solo técnico, no fundamental) en v1."""
    phase_pts = {2: 30, 1: 18, 3: 10, 4: 0}.get(phase, 10)
    rvol_pts  = min(rvol / 3.0, 1.0) * 20  # satura en RVOL=3x
    rs_pts    = (rs_pct or 0) * 0.50
    return round(rs_pts + phase_pts + rvol_pts, 1)


def _compute_breadth_history(close_d: dict, tickers: list, lookback_days: int = 65) -> list:
    """Amplitud de mercado REAL derivada del propio universo S&P 500 que este
    script ya descarga cada noche (500 tickers x 2 años de histórico) — en vez de
    depender de fuentes externas de avance/declive (^ADV/^DEC de Yahoo, que
    llevan tiempo dando datos poco fiables/planos) o de un proxy calculado
    sobre el precio de un solo índice.

    Para cada uno de los últimos `lookback_days` días de mercado calcula:
    - avance/declive neto (para el Oscilador McClellan real: EMA19-EMA39)
    - % de tickers del universo por encima de su propia SMA50
    - nuevos máximos / nuevos mínimos de 52 semanas (para NH-NL)

    Todo vectorizado con pandas sobre datos que ya están en memoria — cero
    llamadas de red adicionales.
    """
    cols = {t: close_d[t] for t in tickers if t in close_d}
    if len(cols) < 50:
        return []

    df = pd.DataFrame(cols).sort_index()
    if len(df) < 60:
        return []
    lookback_days = min(lookback_days, len(df) - 1)
    if lookback_days < 2:
        return []

    diff      = df.diff()
    advances  = (diff > 0).sum(axis=1)
    declines  = (diff < 0).sum(axis=1)

    sma50     = df.rolling(50, min_periods=50).mean()
    above     = df > sma50
    valid_cnt = df.notna().sum(axis=1)
    pct_above = (above.sum(axis=1) / valid_cnt.replace(0, np.nan) * 100)

    roll_max  = df.rolling(252, min_periods=20).max()
    roll_min  = df.rolling(252, min_periods=20).min()
    new_highs = (df >= roll_max).sum(axis=1)
    new_lows  = (df <= roll_min).sum(axis=1)

    history = []
    for d in df.index[-lookback_days:]:
        pa = pct_above.loc[d]
        history.append({
            "date":            d.strftime("%Y-%m-%d"),
            "advances":        int(advances.loc[d]),
            "declines":        int(declines.loc[d]),
            "pct_above_sma50": round(float(pa), 1) if pd.notna(pa) else None,
            "new_highs":       int(new_highs.loc[d]),
            "new_lows":        int(new_lows.loc[d]),
        })
    return history


def run_scan() -> dict:
    tickers  = list(SP500_SECTOR_MAP.keys())
    # Universo ampliado SOLO para amplitud (McClellan/ABI/A-D/NH-NL) — ver
    # comentario junto a RUSSELL2000_TICKERS más arriba. Se descarga en el
    # mismo lote que el S&P 500 (más eficiente, una sola pasada de _fetch_batch)
    # pero se mantiene aparte de `tickers` para que el scoring RS/fase/temático
    # de más abajo siga viendo solo las 500 grandes, sin cambiar esos rankings.
    breadth_universe = list(dict.fromkeys(tickers + RUSSELL2000_TICKERS))
    all_syms = list(dict.fromkeys([BENCHMARK] + breadth_universe))
    print(f"🔍 Universo Scanner: {len(tickers)} tickers S&P 500 (RS/fase) · {len(breadth_universe)} tickers para amplitud (S&P 500 + Russell 2000)")

    close_d, vol_d = _fetch_batch(all_syms)
    if BENCHMARK not in close_d:
        raise ValueError("Sin datos de SPY — cancelado")

    spy  = close_d[BENCHMARK]
    rows = []
    for ticker in tickers:
        if ticker not in close_d:
            continue
        prices = close_d[ticker]
        if len(prices) < 130:
            continue
        aligned_spy = spy.reindex(prices.index).ffill()
        try:
            rs_vals = {}
            for p in PERIODS:
                sm = _rs_smooth(prices, aligned_spy, p)
                rs_vals[p] = float(sm.iloc[-1]) if not sm.empty else 0.0
            rs_score_raw = sum(rs_vals[p] * WEIGHTS[p] for p in PERIODS)

            vols      = vol_d.get(ticker, pd.Series(dtype=float))
            vol_today = float(vols.iloc[-1]) if len(vols) > 0 else 0.0
            vol_avg   = float(vols.tail(RVOL_WINDOW).mean()) if len(vols) >= RVOL_WINDOW else 0.0
            rvol      = round(vol_today / vol_avg, 2) if vol_avg > 0 else 1.0

            phase_info = _classify_phase_debounced(prices)
            phase_weekly_info = _classify_phase_weekly(prices)
            price      = float(prices.iloc[-1])
            sector_raw = SP500_SECTOR_MAP.get(ticker, "")

            sma50_val   = float(prices.rolling(50).mean().iloc[-1]) if len(prices) >= 50 else float('nan')
            above_sma50 = bool(price > sma50_val) if sma50_val == sma50_val else None  # NaN check

            # Nuevo máximo/mínimo sobre la ventana de histórico disponible (hasta 260
            # sesiones ≈ 52 semanas, que es lo que se descarga en _fetch_batch). Con
            # menos histórico disponible sigue siendo una comparación válida, solo que
            # sobre una ventana más corta para los tickers con menos días.
            # Nuevo máximo/mínimo sobre las últimas 252 sesiones (52 semanas)
            # EXPLÍCITAMENTE — antes se comparaba contra prices.max() de TODO
            # el histórico descargado, lo cual era correcto mientras solo se
            # descargaban 260 sesiones (~52 semanas) pero se habría roto en
            # silencio al alargar el histórico a 2 años (habría pasado a
            # comparar contra el máximo de 2 años, no de 52 semanas).
            window_252 = prices.tail(252)
            new_high = bool(price >= float(window_252.max()))
            new_low  = bool(price <= float(window_252.min()))

            # Señal de absorción: RVOL alto + impacto en precio bajo (proxy
            # de Amihud/Lambda de Kyle), sostenido en los últimos 10 días.
            # Reutiliza prices/vols ya descargados -- cero llamadas nuevas
            # a la API. Ver conversación 18/07/2026 (Kyle 1985; Bouchaud,
            # Farmer & Lillo 2008).
            dias_absorcion = 0
            try:
                returns    = prices.pct_change()
                dollar_vol = prices * vols.reindex(prices.index).fillna(0)
                amihud     = (returns.abs() / (dollar_vol / 1_000_000)).replace([float("inf"), float("-inf")], None)
                rvol_series = vols / vols.rolling(RVOL_WINDOW).mean()
                rvol_z   = (rvol_series - rvol_series.rolling(20).mean()) / rvol_series.rolling(20).std()
                amihud_z = (amihud - amihud.rolling(20).mean()) / amihud.rolling(20).std()
                absorcion_dia = (rvol_z > 0.75) & (amihud_z < -0.75)
                dias_absorcion = int(absorcion_dia.tail(10).sum())
            except Exception:
                dias_absorcion = 0

            rows.append({
                "ticker":            ticker,
                "sector":            sector_raw,
                "precio":            round(price, 2),
                "rs_score":          round(rs_score_raw * 100, 2),
                "rvol":              rvol,
                "phase":             phase_info["phase"],
                "phase_label":       phase_info["phase_label"],
                "phase_confirmed":   phase_info.get("phase_confirmed"),
                "trend":             phase_info["trend"],
                "phase_weekly":       phase_weekly_info["phase"],
                "phase_weekly_label": phase_weekly_info["phase_label"],
                "above_sma50":       above_sma50,
                "new_high":          new_high,
                "new_low":           new_low,
                "dias_absorcion":    dias_absorcion,
            })
        except Exception:
            continue

    print(f"✅ {len(rows)}/{len(tickers)} tickers con histórico suficiente")
    if not rows:
        raise ValueError("Sin filas calculadas")

    breadth_history = _compute_breadth_history(close_d, breadth_universe)
    print(f"📊 Amplitud histórica calculada: {len(breadth_history)} sesiones (universo: {len(breadth_universe)} tickers)")

    df = pd.DataFrame(rows).set_index("ticker")
    df["rs_pct"] = df["rs_score"].rank(pct=True).mul(100).round(1)
    df["score_tecnico"] = df.apply(
        lambda r: _technical_score(r["rs_pct"], r["phase"], r["rvol"]), axis=1
    )

    stocks = {}
    for ticker, r in df.iterrows():
        stocks[ticker] = {
            "sector":        r["sector"],
            "precio":        r["precio"],
            "rvol":          r["rvol"],
            "rs_pct":        r["rs_pct"],
            "phase":         None if pd.isna(r["phase"]) else int(r["phase"]),
            "phase_label":   r["phase_label"],
            "trend":         r["trend"],
            "score_tecnico": r["score_tecnico"],
            "above_sma50":   None if pd.isna(r["above_sma50"]) else bool(r["above_sma50"]),
            "new_high":      bool(r["new_high"]),
            "new_low":       bool(r["new_low"]),
        }

    return {
        "ok":            True,
        "stocks":        stocks,
        "breadth_history": breadth_history,
        "universe_size": len(df),
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "meta": {
            "rvol_window": RVOL_WINDOW,
            "score_note":  "score_tecnico = RS_pct(50%) + Fase(30%) + RVOL(20%), sin componente fundamental — ver docstring",
        },
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")
    if not GIST_ID:
        raise ValueError("SCANNER_GIST_ID no configurado")

    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(result, ensure_ascii=False, indent=2)}}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:300]}")
    print(f"✅ Scanner universo guardado en Gist: {r.json()['html_url']}")


def main():
    print(f"🕐 Scanner universo — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    result = run_scan()
    print("💾 Guardando en GitHub Gist...")
    save_to_gist(result)
    print("✅ Scan completado")


if __name__ == "__main__":
    main()