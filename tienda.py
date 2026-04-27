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
        df = pd.read_csv(DB_FILE)
        # Asegurar que las columnas existen
        for col in ["ID", "Producto", "Precio", "Stock", "Ventas"]:
            if col not in df.columns: df[col] = 0
        return df
    return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

URL_APP = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"

# --- 🚀 LÓGICA DE ESCANEO QR ---
params = st.query_params
if "item" in params:
    id_buscado = params["item"]
    item_encontrado = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == str(id_buscado)]
    if not item_encontrado.empty:
        p = item_encontrado.iloc[0]
        st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
        st.query_params.clear()
        st.rerun()

st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>👑 ShopingDolls Pay</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💰 CAJA (Vender)", "➕ AÑADIR NUEVA ROPA", "📦 INVENTARIO Y QRs"])

# --- TAB 1: CAJA (AUTOMÁTICA Y MANUAL) ---
with tab1:
    col_caja, col_resumen = st.columns([1, 1])
    with col_caja:
        st.subheader("🛒 Escaneo / Entrada Manual")
        # Entrada para Lector de Barras
        barcode_input = st.text_input("Haz clic aquí para Lector de Barras:", key="barcode_scan")
        if barcode_input:
            item_match = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == str(barcode_input)]
            if not item_match.empty:
                p = item_match.iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.rerun()
            else:
                st.error("Código no encontrado")
        
        st.write("---")
        # Selección Manual por nombre
        st.write("O selecciona manualmente:")
        opciones_manual = ["Selecciona prenda..."] + st.session_state.inventory['Producto'].tolist()
        seleccion_manual = st.selectbox("Buscar prenda por nombre:", opciones_manual)
        if seleccion_manual != "Selecciona prenda...":
            if st.button("➕ Añadir al Carrito"):
                p = st.session_state.inventory[st.session_state.inventory['Producto'] == seleccion_manual].iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.success(f"{p['Producto']} añadido!")
                st.rerun()

    with col_resumen:
        st.subheader("📋 Resumen de Venta")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[["Producto", "Precio"]])
            total = df_car["Precio"].sum()
            st.markdown(f"## **TOTAL: ${total}**")
            
            if st.button("🚀 FINALIZAR PAGO"):
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
        else:
            st.info("El carrito está vacío.")

# --- TAB 2: AÑADIR ROPA ---
with tab2:
    st.subheader("✨ Registro Rápido")
    with st.form("registro", clear_on_submit=True):
        nombre = st.text_input("Nombre de la prenda")
        precio = st.number_input("Precio $", min_value=0.0, step=0.5)
        stock = st.number_input("Stock Inicial", min_value=1, value=1)
        if st.form_submit_button("GUARDAR EN EL IMPERIO"):
            if nombre:
                nuevo_id = datetime.now().strftime("%H%M%S")
                nueva_fila = pd.DataFrame([{"ID": nuevo_id, "Producto": nombre, "Precio": precio, "Stock": stock, "Ventas": 0}])
                st.session_state.inventory = pd.concat([st.session_state.inventory, nueva_fila], ignore_index=True)
                guardar_datos(st.session_state.inventory)
                st.success(f"¡{nombre} guardado! ID: {nuevo_id}")
                st.rerun()

# --- TAB 3: INVENTARIO / EDICIÓN MANUAL / QRs ---
with tab3:
    st.subheader("📦 Gestión de Inventario")
    
    # Editor Manual Directo
    st.write("💡 Puedes cambiar el precio o stock directamente en la tabla y luego darle a 'Guardar Cambios'.")
    df_editable = st.data_editor(st.session_state.inventory, use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Guardar Cambios Manuales"):
        st.session_state.inventory = df_editable
        guardar_datos(df_editable)
        st.success("Inventario actualizado manualmente.")
        st.rerun()

    st.write("---")
    st.subheader("🏷️ Recuperar Código QR")
    if not st.session_state.inventory.empty:
        prod_qr = st.selectbox("Elige prenda para ver su QR:", st.session_state.inventory['Producto'].unique())
        if prod_qr:
            p_data = st.session_state.inventory[st.session_state.inventory['Producto'] == prod_qr].iloc[0]
            link = f"{URL_APP}/?item={p_data['ID']}"
            qr_img = qrcode.make(link)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf.getvalue(), width=180)
            st.download_button("📥 Descargar QR", buf.getvalue(), f"QR_{prod_qr}.png")
