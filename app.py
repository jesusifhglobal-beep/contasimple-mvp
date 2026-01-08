import streamlit as st
from pypdf import PdfReader
import pandas as pd
import io
import re
from datetime import datetime
PROVEEDORES = {
    "IBERDROLA": ("A84249110", "España"),
    "SECURITAS": ("A79311123", "España"),
    "IONOS": ("B85049435", "España"),
    "IDEALISTA": ("B82085144", "España"),
}

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

               # Normaliza proveedor
        prov = (proveedor or "").strip()
        prov_up = prov.upper()

        # Intenta asignar CIF/País automáticamente si es proveedor conocido
        nif = ""
        pais = "España"
        for k, (cif, p) in PROVEEDORES.items():
            if k in prov_up:
                nif = cif
                pais = p
                break

        filas.append({
            "FECHA": fecha or "",
            "NÚMERO": f"RC-CB-2025-{contador:04d}",
            "CONCEPTO": prov,
            "IMPORTE": importe or "",
            "% IMPUTABLE": 1,
            "TIPO GASTO": 629,
            "DESC. TIPO GASTO": "Otros servicios",
            "NOMBRE O RAZÓN SOCIAL": prov,   # OBLIGATORIO
            "NIF": nif,                      # OBLIGATORIO (si no lo sabemos, lo rellenas tú)
            "PAÍS": pais,                    # OBLIGATORIO
            "MÉTODO DE PAGO": "RECIBO BANCARIO"
        })


        contador += 1

       df = pd.DataFrame(filas)

    st.subheader("Revisa/Completa datos antes de descargar")
    df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    # Bloqueo: no dejar descargar si faltan campos obligatorios para ContaSimple
    faltan = df[
        (df["NIF"].astype(str).str.strip() == "")
        | (df["NOMBRE O RAZÓN SOCIAL"].astype(str).str.strip() == "")
        | (df["PAÍS"].astype(str).str.strip() == "")
    ]
    if len(faltan) > 0:
        st.error("Faltan datos obligatorios del proveedor (NIF/CIF, Nombre o razón social o País). Rellénalos en la tabla para poder descargar.")
        st.stop()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Gastos")

    st.download_button(
        "Descargar Excel de Gastos",
        data=buffer.getvalue(),
        file_name="Gastos_ContaSimple.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
