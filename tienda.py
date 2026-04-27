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

# URL base para los enlaces QR
URL_APP = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"

# --- 🚀 LÓGICA DE ESCANEO ---
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

tab1, tab2, tab3 = st.tabs(["💰 CAJA (Vender)", "➕ AÑADIR ROPA", "📦 INVENTARIO Y QRs"])

# --- TAB 1: CAJA ---
with tab1:
    col_caja, col_resumen = st.columns([1, 1])
    with col_caja:
        st.subheader("🛒 Escaneo de Productos")
        barcode_input = st.text_input("Haz clic aquí y dispara el Lector:", key="barcode_scan")
        if barcode_input:
            item_match = st.session_state.inventory[st.session_state.inventory['ID'] == barcode_input]
            if not item_match.empty:
                p = item_match.iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.rerun()
            else:
                st.error("Código no encontrado")

    with col_resumen:
        st.subheader("📋 Resumen")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[["Producto", "Precio"]])
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

# --- TAB 2: AÑADIR ROPA ---
with tab2:
    st.subheader("✨ Nueva Prenda")
    with st.form("registro_rapido", clear_on_submit=True):
        nombre = st.text_input("Nombre")
        precio = st.number_input("Precio $", min_value=0.0)
        stock = st.number_input("Stock", min_value=1, value=1)
        if st.form_submit_button("GUARDAR"):
            if nombre:
                nuevo_id = datetime.now().strftime("%H%M%S") 
                nueva_fila = pd.DataFrame([{"ID": nuevo_id, "Producto": nombre, "Precio": precio, "Stock": stock, "Ventas": 0}])
                st.session_state.inventory = pd.concat([st.session_state.inventory, nueva_fila], ignore_index=True)
                guardar_datos(st.session_state.inventory)
                st.success(f"Registrado con ID: {nuevo_id}")
                st.rerun()

# --- TAB 3: INVENTARIO Y RECUPERAR QRs ---
with tab3:
    st.subheader("📦 Gestión de Stock y Etiquetas")
    
    if not st.session_state.inventory.empty:
        col_list, col_qr = st.columns([2, 1])
        
        with col_list:
            st.write("Selecciona una prenda para ver su QR:")
            # Buscador para no tener que bajar por toda la lista
            search = st.text_input("🔍 Buscar por nombre...")
            df_display = st.session_state.inventory
            if search:
                df_display = df_display[df_display['Producto'].str.contains(search, case=False)]
            
            # Selector de producto
            opciones = df_display['Producto'].tolist()
            seleccionado = st.selectbox("Prendas encontradas:", opciones)
            
            st.dataframe(df_display, use_container_width=True)

        with col_qr:
            if seleccionado:
                # Obtenemos los datos de la prenda seleccionada
                datos_prenda = st.session_state.inventory[st.session_state.inventory['Producto'] == seleccionado].iloc[0]
                id_p = datos_prenda['ID']
                
                st.markdown(f"### 🏷️ Etiqueta QR\n**{seleccionado}**")
                
                # Generamos el QR de nuevo al vuelo
                link_qr = f"{URL_APP}/?item={id_p}"
                img_qr = qrcode.make(link_qr)
                buf = BytesIO()
                img_qr.save(buf, format="PNG")
                
                st.image(buf.getvalue(), width=200)
                st.code(f"ID: {id_p}")
                st.download_button("📥 Descargar QR", buf.getvalue(), f"QR_{seleccionado}.png")

    else:
        st.info("No hay productos registrados.")
