"""
Orden.ar · Capa de acceso a datos (Supabase)
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

def get_cliente(cliente_id):
    sb = get_client()
    r = sb.table("clientes").select("*").eq("id", cliente_id).single().execute()
    return r.data

def crear_cliente(nombre, tipo, desde, notas=""):
    sb = get_client()
    r = sb.table("clientes").insert({
        "nombre": nombre, "tipo": tipo,
        "desde": str(desde), "notas": notas
    }).execute()
    return r.data

def actualizar_cliente(cliente_id, datos):
    sb = get_client()
    sb.table("clientes").update(datos).eq("id", cliente_id).execute()

def eliminar_cliente(cliente_id):
    sb = get_client()
    # Soft delete — marca como inactivo
    sb.table("clientes").update({"activo": False}).eq("id", cliente_id).execute()

# ---- CARTERAS ----

def get_carteras(cliente_id=None):
    sb = get_client()
    q = sb.table("carteras").select("*, clientes(nombre, tipo)").eq("activa", True)
    if cliente_id:
        q = q.eq("cliente_id", cliente_id)
    r = q.execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_cartera(cartera_id):
    sb = get_client()
    r = sb.table("carteras").select("*, clientes(nombre, tipo)").eq("id", cartera_id).single().execute()
    return r.data

def crear_cartera(cliente_id, nombre, moneda_base):
    sb = get_client()
    r = sb.table("carteras").insert({
        "cliente_id": cliente_id, "nombre": nombre, "moneda_base": moneda_base
    }).execute()
    return r.data

def eliminar_cartera(cartera_id):
    sb = get_client()
    sb.table("carteras").update({"activa": False}).eq("id", cartera_id).execute()

# ---- PERFIL DE RIESGO ----

def get_perfil(cartera_id):
    sb = get_client()
    r = sb.table("perfil_riesgo").select("*").eq("cartera_id", cartera_id)\
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
    r = q.execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def crear_posicion(cartera_id, ticker, nombre, tipo, moneda, cantidad, precio_compra, fecha_compra, precio_manual=None, notas=""):
    sb = get_client()
    r = sb.table("posiciones").insert({
        "cartera_id": cartera_id, "ticker": ticker, "nombre": nombre,
        "tipo": tipo, "moneda": moneda, "cantidad": cantidad,
        "precio_compra": precio_compra, "fecha_compra": str(fecha_compra),
        "precio_manual": precio_manual, "notas": notas
    }).execute()
    return r.data

def actualizar_posicion(posicion_id, datos):
    sb = get_client()
    sb.table("posiciones").update(datos).eq("id", posicion_id).execute()

def eliminar_posicion(posicion_id):
    sb = get_client()
    sb.table("posiciones").update({"activa": False}).eq("id", posicion_id).execute()

# ---- MOVIMIENTOS ----

def get_movimientos(cartera_id=None, limit=100):
    sb = get_client()
    q = sb.table("movimientos").select("*, carteras(nombre, clientes(nombre))")\
          .order("fecha", desc=True).limit(limit)
    if cartera_id:
        q = q.eq("cartera_id", cartera_id)
    r = q.execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def registrar_movimiento(cartera_id, tipo, fecha, ticker, cantidad, precio, moneda, posicion_id=None, notas=""):
    sb = get_client()
    r = sb.table("movimientos").insert({
        "cartera_id": cartera_id, "posicion_id": posicion_id,
        "tipo": tipo, "fecha": str(fecha), "ticker": ticker,
        "cantidad": cantidad, "precio": precio, "moneda": moneda, "notas": notas
    }).execute()
    return r.data

def eliminar_movimiento(movimiento_id):
    sb = get_client()
    sb.table("movimientos").delete().eq("id", movimiento_id).execute()

# ---- RADAR ----

def get_radar():
    sb = get_client()
    r = sb.table("radar").select("*").order("created_at").execute()
    return [row["ticker"] for row in r.data] if r.data else []

def agregar_radar(ticker, agregado_por=""):
    sb = get_client()
    try:
        sb.table("radar").insert({"ticker": ticker.upper(), "agregado_por": agregado_por}).execute()
        return True
    except Exception:
        return False

def eliminar_radar(ticker):
    sb = get_client()
    sb.table("radar").delete().eq("ticker", ticker.upper()).execute()
