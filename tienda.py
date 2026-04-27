import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime

# 1. Configuración de la App
st.set_page_config(page_title="ShopingDolls POS", page_icon="💳", layout="wide")

DB_FILE = "inventario_dolls.csv"

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- 🚀 LÓGICA DE ESCANEO (MÓVIL O CÁMARA) ---
params = st.query_params
if "item" in params:
    id_buscado = params["item"]
    item_encontrado = st.session_state.inventory[st.session_state.inventory['ID'] == id_buscado]
    if not item_encontrado.empty:
        prenda = item_encontrado.iloc[0]
        st.session_state.carrito.append({"Producto": prenda['Producto'], "Precio": prenda['Precio'], "ID": prenda['ID']})
        st.query_params.clear()
        st.rerun()

st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>👑 ShopingDolls Pay</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💰 CAJA (Lector de Barras/QR)", "➕ AÑADIR ROPA", "📦 INVENTARIO"])

# --- TAB 1: CAJA CON SOPORTE PARA LECTOR FÍSICO ---
with tab1:
    col_caja, col_resumen = st.columns([1, 1])
    
    with col_caja:
        st.subheader("🛒 Escaneo de Productos")
        # --- ESTE ES EL CAMPO PARA LA PISTOLA LÁSER ---
        barcode_input = st.text_input("Haz clic aquí y dispara el Lector:", key="barcode_scan", placeholder="Esperando escaneo...")
        
        if barcode_input:
            # Buscamos el ID que acaba de escribir el lector
            item_match = st.session_state.inventory[st.session_state.inventory['ID'] == barcode_input]
            if not item_match.empty:
                p = item_match.iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.success(f"Añadido: {p['Producto']}")
                # Limpiamos el campo para el siguiente escaneo
                st.rerun()
            else:
                st.error("Código no encontrado")

    with col_resumen:
        st.subheader("📋 Resumen de Venta")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[["Producto", "Precio"]])
            total = df_car["Precio"].sum()
            st.markdown(f"## **TOTAL: ${total}**")
            
            if st.button("🚀 FINALIZAR VENTA"):
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] += 1
                guardar_datos(st.session_state.inventory)
                st.balloons()
                st.session_state.carrito = []
                st.rerun()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()

# --- TAB 2: AÑADIR ROPA (Generador de ID para Lector) ---
with tab2:
    st.subheader("✨ Registro de Nueva Prenda")
    with st.form("registro_rapido", clear_on_submit=True):
        nombre = st.text_input("Nombre")
        precio = st.number_input("Precio $", min_value=0.0)
        stock = st.number_input("Stock", min_value=1, value=1)
        # El ID será lo que el lector lea (puedes usar números cortos para que sea más fácil)
        enviar = st.form_submit_button("GUARDAR Y GENERAR CÓDIGO")
        
        if enviar and nombre:
            # Generamos un ID numérico simple (más fácil para lectores de barras)
            nuevo_id = datetime.now().strftime("%H%M%S") 
            nueva_fila = pd.DataFrame([{"ID": nuevo_id, "Producto": nombre, "Precio": precio, "Stock": stock, "Ventas": 0}])
            st.session_state.inventory = pd.concat([st.session_state.inventory, nueva_fila], ignore_index=True)
            guardar_datos(st.session_state.inventory)
            
            st.success(f"Registrado con ID: {nuevo_id}")
            
            # Generamos QR (que también lo lee la pistola si es 2D)
            url_app = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"
            qr_img = qrcode.make(f"{url_app}/?item={nuevo_id}")
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf.getvalue(), width=200, caption="Etiqueta para la prenda")

with tab3:
    st.subheader("📦 Stock")
    st.dataframe(st.session_state.inventory, use_container_width=True)
