"""
Orden.ar · App de Gestión de Carteras
Streamlit + Supabase + yfinance
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

import db
import market
import ui

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Orden.ar · Carteras",
    page_icon="🟩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS global
st.markdown("""
<style>
  [data-testid="stSidebar"] { background-color: #1A1A1A; }
  [data-testid="stSidebar"] * { color: #cccccc !important; }
  [data-testid="stSidebar"] .stRadio label { color: #aaaaaa !important; font-size: 14px; }
  [data-testid="stSidebarNav"] { display: none; }
  h1, h2, h3 { color: #1A1A1A; font-family: Georgia, serif; }
  .stMetric label { font-size: 11px !important; text-transform: uppercase; letter-spacing: .05em; color: #555 !important; }
  .stMetric [data-testid="metric-container"] { border-top: 3px solid #2E8B57; padding-top: 8px; }
  div[data-testid="stHorizontalBlock"] > div:nth-child(even) .stMetric [data-testid="metric-container"] {
    border-top-color: #185FA5;
  }
  .stDataFrame { border: 1px solid #e5e5e5; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    # Logo
    st.markdown("""
    <div style='padding: 4px 0 16px'>
      <div style='display:grid;grid-template-columns:repeat(4,10px);gap:2px;margin-bottom:8px'>
        <div style='width:10px;height:10px;background:#1A5C38'></div>
        <div style='width:10px;height:10px;background:#2E8B57'></div>
        <div style='width:10px;height:10px;background:#A8D5B5'></div>
        <div style='width:10px;height:10px;background:#D6EFE1'></div>
        <div style='width:10px;height:10px;background:#2E8B57'></div>
        <div style='width:10px;height:10px;background:#0C3D6B'></div>
        <div style='width:10px;height:10px;background:#185FA5'></div>
        <div style='width:10px;height:10px;background:#A8D5B5'></div>
        <div style='width:10px;height:10px;background:#A8D5B5'></div>
        <div style='width:10px;height:10px;background:#185FA5'></div>
        <div style='width:10px;height:10px;background:#0C3D6B'></div>
        <div style='width:10px;height:10px;background:#2E8B57'></div>
        <div style='width:10px;height:10px;background:#D6EFE1'></div>
        <div style='width:10px;height:10px;background:#A8D5B5'></div>
        <div style='width:10px;height:10px;background:#2E8B57'></div>
        <div style='width:10px;height:10px;background:#1A5C38'></div>
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
        "↕️  Movimientos",
        "📈  Mercado",
    ], label_visibility="collapsed")

    st.divider()
    st.caption("Jime · Manu · Emma\nv1.0 · 2025")

# ============================================================
# PÁGINAS
# ============================================================

# ---- DASHBOARD ----
if pagina == "📊  Dashboard":
    st.title("Dashboard")

    clientes_df = db.get_clientes()
    carteras_df = db.get_carteras()
    posiciones_df = db.get_posiciones()
    movimientos_df = db.get_movimientos(limit=5)

    n_clientes = len(clientes_df)
    n_carteras = len(carteras_df)
    n_posiciones = len(posiciones_df)

    # Dólar MEP para referencia
    dolares = market.get_dolares()
    mep = next((d for d in dolares if "MEP" in d["nombre"]), None)
    mep_val = f"{mep['venta']:,.2f}" if mep and mep.get("venta") else "—"

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Clientes activos", n_clientes)
    with col2: st.metric("Carteras activas", n_carteras)
    with col3: st.metric("Posiciones totales", n_posiciones)
    with col4: st.metric("Dólar MEP", f"${mep_val}")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Posiciones activas")
        if not posiciones_df.empty:
            pos_valuadas = market.valuar_posiciones(posiciones_df)
            ui.tabla_posiciones(pos_valuadas)
        else:
            st.info("Aún no hay posiciones registradas.")

    with col_right:
        st.subheader("Últimos movimientos")
        if not movimientos_df.empty:
            ui.tabla_movimientos(movimientos_df)
        else:
            st.info("Sin movimientos recientes.")

        st.subheader("Dólares")
        if dolares:
            for d in dolares[:4]:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: st.caption(d["nombre"])
                with c2: st.caption(f"${d['compra']:,.2f}" if d.get("compra") else "—")
                with c3: st.caption(f"${d['venta']:,.2f}" if d.get("venta") else "—")
        else:
            st.caption("Sin datos de cotizaciones.")

# ---- CLIENTES ----
elif pagina == "👥  Clientes":
    st.title("Clientes")

    tab_lista, tab_nuevo = st.tabs(["Lista", "Nuevo cliente"])

    with tab_lista:
        clientes_df = db.get_clientes()
        if clientes_df.empty:
            st.info("No hay clientes registrados todavía.")
        else:
            for _, cl in clientes_df.iterrows():
                with st.expander(f"{'🏢' if cl['tipo']=='empresa' else '👤'}  {cl['nombre']}"):
                    carteras = db.get_carteras(cl["id"])

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"**Tipo:** {'Empresa' if cl['tipo']=='empresa' else 'Persona física'}")
                        st.caption(f"**Desde:** {cl['desde']}")
                    with col2:
                        st.caption(f"**Carteras:** {len(carteras)}")
                    with col3:
                        if cl.get("notas"):
                            st.caption(f"**Notas:** {cl['notas']}")

                    if not carteras.empty:
                        st.markdown("**Carteras:**")
                        for _, cart in carteras.iterrows():
                            perfil = db.get_perfil(cart["id"])
                            tolerancia = perfil.get("tolerancia", "Sin perfil") if perfil else "Sin perfil"
                            st.markdown(f"— **{cart['nombre']}** · {cart['moneda_base']} · {tolerancia}")

                            pos = db.get_posiciones(cart["id"])
                            if not pos.empty:
                                pos_v = market.valuar_posiciones(pos)
                                ui.tabla_posiciones(pos_v)

                            with st.popover("Editar perfil de riesgo"):
                                perfil_data = ui.form_perfil(perfil, form_key=f"perfil_{cart['id']}")
                                if perfil_data:
                                    db.guardar_perfil(
                                        cart["id"],
                                        perfil_data["horizonte"],
                                        perfil_data["tolerancia"],
                                        perfil_data["objetivo"],
                                        perfil_data["liquidez"],
                                        perfil_data["restricciones"],
                                        perfil_data["fecha"]
                                    )
                                    st.success("Perfil actualizado.")
                                    st.rerun()

    with tab_nuevo:
        with st.form("nuevo_cliente"):
            nombre = st.text_input("Nombre completo / Razón social")
            tipo = st.selectbox("Tipo", ["persona", "empresa"])
            desde = st.date_input("Cliente desde", value=date.today(), format="DD/MM/YYYY")
            notas = st.text_area("Notas", height=80)
            if st.form_submit_button("Crear cliente", type="primary"):
                if nombre:
                    db.crear_cliente(nombre, tipo, desde, notas)
                    st.success(f"Cliente '{nombre}' creado.")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio.")

# ---- CARTERAS ----
elif pagina == "💼  Carteras":
    st.title("Carteras")

    tab_consolidado, tab_detalle, tab_nueva = st.tabs([
        "Vista consolidada", "Por cliente", "Nueva cartera"
    ])

    with tab_consolidado:
        st.subheader("Todas las posiciones")
        posiciones_df = db.get_posiciones()
        if not posiciones_df.empty:
            pos_v = market.valuar_posiciones(posiciones_df)
            ui.tabla_posiciones(pos_v)

            # Composición por tipo
            st.subheader("Composición por tipo de instrumento")
            tipo_counts = posiciones_df["tipo"].value_counts().reset_index()
            tipo_counts.columns = ["tipo", "cantidad"]
            tipo_labels = {"accion":"Acción","cedear":"CEDEAR","bono":"Bono","fci":"FCI","pf":"Plazo Fijo","otro":"Otro"}
            tipo_counts["tipo"] = tipo_counts["tipo"].map(tipo_labels).fillna(tipo_counts["tipo"])
            colors = ["#2E8B57","#185FA5","#A8D5B5","#85B7EB","#D6EFE1","#E6F1FB"]
            fig = px.pie(tipo_counts, names="tipo", values="cantidad",
                        color_discrete_sequence=colors, hole=0.4)
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
                "Seleccioná un cliente",
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

                perfil = db.get_perfil(cartera_sel)
                pos = db.get_posiciones(cartera_sel)

                col_perf, col_rend = st.columns(2)

                with col_perf:
                    st.markdown("**Perfil de riesgo**")
                    if perfil:
                        st.caption(f"Horizonte: {perfil.get('horizonte','—')}")
                        st.caption(f"Riesgo: {perfil.get('tolerancia','—')}")
                        st.caption(f"Objetivo: {perfil.get('objetivo','—')}")
                        st.caption(f"Liquidez: {perfil.get('liquidez','—')}")
                        st.caption(f"Actualizado: {perfil.get('fecha_actualizacion','—')}")
                    else:
                        st.caption("Sin perfil cargado.")

                    with st.popover("Actualizar perfil"):
                        perfil_data = ui.form_perfil(perfil, form_key=f"perfil_cart_{cartera_sel}")
                        if perfil_data:
                            db.guardar_perfil(cartera_sel, **{k: perfil_data[k] for k in ["horizonte","tolerancia","objetivo","liquidez","restricciones","fecha"]})
                            st.success("Perfil actualizado.")
                            st.rerun()

                with col_rend:
                    st.markdown("**Posiciones**")
                    if not pos.empty:
                        pos_v = market.valuar_posiciones(pos)
                        # Valuación total por moneda
                        for moneda in ["ARS", "USD"]:
                            sub = pos_v[pos_v["moneda"]==moneda]
                            total = sub["valuacion"].dropna().sum()
                            if total > 0:
                                st.metric(f"Total {moneda}", f"${total:,.0f}")
                    else:
                        st.info("Sin posiciones.")

                st.divider()
                st.markdown("**Posiciones activas**")
                if not pos.empty:
                    pos_v = market.valuar_posiciones(pos)
                    ui.tabla_posiciones(pos_v)

                    # Gráfico de composición
                    if not pos_v["valuacion"].dropna().empty:
                        fig2 = px.bar(
                            pos_v.dropna(subset=["valuacion"]),
                            x="ticker", y="valuacion",
                            color="tipo",
                            color_discrete_sequence=["#2E8B57","#185FA5","#A8D5B5","#85B7EB","#D6EFE1"],
                            labels={"ticker":"Instrumento","valuacion":"Valuación","tipo":"Tipo"}
                        )
                        fig2.update_layout(margin=dict(t=20,b=0,l=0,r=0), height=260, showlegend=True)
                        st.plotly_chart(fig2, use_container_width=True)

                # Agregar posición
                st.divider()
                st.markdown("**Agregar posición**")
                with st.form("nueva_posicion"):
                    c1, c2 = st.columns(2)
                    with c1:
                        ticker = st.text_input("Ticker (ej: GGAL.BA, AAPL, AL30.BA)")
                        nombre_pos = st.text_input("Nombre descriptivo")
                        tipo_pos = st.selectbox("Tipo", ["accion","cedear","bono","fci","pf","otro"])
                    with c2:
                        moneda_pos = st.selectbox("Moneda", ["ARS","USD"])
                        cantidad_pos = st.number_input("Cantidad", min_value=0.0, step=1.0)
                        precio_compra = st.number_input("Precio de compra", min_value=0.0, step=0.01)
                        fecha_compra = st.date_input("Fecha de compra", value=date.today(), format="DD/MM/YYYY")
                    notas_pos = st.text_input("Notas (opcional)")
                    if st.form_submit_button("Agregar posición", type="primary"):
                        if ticker and cantidad_pos > 0:
                            db.crear_posicion(cartera_sel, ticker.upper(), nombre_pos, tipo_pos,
                                            moneda_pos, cantidad_pos, precio_compra, fecha_compra, notas_pos)
                            st.success(f"Posición {ticker.upper()} agregada.")
                            st.rerun()
                        else:
                            st.error("Ticker y cantidad son obligatorios.")

    with tab_nueva:
        clientes_df = db.get_clientes()
        with st.form("nueva_cartera"):
            if clientes_df.empty:
                st.warning("Primero creá un cliente.")
            else:
                cliente_id = st.selectbox(
                    "Cliente",
                    clientes_df["id"].tolist(),
                    format_func=lambda x: clientes_df[clientes_df["id"]==x]["nombre"].values[0]
                )
                nombre_cart = st.text_input("Nombre de la cartera (ej: Principal, USD, Conservadora)")
                moneda_cart = st.selectbox("Moneda base", ["mixta","ARS","USD"])
                if st.form_submit_button("Crear cartera", type="primary"):
                    if nombre_cart:
                        db.crear_cartera(cliente_id, nombre_cart, moneda_cart)
                        st.success("Cartera creada.")
                        st.rerun()
                    else:
                        st.error("El nombre es obligatorio.")

# ---- MOVIMIENTOS ----
elif pagina == "↕️  Movimientos":
    st.title("Movimientos")

    tab_historial, tab_nuevo = st.tabs(["Historial", "Registrar movimiento"])

    with tab_historial:
        carteras_df = db.get_carteras()
        opciones = [None] + carteras_df["id"].tolist() if not carteras_df.empty else [None]

        filtro_cartera = None
        if not carteras_df.empty:
            sel = st.selectbox(
                "Filtrar por cartera",
                [None] + carteras_df["id"].tolist(),
                format_func=lambda x: "Todas" if x is None else (
                    carteras_df[carteras_df["id"]==x]["nombre"].values[0]
                )
            )
            filtro_cartera = sel

        movs = db.get_movimientos(cartera_id=filtro_cartera, limit=200)
        ui.tabla_movimientos(movs)

    with tab_nuevo:
        carteras_df = db.get_carteras()
        if carteras_df.empty:
            st.info("Primero creá una cartera.")
        else:
            with st.form("nuevo_mov"):
                cartera_id = st.selectbox(
                    "Cartera",
                    carteras_df["id"].tolist(),
                    format_func=lambda x: carteras_df[carteras_df["id"]==x]["nombre"].values[0]
                )
                c1, c2 = st.columns(2)
                with c1:
                    tipo_mov = st.selectbox("Tipo de operación", ["compra","venta","renovacion","dividendo","otro"])
                    ticker_mov = st.text_input("Ticker")
                    cantidad_mov = st.number_input("Cantidad", min_value=0.0, step=1.0)
                with c2:
                    fecha_mov = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
                    precio_mov = st.number_input("Precio unitario", min_value=0.0, step=0.01)
                    moneda_mov = st.selectbox("Moneda", ["ARS","USD"])
                notas_mov = st.text_input("Notas")
                if st.form_submit_button("Registrar", type="primary"):
                    if ticker_mov and cantidad_mov > 0:
                        db.registrar_movimiento(
                            cartera_id, tipo_mov, fecha_mov, ticker_mov.upper(),
                            cantidad_mov, precio_mov, moneda_mov, notas=notas_mov
                        )
                        st.success("Movimiento registrado.")
                        st.rerun()
                    else:
                        st.error("Ticker y cantidad son obligatorios.")

# ---- MERCADO ----
elif pagina == "📈  Mercado":
    st.title("Mercado")

    tab_dolares, tab_cartera, tab_radar, tab_inflacion = st.tabs([
        "Dólares", "Acciones en cartera", "Radar", "Inflación"
    ])

    # -- DÓLARES --
    with tab_dolares:
        st.subheader("Tipos de cambio")
        dolares = market.get_dolares()
        if dolares:
            col1, col2 = st.columns(2)
            for i, d in enumerate(dolares):
                target = col1 if i % 2 == 0 else col2
                with target:
                    c1, c2, c3 = st.columns([3, 2, 2])
                    with c1: st.markdown(f"**{d['nombre']}**")
                    with c2: st.caption(f"Compra: ${d['compra']:,.2f}" if d.get("compra") else "—")
                    with c3: st.caption(f"Venta: ${d['venta']:,.2f}" if d.get("venta") else "—")
                    st.divider()
        else:
            st.warning("No se pudo conectar con la API de cotizaciones.")

    # -- ACCIONES EN CARTERA --
    with tab_cartera:
        st.subheader("Acciones y CEDEARs en cartera")
        posiciones_df = db.get_posiciones()
        tickers_en_cartera = []
        if not posiciones_df.empty:
            tickers_en_cartera = posiciones_df[
                posiciones_df["tipo"].isin(["accion","cedear","bono"])
            ]["ticker"].unique().tolist()

        if not tickers_en_cartera:
            st.info("No hay acciones, CEDEARs ni bonos en cartera todavía.")
        else:
            with st.spinner("Trayendo cotizaciones..."):
                cotizaciones = market.cotizar_varios(tickers_en_cartera)
            ui.ticker_header()
            for ticker, datos in cotizaciones.items():
                ui.ticker_row(datos)
                st.divider()

    # -- RADAR --
    with tab_radar:
        st.subheader("Radar de seguimiento")

        col_add, _ = st.columns([2, 3])
        with col_add:
            with st.form("add_radar", clear_on_submit=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    nuevo_ticker = st.text_input("Ticker", placeholder="Ej: GGAL.BA, AAPL, GD30.BA", label_visibility="collapsed")
                with c2:
                    submitted = st.form_submit_button("+ Agregar", type="primary")
                if submitted and nuevo_ticker:
                    ok = db.agregar_radar(nuevo_ticker.strip().upper(), "")
                    if ok:
                        st.success(f"{nuevo_ticker.upper()} agregado.")
                        st.rerun()
                    else:
                        st.warning("Ese ticker ya está en el radar.")

        radar_tickers = db.get_radar()
        if not radar_tickers:
            st.info("El radar está vacío. Agregá tickers para hacer seguimiento.")
        else:
            with st.spinner("Actualizando cotizaciones..."):
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

    # -- INFLACIÓN --
    with tab_inflacion:
        st.subheader("Inflación mensual (IPC)")
        infl_df = market.get_inflacion(12)
        if not infl_df.empty:
            fig = go.Figure(go.Bar(
                x=infl_df["fecha"],
                y=infl_df["valor"],
                marker_color=["#c0392b" if v > 5 else "#2E8B57" for v in infl_df["valor"]],
                text=[f"{v:.1f}%" for v in infl_df["valor"]],
                textposition="outside"
            ))
            fig.update_layout(
                yaxis_title="IPC mensual (%)",
                margin=dict(t=20,b=0,l=0,r=0),
                height=360,
                plot_bgcolor="white",
                yaxis=dict(gridcolor="#f0f0f0")
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No se pudo traer el IPC.")
