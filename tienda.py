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

def generar_qr(id_prenda):
    # Enlace corregido sin la barra final
    url_base = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app" 
    
    # Esto genera el enlace directo a la prenda
    enlace_final = f"{url_base}/?item={id_prenda}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(enlace_final)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()

# --- 🚀 MODO ESCÁNER QR ---
params = st.query_params
if "item" in params:
    id_buscado = params["item"]
    df_filtro = st.session_state.inventory[st.session_state.inventory['ID'] == id_buscado]
    
    if not df_filtro.empty:
        st.warning("📱 **MODO ESCÁNER QR ACTIVADO**")
        prenda = df_filtro.iloc[0]
        st.subheader(f"✨ Detalles de: {prenda['Producto']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID:** `{prenda['ID']}`")
            st.write(f"**Categoría:** {prenda['Categoría']}")
            st.write(f"**Talla:** {prenda['Talla']}")
        with col2:
            st.write(f"**Stock actual:** {prenda['Stock']} unidades")
            st.write(f"**Precio:** ${prenda['Precio']}")
            st.write(f"**Ventas Totales:** {prenda['Ventas_Total']}")
            
        foto_p = os.path.join(FOTOS_DIR, f"{prenda['ID']}.png")
        if os.path.exists(foto_p):
            st.image(foto_p, width=300)
        
        st.divider()
        if st.button("⬅️ Volver a la Tienda Completa"):
            st.query_params.clear()
            st.rerun()
            
        st.stop() 
    else:
        st.error("❌ Prenda no encontrada.")
        if st.button("Volver"):
            st.query_params.clear()
            st.rerun()
        st.stop()

# --- DISEÑO ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .main-header { font-size: 2.2rem; color: #1e1e1e; font-weight: 800; }
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
                # Generamos un ID único basado en el total + 101
                nuevo_id = f"SD-{len(st.session_state.inventory) + 101}"
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                
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
    busc = st.text_input("🔍 Buscar Prenda...")
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

# --- TAB 2: ESTADÍSTICAS ---
with tabs[1]:
    if not df.empty:
        c1, c2 = st.columns(2)
        fig_cat = px.pie(df, values='Stock', names='Categoría', title="Distribución de Stock")
        c1.plotly_chart(fig_cat, use_container_width=True)
        fig_ventas = px.bar(df, x='Producto', y='Ventas_Total', title="Ventas por Producto")
        c2.plotly_chart(fig_ventas, use_container_width=True)

# --- TAB 3: GESTIÓN Y QR ---
with tabs[2]:
    if not df.empty:
        col_m, col_q = st.columns([2, 1])
        with col_m:
            sel = st.selectbox("Seleccionar para gestionar:", df['Producto'].unique())
            idx = df[df['Producto'] == sel].index[0]
            item_sel = df.loc[idx]
            
            st.write(f"**ID:** `{item_sel['ID']}`")
            
            if st.button("💰 REGISTRAR VENTA (-1)"):
                if st.session_state.inventory.at[idx, 'Stock'] > 0:
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas_Total'] += 1
                    guardar_datos(st.session_state.inventory)
                    st.success("¡Venta registrada!")
                    st.rerun()
            
            if st.button("🔥 Eliminar"):
                st.session_state.inventory = st.session_state.inventory.drop(idx)
                guardar_datos(st.session_state.inventory)
                st.rerun()

        with col_q:
            qr_gen = generar_qr(item_sel['ID'])
            st.image(qr_gen, width=200, caption="Escanea para ir al producto")
            st.download_button("📥 Bajar QR", qr_gen, f"QR_{item_sel['ID']}.png")
