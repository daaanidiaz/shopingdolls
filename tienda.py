import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime
import plotly.express as px

# 1. Configuración de la App
st.set_page_config(page_title="ShopingDolls Empire", page_icon="👑", layout="wide")

DB_FILE = "inventario_dolls.csv"
FOTOS_DIR = "fotos"

if not os.path.exists(FOTOS_DIR):
    os.makedirs(FOTOS_DIR)

# Funciones de Datos
def cargar_datos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if "Fecha_Ingreso" not in df.columns: df["Fecha_Ingreso"] = datetime.now().strftime("%Y-%m-%d")
        if "Ventas_Total" not in df.columns: df["Ventas_Total"] = 0
        return df
    return pd.DataFrame(columns=["ID", "Producto", "Categoría", "Talla", "Stock", "Precio", "Fecha_Ingreso", "Ventas_Total"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

def generar_qr(texto):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()

# --- DISEÑO ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .main-header { font-size: 2.2rem; color: #1e1e1e; font-weight: 800; }
    .metric-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-header">👑 ShopingDolls: Empire Edition</p>', unsafe_allow_html=True)

# --- PANEL LATERAL ---
with st.sidebar:
    st.header("🛒 Nueva Entrada")
    with st.form("registro_pro", clear_on_submit=True):
        nombre = st.text_input("Nombre")
        cat = st.selectbox("Categoría", ["Vestidos", "Tops", "Pantalones", "Abrigos", "Accesorios"])
        talla = st.select_slider("Talla", ["XS", "S", "M", "L", "XL"])
        stock = st.number_input("Stock", min_value=0)
        precio = st.number_input("Precio ($)", min_value=0.0)
        foto = st.file_uploader("Subir Foto", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("Registrar en el Imperio"):
            if nombre:
                nuevo_id = f"SD-{len(st.session_state.inventory) + 101}"
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                
                # Guardar foto si existe
                if foto:
                    foto_path = os.path.join(FOTOS_DIR, f"{nuevo_id}.png")
                    with open(foto_path, "wb") as f:
                        f.write(foto.getbuffer())
                
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id, "Producto": nombre, "Categoría": cat, 
                    "Talla": talla, "Stock": stock, "Precio": precio,
                    "Fecha_Ingreso": fecha_hoy, "Ventas_Total": 0
                }])
                st.session_state.inventory = pd.concat([st.session_state.inventory, nueva_fila], ignore_index=True)
                guardar_datos(st.session_state.inventory)
                st.success("¡Prenda Registrada!")
                st.rerun()

# --- CUADRO DE MANDO ---
df = st.session_state.inventory
tabs = st.tabs(["📦 Inventario", "📊 Estadísticas", "🏷️ Etiquetas y Gestión"])

# --- TAB 1: INVENTARIO VISUAL ---
with tabs[0]:
    col_busc, col_alert = st.columns([2, 1])
    with col_busc:
        busc = st.text_input("🔍 Buscar Prenda...")
    
    # Lógica de Alertas (Paso 3: Prendas Olvidadas)
    hoy = datetime.now()
    df_alertas = df.copy()
    df_alertas['Dias'] = (hoy - pd.to_datetime(df_alertas['Fecha_Ingreso'])).dt.days
    prendas_viejas = df_alertas[df_alertas['Dias'] > 30]
    
    if not prendas_viejas.empty:
        st.warning(f"⚠️ Tienes {len(prendas_viejas)} prendas que llevan más de 30 días sin venderse. ¡Considera una rebaja!")

    # Galería de fotos (Paso 1)
    df_v = df[df['Producto'].str.contains(busc, case=False)] if busc else df
    
    for i in range(0, len(df_v), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(df_v):
                item = df_v.iloc[i+j]
                with cols[j]:
                    foto_p = os.path.join(FOTOS_DIR, f"{item['ID']}.png")
                    if os.path.exists(foto_p):
                        st.image(foto_p, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150?text=Sin+Foto", use_container_width=True)
                    st.write(f"**{item['Producto']}**")
                    st.write(f"Stock: {item['Stock']} | ${item['Precio']}")

# --- TAB 2: ANALYTICS (Paso 2) ---
with tabs[1]:
    st.subheader("📈 Rendimiento de tu Boutique")
    if not df.empty:
        c1, c2 = st.columns(2)
        
        # Gráfica de Stock por Categoría
        fig_cat = px.pie(df, values='Stock', names='Categoría', title="Distribución de Stock", hole=0.4)
        c1.plotly_chart(fig_cat, use_container_width=True)
        
        # Gráfica de Ventas
        fig_ventas = px.bar(df, x='Producto', y='Ventas_Total', title="Ventas por Producto", color='Categoría')
        c2.plotly_chart(fig_ventas, use_container_width=True)
    else:
        st.info("Añade datos para ver gráficas.")

# --- TAB 3: GESTIÓN Y QR ---
with tabs[2]:
    if not df.empty:
        col_m, col_q = st.columns([2, 1])
        with col_m:
            sel = st.selectbox("Seleccionar para vender/editar:", df['Producto'].unique())
            idx = df[df['Producto'] == sel].index[0]
            item_sel = df.loc[idx]
            
            st.write(f"**ID Unico:** `{item_sel['ID']}`")
            st.write(f"**Ventas acumuladas:** {item_sel['Ventas_Total']} unidades")
            
            if st.button("💰 REGISTRAR VENTA (-1 unidad)"):
                if st.session_state.inventory.at[idx, 'Stock'] > 0:
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas_Total'] += 1
                    guardar_datos(st.session_state.inventory)
                    st.success("¡Venta registrada!")
                    st.rerun()
            
            if st.button("🔥 Eliminar del Sistema"):
                st.session_state.inventory = st.session_state.inventory.drop(idx)
                guardar_datos(st.session_state.inventory)
                st.rerun()

        with col_q:
            qr_gen = generar_qr(f"ShopingDolls ID: {item_sel['ID']}")
            st.image(qr_gen, width=180)
            st.download_button("📥 Bajar QR", qr_gen, f"QR_{item_sel['ID']}.png")
