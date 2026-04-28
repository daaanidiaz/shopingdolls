import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime
from fpdf import FPDF
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="ShopingDolls POS PRO", page_icon="👑", layout="wide")

DB_FILE = "inventario_dolls.csv"
COUNT_FILE = "ultimo_ticket.txt"
URL_APP = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"

# --- FUNCIONES DE BASE DE DATOS ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Forzamos la creación de columnas si el archivo es antiguo
        if "Talla" not in df.columns: df["Talla"] = "Única"
        if "Ventas" not in df.columns: df["Ventas"] = 0
        df['ID'] = df['ID'].astype(str)
        return df
    return pd.DataFrame(columns=["ID", "Producto", "Talla", "Precio", "Stock", "Ventas"])

def guardar_datos(df): 
    df.to_csv(DB_FILE, index=False)

def obtener_siguiente_ticket():
    if not os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "w") as f: f.write("1")
        return 1
    with open(COUNT_FILE, "r") as f: n = int(f.read())
    return n

def actualizar_contador(n):
    with open(COUNT_FILE, "w") as f: f.write(str(n + 1))

# --- GENERADOR DE TICKET ---
def generar_ticket_pro(carrito, suma_total, n_ticket):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "SHOPINGDOLLS", ln=True, align='C')
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 4, f"Ticket No: #{n_ticket:04d}", ln=True, align='C')
    pdf.cell(0, 4, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.cell(0, 5, "-"*30, ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(10, 8, "#")
    pdf.cell(35, 8, "PRODUCTO")
    pdf.cell(15, 8, "TOTAL", ln=True, align='R')
    
    pdf.set_font("Arial", '', 9)
    for i, item in enumerate(carrito, 1):
        pdf.cell(10, 7, str(i))
        pdf.cell(35, 7, f"{item['Producto'][:12]} ({item['Talla']})")
        pdf.cell(15, 7, f"${item['Precio']}", ln=True, align='R')
    
    pdf.cell(0, 5, "-"*30, ln=True, align='C')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(45, 10, "TOTAL:")
    pdf.cell(15, 10, f"${suma_total}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INICIALIZAR ESTADOS ---
if 'inventory' not in st.session_state: st.session_state.inventory = cargar_datos()
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'pdf_blob' not in st.session_state: st.session_state.pdf_blob = None
if 'ultimo_total' not in st.session_state: st.session_state.ultimo_total = 0

st.markdown("<h1 style='text-align: center; color: #D4AF37;'>👑 ShopingDolls Empire OS</h1>", unsafe_allow_html=True)

# LAS 4 PESTAÑAS
tab1, tab2, tab3, tab4 = st.tabs(["💰 CAJA", "➕ REGISTRO", "📦 STOCK", "📊 DASHBOARD"])

# --- TAB 1: CAJA ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔍 Añadir")
        scan = st.text_input("Lector / QR:", key="input_scan")
        if scan:
            match = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == str(scan)]
            if not match.empty:
                st.session_state.carrito.append(match.iloc[0].to_dict())
                st.rerun()
        
        st.write("---")
        opciones_m = ["Manual..."] + [f"{r['Producto']} ({r['Talla']})" for _, r in st.session_state.inventory.iterrows()]
        manual = st.selectbox("Selección Manual:", opciones_m)
        if manual != "Manual..." and st.button("Añadir al Carrito"):
            nombre_p = manual.split(" (")[0]
            talla_p = manual.split(" (")[1].replace(")", "")
            p = st.session_state.inventory[(st.session_state.inventory['Producto'] == nombre_p) & (st.session_state.inventory['Talla'] == talla_p)].iloc[0]
            st.session_state.carrito.append(p.to_dict())
            st.rerun()

    with c2:
        st.subheader("🧾 Ticket")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[["Producto", "Talla", "Precio"]])
            total_v = df_c["Precio"].sum()
            st.session_state.ultimo_total = total_v # Guardamos para el WhatsApp
            st.markdown(f"## TOTAL: ${total_v}")
            
            if st.button("🚀 FINALIZAR VENTA"):
                n_actual = obtener_siguiente_ticket()
                st.session_state.pdf_blob = generar_ticket_pro(st.session_state.carrito, total_v, n_actual)
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == str(item['ID'])].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] += 1
                guardar_datos(st.session_state.inventory)
                actualizar_contador(n_actual)
                st.session_state.carrito = []
                st.balloons()
                st.rerun()

        if st.session_state.pdf_blob:
            st.success("✅ ¡Venta finalizada!")
            st.download_button("📥 DESCARGAR TICKET PDF", st.session_state.pdf_blob, "ticket.pdf")
            
            # WhatsApp Corregido
            msg = f"¡Gracias por tu compra en ShopingDolls! Total: ${st.session_state.ultimo_total}. 👑"
            st.link_button("📲 ENVIAR POR WHATSAPP", f"https://wa.me/?text={msg}")
            
            if st.button("Nueva Venta"):
                st.session_state.pdf_blob = None
                st.rerun()

# --- TAB 2: REGISTRO CON TALLAS ---
with tab2:
    with st.form("reg"):
        st.subheader("✨ Registro de Prenda")
        n = st.text_input("Nombre")
        t = st.selectbox("Talla", ["Única", "S", "M", "L", "XL"])
        p = st.number_input("Precio", min_value=0.0)
        s = st.number_input("Stock", min_value=1)
        if st.form_submit_button("Guardar"):
            new_id = datetime.now().strftime("%H%M%S")
            new_row = pd.DataFrame([{"ID": new_id, "Producto": n, "Talla": t, "Precio": p, "Stock": s, "Ventas": 0}])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
            guardar_datos(st.session_state.inventory)
            st.rerun()

# --- TAB 3: STOCK ---
with tab3:
    st.subheader("📦 Control de Inventario")
    bajo = st.session_state.inventory[st.session_state.inventory['Stock'] <= 3]
    if not bajo.empty:
        st.warning(f"⚠️ Stock bajo en {len(bajo)} prendas.")
    
    df_ed = st.data_editor(st.session_state.inventory, use_container_width=True)
    if st.button("Guardar cambios manuales"):
        st.session_state.inventory = df_ed
        guardar_datos(df_ed)
        st.success("¡Datos actualizados!")

# --- TAB 4: DASHBOARD (Gráficas) ---
with tab4:
    st.subheader("📊 Estadísticas de Ventas")
    if not st.session_state.inventory.empty:
        col1, col2 = st.columns(2)
        dinero = (st.session_state.inventory['Ventas'] * st.session_state.inventory['Precio']).sum()
        col1.metric("Ingresos Totales", f"${dinero}")
        col2.metric("Total Vendido", st.session_state.inventory['Ventas'].sum())
        
        fig = px.bar(st.session_state.inventory, x='Producto', y='Ventas', color='Talla', title="Productos más vendidos")
        st.plotly_chart(fig, use_container_width=True)
