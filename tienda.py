import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime

# 1. Configuración Estética
st.set_page_config(page_title="ShopingDolls Pay", page_icon="💳", layout="centered")

DB_FILE = "inventario_dolls.csv"

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Producto", "Categoría", "Talla", "Stock", "Precio", "Fecha_Ingreso", "Ventas_Total"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- LÓGICA DE ESCANEO (LECTOR QR) ---
params = st.query_params
if "item" in params:
    id_buscado = params["item"]
    df = st.session_state.inventory
    item_encontrado = df[df['ID'] == id_buscado]

    if not item_encontrado.empty:
        prenda = item_encontrado.iloc[0]
        st.success(f"✅ ¡Producto detectado: {prenda['Producto']}!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Precio", f"${prenda['Precio']}")
        with col2:
            if st.button("➕ Añadir al Carrito"):
                st.session_state.carrito.append({
                    "ID": prenda['ID'],
                    "Producto": prenda['Producto'],
                    "Precio": prenda['Precio']
                })
                st.query_params.clear() # Limpiamos el link para poder seguir comprando
                st.rerun()
    else:
        st.error("Producto no encontrado.")

# --- INTERFAZ DE CAJA ---
st.markdown("<h1 style='text-align: center; color: #E91E63;'>🛍️ ShopingDolls Pay</h1>", unsafe_allow_html=True)
st.write("---")

# Muestra el carrito actual
if st.session_state.carrito:
    st.subheader("🛒 Tu Carrito")
    df_carrito = pd.DataFrame(st.session_state.carrito)
    st.table(df_carrito[['Producto', 'Precio']])
    
    total = sum(item['Precio'] for item in st.session_state.carrito)
    st.markdown(f"### 💰 TOTAL A PAGAR: `${total}`")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("❌ Vaciar Carrito"):
            st.session_state.carrito = []
            st.rerun()
    with col_b:
        if st.button("🚀 FINALIZAR Y PAGAR"):
            # Aquí restamos el stock de la base de datos
            for item in st.session_state.carrito:
                idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                if st.session_state.inventory.at[idx, 'Stock'] > 0:
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas_Total'] += 1
            
            guardar_datos(st.session_state.inventory)
            st.balloons()
            st.success("¡Pago procesado con éxito! Gracias por tu compra.")
            st.session_state.carrito = []
            # st.rerun() # Opcional: reiniciar tras pagar

else:
    st.info("👋 ¡Bienvenida! Escanea un código QR de una prenda para empezar a cobrar.")

# --- SECCIÓN DE ADMINISTRACIÓN (PARA GENERAR QR) ---
with st.expander("⚙️ Panel de Control (Generar QRs y Stock)"):
    st.subheader("Generar Etiquetas para la ropa")
    df_admin = st.session_state.inventory
    if not df_admin.empty:
        sel = st.selectbox("Selecciona prenda para imprimir QR:", df_admin['Producto'].unique())
        item_sel = df_admin[df_admin['Producto'] == sel].iloc[0]
        
        # Generador de QR corregido con tu link
        url_base = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"
        enlace_qr = f"{url_base}/?item={item_sel['ID']}"
        
        qr = qrcode.make(enlace_qr)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf.getvalue(), width=200)
        st.write(f"ID: {item_sel['ID']}")
    else:
        st.write("Aún no tienes productos en el inventario.")

    if st.button("📊 Ver Inventario Completo"):
        st.dataframe(st.session_state.inventory)
