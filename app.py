import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime
from pypdf import PdfReader

st.set_page_config(page_title="ContaSimple MVP", layout="wide")

st.title("Generador de Excel para ContaSimple – GASTOS")
st.write("Sube recibos bancarios de CaixaBank y descarga el Excel compatible con ContaSimple.")

# Proveedores frecuentes (CIF + País)
PROVEEDORES = {
    "IBERDROLA": ("A84249110", "España"),
    "SECURITAS": ("A79311123", "España"),
    "IONOS": ("B85049435", "España"),
    "IDEALISTA": ("B82085144", "España"),
}

uploaded_files = st.file_uploader(
    "Sube recibos bancarios (PDF)",
    type=["pdf"],
    accept_multiple_files=True
)

def extraer_datos(pdf_bytes: bytes):
    """
    Extrae texto del PDF y saca (fecha, proveedor/concepto, importe) con heurísticas simples.
    MVP: suficiente para recibos bancarios típicos.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texto = ""
    for page in reader.pages:
        texto += (page.extract_text() or "") + "\n"

    fecha = ""
    proveedor = ""
    importe = ""

    # Fecha tipo 29.10.25 -> 29/10/2025
    m_fecha = re.search(r"\b\d{2}\.\d{2}\.\d{2}\b", texto)
    if m_fecha:
        try:
            fecha = datetime.strptime(m_fecha.group(), "%d.%m.%y").strftime("%d/%m/%Y")
        except Exception:
            fecha = ""

    # Importe: coge el último número con coma (quita miles con punto)
    m_importe = re.findall(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b|\b\d+,\d{2}\b", texto)
    if m_importe:
        importe = m_importe[-1].replace(".", "")

    # Proveedor/Concepto (heurística): primera línea que contenga "INICIATIVAS FINANCIERAS"
    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
    for l in lineas:
        if "INICIATIVAS FINANCIERAS" in l.upper():
            proveedor = l
            break

    # Si no encuentra proveedor, usa una alternativa simple
    if not proveedor and lineas:
        proveedor = lineas[0]

    return fecha, proveedor, importe

if uploaded_files:
    filas = []
    contador = 1

    for f in uploaded_files:
        fecha, proveedor, importe = extraer_datos(f.read())

        prov = (proveedor or "").strip()
        prov_up = prov.upper()

        # CIF/País por defecto (si es proveedor conocido)
        nif = ""
        pais = "España"
        for k, (cif, p) in PROVEEDORES.items():
            if k in prov_up:
                nif = cif
                pais = p
                break

        filas.append({
            "FECHA": fecha,
            "NÚMERO": f"RC-CB-2026-{contador:04d}",
            "CONCEPTO": prov,
            "IMPORTE": importe,
            "% IMPUTABLE": 1,
            "TIPO GASTO": 629,
            "DESC. TIPO GASTO": "Otros servicios",
            "NOMBRE O RAZÓN SOCIAL": prov,     # OBLIGATORIO
            "NIF": nif,                        # OBLIGATORIO (si no lo sabe, lo rellenas tú en la tabla)
            "PAÍS": pais,                      # OBLIGATORIO
            "MÉTODO DE PAGO": "RECIBO BANCARIO",

            # Campos obligatorios en la importación de ContaSimple (para que no te los pida en el mapeo)
            # Si tu ContaSimple usa "Pagado" en vez de "Pagada", cambia aquí el valor.
            "ESTADO": "Pagada",
            "TIPO INGRESO": "Gasto",
            "TIPO OPERACIÓN": "Gasto",
        })

        contador += 1

    df = pd.DataFrame(filas)

    # Orden recomendado de columnas
    orden = [
        "FECHA", "NÚMERO", "CONCEPTO", "IMPORTE", "% IMPUTABLE",
        "TIPO GASTO", "DESC. TIPO GASTO",
        "NOMBRE O RAZÓN SOCIAL", "NIF", "PAÍS",
        "MÉTODO DE PAGO",
        "ESTADO", "TIPO INGRESO", "TIPO OPERACIÓN"
    ]
    df = df[[c for c in orden if c in df.columns]]

    st.subheader("Revisa/Completa datos antes de descargar")
    df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    # Bloqueo: no permitir descarga si faltan campos obligatorios
    faltan = df[
        (df["NIF"].astype(str).str.strip() == "")
        | (df["NOMBRE O RAZÓN SOCIAL"].astype(str).str.strip() == "")
        | (df["PAÍS"].astype(str).str.strip() == "")
        | (df["ESTADO"].astype(str).str.strip() == "")
        | (df["TIPO INGRESO"].astype(str).str.strip() == "")
        | (df["TIPO OPERACIÓN"].astype(str).str.strip() == "")
    ]
    if len(faltan) > 0:
        st.error("Faltan campos obligatorios. Rellena NIF/CIF, Nombre/Razón social, País y los campos de Estado/Tipo.")
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
else:
    st.info("Sube uno o varios PDFs para generar el Excel.")
