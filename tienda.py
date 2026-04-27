import streamlit as st
import pandas as pd
import os
import qrcode
from io import BytesIO
from datetime import datetime
from fpdf import FPDF
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="ShopingDolls POS PRO", page_icon="👑", layout="wide")

# Archivos de datos
DB_FILE = "inventario_dolls.csv"
COUNT_FILE = "ultimo_ticket.txt"
URL_APP = "https://shopingdolls-2yk4fnpwuwp3muzynxeq5i.streamlit.app"

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Aseguramos que existan las nuevas columnas
        if "Talla" not in df.columns: df["Talla"] = "Única"
        if "Ventas" not in df.columns: df["Ventas"] = 0
        return df
    return pd.DataFrame(columns=["ID", "Producto", "Talla", "Precio", "Stock", "Ventas"])

def guardar_datos(df): df.to_csv(DB_FILE, index=False)

def obtener_siguiente_ticket():
    if not os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "w") as f: f.write("1")
        return 1
    with open(COUNT_FILE, "r") as f: n = int(f.read())
    return n

def actualizar_contador(n):
    with open(COUNT_FILE, "w") as f: f.write(str(n + 1))

# --- GENERADOR DE TICKET PROFESIONAL ---
def generar_ticket_pro(carrito, total, n_ticket):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "SHOPINGDOLLS", ln=True, align='C')
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 4, "EMPIRE BOUTIQUE LUXURY", ln=True, align='C')
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
        # Mostrar nombre y talla en el ticket
        pdf.cell(35, 7, f"{item['Producto'][:12]} ({item['Talla']})")
        pdf.cell(15, 7, f"${item['Precio']}", ln=True, align='R')
    
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

tab1, tab2, tab3, tab4 = st.tabs(["💰 CAJA", "➕ REGISTRO", "📦 STOCK", "📊 ESTADÍSTICAS"])

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
        # Buscador manual mejorado con Talla
        opciones = ["Buscar manualmente..."] + [f"{r['Producto']} ({r['Talla']})" for _, r in st.session_state.inventory.iterrows()]
        manual = st.selectbox("O selecciona por nombre:", opciones)
        if manual != "Buscar manualmente..." and st.button("Añadir al Carrito"):
            # Extraer nombre y talla para buscar el ID correcto
            nombre_sel = manual.split(" (")[0]
            talla_sel = manual.split(" (")[1].replace(")", "")
            p = st.session_state.inventory[(st.session_state.inventory['Producto'] == nombre_sel) & (st.session_state.inventory['Talla'] == talla_sel)].iloc[0]
            st.session_state.carrito.append(p.to_dict())
            st.rerun()

    with c2:
        st.subheader("🧾 Detalle del Ticket")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[["Producto", "Talla", "Precio"]])
            total = df_c["Precio"].sum()
            st.markdown(f"## TOTAL: ${total}")
            
            if st.button("💳 FINALIZAR COMPRA"):
                n_actual = obtener_siguiente_ticket()
                st.session_state.pdf_blob = generar_ticket_pro(st.session_state.carrito, total, n_actual)
                
                for item in st.session_state.carrito:
                    idx = st.session_state.inventory[st.session_state.inventory['ID'] == item['ID']].index[0]
                    st.session_state.inventory.at[idx, 'Stock'] -= 1
                    st.session_state.inventory.at[idx, 'Ventas'] += 1
                
                guardar_datos(st.session_state.inventory)
                actualizar_contador(n_actual)
                st.session_state.carrito = []
                st.balloons()
        
        if st.session_state.pdf_blob:
            st.success("¡Venta procesada!")
            st.download_button("📥 DESCARGAR TICKET PDF", st.session_state.pdf_blob, "ticket.pdf", "application/pdf")
            
            # Botón de WhatsApp
            txt_wa = f"¡Hola! Gracias por comprar en ShopingDolls. Tu ticket #{obtener_siguiente_ticket()-1:04d} por ${total} está listo. 👑"
            st.link_button("📲 ENVIAR POR WHATSAPP", f"https://wa.me/?text={txt_wa}")
            
            if st.button("Nueva Venta"):
                st.session_state.pdf_blob = None
                st.rerun()

# --- TAB 2: ALTA DE PRENDAS ---
with tab2:
    with st.form("registro"):
        st.subheader("✨ Nueva Prenda Multi-Talla")
        col_n, col_t = st.columns(2)
        with col_n: n = st.text_input("Nombre de la Prenda")
        with col_t: t = st.selectbox("Talla", ["Única", "S", "M", "L", "XL", "XXL"])
        
        col_p, col_s = st.columns(2)
        with col_p: p = st.number_input("Precio $", min_value=0.0)
        with col_s: s = st.number_input("Stock Inicial", min_value=1)
        
        if st.form_submit_button("Guardar en el Imperio"):
            if n:
                new_id = datetime.now().strftime("%H%M%S")
                new_row = pd.DataFrame([{"ID": new_id, "Producto": n, "Talla": t, "Precio": p, "Stock": s, "Ventas": 0}])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
                guardar_datos(st.session_state.inventory)
                st.success(f"{n} ({t}) guardado correctamente.")
                st.rerun()

# --- TAB 3: INVENTARIO Y ALERTAS ---
with tab3:
    st.subheader("📦 Control de Stock")
    # Alerta de stock bajo
    bajo_stock = st.session_state.inventory[st.session_state.inventory['Stock'] <= 3]
    if not bajo_stock.empty:
        st.warning(f"⚠️ ¡Atención! Tienes {len(bajo_stock)} productos con stock bajo (3 unidades o menos).")
    
    # Editor de datos
    df_edit = st.data_editor(st.session_state.inventory, use_container_width=True)
    if st.button("💾 Guardar cambios del inventario"):
        st.session_state.inventory = df_edit
        guardar_datos(df_edit)
        st.success("Inventario actualizado.")

    st.write("---")
    if not st.session_state.inventory.empty:
        sel = st.selectbox("Generar QR de:", opciones[1:])
        nombre_qr = sel.split(" (")[0]
        talla_qr = sel.split(" (")[1].replace(")", "")
        row = st.session_state.inventory[(st.session_state.inventory['Producto'] == nombre_qr) & (st.session_state.inventory['Talla'] == talla_qr)].iloc[0]
        
        qr = qrcode.make(f"{URL_APP}/?item={row['ID']}")
        b = BytesIO()
        qr.save(b, format="PNG")
        st.image(b.getvalue(), width=150, caption=f"ID: {row['ID']}")

# --- TAB 4: DASHBOARD ---
with tab4:
    st.subheader("📊 Rendimiento del Imperio")
    if not st.session_state.inventory.empty:
        m1, m2, m3 = st.columns(3)
        total_ingresos = (st.session_state.inventory['Ventas'] * st.session_state.inventory['Precio']).sum()
        total_unidades = st.session_state.inventory['Ventas'].sum()
        mejor_producto = st.session_state.inventory.loc[st.session_state.inventory['Ventas'].idxmax()]['Producto']
        
        m1.metric("Ingresos Totales", f"${total_ingresos}")
        m2.metric("Prendas Vendidas", total_unidades)
        m3.metric("Producto Estrella", mejor_producto)
        
        # Gráfica de ventas
        fig = px.bar(st.session_state.inventory, x='Producto', y='Ventas', color='Talla', 
                     title="Ventas por Producto y Talla", barmode='group',
                     color_discrete_sequence=px.colors.qualitative.Antique)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aún no hay datos para mostrar estadísticas.")
