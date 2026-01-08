import streamlit as st
from pypdf import PdfReader
import pandas as pd
import io
import re
from datetime import datetime

st.set_page_config(page_title="ContaSimple MVP", layout="wide")

st.title("Generador de Excel para ContaSimple – GASTOS")

st.write("Sube recibos bancarios de CaixaBank y descarga el Excel compatible con ContaSimple.")

uploaded_files = st.file_uploader(
    "Sube recibos bancarios (PDF)",
    type=["pdf"],
    accept_multiple_files=True
)

def extraer_datos(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texto = ""
    for page in reader.pages:
        texto += (page.extract_text() or "") + "\n"

    fecha = None
    proveedor = None
    importe = None

    m_fecha = re.search(r"\d{2}\.\d{2}\.\d{2}", texto)
    if m_fecha:
        fecha = datetime.strptime(m_fecha.group(), "%d.%m.%y").strftime("%d/%m/%Y")

    lineas = texto.split("\n")
    for l in lineas:
        if "INICIATIVAS FINANCIERAS" in l and fecha:
            proveedor = l.replace(fecha, "").replace("INICIATIVAS FINANCIERAS HIPOTECARIAS SL", "").strip()

    m_importe = re.findall(r"\d+,\d{2}", texto)
    if m_importe:
        importe = m_importe[-1]

    return fecha, proveedor, importe


    fecha = None
    proveedor = None
    importe = None

    m_fecha = re.search(r"\d{2}\.\d{2}\.\d{2}", texto)
    if m_fecha:
        fecha = datetime.strptime(m_fecha.group(), "%d.%m.%y").strftime("%d/%m/%Y")

    lineas = texto.split("\n")
    for l in lineas:
        if "INICIATIVAS FINANCIERAS" in l and fecha:
            proveedor = l.replace(fecha, "").replace("INICIATIVAS FINANCIERAS HIPOTECARIAS SL", "").strip()

    m_importe = re.findall(r"\d+,\d{2}", texto)
    if m_importe:
        importe = m_importe[-1]

    return fecha, proveedor, importe

if uploaded_files:
    filas = []
    contador = 1

    for f in uploaded_files:
        fecha, proveedor, importe = extraer_datos(f.read())

        filas.append({
            "FECHA": fecha,
            "NÚMERO": f"RC-CB-2025-{contador:04d}",
            "CONCEPTO": proveedor,
            "IMPORTE": importe,
            "% IMPUTABLE": 1,
            "TIPO GASTO": 629,
            "DESC. TIPO GASTO": "Otros servicios",
            "NOMBRE O RAZÓN SOCIAL": proveedor,
            "NIF": "X0000000X",
            "MÉTODO DE PAGO": "RECIBO BANCARIO"
        })

        contador += 1

    df = pd.DataFrame(filas)

    st.dataframe(df)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Gastos")

    st.download_button(
        "Descargar Excel de Gastos",
        data=buffer.getvalue(),
        file_name="Gastos_ContaSimple.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

