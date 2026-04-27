import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime

# 1. Configuración de la App
st.set_page_config(page_title="ShopingDolls Pay", page_icon="💳", layout="wide")

DB_FILE = "inventario_dolls.csv"

# --- FUNCIONES DE BASE DE DATOS ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

# Inicializar estados
if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- 🚀 LÓGICA DE ESCANEO (COBRO POR QR) ---
params = st.query_params
if "item" in params:
    id_buscado = params["item"]
    item_encontrado = st.session_state.inventory[st.session_state.inventory['ID'] == id_buscado]
    
    if not item_encontrado.empty:
        prenda = item_encontrado.iloc[0]
        st.toast(f"✅ DETECTADO: {prenda['Producto']}")
        
        # Guardar en el carrito automáticamente
        st.session_state.carrito.append({
            "Producto": prenda['Producto'],
            "Precio": prenda['Precio'],
            "ID": prenda['ID']
        })
        # Limpiar URL para que no se duplique al refrescar
        st.query_params.clear()
        st.rerun()

# --- DISEÑO DE LA INTERFAZ ---
st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>👑 ShopingDolls Pay</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💰 CAJA (Cobrar)", "➕ AÑADIR ROPA", "📦 INVENTARIO"])

# --- TAB 1: SISTEMA DE COBRO ---
with tab1:
    st.subheader("🛒 Carrito de Venta")
    if st.session_state.carrito:
        df_car = pd.DataFrame(st.session_state.carrito)
        st.table(df_car[["Producto", "Precio"]])
        
        total = df_car["Precio"].sum()
        st.markdown(f"## **TOTAL A PAGAR: ${total}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 FINALIZAR PAGO"):
                # Restar stock
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] = st.session_state.inventory.at[idx, 'Ventas'] + 1
                
                guardar_datos(st.session_state.inventory)
                st.balloons()
                st.success("¡Venta Realizada!")
                st.session_state.carrito = []
                st.rerun()
        with col2:
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
    else:
        st.info("Escanea un código QR de una prenda para que aparezca aquí.")

# --- TAB 2: AÑADIR ROPA Y GENERAR QR ---
with tab2:
    st.subheader("✨ Registro Rápido")
    with st.form("registro_rapido", clear_on_submit=True):
        col_n, col_p, col_s = st.columns([3,1,1])
        with col_n: nombre = st.text_input("Nombre de la prenda (Ej: Vestido Gala)")
        with col_p: precio = st.number_input("Precio $", min_value=0.0)
        with col_s: stock = st.number_input("Stock", min_value=1, value=10)
        
        enviar = st.form_submit_button("GUARDAR Y GENERAR QR")
        
        if enviar and nombre:
            nuevo_id = f"SD-{datetime.now().strftime('%M%S')}"
            nueva_fila = pd.DataFrame([{
                "ID": nuevo_id, "Producto": nombre, "Precio": precio, "Stock": stock, "Ventas": 0
            }])
            
            st.session_state.inventory = pd.concat([st.session_state.inventory, nueva_fila], ignore_index=True)
            guardar_datos(st.session_state.inventory)
            
            st.success(f"¡{nombre} registrado con éxito!")
            
            # --- MOSTRAR QR INMEDIATAMENTE ---
            url_app = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"
            link_final = f"{url_app}/?item={nuevo_id}"
            
            qr_img = qrcode.make(link_final)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            
            st.image(buf.getvalue(), width=300, caption=f"QR para {nombre} (ID: {nuevo_id})")
            st.download_button("📥 DESCARGAR ETIQUETA QR", buf.getvalue(), f"QR_{nombre}.png")

# --- TAB 3: INVENTARIO ---
with tab3:
    st.subheader("📦 Stock Actual")
    st.dataframe(st.session_state.inventory, use_container_width=True)
    
    if st.button("🗑️ Borrar Todo el Inventario (Cuidado)"):
        st.session_state.inventory = pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])
        guardar_datos(st.session_state.inventory)
        st.rerun()
