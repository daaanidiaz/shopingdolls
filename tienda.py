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
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

# --- FUNCIÓN TICKET PDF ---
def generar_ticket(carrito, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "SHOPINGDOLLS EMPIRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.cell(0, 5, "-"*50, ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Producto")
    pdf.cell(0, 10, "Precio", ln=True)
    pdf.set_font("Arial", '', 12)
    for item in carrito:
        pdf.cell(100, 10, f"{item['Producto']}")
        pdf.cell(0, 10, f"${item['Precio']}", ln=True)
    
    pdf.cell(0, 10, "-"*50, ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(100, 10, "TOTAL:")
    pdf.cell(0, 10, f"${total}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# Inicializar estados
if 'inventory' not in st.session_state: st.session_state.inventory = cargar_datos()
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ticket_listo' not in st.session_state: st.session_state.ticket_listo = None

# --- LÓGICA QR (ENTRADA DESDE MÓVIL) ---
params = st.query_params
if "item" in params:
    id_buscado = str(params["item"])
    match = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == id_buscado]
    if not match.empty:
        p = match.iloc[0]
        st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
        st.query_params.clear()
        st.rerun()

st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>👑 ShopingDolls Pay</h1>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["💰 CAJA (Vender)", "➕ REGISTRAR ROPA", "📦 INVENTARIO"])

# --- TAB 1: CAJA (AQUÍ ESTÁ EL MODO MANUAL) ---
with t1:
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("🔍 Añadir Productos")
        
        # 1. MODO LECTOR DE BARRAS
        barcode = st.text_input("Lector de Barras / QR (clic aquí):", key="scan")
        if barcode:
            match = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == str(barcode)]
            if not match.empty:
                p = match.iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.rerun()
            else: st.error("Código no encontrado")
        
        st.divider()
        
        # 2. MODO MANUAL (BUSCADOR)
        st.write("✨ **Selección Manual:**")
        lista_nombres = ["Buscar prenda..."] + st.session_state.inventory['Producto'].tolist()
        seleccion = st.selectbox("Escribe o busca el nombre:", lista_nombres)
        if seleccion != "Buscar prenda...":
            if st.button("➕ Añadir Manualmente"):
                p = st.session_state.inventory[st.session_state.inventory['Producto'] == seleccion].iloc[0]
                st.session_state.carrito.append({"Producto": p['Producto'], "Precio": p['Precio'], "ID": p['ID']})
                st.toast(f"{p['Producto']} añadido!")
                st.rerun()

    with col_der:
        st.subheader("📋 Tu Carrito")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[["Producto", "Precio"]])
            total_v = df_car["Precio"].sum()
            st.markdown(f"## **TOTAL: ${total_v}**")
            
            if st.button("🚀 FINALIZAR Y PAGAR"):
                st.session_state.ticket_listo = generar_ticket(st.session_state.carrito, total_v)
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] += 1
                guardar_datos(st.session_state.inventory)
                st.session_state.carrito = []
                st.balloons()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()

        if st.session_state.ticket_listo:
            st.download_button("📥 DESCARGAR TICKET PDF", st.session_state.ticket_listo, 
                               f"ticket_{datetime.now().strftime('%H%M%S')}.pdf", "application/pdf")
            if st.button("Siguiente Venta"):
                st.session_state.ticket_listo = None
                st.rerun()

# --- TAB 2: REGISTRO ---
with t2:
    with st.form("new"):
        n = st.text_input("Nombre de prenda")
        p = st.number_input("Precio", min_value=0.0)
        s = st.number_input("Stock", min_value=1)
        if st.form_submit_button("Guardar"):
            new_id = datetime.now().strftime("%H%M%S")
            new_row = pd.DataFrame([{"ID": new_id, "Producto": n, "Precio": p, "Stock": s, "Ventas": 0}])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
            guardar_datos(st.session_state.inventory)
            st.success(f"Guardado: {n}")
            st.rerun()

# --- TAB 3: INVENTARIO Y QRS ---
with t3:
    st.subheader("📦 Stock y Etiquetas")
    # Editor manual por si quieres cambiar un precio rápido
    df_ed = st.data_editor(st.session_state.inventory, use_container_width=True)
    if st.button("💾 Guardar Cambios en Tabla"):
        st.session_state.inventory = df_ed
        guardar_datos(df_ed)
        st.success("¡Datos actualizados!")
    
    st.divider()
    if not st.session_state.inventory.empty:
        sel_qr = st.selectbox("Elegir para ver QR:", st.session_state.inventory['Producto'])
        row_q = st.session_state.inventory[st.session_state.inventory['Producto'] == sel_qr].iloc[0]
        qr = qrcode.make(f"{URL_APP}/?item={row_q['ID']}")
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf.getvalue(), width=150, caption=f"ID: {row_q['ID']}")
