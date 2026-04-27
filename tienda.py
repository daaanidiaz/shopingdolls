import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# Configuración de página
st.set_page_config(page_title="ShopingDolls POS PRO", page_icon="👑", layout="wide")

# Archivos de datos
DB_FILE = "inventario_dolls.csv"
COUNT_FILE = "ultimo_ticket.txt"
URL_APP = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_datos():
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Producto", "Precio", "Stock", "Ventas"])

def guardar_datos(df): df.to_csv(DB_FILE, index=False)

def obtener_siguiente_ticket():
    if not os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "w") as f: f.write("1")
        return 1
    with open(COUNT_FILE, "r") as f:
        n = int(f.read())
    return n

def actualizar_contador(n):
    with open(COUNT_FILE, "w") as f: f.write(str(n + 1))

# --- GENERADOR DE TICKET PROFESIONAL ---
def generar_ticket_pro(carrito, total, n_ticket):
    pdf = FPDF(format=(80, 150)) # Tamaño ticketera
    pdf.add_page()
    
    # Encabezado con estilo
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "SHOPINGDOLLS", ln=True, align='C')
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 4, "EMPIRE BOUTIQUE LUXURY", ln=True, align='C')
    pdf.cell(0, 4, f"Ticket No: #{n_ticket:04d}", ln=True, align='C')
    pdf.cell(0, 4, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.cell(0, 5, "-"*30, ln=True, align='C')
    
    # Tabla de productos
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(10, 8, "#", border=0)
    pdf.cell(35, 8, "PRODUCTO", border=0)
    pdf.cell(15, 8, "TOTAL", border=0, ln=True, align='R')
    
    pdf.set_font("Arial", '', 9)
    for i, item in enumerate(carrito, 1):
        pdf.cell(10, 7, str(i))
        pdf.cell(35, 7, f"{item['Producto'][:15]}") # Corta nombre si es muy largo
        pdf.cell(15, 7, f"${item['Precio']}", ln=True, align='R')
    
    # Pie de ticket
    pdf.cell(0, 5, "-"*30, ln=True, align='C')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(45, 10, "TOTAL PAGADO:")
    pdf.cell(15, 10, f"${total}", ln=True, align='R')
    
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, "\n¡Gracias por elegir el Imperio!\nNo se aceptan devoluciones sin ticket.", align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# Inicializar estados
if 'inventory' not in st.session_state: st.session_state.inventory = cargar_datos()
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'pdf_blob' not in st.session_state: st.session_state.pdf_blob = None

st.markdown("<h1 style='text-align: center; color: #D4AF37;'>👑 ShopingDolls Pay PRO</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💰 CAJA REGISTRADORA", "➕ ALTA DE PRENDAS", "📦 INVENTARIO"])

# --- TAB 1: CAJA ---
with tab1:
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("🔍 Entrada de Venta")
        scan = st.text_input("Escanear con Lector:", key="input_scan")
        if scan:
            match = st.session_state.inventory[st.session_state.inventory['ID'].astype(str) == str(scan)]
            if not match.empty:
                st.session_state.carrito.append(match.iloc[0].to_dict())
                st.rerun()
        
        st.write("---")
        opciones = ["Buscar manualmente..."] + st.session_state.inventory['Producto'].tolist()
        manual = st.selectbox("O selecciona por nombre:", opciones)
        if manual != "Buscar manualmente..." and st.button("Añadir al Carrito"):
            p = st.session_state.inventory[st.session_state.inventory['Producto'] == manual].iloc[0]
            st.session_state.carrito.append(p.to_dict())
            st.rerun()

    with c2:
        st.subheader("🧾 Detalle del Ticket")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[["Producto", "Precio"]])
            total = df_c["Precio"].sum()
            st.markdown(f"## TOTAL: ${total}")
            
            if st.button("💳 FINALIZAR COMPRA"):
                n_actual = obtener_siguiente_ticket()
                # Generar PDF
                st.session_state.pdf_blob = generar_ticket_pro(st.session_state.carrito, total, n_actual)
                
                # Actualizar Stock y Ventas
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] += 1
                
                guardar_datos(st.session_state.inventory)
                actualizar_contador(n_actual)
                st.session_state.carrito = []
                st.balloons()
        
        if st.session_state.pdf_blob:
            st.success("¡Venta procesada con éxito!")
            st.download_button("📥 IMPRIMIR TICKET PDF", st.session_state.pdf_blob, "ticket_shopingdolls.pdf", "application/pdf")
            if st.button("Nueva Venta"):
                st.session_state.pdf_blob = None
                st.rerun()

# --- TAB 2 Y 3 (Mantenemos la lógica anterior pero con diseño limpio) ---
with tab2:
    with st.form("registro"):
        n = st.text_input("Nombre")
        p = st.number_input("Precio $")
        s = st.number_input("Stock", min_value=1)
        if st.form_submit_button("Guardar Prenda"):
            new_id = datetime.now().strftime("%H%M%S")
            new_row = pd.DataFrame([{"ID": new_id, "Producto": n, "Precio": p, "Stock": s, "Ventas": 0}])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
            guardar_datos(st.session_state.inventory)
            st.rerun()

with tab3:
    st.data_editor(st.session_state.inventory, use_container_width=True)
    if not st.session_state.inventory.empty:
        sel = st.selectbox("Ver QR de:", st.session_state.inventory['Producto'])
        row = st.session_state.inventory[st.session_state.inventory['Producto'] == sel].iloc[0]
        qr = qrcode.make(f"{URL_APP}/?item={row['ID']}")
        b = BytesIO()
        qr.save(b, format="PNG")
        st.image(b.getvalue(), width=150)
