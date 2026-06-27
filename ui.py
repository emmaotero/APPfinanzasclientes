"""
Orden.ar · Componentes de UI reutilizables
"""
import streamlit as st
import pandas as pd

# ---- COLORES ----
VERDE = "#2E8B57"
VERDE_P = "#1A5C38"
VERDE_C = "#D6EFE1"
AZUL = "#185FA5"
AZUL_P = "#0C3D6B"
ROJO = "#c0392b"

# ---- MÉTRICAS ----

def metrica(label, valor, delta=None, prefix="$", suffix=""):
    """Métrica estilizada con delta opcional."""
    delta_str = None
    if delta is not None:
        signo = "+" if delta >= 0 else ""
        delta_str = f"{signo}{delta:.1f}%"
    st.metric(label=label, value=f"{prefix}{valor}{suffix}", delta=delta_str)

def metricas_row(items: list):
    """
    items: lista de dicts con keys: label, valor, delta (opcional), prefix, suffix
    """
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            metrica(
                item.get("label", ""),
                item.get("valor", "—"),
                item.get("delta"),
                item.get("prefix", "$"),
                item.get("suffix", "")
            )

# ---- TABLAS ----

def tabla_posiciones(df: pd.DataFrame, moneda="ARS"):
    """Tabla de posiciones con formato."""
    if df.empty:
        st.info("Sin posiciones registradas.")
        return

    TIPO_LABELS = {
        "accion": "Acción", "cedear": "CEDEAR",
        "bono": "Bono", "fci": "FCI", "pf": "Plazo Fijo", "otro": "Otro"
    }

    display = pd.DataFrame()
    display["Instrumento"] = df["nombre"].fillna(df["ticker"])
    display["Ticker"] = df["ticker"]
    display["Tipo"] = df["tipo"].map(TIPO_LABELS).fillna(df["tipo"])
    display["Moneda"] = df["moneda"]
    display["Cantidad"] = df["cantidad"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
    display["P. Compra"] = df["precio_compra"].apply(
        lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
    )

    if "precio_actual" in df.columns:
        display["P. Actual"] = df["precio_actual"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )
    if "valuacion" in df.columns:
        display["Valuación"] = df["valuacion"].apply(
            lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
        )
    if "var_dia" in df.columns:
        display["Var. día"] = df["var_dia"].apply(
            lambda x: f"+{x:.1f}%" if (pd.notna(x) and x >= 0) else (f"{x:.1f}%" if pd.notna(x) else "—")
        )
    if "rendimiento" in df.columns:
        display["Rendim."] = df["rendimiento"].apply(
            lambda x: f"+{x:.1f}%" if (pd.notna(x) and x >= 0) else (f"{x:.1f}%" if pd.notna(x) else "—")
        )

    st.dataframe(display, use_container_width=True, hide_index=True)

def tabla_movimientos(df: pd.DataFrame):
    """Tabla de movimientos con formato."""
    if df.empty:
        st.info("Sin movimientos registrados.")
        return

    TIPO_LABELS = {
        "compra": "🟢 Compra", "venta": "🔴 Venta",
        "renovacion": "🔄 Renovación", "dividendo": "💰 Dividendo", "otro": "Otro"
    }

    display = pd.DataFrame()
    display["Fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%d/%m/%Y")
    display["Tipo"] = df["tipo"].map(TIPO_LABELS).fillna(df["tipo"])
    display["Ticker"] = df["ticker"]
    display["Cantidad"] = df["cantidad"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
    display["Precio"] = df.apply(
        lambda r: f"${r['precio']:,.2f} {r['moneda']}" if pd.notna(r.get("precio")) else "—", axis=1
    )
    display["Total"] = df.apply(
        lambda r: f"${r['cantidad']*r['precio']:,.0f} {r['moneda']}"
        if pd.notna(r.get("cantidad")) and pd.notna(r.get("precio")) else "—", axis=1
    )
    if "notas" in df.columns:
        display["Notas"] = df["notas"].fillna("")

    st.dataframe(display, use_container_width=True, hide_index=True)

# ---- TICKER ROW (mercado) ----

def ticker_row(datos: dict):
    """Fila de cotización para el panel de mercado."""
    if not datos.get("ok"):
        cols = st.columns([2, 6])
        with cols[0]:
            st.markdown(f"**{datos['ticker']}**")
        with cols[1]:
            st.caption(f"Sin datos — {datos.get('error', '')}")
        return

    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 1.2, 0.9, 0.9, 0.9, 1.2, 1.2])

    def var_str(v):
        if v is None:
            return "—"
        signo = "+" if v >= 0 else ""
        color = VERDE if v >= 0 else ROJO
        return f"<span style='color:{color}'>{signo}{v:.1f}%</span>"

    with c1:
        st.markdown(f"**{datos['ticker']}**  \n<small style='color:#888'>{datos.get('nombre','')[:28]}</small>", unsafe_allow_html=True)
    with c2:
        moneda = datos.get("moneda", "")
        precio = datos.get("precio")
        st.markdown(f"**{moneda} {precio:,.2f}**" if precio else "—")
    with c3:
        st.markdown(var_str(datos.get("var_dia")), unsafe_allow_html=True)
    with c4:
        st.markdown(var_str(datos.get("var_sem")), unsafe_allow_html=True)
    with c5:
        st.markdown(var_str(datos.get("var_mes")), unsafe_allow_html=True)
    with c6:
        vol = datos.get("volumen")
        if vol:
            if vol >= 1_000_000:
                st.caption(f"{vol/1_000_000:.1f}M")
            elif vol >= 1_000:
                st.caption(f"{vol/1_000:.0f}K")
            else:
                st.caption(str(vol))
        else:
            st.caption("—")
    with c7:
        min52 = datos.get("min52")
        max52 = datos.get("max52")
        if min52 and max52:
            st.caption(f"{min52:,.0f} / {max52:,.0f}")
        else:
            st.caption("—")

def ticker_header():
    """Encabezado para tabla de tickers."""
    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 1.2, 0.9, 0.9, 0.9, 1.2, 1.2])
    style = "color:#888;font-size:11px;text-transform:uppercase;letter-spacing:.05em"
    with c1: st.markdown(f"<span style='{style}'>Ticker</span>", unsafe_allow_html=True)
    with c2: st.markdown(f"<span style='{style}'>Precio</span>", unsafe_allow_html=True)
    with c3: st.markdown(f"<span style='{style}'>Var. día</span>", unsafe_allow_html=True)
    with c4: st.markdown(f"<span style='{style}'>Var. sem.</span>", unsafe_allow_html=True)
    with c5: st.markdown(f"<span style='{style}'>Var. mes</span>", unsafe_allow_html=True)
    with c6: st.markdown(f"<span style='{style}'>Volumen</span>", unsafe_allow_html=True)
    with c7: st.markdown(f"<span style='{style}'>Mín/Máx 52s</span>", unsafe_allow_html=True)
    st.divider()

# ---- PERFIL DE RIESGO ----

def form_perfil(perfil_actual=None, form_key="form_perfil"):
    """Formulario de perfil de riesgo. Devuelve datos si se guarda."""
    p = perfil_actual or {}
    with st.form(form_key):
        st.markdown("**Cuestionario de perfil de riesgo**")
        horizonte = st.selectbox("Horizonte de inversión", [
            "Corto plazo (hasta 12 meses)",
            "Mediano plazo (1–3 años)",
            "Largo plazo (+5 años)"
        ], index=["Corto plazo (hasta 12 meses)", "Mediano plazo (1–3 años)", "Largo plazo (+5 años)"].index(
            p.get("horizonte", "Mediano plazo (1–3 años)")
        ) if p.get("horizonte") else 1)

        tolerancia = st.selectbox("Tolerancia al riesgo", [
            "Conservadora — prioriza estabilidad",
            "Moderada — acepta volatilidad parcial",
            "Agresiva — busca rendimiento máximo"
        ], index=["Conservadora — prioriza estabilidad", "Moderada — acepta volatilidad parcial", "Agresiva — busca rendimiento máximo"].index(
            p.get("tolerancia", "Moderada — acepta volatilidad parcial")
        ) if p.get("tolerancia") else 1)

        objetivo = st.text_input("Objetivo principal", value=p.get("objetivo", ""))
        liquidez = st.text_input("Liquidez requerida", value=p.get("liquidez", ""))
        restricciones = st.text_area("Restricciones / preferencias", value=p.get("restricciones", ""), height=80)

        import datetime
        fecha = st.date_input("Fecha de actualización", value=datetime.date.today(), format="DD/MM/YYYY")

        submitted = st.form_submit_button("Guardar perfil", type="primary")
        if submitted:
            return {
                "horizonte": horizonte, "tolerancia": tolerancia,
                "objetivo": objetivo, "liquidez": liquidez,
                "restricciones": restricciones, "fecha": fecha
            }
    return None

# ---- PILL TIPO ----

TIPO_COLORS = {
    "accion":  ("E6F1FB", "0C3D6B"),
    "cedear":  ("E6F1FB", "185FA5"),
    "bono":    ("FFF3CD", "856404"),
    "fci":     ("D6EFE1", "1A5C38"),
    "pf":      ("F0F0F0", "555555"),
    "otro":    ("F0F0F0", "555555"),
}
TIPO_LABELS = {
    "accion": "Acción", "cedear": "CEDEAR", "bono": "Bono",
    "fci": "FCI", "pf": "Plazo Fijo", "otro": "Otro"
}

def pill(tipo):
    bg, fg = TIPO_COLORS.get(tipo, ("F0F0F0", "555555"))
    label = TIPO_LABELS.get(tipo, tipo)
    return f"<span style='background:#{bg};color:#{fg};padding:2px 8px;border-radius:2px;font-size:11px;font-weight:500'>{label}</span>"
