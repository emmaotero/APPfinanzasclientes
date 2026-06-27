"""
Orden.ar · Datos de mercado
yfinance para acciones/CEDEARs/bonos
ArgentinaDatos para dólares e inflación
"""
import yfinance as yf
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ---- HELPERS ----

def _pct(a, b):
    """Variación porcentual entre dos valores."""
    if a and b and b != 0:
        return round((a - b) / b * 100, 2)
    return None

# ---- COTIZACIÓN INDIVIDUAL ----

@st.cache_data(ttl=300)  # cache 5 minutos
def cotizar(ticker: str) -> dict:
    """
    Trae precio actual + métricas de un ticker.
    Tickers argentinos: GGAL.BA, YPF.BA, AL30.BA
    CEDEARs / internacionales: AAPL, MSFT, TSLA
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info

        precio = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        open_price = info.get("open") or info.get("regularMarketOpen")

        # Histórico para variaciones semanal y mensual
        hist = t.history(period="1y")
        var_sem = var_mes = min52 = max52 = vol_52s = None

        if not hist.empty:
            closes = hist["Close"]
            hoy = closes.iloc[-1] if len(closes) > 0 else None
            hace_7 = closes.iloc[-6] if len(closes) >= 6 else None
            hace_30 = closes.iloc[-22] if len(closes) >= 22 else None
            min52 = round(closes.min(), 2)
            max52 = round(closes.max(), 2)
            vol_52s = int(hist["Volume"].mean()) if "Volume" in hist else None
            var_sem = _pct(hoy, hace_7)
            var_mes = _pct(hoy, hace_30)

        return {
            "ticker": ticker,
            "nombre": info.get("longName") or info.get("shortName") or ticker,
            "precio": round(precio, 2) if precio else None,
            "moneda": info.get("currency", "ARS"),
            "var_dia": _pct(precio, prev_close),
            "var_sem": var_sem,
            "var_mes": var_mes,
            "volumen": info.get("volume") or info.get("regularMarketVolume"),
            "vol_52s": vol_52s,
            "min52": min52,
            "max52": max52,
            "open": round(open_price, 2) if open_price else None,
            "prev_close": round(prev_close, 2) if prev_close else None,
            "ok": True
        }
    except Exception as e:
        return {"ticker": ticker, "ok": False, "error": str(e)}

@st.cache_data(ttl=300)
def cotizar_varios(tickers: list) -> dict:
    """Cotiza una lista de tickers. Devuelve dict {ticker: datos}."""
    return {t: cotizar(t) for t in tickers}

# ---- HISTORIAL PARA GRÁFICOS ----

@st.cache_data(ttl=3600)
def historial(ticker: str, periodo: str = "6mo") -> pd.DataFrame:
    """Historial de precios para graficar rendimiento."""
    try:
        t = yf.Ticker(ticker)
        h = t.history(period=periodo)
        h.index = pd.to_datetime(h.index)
        return h[["Close", "Volume"]].rename(columns={"Close": "precio", "Volume": "volumen"})
    except Exception:
        return pd.DataFrame()

# ---- DÓLARES ----

@st.cache_data(ttl=600)  # cache 10 minutos
def get_dolares() -> list:
    """Tipos de cambio desde ArgentinaDatos."""
    try:
        r = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares", timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Deduplicar: quedarse con la última entrada por casa
            seen = {}
            for d in data:
                seen[d["casa"]] = d
            orden = ["oficial", "blue", "mep", "ccl", "mayorista", "tarjeta", "cripto"]
            nombres = {
                "oficial": "Dólar Oficial", "blue": "Dólar Blue",
                "mep": "Dólar MEP", "ccl": "Dólar CCL",
                "mayorista": "Mayorista", "tarjeta": "Tarjeta", "cripto": "Cripto"
            }
            result = []
            for casa in orden:
                if casa in seen:
                    d = seen[casa]
                    result.append({
                        "nombre": nombres.get(casa, casa),
                        "compra": d.get("compra"),
                        "venta": d.get("venta")
                    })
            return result
    except Exception:
        pass
    return []

# ---- INFLACIÓN ----

@st.cache_data(ttl=3600 * 6)  # cache 6 horas
def get_inflacion(ultimos_n: int = 12) -> pd.DataFrame:
    """IPC mensual desde ArgentinaDatos."""
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=5)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data).tail(ultimos_n)
            df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%m/%Y")
            return df
    except Exception:
        pass
    return pd.DataFrame()

# ---- VALUACIÓN DE CARTERA ----

def valuar_posiciones(posiciones_df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega precio_actual, valuacion y rendimiento a un DataFrame de posiciones.
    Si el tipo es 'pf' o 'fci' (sin ticker de yfinance), deja precio_actual vacío
    para que se cargue manualmente.
    """
    if posiciones_df.empty:
        return posiciones_df

    df = posiciones_df.copy()
    tickers_yf = df[df["tipo"].isin(["accion", "cedear", "bono"])]["ticker"].unique().tolist()

    cotizaciones = cotizar_varios(tickers_yf) if tickers_yf else {}

    precios, variaciones, valuaciones, rendimientos = [], [], [], []

    for _, row in df.iterrows():
        if row["tipo"] in ["accion", "cedear", "bono"] and row["ticker"] in cotizaciones:
            c = cotizaciones[row["ticker"]]
            precio = c.get("precio") if c.get("ok") else None
            var_dia = c.get("var_dia")
        else:
            precio = None
            var_dia = None

        precios.append(precio)
        variaciones.append(var_dia)

        if precio and row.get("cantidad"):
            val = round(precio * row["cantidad"], 2)
            valuaciones.append(val)
            if row.get("precio_compra") and row["precio_compra"] > 0:
                rend = _pct(precio, row["precio_compra"])
                rendimientos.append(rend)
            else:
                rendimientos.append(None)
        else:
            valuaciones.append(None)
            rendimientos.append(None)

    df["precio_actual"] = precios
    df["var_dia"] = variaciones
    df["valuacion"] = valuaciones
    df["rendimiento"] = rendimientos
    return df
