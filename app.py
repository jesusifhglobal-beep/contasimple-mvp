import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

st.set_page_config(
    page_title="ContaSimple MVP – Gastos",
    layout="wide"
)

st.title("Generador de Excel para ContaSimple – GASTOS")
st.write("Sube recibos bancarios (CaixaBank) y descarga el Excel listo para importar como GASTOS.")

uploaded_files = st.file_uploader(
    "Sube recibos bancarios (PDF)",
    type=["pdf"],
    accept_multiple_files=True
)

def extraer_datos(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() or ""

    # Fecha
    fecha = ""
    m_fecha = re.search(r"\d{2}\.\d{2}\.\d{2}", texto)
    if m_fecha:
        fecha = datetime.strptime(m_fecha.group(), "%d.%m.%y").strftime("%d/%m/%Y")

    # Proveedor
    proveedor = "Proveedor no identificado"
    for linea in texto.split("\n"):
        if "S.A." in linea or "SL" in linea:
            proveedor = linea.strip()
            break

    # Importe
    importe = ""
    m_importes = re.findall(r"\d+,\d{2}", texto)
    if m_importes:
        importe = m_importes[-1].replace(",", ".")

    return fecha, proveedor, importe

if uploaded_files:
    filas = []
    contador = 1

    for f in uploaded_files:
        fecha, proveedor, importe = extraer_datos(f.read())

        filas.append({
            "FECHA": fecha,
            "NÚMERO": f"RC-CB-2026-{contador:04d}",
            "CONCEPTO": proveedor,
            "IMPORTE": importe,
            "% IMPUTABLE": 1,
            "TIPO GASTO": 629,
            "DESC. TIPO GASTO": "Otros servicios",
            "NOMBRE O RAZÓN SOCIAL": proveedor,
            "NIF": "B00000000",
            "PAÍS": "España",
            "MÉTODO DE PAGO": "RECIBO BANCARIO",
            "ESTADO": "Pagado",
            "TIPO INGRESO": "Gasto",
            "TIPO OPERACIÓN": "Gasto",
        })

        contador += 1

    df = pd.DataFrame(filas)

    orden = [
        "FECHA", "NÚMERO", "CONCEPTO", "IMPORTE", "% IMPUTABLE",
        "TIPO GASTO", "DESC. TIPO GASTO",
        "NOMBRE O RAZÓN SOCIAL", "NIF", "PAÍS",
        "MÉTODO DE PAGO", "ESTADO", "TIPO INGRESO", "TIPO OPERACIÓN"
    ]
    df = df[orden]

    st.subheader("Vista previa")
    st.dataframe(df, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Gastos")

    st.download_button(
        "Descargar Excel de Gastos (ContaSimple)",
        data=buffer.getvalue(),
        file_name="Gastos_ContaSimple.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
