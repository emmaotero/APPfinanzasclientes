"""
Orden.ar · App de Gestión de Carteras
Streamlit + Supabase + yfinance
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date

import db
import market
import ui

# ============================================================
# CONSTANTES
# ============================================================
NOMBRES_DESCRIPTIVOS = [
    "FCI Pesos", "FCI Dólares",
    "Acciones Pesos", "Acciones USD",
    "CEDEARs Pesos", "CEDEARs Dólares",
    "Plazo Fijo Pesos", "Plazo Fijo Dólares",
    "ON Pesos", "ON Dólares",
    "Bono Pesos", "Bono Dólares",
    "Cash Pesos", "Cash Dólares",
    "Otro",
]
TIPOS = ["accion", "cedear", "bono", "fci", "pf", "on", "cash", "otro"]
TIPOS_LABELS = {
    "accion": "Acción", "cedear": "CEDEAR", "bono": "Bono",
    "fci": "FCI", "pf": "Plazo Fijo", "on": "ON",
    "cash": "Cash", "otro": "Otro"
}
TIPO_MOV_LABELS = {
    "compra": "🟢 Compra", "venta": "🔴 Venta",
    "renovacion": "🔄 Renovación", "carga_inicial": "📥 Carga inicial",
    "dividendo": "💰 Dividendo", "otro": "Otro"
}
# Tipos que usan precio manual (sin ticker yfinance)
TIPOS_MANUALES = ["fci", "pf", "cash", "otro"]

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Orden.ar · Carteras", page_icon="🟩",
    layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  [data-testid="stSidebar"] { background-color: #1A1A1A; }
  [data-testid="stSidebar"] * { color: #cccccc !important; }
  [data-testid="stSidebarNav"] { display: none; }
  h1,h2,h3 { color: #1A1A1A; font-family: Georgia, serif; }
  .stMetric label { font-size:11px !important; text-transform:uppercase; letter-spacing:.05em; color:#555 !important; }
  .stMetric [data-testid="metric-container"] { border-top: 3px solid #2E8B57; padding-top:8px; }
  .stDataFrame { border: 1px solid #e5e5e5; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style='padding:4px 0 16px'>
      <div style='display:grid;grid-template-columns:repeat(4,10px);gap:2px;margin-bottom:8px'>
        <div style='width:10px;height:10px;background:#1A5C38'></div><div style='width:10px;height:10px;background:#2E8B57'></div>
        <div style='width:10px;height:10px;background:#A8D5B5'></div><div style='width:10px;height:10px;background:#D6EFE1'></div>
        <div style='width:10px;height:10px;background:#2E8B57'></div><div style='width:10px;height:10px;background:#0C3D6B'></div>
        <div style='width:10px;height:10px;background:#185FA5'></div><div style='width:10px;height:10px;background:#A8D5B5'></div>
        <div style='width:10px;height:10px;background:#A8D5B5'></div><div style='width:10px;height:10px;background:#185FA5'></div>
        <div style='width:10px;height:10px;background:#0C3D6B'></div><div style='width:10px;height:10px;background:#2E8B57'></div>
        <div style='width:10px;height:10px;background:#D6EFE1'></div><div style='width:10px;height:10px;background:#A8D5B5'></div>
        <div style='width:10px;height:10px;background:#2E8B57'></div><div style='width:10px;height:10px;background:#1A5C38'></div>
      </div>
      <span style='font-family:Georgia,serif;font-size:20px;font-weight:600;color:#fff'>
        Orden<span style='color:#2E8B57'>.ar</span>
      </span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    pagina = st.radio("", [
        "📊  Dashboard",
        "👥  Clientes",
        "💼  Carteras",
        "📈  Mercado",
        "📖  Metodología",
    ], label_visibility="collapsed")
    st.divider()
    st.caption("Jime · Manu · Emma\nv1.0 · 2025")

# ============================================================
# HELPERS UI
# ============================================================

def confirmar_eliminar(key, label, accion):
    """Botón de eliminar con confirmación en dos pasos."""
    if st.button("🗑️", key=f"del_{key}", help=f"Eliminar {label}"):
        st.session_state[f"confirm_{key}"] = True
    if st.session_state.get(f"confirm_{key}"):
        st.warning(f"¿Eliminar **{label}**? Esta acción no se puede deshacer.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sí, eliminar", key=f"yes_{key}", type="primary"):
                accion()
                st.session_state.pop(f"confirm_{key}", None)
                st.rerun()
        with c2:
            if st.button("Cancelar", key=f"no_{key}"):
                st.session_state.pop(f"confirm_{key}", None)
                st.rerun()

def form_campos_instrumento(key_prefix, defaults=None):
    """Campos comunes para instrumento (nombre, ticker, tipo, moneda)."""
    d = defaults or {}
    nombre_desc = st.selectbox("Categoría", NOMBRES_DESCRIPTIVOS,
        index=NOMBRES_DESCRIPTIVOS.index(d.get("nombre", "Otro"))
              if d.get("nombre") in NOMBRES_DESCRIPTIVOS else len(NOMBRES_DESCRIPTIVOS)-1,
        key=f"{key_prefix}_nombre")
    ticker = st.text_input("Ticker yfinance — siempre en MAYÚSCULAS (ej: GGAL.BA, AAPL, AL30.BA)\n"
                           "Para FCI, PF o Cash podés dejar el ticker vacío.",
        value=d.get("ticker", ""), key=f"{key_prefix}_ticker")
    tipo = st.selectbox("Tipo", TIPOS, format_func=lambda x: TIPOS_LABELS.get(x, x),
        index=TIPOS.index(d.get("tipo","accion")) if d.get("tipo") in TIPOS else 0,
        key=f"{key_prefix}_tipo")
    moneda = st.selectbox("Moneda", ["ARS","USD"],
        index=["ARS","USD"].index(d.get("moneda","ARS")) if d.get("moneda") in ["ARS","USD"] else 0,
        key=f"{key_prefix}_moneda")
    return nombre_desc, ticker, tipo, moneda


def seccion_cartera(cartera_id, cartera_nombre):
    """Renderiza detalle completo de una cartera."""
    pos = db.get_posiciones(cartera_id)
    movs = db.get_movimientos(cartera_id, limit=100)
    perfil = db.get_perfil(cartera_id)

    tab_pos, tab_ops, tab_mov, tab_perfil = st.tabs([
        "📊 Posiciones", "➕ Operaciones", "📋 Movimientos", "👤 Perfil de riesgo"
    ])

    # ---- POSICIONES ----
    with tab_pos:
        if pos.empty:
            st.info("Sin posiciones. Usá la pestaña **Operaciones** para cargar la primera posición.")
        else:
            pos_v = market.valuar_posiciones(pos)

            # Totales
            c1, c2 = st.columns(2)
            for col, moneda in zip([c1, c2], ["ARS", "USD"]):
                sub = pos_v[pos_v["moneda"] == moneda]
                total = sub["valuacion"].dropna().sum()
                if total > 0:
                    with col:
                        st.metric(f"Total {moneda}", f"${total:,.0f}")

            st.divider()

            for _, row in pos_v.iterrows():
                p_actual = row.get("precio_actual")
                p_manual = row.get("precio_manual")
                ppp = row.get("precio_compra")
                precio_usado = p_actual if p_actual else p_manual
                precio_str = (f"${p_actual:,.2f} ↗" if p_actual else
                             (f"${p_manual:,.2f} ✏️" if p_manual else "sin precio"))
                fuente = "yfinance" if p_actual else ("manual" if p_manual else "—")

                rend = row.get("rendimiento")
                val = row.get("valuacion")
                gp_no_real = (precio_usado - ppp) * row["cantidad"] if precio_usado and ppp else None

                col_info, col_nums, col_btns = st.columns([4, 4, 1])

                with col_info:
                    st.markdown(f"**{row.get('nombre', row['ticker'])}**  \n"
                        f"<small style='color:#888'>{row['ticker']} · "
                        f"{TIPOS_LABELS.get(row['tipo'], row['tipo'])} · "
                        f"{row['moneda']} · Cant: {row['cantidad']:,.2f}</small>",
                        unsafe_allow_html=True)

                with col_nums:
                    c_ppp, c_precio, c_val, c_rend = st.columns(4)
                    with c_ppp:
                        st.caption("PPP")
                        st.markdown(f"**${ppp:,.2f}**" if ppp else "**—**")
                    with c_precio:
                        st.caption(f"Actual ({fuente})")
                        st.markdown(f"**{precio_str}**")
                    with c_val:
                        st.caption("Valuación")
                        st.markdown(f"**${val:,.0f}**" if val else "**—**")
                    with c_rend:
                        st.caption("Rendim.")
                        if rend is not None:
                            color = "#2E8B57" if rend >= 0 else "#c0392b"
                            st.markdown(f"<span style='color:{color};font-weight:600'>"
                                       f"{'+' if rend>=0 else ''}{rend:.1f}%</span>",
                                       unsafe_allow_html=True)
                        else:
                            st.caption("—")

                with col_btns:
                    if st.button("✏️", key=f"edit_{row['id']}", help="Editar"):
                        st.session_state[f"edit_{row['id']}"] = True
                    confirmar_eliminar(
                        f"pos_{row['id']}", row.get("nombre", row["ticker"]),
                        lambda pid=row["id"]: db.eliminar_posicion(pid)
                    )

                # Edición inline
                if st.session_state.get(f"edit_{row['id']}"):
                    with st.form(f"edit_form_{row['id']}"):
                        st.caption("Editando posición — solo modifica datos descriptivos. Para cambiar cantidad usá Operaciones.")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            e_nombre = st.selectbox("Categoría", NOMBRES_DESCRIPTIVOS,
                                index=NOMBRES_DESCRIPTIVOS.index(row.get("nombre","Otro"))
                                      if row.get("nombre") in NOMBRES_DESCRIPTIVOS else len(NOMBRES_DESCRIPTIVOS)-1)
                            e_tipo = st.selectbox("Tipo", TIPOS, format_func=lambda x: TIPOS_LABELS[x],
                                index=TIPOS.index(row["tipo"]) if row["tipo"] in TIPOS else 0)
                        with ec2:
                            e_precio_manual = st.number_input("Precio manual",
                                value=float(row.get("precio_manual") or 0), min_value=0.0, step=0.01)
                            e_notas = st.text_input("Notas", value=row.get("notas","") or "")
                        c_save, c_cancel = st.columns(2)
                        with c_save:
                            if st.form_submit_button("Guardar", type="primary"):
                                db.actualizar_posicion(row["id"], {
                                    "nombre": e_nombre, "tipo": e_tipo,
                                    "precio_manual": e_precio_manual if e_precio_manual > 0 else None,
                                    "notas": e_notas
                                })
                                st.session_state.pop(f"edit_{row['id']}", None)
                                st.success("Posición actualizada.")
                                st.rerun()
                        with c_cancel:
                            if st.form_submit_button("Cancelar"):
                                st.session_state.pop(f"edit_{row['id']}", None)
                                st.rerun()

                if gp_no_real is not None:
                    color = "#2E8B57" if gp_no_real >= 0 else "#c0392b"
                    signo = "+" if gp_no_real >= 0 else ""
                    st.caption(
                        f"G/P no realizada: "
                        f"<span style='color:{color}'>{signo}${gp_no_real:,.0f}</span>",
                        unsafe_allow_html=True
                    )

                st.divider()

    # ---- OPERACIONES ----
    with tab_ops:
        st.caption("Todas las operaciones actualizan automáticamente las posiciones.")

        tipo_op = st.radio("Tipo de operación", [
            "📥 Carga inicial", "🟢 Compra", "🔴 Venta", "🔄 Renovación (PF / FCI)"
        ], horizontal=True, key=f"radio_op_{cartera_id}")

        st.divider()

        # CARGA INICIAL
        if tipo_op == "📥 Carga inicial":
            st.markdown("**Carga inicial** — para registrar posiciones que ya existían antes de usar la app.")
            with st.form(f"carga_inicial_{cartera_id}"):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_desc = st.selectbox("Categoría", NOMBRES_DESCRIPTIVOS)
                    ticker = st.text_input("Ticker (MAYÚSCULAS) — opcional para FCI/PF/Cash")
                    tipo = st.selectbox("Tipo", TIPOS, format_func=lambda x: TIPOS_LABELS[x])
                    moneda = st.selectbox("Moneda", ["ARS","USD"])
                with c2:
                    cantidad = st.number_input("Cantidad actual", min_value=0.0, step=1.0)
                    ppp = st.number_input("PPP / Precio promedio de compra",
                        min_value=0.0, step=0.01,
                        help="Si compraste en varios momentos, ingresá el promedio ponderado ya calculado.")
                    fecha = st.date_input("Fecha de referencia", value=date.today(), format="DD/MM/YYYY")
                    precio_manual = st.number_input("Precio actual manual (para FCI/PF)",
                        min_value=0.0, step=0.01)
                notas = st.text_input("Notas")
                if st.form_submit_button("Cargar posición inicial", type="primary"):
                    if cantidad > 0:
                        ticker_f = ticker.strip().upper() if ticker.strip() else nombre_desc.replace(" ","_").upper()
                        db.registrar_carga_inicial(
                            cartera_id, ticker_f, nombre_desc, tipo, moneda,
                            cantidad, ppp, fecha,
                            precio_manual if precio_manual > 0 else None, notas
                        )
                        st.success(f"✅ Posición **{nombre_desc}** cargada.")
                        st.rerun()
                    else:
                        st.error("La cantidad es obligatoria.")

        # COMPRA
        elif tipo_op == "🟢 Compra":
            st.markdown("**Compra** — si ya tenés esta posición, suma la cantidad y recalcula el PPP automáticamente.")
            with st.form(f"compra_{cartera_id}"):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_desc = st.selectbox("Categoría", NOMBRES_DESCRIPTIVOS)
                    ticker = st.text_input("Ticker (MAYÚSCULAS — ej: GGAL.BA, AAPL)")
                    tipo = st.selectbox("Tipo", TIPOS, format_func=lambda x: TIPOS_LABELS[x])
                    moneda = st.selectbox("Moneda", ["ARS","USD"])
                with c2:
                    cantidad = st.number_input("Cantidad comprada", min_value=0.0, step=1.0)
                    precio = st.number_input("Precio de compra", min_value=0.0, step=0.01)
                    fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
                    precio_manual = st.number_input("Precio manual (solo FCI/PF)",
                        min_value=0.0, step=0.01)
                notas = st.text_input("Notas")
                if st.form_submit_button("Registrar compra", type="primary"):
                    if cantidad > 0 and precio > 0:
                        ticker_f = ticker.strip().upper() if ticker.strip() else nombre_desc.replace(" ","_").upper()
                        # Mostrar PPP resultante si ya existe la posición
                        pos_existente = db.get_posicion_by_ticker(cartera_id, ticker_f, moneda)
                        db.registrar_compra(
                            cartera_id, ticker_f, nombre_desc, tipo, moneda,
                            cantidad, precio, fecha,
                            precio_manual if precio_manual > 0 else None, notas
                        )
                        if pos_existente:
                            nuevo_ppp = db._calcular_ppp(
                                pos_existente["cantidad"], pos_existente["precio_compra"],
                                cantidad, precio
                            )
                            st.success(f"✅ Compra registrada. Nuevo PPP: **${nuevo_ppp:,.2f}**")
                        else:
                            st.success(f"✅ Posición **{nombre_desc}** creada. PPP: **${precio:,.2f}**")
                        st.rerun()
                    else:
                        st.error("Cantidad y precio son obligatorios.")

        # VENTA
        elif tipo_op == "🔴 Venta":
            if pos.empty:
                st.info("No hay posiciones para vender.")
            else:
                st.markdown("**Venta** — seleccioná la posición y cargá la cantidad y precio de venta.")
                opciones_pos = pos[pos["activa"] == True] if "activa" in pos.columns else pos
                if opciones_pos.empty:
                    st.info("No hay posiciones activas.")
                else:
                    pos_id = st.selectbox(
                        "Posición a vender",
                        opciones_pos["id"].tolist(),
                        format_func=lambda x: (
                            lambda r: f"{r.get('nombre', r['ticker'])} · {r['ticker']} · "
                                     f"{r['moneda']} · Cant: {r['cantidad']:,.2f} · PPP: ${r.get('precio_compra',0):,.2f}"
                        )(opciones_pos[opciones_pos["id"]==x].iloc[0].to_dict()),
                        key=f"sel_venta_{cartera_id}"
                    )
                    pos_sel = opciones_pos[opciones_pos["id"]==pos_id].iloc[0]

                    with st.form(f"venta_{cartera_id}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            cantidad_venta = st.number_input(
                                f"Cantidad a vender (máx: {pos_sel['cantidad']:,.2f})",
                                min_value=0.0, max_value=float(pos_sel["cantidad"]), step=1.0
                            )
                            fecha_v = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
                        with c2:
                            precio_venta = st.number_input("Precio de venta", min_value=0.0, step=0.01)
                            moneda_v = st.selectbox("Moneda", ["ARS","USD"],
                                index=["ARS","USD"].index(pos_sel["moneda"]) if pos_sel["moneda"] in ["ARS","USD"] else 0)
                        notas_v = st.text_input("Notas")

                        # Preview de ganancia/pérdida
                        ppp_actual = pos_sel.get("precio_compra", 0) or 0
                        if precio_venta > 0 and cantidad_venta > 0 and ppp_actual > 0:
                            gp = (precio_venta - ppp_actual) * cantidad_venta
                            gp_pct = ((precio_venta / ppp_actual) - 1) * 100
                            color = "#2E8B57" if gp >= 0 else "#c0392b"
                            st.markdown(
                                f"<small>PPP: <b>${ppp_actual:,.2f}</b> · "
                                f"G/P estimada: <span style='color:{color}'><b>"
                                f"{'+'if gp>=0 else ''}${gp:,.0f} ({gp_pct:+.1f}%)</b></span></small>",
                                unsafe_allow_html=True
                            )

                        if st.form_submit_button("Registrar venta", type="primary"):
                            if cantidad_venta > 0 and precio_venta > 0:
                                try:
                                    resultado = db.registrar_venta(
                                        cartera_id, pos_id, pos_sel["ticker"],
                                        cantidad_venta, precio_venta, fecha_v, moneda_v, notas_v
                                    )
                                    gp = resultado["ganancia"]
                                    gp_pct = resultado["ganancia_pct"]
                                    signo = "+" if gp >= 0 else ""
                                    emoji = "📈" if gp >= 0 else "📉"
                                    st.success(
                                        f"✅ Venta registrada. {emoji} G/P realizada: "
                                        f"**{signo}${gp:,.0f} ({gp_pct:+.1f}%)**  \n"
                                        f"PPP utilizado: ${resultado['ppp']:,.2f}"
                                    )
                                    st.rerun()
                                except ValueError as e:
                                    st.error(str(e))
                            else:
                                st.error("Cantidad y precio son obligatorios.")

        # RENOVACIÓN
        elif tipo_op == "🔄 Renovación (PF / FCI)":
            pos_manuales = pos[pos["tipo"].isin(TIPOS_MANUALES)] if not pos.empty else pd.DataFrame()
            if pos_manuales.empty:
                st.info("No hay posiciones de FCI, PF o Cash para renovar.")
            else:
                st.markdown("**Renovación** — actualizá el precio/valor actual de una posición manual.")
                pos_id_r = st.selectbox(
                    "Posición a renovar",
                    pos_manuales["id"].tolist(),
                    format_func=lambda x: (
                        lambda r: f"{r.get('nombre', r['ticker'])} · {r['moneda']} · Cant: {r['cantidad']:,.2f}"
                    )(pos_manuales[pos_manuales["id"]==x].iloc[0].to_dict()),
                    key=f"sel_renov_{cartera_id}"
                )
                with st.form(f"renov_{cartera_id}"):
                    nuevo_precio = st.number_input("Nuevo valor / cuota / precio", min_value=0.0, step=0.01)
                    fecha_r = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
                    notas_r = st.text_input("Notas (ej: renovación 30 días, nueva tasa)")
                    if st.form_submit_button("Registrar renovación", type="primary"):
                        if nuevo_precio > 0:
                            db.registrar_renovacion(pos_id_r, nuevo_precio, fecha_r, notas_r)
                            st.success("✅ Renovación registrada y precio actualizado.")
                            st.rerun()
                        else:
                            st.error("El precio es obligatorio.")

    # ---- MOVIMIENTOS ----
    with tab_mov:
        if movs.empty:
            st.info("Sin movimientos registrados.")
        else:
            for _, mov in movs.iterrows():
                c1, c2, c3, c4 = st.columns([1.2, 1.5, 5, 0.6])
                with c1:
                    st.caption(pd.to_datetime(mov["fecha"]).strftime("%d/%m/%Y"))
                with c2:
                    st.caption(TIPO_MOV_LABELS.get(mov["tipo"], mov["tipo"]))
                with c3:
                    precio = f"${mov['precio']:,.2f} {mov['moneda']}" if mov.get("precio") else "—"
                    total = (f"${mov['cantidad']*mov['precio']:,.0f} {mov['moneda']}"
                             if mov.get("cantidad") and mov.get("precio") else "—")
                    st.caption(f"**{mov['ticker']}** · Cant: {mov.get('cantidad','—')} · "
                               f"P: {precio} · Total: {total}")
                    if mov.get("notas"):
                        st.caption(f"_{mov['notas']}_")
                with c4:
                    if st.button("🗑️", key=f"del_mov_{mov['id']}", help="Eliminar"):
                        db.eliminar_movimiento(mov["id"])
                        st.rerun()
                st.divider()

    # ---- PERFIL ----
    with tab_perfil:
        if perfil:
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"**Horizonte:** {perfil.get('horizonte','—')}")
                st.caption(f"**Tolerancia:** {perfil.get('tolerancia','—')}")
                st.caption(f"**Objetivo:** {perfil.get('objetivo','—')}")
            with c2:
                st.caption(f"**Liquidez:** {perfil.get('liquidez','—')}")
                st.caption(f"**Restricciones:** {perfil.get('restricciones','—')}")
                st.caption(f"**Actualizado:** {perfil.get('fecha_actualizacion','—')}")
            st.divider()
        perfil_data = ui.form_perfil(perfil, form_key=f"perfil_{cartera_id}")
        if perfil_data:
            db.guardar_perfil(cartera_id,
                perfil_data["horizonte"], perfil_data["tolerancia"],
                perfil_data["objetivo"], perfil_data["liquidez"],
                perfil_data["restricciones"], perfil_data["fecha"])
            st.success("✅ Perfil actualizado.")
            st.rerun()


# ============================================================
# PÁGINAS
# ============================================================

# ---- DASHBOARD ----
if pagina == "📊  Dashboard":
    st.title("Dashboard")

    clientes_df = db.get_clientes()
    carteras_df = db.get_carteras()
    posiciones_df = db.get_posiciones()
    dolares = market.get_dolares()
    mep = next((d for d in dolares if "MEP" in d["nombre"]), None)
    mep_val = f"{mep['venta']:,.2f}" if mep and mep.get("venta") else "—"

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Clientes activos", len(clientes_df))
    with col2: st.metric("Carteras activas", len(carteras_df))
    with col3: st.metric("Posiciones totales", len(posiciones_df))
    with col4: st.metric("Dólar MEP", f"${mep_val}")

    st.divider()
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Posiciones activas")
        if not posiciones_df.empty:
            ui.tabla_posiciones(market.valuar_posiciones(posiciones_df))
        else:
            st.info("Aún no hay posiciones.")

    with col_right:
        st.subheader("Dólares")
        if dolares:
            for d in dolares[:5]:
                c1, c2, c3 = st.columns([3,2,2])
                with c1: st.caption(d["nombre"])
                with c2: st.caption(f"${d['compra']:,.2f}" if d.get("compra") else "—")
                with c3: st.caption(f"${d['venta']:,.2f}" if d.get("venta") else "—")
        else:
            st.caption("Sin datos.")

# ---- CLIENTES ----
elif pagina == "👥  Clientes":
    st.title("Clientes")
    tab_lista, tab_nuevo = st.tabs(["Lista de clientes", "Nuevo cliente"])

    with tab_lista:
        clientes_df = db.get_clientes()
        if clientes_df.empty:
            st.info("No hay clientes registrados todavía.")
        else:
            for _, cl in clientes_df.iterrows():
                with st.expander(f"{'🏢' if cl['tipo']=='empresa' else '👤'}  {cl['nombre']}"):
                    carteras = db.get_carteras(cl["id"])
                    col1, col2, col_del = st.columns([4, 4, 1])
                    with col1:
                        st.caption(f"**Tipo:** {'Empresa' if cl['tipo']=='empresa' else 'Persona física'}")
                        st.caption(f"**Desde:** {cl['desde']} · **Carteras:** {len(carteras)}")
                    with col2:
                        if cl.get("notas"): st.caption(f"**Notas:** {cl['notas']}")
                    with col_del:
                        confirmar_eliminar(f"cl_{cl['id']}", cl["nombre"],
                            lambda cid=cl["id"]: db.eliminar_cliente(cid))

                    st.divider()
                    if not carteras.empty:
                        for _, cart in carteras.iterrows():
                            col_c, col_dc = st.columns([9, 1])
                            with col_c:
                                st.markdown(f"**📁 {cart['nombre']}** · {cart['moneda_base']}")
                            with col_dc:
                                confirmar_eliminar(f"cart_{cart['id']}", cart["nombre"],
                                    lambda cid=cart["id"]: db.eliminar_cartera(cid))
                            seccion_cartera(cart["id"], cart["nombre"])
                            st.divider()

                    with st.expander("➕ Nueva cartera para este cliente"):
                        with st.form(f"nueva_cart_{cl['id']}"):
                            nombre_cart = st.text_input("Nombre (ej: Principal, USD, Conservadora)")
                            moneda_cart = st.selectbox("Moneda base", ["mixta","ARS","USD"])
                            if st.form_submit_button("Crear cartera", type="primary"):
                                if nombre_cart:
                                    db.crear_cartera(cl["id"], nombre_cart, moneda_cart)
                                    st.success(f"✅ Cartera **{nombre_cart}** creada.")
                                    st.rerun()
                                else:
                                    st.error("El nombre es obligatorio.")

    with tab_nuevo:
        with st.form("nuevo_cliente"):
            nombre = st.text_input("Nombre completo / Razón social")
            tipo = st.selectbox("Tipo", ["persona","empresa"],
                format_func=lambda x: "Persona física" if x=="persona" else "Empresa")
            desde = st.date_input("Cliente desde", value=date.today(), format="DD/MM/YYYY")
            notas = st.text_area("Notas", height=80)
            if st.form_submit_button("Crear cliente", type="primary"):
                if nombre:
                    db.crear_cliente(nombre, tipo, desde, notas)
                    st.success(f"✅ Cliente **{nombre}** creado correctamente.")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio.")

# ---- CARTERAS ----
elif pagina == "💼  Carteras":
    st.title("Carteras")
    tab_consolidado, tab_detalle = st.tabs(["Vista consolidada", "Por cliente"])

    with tab_consolidado:
        posiciones_df = db.get_posiciones()
        if not posiciones_df.empty:
            ui.tabla_posiciones(market.valuar_posiciones(posiciones_df))
            tipo_counts = posiciones_df["tipo"].value_counts().reset_index()
            tipo_counts.columns = ["tipo","cantidad"]
            tipo_counts["tipo"] = tipo_counts["tipo"].map(TIPOS_LABELS).fillna(tipo_counts["tipo"])
            fig = px.pie(tipo_counts, names="tipo", values="cantidad",
                color_discrete_sequence=["#2E8B57","#185FA5","#A8D5B5","#85B7EB","#D6EFE1","#E6F1FB"], hole=0.4)
            fig.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin posiciones registradas.")

    with tab_detalle:
        clientes_df = db.get_clientes()
        if clientes_df.empty:
            st.info("No hay clientes todavía.")
        else:
            cliente_sel = st.selectbox("Cliente", clientes_df["id"].tolist(),
                format_func=lambda x: clientes_df[clientes_df["id"]==x]["nombre"].values[0])
            carteras = db.get_carteras(cliente_sel)
            if carteras.empty:
                st.info("Este cliente no tiene carteras.")
            else:
                cartera_sel = st.selectbox("Cartera", carteras["id"].tolist(),
                    format_func=lambda x: carteras[carteras["id"]==x]["nombre"].values[0])
                seccion_cartera(cartera_sel, carteras[carteras["id"]==cartera_sel]["nombre"].values[0])

# ---- MERCADO ----
elif pagina == "📈  Mercado":
    st.title("Mercado")
    tab_dolares, tab_cartera, tab_radar, tab_inflacion = st.tabs([
        "Dólares", "En cartera", "Radar", "Inflación"])

    with tab_dolares:
        dolares = market.get_dolares()
        if dolares:
            col1, col2 = st.columns(2)
            for i, d in enumerate(dolares):
                with (col1 if i%2==0 else col2):
                    c1,c2,c3 = st.columns([3,2,2])
                    with c1: st.markdown(f"**{d['nombre']}**")
                    with c2: st.caption(f"Compra: ${d['compra']:,.2f}" if d.get("compra") else "—")
                    with c3: st.caption(f"Venta: ${d['venta']:,.2f}" if d.get("venta") else "—")
                    st.divider()
        else:
            st.warning("No se pudo conectar con la API.")

    with tab_cartera:
        posiciones_df = db.get_posiciones()
        tickers_yf = []
        if not posiciones_df.empty:
            tickers_yf = posiciones_df[
                posiciones_df["tipo"].isin(["accion","cedear","bono","on"])
            ]["ticker"].unique().tolist()
        if not tickers_yf:
            st.info("No hay acciones, CEDEARs, bonos ni ONs en cartera todavía.")
        else:
            with st.spinner("Trayendo cotizaciones..."):
                cotizaciones = market.cotizar_varios(tickers_yf)
            ui.ticker_header()
            for ticker, datos in cotizaciones.items():
                ui.ticker_row(datos)
                st.divider()

    with tab_radar:
        with st.form("add_radar", clear_on_submit=True):
            c1, c2 = st.columns([4,1])
            with c1:
                nuevo_ticker = st.text_input("Ticker (MAYÚSCULAS)", label_visibility="collapsed",
                    placeholder="Agregar ticker al radar — ej: GGAL.BA, AAPL, GD30.BA")
            with c2:
                submitted = st.form_submit_button("+ Agregar", type="primary")
            if submitted and nuevo_ticker:
                ok = db.agregar_radar(nuevo_ticker.strip().upper())
                st.success(f"✅ {nuevo_ticker.upper()} agregado.") if ok else st.warning("Ya está en el radar.")
                if ok: st.rerun()

        radar_tickers = db.get_radar()
        if not radar_tickers:
            st.info("El radar está vacío.")
        else:
            with st.spinner("Actualizando..."):
                cotizaciones = market.cotizar_varios(radar_tickers)
            ui.ticker_header()
            for ticker in radar_tickers:
                datos = cotizaciones.get(ticker, {"ticker": ticker, "ok": False})
                col_data, col_del = st.columns([11,1])
                with col_data: ui.ticker_row(datos)
                with col_del:
                    st.write("")
                    if st.button("✕", key=f"del_{ticker}", help=f"Eliminar {ticker}"):
                        db.eliminar_radar(ticker)
                        st.rerun()
                st.divider()

    with tab_inflacion:
        infl_df = market.get_inflacion(12)
        if not infl_df.empty:
            fig = go.Figure(go.Bar(
                x=infl_df["fecha"], y=infl_df["valor"],
                marker_color=["#c0392b" if v>5 else "#2E8B57" for v in infl_df["valor"]],
                text=[f"{v:.1f}%" for v in infl_df["valor"]], textposition="outside"
            ))
            fig.update_layout(yaxis_title="IPC mensual (%)",
                margin=dict(t=20,b=0,l=0,r=0), height=360,
                plot_bgcolor="white", yaxis=dict(gridcolor="#f0f0f0"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No se pudo traer el IPC.")

# ---- METODOLOGÍA ----
elif pagina == "📖  Metodología":
    st.title("Metodología")
    st.caption("Cómo funciona la lógica de la app — para uso interno y para explicarle a clientes.")

    st.divider()

    st.subheader("01 · Precio Promedio Ponderado (PPP)")
    st.markdown("""
El PPP es el costo promedio de adquisición de una posición cuando se realizaron compras
en distintos momentos y a distintos precios. Es la métrica base para calcular el rendimiento.

**Fórmula:**
> PPP = Σ (precio × cantidad por compra) / Cantidad total acumulada

**Ejemplo — GGAL comprada en dos momentos:**
""")
    st.table(pd.DataFrame({
        "Evento": ["Compra 1", "Compra 2", "Estado actual"],
        "Cantidad": ["100", "200", "300"],
        "Precio unitario": ["$3.000", "$4.000", "—"],
        "Monto operado": ["$300.000", "$800.000", "$1.100.000"],
        "PPP resultante": ["$3.000,00", "$3.666,67", "→ $3.666,67 ✓"],
    }))
    st.caption("El PPP de $3.666,67 es el precio de referencia para medir el rendimiento, "
               "independientemente de en qué momento se compraron las acciones.")

    st.divider()
    st.subheader("02 · Registro de operaciones")
    st.markdown("Cada operación actualiza automáticamente la posición correspondiente:")
    st.table(pd.DataFrame({
        "Acción": ["📥 Carga inicial", "🟢 Compra", "🔴 Venta parcial", "🔴 Venta total", "🔄 Renovación"],
        "Qué hace la app": [
            "Registra posiciones preexistentes con PPP ya conocido. Punto de partida del historial.",
            "Si la posición existe: suma cantidad y recalcula PPP. Si no existe: la crea.",
            "Resta la cantidad. Calcula G/P realizada vs PPP. PPP no cambia.",
            "Igual que venta parcial, pero cierra la posición (marcada inactiva).",
            "Actualiza precio manual (PF, FCI). No modifica cantidad ni PPP.",
        ]
    }))

    st.divider()
    st.subheader("03 · Venta parcial — ejemplo")
    st.markdown("300 acciones de GGAL con PPP $3.666,67. Se venden 100 a $5.000:")
    st.table(pd.DataFrame({
        "Concepto": ["Cantidad vendida", "Precio de venta", "Costo de lo vendido (PPP × cant.)", "Ganancia realizada", "Posición restante"],
        "Valor": ["100 acciones", "$5.000", "$3.666,67 × 100 = $366.667", "$500.000 − $366.667 = $133.333 (+36,4%)", "200 acciones · PPP sin cambio: $3.666,67"],
    }))

    st.divider()
    st.subheader("04 · Métricas de rendimiento")
    st.table(pd.DataFrame({
        "Métrica": ["Rendimiento por posición", "Valuación", "G/P no realizada", "G/P realizada", "Rendimiento de cartera"],
        "Cálculo": [
            "(Precio actual − PPP) / PPP × 100",
            "Precio actual × cantidad (o precio manual × cantidad para FCI/PF)",
            "Valuación actual − (PPP × cantidad) — lo que ganarías si vendieras hoy",
            "Acumulado en el historial de movimientos de cada venta",
            "Σ valuaciones actuales / Σ costos históricos − 1, ponderado por posición",
        ]
    }))

    st.divider()
    st.subheader("05 · Casos especiales")

    with st.expander("FCI y Plazo Fijo"):
        st.markdown("""
Estos instrumentos no tienen ticker en yfinance. El precio actual se carga manualmente
al registrar una **Renovación**. La app usa ese precio para calcular valuación y rendimiento.

Al registrar la compra/carga inicial de un FCI o PF, podés dejar el ticker vacío —
la app genera un identificador interno automáticamente.
""")

    with st.expander("Carteras mixtas ARS / USD"):
        st.markdown("""
Cada posición tiene su moneda asignada (ARS o USD). Las valuaciones se muestran
en la moneda de cada posición y los totales de cartera se presentan **separados por moneda**
para no mezclar valores sin un tipo de cambio acordado.
""")

    with st.expander("Tickers en yfinance — formato correcto"):
        st.table(pd.DataFrame({
            "Instrumento": ["Acciones BYMA", "CEDEARs / internacionales", "Bonos BYMA", "ONs BYMA", "FCI / Plazo Fijo / Cash"],
            "Formato": ["TICKER.BA", "Sin sufijo", "TICKER.BA", "TICKER.BA", "Sin ticker (precio manual)"],
            "Ejemplos": ["GGAL.BA · YPF.BA · BMA.BA", "AAPL · MSFT · TSLA · AMZN", "AL30.BA · GD30.BA · AE38.BA", "YCA6O.BA · YMCXO.BA", "Dejar vacío — la app asigna ID interno"],
        }))

    with st.expander("Carga inicial — primer uso de la app"):
        st.markdown("""
Cuando un cliente ya tenía inversiones antes de incorporarse, se registran con **Carga inicial**.
Se ingresa el PPP ya calculado (o el precio de la última compra conocida) y la cantidad actual.

No genera movimiento de compra en el historial — es el punto de partida.
A partir de ahí, todas las operaciones subsiguientes actualizan la posición automáticamente.
""")
