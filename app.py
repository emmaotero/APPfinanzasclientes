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
    "FCI Pesos",
    "FCI Dólares",
    "Acciones Pesos",
    "Acciones USD",
    "CEDEARs Pesos",
    "CEDEARs Dólares",
    "Plazo Fijo Pesos",
    "Plazo Fijo Dólares",
    "ON Pesos",
    "ON Dólares",
    "Bono Pesos",
    "Bono Dólares",
    "Cash Pesos",
    "Cash Dólares",
    "Otro",
]

TIPOS_POSICION = ["accion", "cedear", "bono", "fci", "pf", "on", "cash", "otro"]
TIPOS_LABELS = {
    "accion": "Acción", "cedear": "CEDEAR", "bono": "Bono",
    "fci": "FCI", "pf": "Plazo Fijo", "on": "ON",
    "cash": "Cash", "otro": "Otro"
}

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Orden.ar · Carteras",
    page_icon="🟩",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  [data-testid="stSidebar"] { background-color: #1A1A1A; }
  [data-testid="stSidebar"] * { color: #cccccc !important; }
  [data-testid="stSidebarNav"] { display: none; }
  h1, h2, h3 { color: #1A1A1A; font-family: Georgia, serif; }
  .stMetric label { font-size: 11px !important; text-transform: uppercase; letter-spacing: .05em; color: #555 !important; }
  .stMetric [data-testid="metric-container"] { border-top: 3px solid #2E8B57; padding-top: 8px; }
  .stDataFrame { border: 1px solid #e5e5e5; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style='padding: 4px 0 16px'>
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
    ], label_visibility="collapsed")
    st.divider()
    st.caption("Jime · Manu · Emma\nv1.0 · 2025")

# ============================================================
# HELPERS
# ============================================================

def form_posicion(cartera_id, form_key, posicion_existente=None):
    """Formulario reutilizable para crear o editar una posición."""
    p = posicion_existente or {}
    es_edicion = bool(p)

    with st.form(form_key):
        c1, c2 = st.columns(2)
        with c1:
            nombre_desc = st.selectbox(
                "Categoría",
                NOMBRES_DESCRIPTIVOS,
                index=NOMBRES_DESCRIPTIVOS.index(p.get("nombre", "Otro")) if p.get("nombre") in NOMBRES_DESCRIPTIVOS else len(NOMBRES_DESCRIPTIVOS)-1
            )
            ticker = st.text_input(
                "Ticker yfinance (en MAYÚSCULAS — ej: GGAL.BA, AAPL, AL30.BA)",
                value=p.get("ticker", "")
            )
            tipo_pos = st.selectbox(
                "Tipo",
                TIPOS_POSICION,
                format_func=lambda x: TIPOS_LABELS.get(x, x),
                index=TIPOS_POSICION.index(p.get("tipo", "accion")) if p.get("tipo") in TIPOS_POSICION else 0
            )
            moneda_pos = st.selectbox("Moneda", ["ARS", "USD"],
                index=["ARS","USD"].index(p.get("moneda","ARS")) if p.get("moneda") in ["ARS","USD"] else 0)

        with c2:
            cantidad_pos = st.number_input("Cantidad", min_value=0.0, step=1.0, value=float(p.get("cantidad", 0)))
            precio_compra = st.number_input("Precio de compra", min_value=0.0, step=0.01, value=float(p.get("precio_compra", 0)))
            fecha_compra = st.date_input("Fecha de compra", value=date.today(), format="DD/MM/YYYY")
            precio_manual = st.number_input(
                "Precio actual manual (opcional — para FCI, PF y activos sin ticker)",
                min_value=0.0, step=0.01,
                value=float(p.get("precio_manual", 0) or 0),
                help="Si completás este campo, se usa este precio en lugar del de yfinance."
            )

        notas_pos = st.text_input("Notas (opcional)", value=p.get("notas", ""))

        label_btn = "Guardar cambios" if es_edicion else "Agregar posición"
        if st.form_submit_button(label_btn, type="primary"):
            if cantidad_pos > 0:
                ticker_final = ticker.strip().upper() if ticker.strip() else nombre_desc.upper().replace(" ", "_")
                precio_man = precio_manual if precio_manual > 0 else None
                return {
                    "ticker": ticker_final,
                    "nombre": nombre_desc,
                    "tipo": tipo_pos,
                    "moneda": moneda_pos,
                    "cantidad": cantidad_pos,
                    "precio_compra": precio_compra,
                    "fecha_compra": fecha_compra,
                    "precio_manual": precio_man,
                    "notas": notas_pos
                }
            else:
                st.error("La cantidad es obligatoria.")
    return None


def seccion_cartera(cartera_id, cartera_nombre):
    """Renderiza el detalle completo de una cartera: perfil, posiciones, movimientos."""

    perfil = db.get_perfil(cartera_id)
    pos = db.get_posiciones(cartera_id)
    movs = db.get_movimientos(cartera_id, limit=50)

    tab_pos, tab_mov, tab_perfil = st.tabs(["Posiciones", "Movimientos", "Perfil de riesgo"])

    # ---- POSICIONES ----
    with tab_pos:
        if not pos.empty:
            pos_v = market.valuar_posiciones(pos)

            # Totales por moneda
            cols_tot = st.columns(2)
            for i, moneda in enumerate(["ARS", "USD"]):
                sub = pos_v[pos_v["moneda"] == moneda]
                total = sub["valuacion"].dropna().sum()
                if total > 0:
                    with cols_tot[i]:
                        st.metric(f"Total {moneda}", f"${total:,.0f}")

            st.divider()

            # Tabla con editar / eliminar
            for _, row in pos_v.iterrows():
                c_info, c_precio, c_val, c_rend, c_edit, c_del = st.columns([3, 1.5, 1.5, 1, 0.6, 0.6])
                with c_info:
                    st.markdown(f"**{row.get('nombre', row['ticker'])}**  \n"
                                f"<small style='color:#888'>{row['ticker']} · {TIPOS_LABELS.get(row['tipo'], row['tipo'])} · {row['moneda']}</small>",
                                unsafe_allow_html=True)
                with c_precio:
                    p_actual = row.get("precio_actual")
                    p_man = row.get("precio_manual")
                    precio_str = f"${p_actual:,.2f}" if p_actual else (f"${p_man:,.2f} ✏️" if p_man else "—")
                    st.caption(f"Precio: {precio_str}")
                    st.caption(f"Cant: {row['cantidad']:,.0f}")
                with c_val:
                    val = row.get("valuacion")
                    st.caption(f"Valuación:")
                    st.markdown(f"**${val:,.0f}**" if val else "**—**")
                with c_rend:
                    rend = row.get("rendimiento")
                    if rend is not None:
                        color = "#2E8B57" if rend >= 0 else "#c0392b"
                        st.markdown(f"<span style='color:{color};font-weight:600'>{'+' if rend>=0 else ''}{rend:.1f}%</span>", unsafe_allow_html=True)
                    else:
                        st.caption("—")
                with c_edit:
                    if st.button("✏️", key=f"edit_pos_{row['id']}", help="Editar"):
                        st.session_state[f"editando_{row['id']}"] = True
                with c_del:
                    if st.button("🗑️", key=f"del_pos_{row['id']}", help="Eliminar"):
                        st.session_state[f"confirmar_del_pos_{row['id']}"] = True

                # Confirmar eliminación
                if st.session_state.get(f"confirmar_del_pos_{row['id']}"):
                    st.warning(f"¿Eliminar **{row.get('nombre', row['ticker'])}**? Esta acción no se puede deshacer.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Sí, eliminar", key=f"confirm_del_{row['id']}", type="primary"):
                            db.eliminar_posicion(row["id"])
                            st.session_state.pop(f"confirmar_del_pos_{row['id']}", None)
                            st.success("Posición eliminada.")
                            st.rerun()
                    with cc2:
                        if st.button("Cancelar", key=f"cancel_del_{row['id']}"):
                            st.session_state.pop(f"confirmar_del_pos_{row['id']}", None)
                            st.rerun()

                # Formulario de edición inline
                if st.session_state.get(f"editando_{row['id']}"):
                    with st.container():
                        st.markdown("**Editando posición:**")
                        datos = form_posicion(cartera_id, f"edit_form_{row['id']}", posicion_existente=row.to_dict())
                        if datos:
                            db.actualizar_posicion(row["id"], {
                                "ticker": datos["ticker"], "nombre": datos["nombre"],
                                "tipo": datos["tipo"], "moneda": datos["moneda"],
                                "cantidad": datos["cantidad"], "precio_compra": datos["precio_compra"],
                                "precio_manual": datos["precio_manual"], "notas": datos["notas"]
                            })
                            st.session_state.pop(f"editando_{row['id']}", None)
                            st.success("Posición actualizada.")
                            st.rerun()
                        if st.button("Cancelar edición", key=f"cancel_edit_{row['id']}"):
                            st.session_state.pop(f"editando_{row['id']}", None)
                            st.rerun()

                st.divider()
        else:
            st.info("Sin posiciones en esta cartera.")

        # Agregar nueva posición
        with st.expander("➕ Agregar posición"):
            datos = form_posicion(cartera_id, f"nueva_pos_{cartera_id}")
            if datos:
                db.crear_posicion(
                    cartera_id, datos["ticker"], datos["nombre"], datos["tipo"],
                    datos["moneda"], datos["cantidad"], datos["precio_compra"],
                    datos["fecha_compra"], datos["precio_manual"], datos["notas"]
                )
                st.success(f"✅ Posición **{datos['nombre']}** ({datos['ticker']}) agregada.")
                st.rerun()

    # ---- MOVIMIENTOS ----
    with tab_mov:
        st.caption("Los movimientos quedan registrados como historial de operaciones de esta cartera.")

        if not movs.empty:
            for _, mov in movs.iterrows():
                c1, c2, c3, c4 = st.columns([1.5, 2, 3, 0.6])
                TIPO_MOV = {"compra":"🟢 Compra","venta":"🔴 Venta","renovacion":"🔄 Renovación","dividendo":"💰 Dividendo","otro":"Otro"}
                with c1: st.caption(pd.to_datetime(mov["fecha"]).strftime("%d/%m/%Y"))
                with c2: st.caption(TIPO_MOV.get(mov["tipo"], mov["tipo"]))
                with c3:
                    precio = f"${mov['precio']:,.2f} {mov['moneda']}" if mov.get("precio") else "—"
                    total = f"${mov['cantidad']*mov['precio']:,.0f}" if mov.get("cantidad") and mov.get("precio") else "—"
                    st.caption(f"**{mov['ticker']}** · Cant: {mov.get('cantidad','—')} · P: {precio} · Total: {total}")
                    if mov.get("notas"):
                        st.caption(f"_{mov['notas']}_")
                with c4:
                    if st.button("🗑️", key=f"del_mov_{mov['id']}", help="Eliminar"):
                        db.eliminar_movimiento(mov["id"])
                        st.success("Movimiento eliminado.")
                        st.rerun()
                st.divider()
        else:
            st.info("Sin movimientos registrados.")

        with st.expander("➕ Registrar movimiento"):
            with st.form(f"nuevo_mov_{cartera_id}"):
                c1, c2 = st.columns(2)
                with c1:
                    tipo_mov = st.selectbox("Tipo", ["compra","venta","renovacion","dividendo","otro"],
                        format_func=lambda x: {"compra":"Compra","venta":"Venta","renovacion":"Renovación","dividendo":"Dividendo","otro":"Otro"}[x])
                    ticker_mov = st.text_input("Ticker (MAYÚSCULAS)")
                    cantidad_mov = st.number_input("Cantidad", min_value=0.0, step=1.0)
                with c2:
                    fecha_mov = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
                    precio_mov = st.number_input("Precio unitario", min_value=0.0, step=0.01)
                    moneda_mov = st.selectbox("Moneda", ["ARS","USD"])
                notas_mov = st.text_input("Notas")
                if st.form_submit_button("Registrar movimiento", type="primary"):
                    if ticker_mov.strip() and cantidad_mov > 0:
                        db.registrar_movimiento(
                            cartera_id, tipo_mov, fecha_mov,
                            ticker_mov.strip().upper(), cantidad_mov,
                            precio_mov, moneda_mov, notas=notas_mov
                        )
                        st.success("✅ Movimiento registrado.")
                        st.rerun()
                    else:
                        st.error("Ticker y cantidad son obligatorios.")

    # ---- PERFIL ----
    with tab_perfil:
        if perfil:
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"**Horizonte:** {perfil.get('horizonte','—')}")
                st.caption(f"**Tolerancia:** {perfil.get('tolerancia','—')}")
                st.caption(f"**Objetivo:** {perfil.get('objetivo','—')}")
            with col2:
                st.caption(f"**Liquidez:** {perfil.get('liquidez','—')}")
                st.caption(f"**Restricciones:** {perfil.get('restricciones','—')}")
                st.caption(f"**Actualizado:** {perfil.get('fecha_actualizacion','—')}")
            st.divider()

        perfil_data = ui.form_perfil(perfil, form_key=f"perfil_{cartera_id}")
        if perfil_data:
            db.guardar_perfil(
                cartera_id,
                perfil_data["horizonte"], perfil_data["tolerancia"],
                perfil_data["objetivo"], perfil_data["liquidez"],
                perfil_data["restricciones"], perfil_data["fecha"]
            )
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
            pos_v = market.valuar_posiciones(posiciones_df)
            ui.tabla_posiciones(pos_v)
        else:
            st.info("Aún no hay posiciones registradas.")

    with col_right:
        st.subheader("Dólares")
        if dolares:
            for d in dolares[:5]:
                c1, c2, c3 = st.columns([3, 2, 2])
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

                    col1, col2, col_del = st.columns([3, 3, 1])
                    with col1:
                        st.caption(f"**Tipo:** {'Empresa' if cl['tipo']=='empresa' else 'Persona física'}")
                        st.caption(f"**Desde:** {cl['desde']}")
                        st.caption(f"**Carteras:** {len(carteras)}")
                    with col2:
                        if cl.get("notas"):
                            st.caption(f"**Notas:** {cl['notas']}")
                    with col_del:
                        if st.button("🗑️ Eliminar cliente", key=f"del_cl_{cl['id']}"):
                            st.session_state[f"confirmar_del_cl_{cl['id']}"] = True

                    if st.session_state.get(f"confirmar_del_cl_{cl['id']}"):
                        st.warning(f"¿Eliminar a **{cl['nombre']}** y todas sus carteras? Esta acción no se puede deshacer.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Sí, eliminar", key=f"confirm_cl_{cl['id']}", type="primary"):
                                db.eliminar_cliente(cl["id"])
                                st.session_state.pop(f"confirmar_del_cl_{cl['id']}", None)
                                st.success(f"Cliente '{cl['nombre']}' eliminado.")
                                st.rerun()
                        with cc2:
                            if st.button("Cancelar", key=f"cancel_cl_{cl['id']}"):
                                st.session_state.pop(f"confirmar_del_cl_{cl['id']}", None)
                                st.rerun()

                    st.divider()

                    # Carteras del cliente
                    if not carteras.empty:
                        for _, cart in carteras.iterrows():
                            col_cart, col_del_cart = st.columns([8, 1])
                            with col_cart:
                                st.markdown(f"**📁 {cart['nombre']}** · {cart['moneda_base']}")
                            with col_del_cart:
                                if st.button("🗑️", key=f"del_cart_{cart['id']}", help="Eliminar cartera"):
                                    st.session_state[f"confirmar_del_cart_{cart['id']}"] = True

                            if st.session_state.get(f"confirmar_del_cart_{cart['id']}"):
                                st.warning(f"¿Eliminar cartera **{cart['nombre']}**?")
                                cc1, cc2 = st.columns(2)
                                with cc1:
                                    if st.button("Sí, eliminar", key=f"confirm_cart_{cart['id']}", type="primary"):
                                        db.eliminar_cartera(cart["id"])
                                        st.session_state.pop(f"confirmar_del_cart_{cart['id']}", None)
                                        st.success("Cartera eliminada.")
                                        st.rerun()
                                with cc2:
                                    if st.button("Cancelar", key=f"cancel_cart_{cart['id']}"):
                                        st.session_state.pop(f"confirmar_del_cart_{cart['id']}", None)
                                        st.rerun()

                            seccion_cartera(cart["id"], cart["nombre"])
                            st.divider()

                    # Nueva cartera para este cliente
                    with st.expander("➕ Nueva cartera"):
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
            tipo = st.selectbox("Tipo", ["persona", "empresa"],
                format_func=lambda x: "Persona física" if x == "persona" else "Empresa")
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
            pos_v = market.valuar_posiciones(posiciones_df)
            ui.tabla_posiciones(pos_v)

            tipo_counts = posiciones_df["tipo"].value_counts().reset_index()
            tipo_counts.columns = ["tipo", "cantidad"]
            tipo_counts["tipo"] = tipo_counts["tipo"].map(TIPOS_LABELS).fillna(tipo_counts["tipo"])
            fig = px.pie(tipo_counts, names="tipo", values="cantidad",
                        color_discrete_sequence=["#2E8B57","#185FA5","#A8D5B5","#85B7EB","#D6EFE1","#E6F1FB"],
                        hole=0.4)
            fig.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin posiciones registradas.")

    with tab_detalle:
        clientes_df = db.get_clientes()
        if clientes_df.empty:
            st.info("No hay clientes todavía.")
        else:
            cliente_sel = st.selectbox(
                "Cliente",
                clientes_df["id"].tolist(),
                format_func=lambda x: clientes_df[clientes_df["id"]==x]["nombre"].values[0]
            )
            carteras = db.get_carteras(cliente_sel)
            if carteras.empty:
                st.info("Este cliente no tiene carteras.")
            else:
                cartera_sel = st.selectbox(
                    "Cartera",
                    carteras["id"].tolist(),
                    format_func=lambda x: carteras[carteras["id"]==x]["nombre"].values[0]
                )
                seccion_cartera(cartera_sel, carteras[carteras["id"]==cartera_sel]["nombre"].values[0])

# ---- MERCADO ----
elif pagina == "📈  Mercado":
    st.title("Mercado")

    tab_dolares, tab_cartera, tab_radar, tab_inflacion = st.tabs([
        "Dólares", "En cartera", "Radar", "Inflación"
    ])

    with tab_dolares:
        dolares = market.get_dolares()
        if dolares:
            col1, col2 = st.columns(2)
            for i, d in enumerate(dolares):
                with (col1 if i % 2 == 0 else col2):
                    c1, c2, c3 = st.columns([3, 2, 2])
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
            c1, c2 = st.columns([4, 1])
            with c1:
                nuevo_ticker = st.text_input("Ticker (MAYÚSCULAS — ej: GGAL.BA, AAPL, GD30.BA)",
                    label_visibility="collapsed", placeholder="Agregar ticker al radar...")
            with c2:
                submitted = st.form_submit_button("+ Agregar", type="primary")
            if submitted and nuevo_ticker:
                ok = db.agregar_radar(nuevo_ticker.strip().upper(), "")
                if ok:
                    st.success(f"✅ {nuevo_ticker.upper()} agregado.")
                    st.rerun()
                else:
                    st.warning("Ese ticker ya está en el radar.")

        radar_tickers = db.get_radar()
        if not radar_tickers:
            st.info("El radar está vacío. Agregá tickers arriba.")
        else:
            with st.spinner("Actualizando..."):
                cotizaciones = market.cotizar_varios(radar_tickers)
            ui.ticker_header()
            for ticker in radar_tickers:
                datos = cotizaciones.get(ticker, {"ticker": ticker, "ok": False})
                col_data, col_del = st.columns([11, 1])
                with col_data:
                    ui.ticker_row(datos)
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
                marker_color=["#c0392b" if v > 5 else "#2E8B57" for v in infl_df["valor"]],
                text=[f"{v:.1f}%" for v in infl_df["valor"]], textposition="outside"
            ))
            fig.update_layout(yaxis_title="IPC mensual (%)",
                margin=dict(t=20,b=0,l=0,r=0), height=360,
                plot_bgcolor="white", yaxis=dict(gridcolor="#f0f0f0"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No se pudo traer el IPC.")
