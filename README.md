# Orden.ar · App de Gestión de Carteras

Streamlit + Supabase + yfinance

## Setup en 5 pasos

### 1. Clonar el repo
```bash
git clone https://github.com/tu-usuario/ordenar-carteras
cd ordenar-carteras
```

### 2. Crear base de datos en Supabase
1. Ir a [supabase.com](https://supabase.com) → tu proyecto → **SQL Editor**
2. Pegar el contenido de `supabase_schema.sql` y ejecutar
3. Copiar la **URL** y la **anon key** desde Settings → API

### 3. Configurar secrets
Editar `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "tu-anon-key"
```

### 4. Instalar dependencias y correr local
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 5. Deploy en Streamlit Cloud
1. Subir el repo a GitHub
2. Ir a [share.streamlit.io](https://share.streamlit.io)
3. Conectar el repo → seleccionar `app.py`
4. En **Secrets**, pegar el contenido de `.streamlit/secrets.toml`
5. Deploy

---

## Estructura del proyecto

```
ordenar-carteras/
├── app.py                  # App principal (páginas)
├── db.py                   # Acceso a Supabase
├── market.py               # yfinance + ArgentinaDatos
├── ui.py                   # Componentes visuales
├── supabase_schema.sql     # Schema de base de datos
├── requirements.txt
└── .streamlit/
    ├── config.toml         # Tema y colores
    └── secrets.toml        # Credenciales (NO subir a GitHub)
```

## Tickers — formato yfinance
| Instrumento | Formato | Ejemplo |
|---|---|---|
| Acciones BYMA | `TICKER.BA` | `GGAL.BA`, `YPF.BA` |
| CEDEARs / internacionales | Sin sufijo | `AAPL`, `MSFT`, `TSLA` |
| Bonos BYMA | `TICKER.BA` | `AL30.BA`, `GD30.BA` |
| FCI / Plazo Fijo | Sin ticker yfinance | Carga manual de precio |

## Próximo paso: Login
Cuando estén listos, el login se agrega con **Supabase Auth** — una semana de trabajo adicional.

---
*Orden.ar · El punto de partida para decidir con claridad*
