"""
Orden.ar · Capa de acceso a datos (Supabase)
Lógica de PPP integrada en registro de movimientos.
"""
import streamlit as st
from supabase import create_client, Client
import pandas as pd

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ---- CLIENTES ----

def get_clientes(solo_activos=True):
    sb = get_client()
    q = sb.table("clientes").select("*").order("nombre")
    if solo_activos:
        q = q.eq("activo", True)
    r = q.execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def crear_cliente(nombre, tipo, desde, notas=""):
    sb = get_client()
    return sb.table("clientes").insert({
        "nombre": nombre, "tipo": tipo, "desde": str(desde), "notas": notas
    }).execute().data

def eliminar_cliente(cliente_id):
    get_client().table("clientes").update({"activo": False}).eq("id", cliente_id).execute()

# ---- CARTERAS ----

def get_carteras(cliente_id=None):
    sb = get_client()
    q = sb.table("carteras").select("*, clientes(nombre, tipo)").eq("activa", True)
    if cliente_id:
        q = q.eq("cliente_id", cliente_id)
    return pd.DataFrame(q.execute().data or [])

def crear_cartera(cliente_id, nombre, moneda_base):
    return get_client().table("carteras").insert({
        "cliente_id": cliente_id, "nombre": nombre, "moneda_base": moneda_base
    }).execute().data

def eliminar_cartera(cartera_id):
    get_client().table("carteras").update({"activa": False}).eq("id", cartera_id).execute()

# ---- PERFIL DE RIESGO ----

def get_perfil(cartera_id):
    r = get_client().table("perfil_riesgo").select("*").eq("cartera_id", cartera_id)\
        .order("created_at", desc=True).limit(1).execute()
    return r.data[0] if r.data else None

def guardar_perfil(cartera_id, horizonte, tolerancia, objetivo, liquidez, restricciones, fecha):
    sb = get_client()
    existing = get_perfil(cartera_id)
    datos = {
        "cartera_id": cartera_id, "horizonte": horizonte, "tolerancia": tolerancia,
        "objetivo": objetivo, "liquidez": liquidez, "restricciones": restricciones,
        "fecha_actualizacion": str(fecha)
    }
    if existing:
        sb.table("perfil_riesgo").update(datos).eq("id", existing["id"]).execute()
    else:
        sb.table("perfil_riesgo").insert(datos).execute()

# ---- POSICIONES ----

def get_posiciones(cartera_id=None, solo_activas=True):
    sb = get_client()
    q = sb.table("posiciones").select("*, carteras(nombre, cliente_id, clientes(nombre))")
    if cartera_id:
        q = q.eq("cartera_id", cartera_id)
    if solo_activas:
        q = q.eq("activa", True)
    return pd.DataFrame(q.execute().data or [])

def get_posicion_by_ticker(cartera_id, ticker, moneda):
    """Busca una posición activa por ticker y moneda dentro de una cartera."""
    r = get_client().table("posiciones").select("*")\
        .eq("cartera_id", cartera_id)\
        .eq("ticker", ticker.upper())\
        .eq("moneda", moneda)\
        .eq("activa", True)\
        .limit(1).execute()
    return r.data[0] if r.data else None

def _calcular_ppp(cantidad_actual, ppp_actual, cantidad_nueva, precio_nuevo):
    """Calcula el nuevo PPP al agregar una compra."""
    costo_actual = (cantidad_actual or 0) * (ppp_actual or 0)
    costo_nuevo = cantidad_nueva * precio_nuevo
    total_cantidad = (cantidad_actual or 0) + cantidad_nueva
    if total_cantidad == 0:
        return 0
    return (costo_actual + costo_nuevo) / total_cantidad

def registrar_compra(cartera_id, ticker, nombre, tipo, moneda, cantidad, precio, fecha, precio_manual=None, notas=""):
    """
    Registra una compra. Si la posición ya existe, suma cantidad y recalcula PPP.
    Si no existe, la crea. Siempre registra el movimiento en el historial.
    """
    sb = get_client()
    ticker = ticker.upper().strip()
    pos = get_posicion_by_ticker(cartera_id, ticker, moneda)

    if pos:
        # Posición existente — actualizar PPP y cantidad
        nuevo_ppp = _calcular_ppp(pos["cantidad"], pos["precio_compra"], cantidad, precio)
        nueva_cantidad = pos["cantidad"] + cantidad
        sb.table("posiciones").update({
            "cantidad": nueva_cantidad,
            "precio_compra": round(nuevo_ppp, 6),
            "nombre": nombre or pos["nombre"],
            "tipo": tipo or pos["tipo"],
            "precio_manual": precio_manual if precio_manual else pos.get("precio_manual"),
        }).eq("id", pos["id"]).execute()
        posicion_id = pos["id"]
    else:
        # Nueva posición
        r = sb.table("posiciones").insert({
            "cartera_id": cartera_id, "ticker": ticker, "nombre": nombre,
            "tipo": tipo, "moneda": moneda, "cantidad": cantidad,
            "precio_compra": precio, "fecha_compra": str(fecha),
            "precio_manual": precio_manual, "activa": True, "notas": notas
        }).execute()
        posicion_id = r.data[0]["id"] if r.data else None

    # Registrar movimiento
    sb.table("movimientos").insert({
        "cartera_id": cartera_id, "posicion_id": posicion_id,
        "tipo": "compra", "fecha": str(fecha), "ticker": ticker,
        "cantidad": cantidad, "precio": precio, "moneda": moneda, "notas": notas
    }).execute()

    return posicion_id

def registrar_carga_inicial(cartera_id, ticker, nombre, tipo, moneda, cantidad, ppp, fecha, precio_manual=None, notas=""):
    """
    Carga inicial: registra una posición preexistente con PPP ya conocido.
    No genera movimiento de compra — es el punto de partida del historial.
    """
    sb = get_client()
    ticker = ticker.upper().strip()
    pos = get_posicion_by_ticker(cartera_id, ticker, moneda)

    if pos:
        # Si ya existe, actualiza
        sb.table("posiciones").update({
            "cantidad": cantidad, "precio_compra": ppp,
            "nombre": nombre or pos["nombre"], "tipo": tipo or pos["tipo"],
            "precio_manual": precio_manual,
        }).eq("id", pos["id"]).execute()
        posicion_id = pos["id"]
    else:
        r = sb.table("posiciones").insert({
            "cartera_id": cartera_id, "ticker": ticker, "nombre": nombre,
            "tipo": tipo, "moneda": moneda, "cantidad": cantidad,
            "precio_compra": ppp, "fecha_compra": str(fecha),
            "precio_manual": precio_manual, "activa": True, "notas": notas
        }).execute()
        posicion_id = r.data[0]["id"] if r.data else None

    # Movimiento tipo "carga_inicial" para trazabilidad
    sb.table("movimientos").insert({
        "cartera_id": cartera_id, "posicion_id": posicion_id,
        "tipo": "carga_inicial", "fecha": str(fecha), "ticker": ticker,
        "cantidad": cantidad, "precio": ppp, "moneda": moneda,
        "notas": f"Carga inicial. {notas}".strip()
    }).execute()

    return posicion_id

def registrar_venta(cartera_id, posicion_id, ticker, cantidad_venta, precio_venta, fecha, moneda, notas=""):
    """
    Registra una venta parcial o total.
    Descuenta la cantidad de la posición.
    Calcula y devuelve la ganancia/pérdida realizada.
    Si cantidad llega a 0, cierra la posición.
    """
    sb = get_client()
    r = sb.table("posiciones").select("*").eq("id", posicion_id).single().execute()
    pos = r.data
    if not pos:
        return None

    ppp = pos["precio_compra"] or 0
    cantidad_actual = pos["cantidad"] or 0

    if cantidad_venta > cantidad_actual:
        raise ValueError(f"No podés vender {cantidad_venta} — solo tenés {cantidad_actual}.")

    # Ganancia/pérdida realizada
    costo = ppp * cantidad_venta
    ingreso = precio_venta * cantidad_venta
    ganancia = ingreso - costo
    ganancia_pct = ((precio_venta / ppp) - 1) * 100 if ppp > 0 else 0

    nueva_cantidad = cantidad_actual - cantidad_venta

    if nueva_cantidad <= 0:
        # Cerrar posición
        sb.table("posiciones").update({"cantidad": 0, "activa": False}).eq("id", posicion_id).execute()
    else:
        # PPP no cambia en venta parcial
        sb.table("posiciones").update({"cantidad": nueva_cantidad}).eq("id", posicion_id).execute()

    # Registrar movimiento con ganancia en notas
    nota_venta = f"PPP: ${ppp:,.2f} | G/P realizada: ${ganancia:,.0f} ({ganancia_pct:+.1f}%)"
    if notas:
        nota_venta = f"{notas} | {nota_venta}"

    sb.table("movimientos").insert({
        "cartera_id": cartera_id, "posicion_id": posicion_id,
        "tipo": "venta", "fecha": str(fecha), "ticker": ticker.upper(),
        "cantidad": cantidad_venta, "precio": precio_venta, "moneda": moneda,
        "notas": nota_venta
    }).execute()

    return {"ganancia": ganancia, "ganancia_pct": ganancia_pct, "ppp": ppp}

def registrar_renovacion(posicion_id, precio_nuevo, fecha, notas=""):
    """Actualiza precio manual de una posición (PF, FCI). Registra movimiento."""
    sb = get_client()
    pos = sb.table("posiciones").select("*").eq("id", posicion_id).single().execute().data
    if not pos:
        return

    sb.table("posiciones").update({
        "precio_manual": precio_nuevo
    }).eq("id", posicion_id).execute()

    sb.table("movimientos").insert({
        "cartera_id": pos["cartera_id"], "posicion_id": posicion_id,
        "tipo": "renovacion", "fecha": str(fecha), "ticker": pos["ticker"],
        "cantidad": pos["cantidad"], "precio": precio_nuevo,
        "moneda": pos["moneda"], "notas": notas
    }).execute()

def eliminar_posicion(posicion_id):
    get_client().table("posiciones").update({"activa": False}).eq("id", posicion_id).execute()

def actualizar_posicion(posicion_id, datos):
    get_client().table("posiciones").update(datos).eq("id", posicion_id).execute()

# ---- MOVIMIENTOS ----

def get_movimientos(cartera_id=None, limit=100):
    sb = get_client()
    q = sb.table("movimientos").select("*, carteras(nombre, clientes(nombre))")\
          .order("fecha", desc=True).limit(limit)
    if cartera_id:
        q = q.eq("cartera_id", cartera_id)
    return pd.DataFrame(q.execute().data or [])

def eliminar_movimiento(movimiento_id):
    get_client().table("movimientos").delete().eq("id", movimiento_id).execute()

# ---- RADAR ----

def get_radar():
    r = get_client().table("radar").select("*").order("created_at").execute()
    return [row["ticker"] for row in r.data] if r.data else []

def agregar_radar(ticker, agregado_por=""):
    try:
        get_client().table("radar").insert({"ticker": ticker.upper(), "agregado_por": agregado_por}).execute()
        return True
    except Exception:
        return False

def eliminar_radar(ticker):
    get_client().table("radar").delete().eq("ticker", ticker.upper()).execute()
