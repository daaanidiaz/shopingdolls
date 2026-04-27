import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# 1. Configuración de la App
st.set_page_config(page_title="ShopingDolls POS", page_icon="💳", layout="wide")

DB_FILE = "inventario_dolls.csv"
URL_APP = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"

# --- FUNCIONES DE BASE DE DATOS ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        return df
    return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

# --- FUNCIÓN PARA GENERAR EL TICKET (PDF) ---
def generar_ticket(carrito, total):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado del Imperio
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "SHOPINGDOLLS EMPIRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.cell(0, 5, "--------------------------------------------------------", ln=True, align='C')
    
    # Detalle de productos
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Producto", border=0)
    pdf.cell(0, 10, "Precio", border=0, ln=True)
    pdf.set_font("Arial", '', 12)
    
    for item in carrito:
        pdf.cell(100, 10, f"{item['Producto']}")
        pdf.cell(0, 10, f"${item['Precio']}", ln=True)
    
    # Total
    pdf.cell(0, 10, "--------------------------------------------------------", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(100, 10, "TOTAL A PAGAR:")
    pdf.cell(0, 10, f"${total}", ln=True)
    
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 20, "Gracias por tu compra en el Imperio.", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# Inicializar estados
if 'inventory' not in st.session_state:
    st.session_state.inventory = cargar_datos()
if 'carrito' not in st.session_state:
    st.session_state.carrito = []
if 'ticket_listo' not in st.session_state:
    st.session_state.ticket_listo = None

# --- LÓGICA QR ---
params = st.query_params
if "item" in params:
    id_buscado = str(params["item"])
    item_encontrado = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == id_buscado]
    if not item_encontrado.empty:
        p = item_encontrado.iloc[0]
        st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
        st.query_params.clear()
        st.rerun()

st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>👑 ShopingDolls Pay</h1>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["💰 CAJA", "➕ REGISTRAR", "📦 INVENTARIO"])

# --- TAB 1: CAJA Y TICKET ---
with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🛒 Escaneo")
        barcode = st.text_input("Lector de Barras:", key="main_scan")
        if barcode:
            match = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == str(barcode)]
            if not match.empty:
                p = match.iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.rerun()

    with c2:
        st.subheader("📋 Resumen")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[["Producto", "Precio"]])
            total_venta = df_car["Precio"].sum()
            st.markdown(f"### TOTAL: ${total_venta}")
            
            if st.button("🚀 FINALIZAR PAGO"):
                # Generar ticket antes de limpiar carrito
                st.session_state.ticket_listo = generar_ticket(st.session_state.carrito, total_venta)
                
                # Restar Stock
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] += 1
                
                guardar_datos(st.session_state.inventory)
                st.session_state.carrito = [] # Limpiamos para la siguiente venta
                st.balloons()

        if st.session_state.ticket_listo:
            st.success("✅ ¡Venta completada!")
            st.download_button(
                label="📥 DESCARGAR TICKET (PDF)",
                data=st.session_state.ticket_listo,
                file_name=f"ticket_{datetime.now().strftime('%H%M%S')}.pdf",
                mime="application/pdf"
            )
            if st.button("Nueva Venta"):
                st.session_state.ticket_listo = None
                st.rerun()

# --- TAB 2: REGISTRO ---
with t2:
    with st.form("new_item"):
        n = st.text_input("Nombre")
        p = st.number_input("Precio", min_value=0.0)
        s = st.number_input("Stock", min_value=1)
        if st.form_submit_button("Guardar"):
            new_id = datetime.now().strftime("%H%M%S")
            new_row = pd.DataFrame([{"ID": new_id, "Producto": n, "Precio": p, "Stock": s, "Ventas": 0}])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
            guardar_datos(st.session_state.inventory)
            st.rerun()

# --- TAB 3: INVENTARIO Y QRs ---
with t3:
    st.data_editor(st.session_state.inventory, use_container_width=True)
    if not st.session_state.inventory.empty:
        sel = st.selectbox("QR de:", st.session_state.inventory['Producto'])
        row = st.session_state.inventory[st.session_state.inventory['Producto'] == sel].iloc[0]
        qr = qrcode.make(f"{URL_APP}/?item={row['ID']}")
        b = BytesIO()
        qr.save(b, format="PNG")
        st.image(b.getvalue(), width=150)
