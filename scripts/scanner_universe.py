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
import sys
import json
import time
import requests
import math
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import yfinance as yf

# Universo compartido -- ver shared/sp500_universe.py (Fase 2.1 del Plan
# Maestro, 20/07/2026). Antes había un diccionario embebido aquí mismo,
# duplicado también en rsrw_scan.py y rsrw_service.py -- ahora una sola
# fuente de verdad para los tres. sys.path apunta a shared/ (sibling de
# scripts/), sin depender de nada de backend/ -- sigue siendo standalone,
# compatible con el runner de GitHub Actions.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from weinstein_phases import classify_phase_debounced, classify_phase_weekly  # noqa: E402
from l3_banker import calcular_l3  # noqa: E402
from rsrw_engine import (  # noqa: E402
    rs_smooth as _rs_smooth, rs_percentile, PERIODS, WEIGHTS, EMA_SMOOTH,
)
from yf_batch import download_batch  # noqa: E402
from absorption import rolling_zscore_excluding_recent, THRESHOLD as ABSORPTION_THRESHOLD  # noqa: E402

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("SCANNER_GIST_ID", "")
GIST_FILE  = "scanner_scan.json"

BENCHMARK    = "SPY"
RVOL_WINDOW  = 20   # media de volumen — ver hilo de decisión: 20d, no 14d (sin base estándar) ni 50d (menos reactivo)
BATCH_SIZE   = 40
BATCH_SLEEP  = 1.8

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
    "ABSI", "ABUS", "ACA", "ACAD", "ACCO", "ACDC", "ACEL", "ACH", "ACHC",
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
    "AZZ", "BALY", "BANC", "BAND", "BANF", "BANR", "BATRA", "BBAI", "BBCP",
    "BBNX", "BBSI", "BBW", "BCAL", "BCAX", "BCBP", "BCC", "BCML", "BCO",
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



def _fetch_batch(all_syms: list) -> tuple:
    # max_retries=1 (por defecto) significaba un único intento por lote,
    # sin reintento real -- un lote entero perdido (fallo transitorio de
    # Yahoo) se quedaba sin esos ~40 tickers para toda la noche. RS/RW ya
    # usa este mismo patrón (rsrw_service.py/rsrw_scan.py). Ver auditoría
    # Scanner 21/07/2026, hallazgo #2.
    # include_hl trae Open/High/Low en la MISMA respuesta que ya se pedía --
    # cero peticiones extra. Hace falta para el oscilador L3, que necesita el
    # OHLC completo (su precio típico usa la apertura).
    return download_batch(all_syms, period="2y", batch_size=BATCH_SIZE, batch_sleep=BATCH_SLEEP,
                           max_retries=3, coverage_threshold=0.85, include_hl=True,
                           log_prefix="[Scanner] ")


# Techo de la curva de volumen. Calibrado sobre las 6.012 observaciones reales
# guardadas en snapshots.db (12 sesiones x ~500 valores): mediana 0,78,
# p90 1,35, p95 1,65, p99 2,42, p99,9 4,18 y máximo histórico 9,67.
#
# ELEGIR ESTE NÚMERO ES UN COMPROMISO, y conviene dejarlo escrito: solo hay 20
# puntos, así que una curva que llegue al máximo en 10x tiene que dar ~9 en 3x,
# y aplastaría el tramo 1-2,5 donde vive el 99% de los datos. Con el techo en 4
# el 0,13% de observaciones que lo superan siguen empatando arriba -- así que
# el hallazgo #9 de la auditoría queda MEJOR, no resuelto del todo. Se prefiere
# eso a perder resolución donde el módulo discrimina cada día.
RVOL_TECHO = 4.0


def _rvol(vols) -> float:
    """Volumen de hoy frente a lo normal en ese valor.

    El promedio EXCLUYE el día evaluado. Incluirlo hace que un día de volumen
    alto infle su propio denominador y acerque el cociente a 1, disimulando
    justo los días anómalos que el RVOL busca. Es el mismo fallo ya corregido
    dos veces en este proyecto -- alertas de Watchlist (#3 de su auditoría) y
    `_vol_ratio_desde_serie` de Market -- y aquí seguía vivo.

    Devuelve 1.0 (o sea, "normal") cuando no hay serie bastante: es lo que
    hacía antes y lo que el score espera, y con la curva nueva 1.0 vale cero
    puntos, así que no regala nada.
    """
    if vols is None or len(vols) <= RVOL_WINDOW:
        return 1.0
    vol_today = float(vols.iloc[-1])
    vol_avg   = float(vols.iloc[:-1].tail(RVOL_WINDOW).mean())
    if vol_avg <= 0:
        return 1.0
    return round(vol_today / vol_avg, 2)


def _rvol_pts(rvol: float) -> float:
    """Puntos por volumen relativo, 0-20.

    DOS ARREGLOS sobre `min(rvol/3, 1) * 20` (hallazgo #9 de la auditoría de
    Scanner, más uno que salió al medirlo):

    1. Por DEBAJO de lo normal no se puntúa. La fórmula anterior era lineal
       desde 0, así que un valor con volumen NORMAL (RVOL 1) se llevaba 6,7 de
       los 20 puntos y uno con la mitad de lo habitual, 3,3. Con la mediana del
       universo en 0,58, eso era un sumando casi constante que añadía ruido al
       score sin distinguir nada.
    2. Crecimiento LOGARÍTMICO en vez de lineal con tope en 3. La anterior
       saturaba tan pronto que un día de RVOL 12 puntuaba igual que uno de 3, y
       no son el mismo suceso. El logaritmo mantiene sensibilidad donde se
       concentran los datos y sigue premiando los extremos.
    """
    if not rvol or rvol <= 1:
        return 0.0
    return min(math.log(rvol) / math.log(RVOL_TECHO), 1.0) * 20


def _technical_score(rs_pct: float, phase: int, rvol: float) -> float:
    """Score Técnico 0-100 — ver docstring del módulo para el porqué de este
    alcance (solo técnico, no fundamental) en v1."""
    phase_pts = {2: 30, 1: 18, 3: 10, 4: 0}.get(phase, 10)
    rs_pts    = (rs_pct or 0) * 0.50
    return round(rs_pts + phase_pts + _rvol_pts(rvol), 1)


def _amplitudes_separadas(close_d: dict, tickers_sp500: list):
    """Las dos amplitudes, cada una sobre SU universo.

    Función aparte para poder probar QUÉ SE PUBLICA, no solo que el cálculo
    sepa separar. Con `_compute_breadth_history` correcta pero llamada dos
    veces con el universo combinado, las dos series saldrían idénticas y la
    brecha sería cero para siempre -- y un test sobre la función no lo vería.
    Lo destapó el sabotaje el 15/08/2026, igual que con la ordenación de las
    cestas temáticas ese mismo día.
    """
    return (_compute_breadth_history(close_d, tickers_sp500, lookback_days=60),
            _compute_breadth_history(close_d, RUSSELL2000_TICKERS, lookback_days=60))


def _compute_breadth_history(close_d: dict, tickers: list, lookback_days: int = 150) -> list:
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

    lookback_days=150 (antes 65, sesión 20, 23/07/2026): el histórico se
    RECALCULA DESDE CERO cada noche (no hay estado de EMA persistido entre
    scans), así que la EMA39 del McClellan necesita suficiente ventana
    propia para madurar cada vez. Verificado empíricamente con datos reales
    (168 tickers, ~2.5 años): con 65 días, el valor resultante tenía un 33%
    más de ruido día-a-día que el mismo cálculo sobre histórico largo
    (correlación 0.906) — un artefacto de la ventana corta, no movimiento
    real de mercado. A partir de ~130 días la divergencia desaparece del
    todo (correlación 0.9998); 150 deja margen cómodo. Ver memoria del
    proyecto para el detalle de la comparación.
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
    # EL DENOMINADOR SON LOS QUE TIENEN SMA50 CALCULABLE, no los que tienen
    # precio. Parece un matiz y es un fallo grande, encontrado el 15/08/2026 al
    # separar los dos universos:
    #
    # `rolling(50, min_periods=50)` exige 50 sesiones SIN huecos. Un solo día en
    # el que la descarga no traiga a parte del universo deja a esos valores sin
    # SMA50 durante las 50 sesiones siguientes. Siguen teniendo precio, así que
    # entraban en el denominador; pero `NaN > NaN` es False, así que no entraban
    # nunca en el numerador. El porcentaje se hundía sin que hubiera pasado nada
    # en el mercado.
    #
    # Medido sobre 386 valores del Russell: el 11/08 faltaron 149, y del 12 al
    # 14 el "% sobre SMA50" marcaba 38,6 / 39,1 / 40,4 cuando lo real era
    # 62,9 / 63,7 / 65,8 -- mientras el índice SUBÍA los tres días. No es un
    # detalle de esta sección: este número alimenta el widget de amplitud de
    # Market, `snapshot_mercado` y el factor Breadth del RSU Algoritmo.
    valid_cnt = (df.notna() & sma50.notna()).sum(axis=1)
    pct_above = (above.sum(axis=1) / valid_cnt.replace(0, np.nan) * 100)

    # shift(1) antes del rolling: la ventana de referencia de cada día
    # EXCLUYE ese propio día, para que una meseta lateral en el máximo no
    # cuente como "nuevo máximo" cada sesión que persiste (mismo criterio
    # que el chequeo per-ticker más abajo). Ver auditoría Scanner
    # 21/07/2026, hallazgo #5.
    roll_max  = df.shift(1).rolling(252, min_periods=20).max()
    roll_min  = df.shift(1).rolling(252, min_periods=20).min()
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

    close_d, vol_d, hl_d = _fetch_batch(all_syms)
    if BENCHMARK not in close_d:
        raise ValueError("Sin datos de SPY — cancelado")

    # Tickers del universo (sobre todo RUSSELL2000_TICKERS, la lista más
    # propensa a quedarse desactualizada) que no devolvieron datos --
    # candidato a ticker muerto/renombrado (como fue "ABX", eliminado en
    # esta misma sesión). Se loguea cada noche para poder auditar la lista
    # con el tiempo, en vez de un repaso manual puntual de las ~2.000
    # entradas. Ver auditoría Scanner 21/07/2026, hallazgo #4.
    missing = [s for s in breadth_universe if s not in close_d]
    if missing:
        print(f"⚠️  {len(missing)} tickers del universo sin datos (posibles tickers muertos/renombrados): {missing[:30]}{'...' if len(missing) > 30 else ''}")

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

            rvol      = _rvol(vol_d.get(ticker, pd.Series(dtype=float)))

            phase_info = classify_phase_debounced(prices)
            phase_weekly_info = classify_phase_weekly(prices)
            price      = float(prices.iloc[-1])
            sector_raw = SP500_SECTOR_MAP.get(ticker, "")

            sma50_val   = float(prices.rolling(50).mean().iloc[-1]) if len(prices) >= 50 else float('nan')
            above_sma50 = bool(price > sma50_val) if sma50_val == sma50_val else None  # NaN check

            # Nuevo máximo/mínimo sobre las últimas 252 sesiones (52 semanas)
            # EXPLÍCITAMENTE — antes se comparaba contra prices.max() de TODO
            # el histórico descargado, lo cual era correcto mientras solo se
            # descargaban 260 sesiones (~52 semanas) pero se habría roto en
            # silencio al alargar el histórico a 2 años (habría pasado a
            # comparar contra el máximo de 2 años, no de 52 semanas).
            # La ventana EXCLUYE el día evaluado (prices.iloc[-253:-1], no
            # tail(252)) -- si no, una meseta lateral en el máximo cuenta
            # como "nuevo máximo" cada día que persiste, no solo el día real
            # de la ruptura (price siempre es >= su propio máximo incluido
            # en la ventana). Ver auditoría Scanner 21/07/2026, hallazgo #5.
            window_252 = prices.iloc[-253:-1] if len(prices) >= 253 else prices.iloc[:-1]
            new_high = bool(len(window_252) > 0 and price >= float(window_252.max()))
            new_low  = bool(len(window_252) > 0 and price <= float(window_252.min()))

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
                # shared/absorption.py -- ventana de referencia que EXCLUYE
                # el día evaluado y sus vecinos inmediatos, para que el
                # propio pico anómalo no contamine su media/std de
                # referencia (causa real de por qué 0.75 daba 0 coincidencias
                # antes). Umbral restaurado a 0.75, coherente con
                # turnover_service.py (Research), que usa la misma función.
                # Ver auditoría Scanner 21/07/2026, hallazgo #1.
                rvol_z   = rolling_zscore_excluding_recent(rvol_series)
                amihud_z = rolling_zscore_excluding_recent(amihud)
                absorcion_dia = (rvol_z > ABSORPTION_THRESHOLD) & (amihud_z < -ABSORPTION_THRESHOLD)
                dias_absorcion = int(absorcion_dia.tail(10).sum())
            except Exception:
                dias_absorcion = 0

            # Oscilador L3 (el "indicador RSU" de Research), para poder
            # rastrear desde el escáner los que están en la zona baja. Se
            # calcula con el MISMO módulo que usa Research, no con una copia:
            # si algún día cambia la fórmula, cambia en los dos sitios a la vez.
            # Un ticker sin OHLC completo se queda sin estas tres columnas en
            # vez de tumbar su fila entera -- el resto del escáner sigue
            # sirviendo para él.
            l3_fundtrend = l3_linea = l3_estado = None
            hl = hl_d.get(ticker)
            if hl is not None and not hl.empty:
                try:
                    ohlc = pd.DataFrame({
                        "Open":  hl["Open"], "High": hl["High"],
                        "Low":   hl["Low"],  "Close": prices,
                    }).dropna()
                    if len(ohlc) >= 60:
                        l3 = calcular_l3(ohlc).dropna(subset=["fundtrend", "linea", "estado"])
                        if not l3.empty:
                            l3_fundtrend = round(float(l3["fundtrend"].iloc[-1]), 1)
                            l3_linea     = round(float(l3["linea"].iloc[-1]), 1)
                            l3_estado    = l3["estado"].iloc[-1]
                except Exception:
                    pass

            rows.append({
                "ticker":            ticker,
                "sector":            sector_raw,
                "l3_fundtrend":      l3_fundtrend,
                "l3_linea":          l3_linea,
                "l3_estado":         l3_estado,
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
    # Y ahora los dos universos POR SEPARADO. El combinado de arriba no se
    # toca: alimenta el McClellan de Market, snapshot_mercado y el RSU
    # Algoritmo, y cambiarlo movería esos números sin que nadie lo pida.
    #
    # Separarlos responde la pregunta que el combinado esconde por
    # construcción: cuando las grandes hacen máximos y las pequeñas no, el
    # liderazgo se está estrechando. Mezclados, una mitad tapa a la otra.
    #
    # 60 sesiones y no 150: la divergencia es una lectura de semanas, no de
    # meses, y son dos series más en el mismo Gist.
    breadth_sp500, breadth_russell = _amplitudes_separadas(close_d, tickers)
    print(f"📊 Amplitud separada: S&P 500 {len(breadth_sp500)} sesiones · "
          f"Russell 2000 {len(breadth_russell)} sesiones")
    print(f"📊 Amplitud histórica calculada: {len(breadth_history)} sesiones (universo: {len(breadth_universe)} tickers)")

    df = pd.DataFrame(rows).set_index("ticker")
    df["rs_pct"] = rs_percentile(df["rs_score"])
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
            # rs_score es la única medida ABSOLUTA de fuerza relativa que
            # produce este scan: el diferencial ponderado contra el SPY. Se
            # calculaba desde siempre (ver `rows`) pero se quedaba fuera de
            # este diccionario, así que nunca salía del Gist -- mismo olvido
            # que sufrieron los 4 campos de abajo. Sin él no existe amplitud
            # RS posible: rs_pct es un RANGO dentro del universo, y el
            # porcentaje que supera cualquier corte es constante por
            # construcción (20,2% por encima de 80, todos los días). Ver
            # RS/RW #16, 02/08/2026.
            "rs_score":      round(float(r["rs_score"]), 2),
            # Oscilador L3 -- el mismo "indicador RSU" que se ve en Research.
            # None cuando ese ticker no tuvo OHLC completo: se muestra "—", no
            # un 0 que parecería una lectura de sobreventa extrema.
            "l3_fundtrend":  None if pd.isna(r.get("l3_fundtrend")) else float(r.get("l3_fundtrend")),
            "l3_linea":      None if pd.isna(r.get("l3_linea")) else float(r.get("l3_linea")),
            "l3_estado":     None if pd.isna(r.get("l3_estado")) else r.get("l3_estado"),
            "phase":         None if pd.isna(r["phase"]) else int(r["phase"]),
            "phase_label":   r["phase_label"],
            "phase_confirmed": None if pd.isna(r.get("phase_confirmed")) else bool(r.get("phase_confirmed")),
            "phase_weekly":       None if pd.isna(r.get("phase_weekly")) else int(r.get("phase_weekly")),
            "phase_weekly_label": None if pd.isna(r.get("phase_weekly_label")) else r.get("phase_weekly_label"),
            "trend":         r["trend"],
            "score_tecnico": r["score_tecnico"],
            "above_sma50":   None if pd.isna(r["above_sma50"]) else bool(r["above_sma50"]),
            "new_high":      bool(r["new_high"]),
            "new_low":       bool(r["new_low"]),
            # FALTABAN estos 4 campos -- se calculaban en `rows` pero nunca
            # llegaban a este diccionario final, así que nunca salían del
            # Gist. Explica por qué "dias_absorcion" llevaba días en 0 para
            # todos los tickers (no solo era el umbral, el dato ni siquiera
            # se guardaba). Ver conversación 20/07/2026.
            "dias_absorcion": int(r.get("dias_absorcion", 0)),
        }

    return {
        "ok":            True,
        "stocks":        stocks,
        "breadth_history": breadth_history,
        "breadth_sp500":   breadth_sp500,
        "breadth_russell": breadth_russell,
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