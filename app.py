import os
import json
import io
import re
import unicodedata
import requests
import pandas as pd
import streamlit as st
from google import genai

# 1. Configuración de la página
st.set_page_config(page_title="SEO Catalog Pro | AI E-commerce", page_icon="🚀", layout="wide")

# 2. Gestión segura de la API Key
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Falta configurar GEMINI_API_KEY en los Secrets del servidor.")
    st.stop()

client = genai.Client(api_key=API_KEY)

MODELOS_BACKUP = [
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-3.8-flash'
]

# Función para validar licencias con Lemon Squeezy (y clave maestra para tus pruebas)
def verificar_licencia(clave: str) -> bool:
    clave = clave.strip()
    if not clave:
        return False
    # Clave maestra secreta para que tú puedas probar el modo PRO sin pagar
    if clave == "PRO-TEST-2026":
        return True
    try:
        res = requests.post(
            "https://api.lemonsqueezy.com/v1/licenses/validate",
            data={"license_key": clave},
            headers={"Accept": "application/json"},
            timeout=10
        )
        datos = res.json()
        return datos.get("valid", False)
    except Exception:
        return False

def crear_handle(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    texto = re.sub(r'[^\w\s-]', '', texto.lower())
    return re.sub(r'[-\s]+', '-', texto).strip('-')

# 3. Barra lateral: Licencia + Configuración
with st.sidebar:
    st.header("🔑 Acceso Pro")
    licencia_input = st.text_input("Introduce tu Clave de Licencia", type="password", placeholder="XXXX-XXXX-XXXX-XXXX")
    es_pro = verificar_licencia(licencia_input)
    
    if es_pro:
        st.success("✅ Plan PRO Activo (Catálogos ilimitados)")
        limite_productos = 500
    else:
        st.warning("⚡ Modo Gratuito (Máx. 3 productos por lote)")
        st.markdown("[👉 **Consigue tu Licencia PRO aquí (10€/mes)**](https://tu-tienda.lemonsqueezy.com)")
        limite_productos = 3

    st.divider()
    st.header("⚙️ Configuración del Catálogo")
    plataforma = st.selectbox(
        "Formato de tienda destino",
        ["Shopify (CSV Oficial)", "WooCommerce (CSV Oficial)", "Estándar (Excel Multiuso)"]
    )
    tono = st.selectbox(
        "Tono de copywriting",
        ["Persuasivo y enfocado a conversión", "Técnico y detallado", "Minimalista / Premium", "Cercano y dinámico"]
    )
    idioma = st.selectbox(
        "Idioma de salida",
        ["Español", "Inglés", "Catalán", "Francés", "Alemán", "Italiano"]
    )
    st.divider()
    st.caption("🔒 Motor IA con balanceo de carga activo.")

# 4. Cuerpo principal
st.title("🚀 Optimizador Masivo de Catálogos para E-commerce")
st.markdown("Transforma el Excel crudo de tu proveedor en un catálogo optimizado para SEO listo para importar en **Shopify** o **WooCommerce** en segundos.")

opcion_carga = st.radio(
    "Selecciona el origen de los datos:",
    ["Probar con catálogo de demostración", "Subir mi propio archivo (.xlsx / .csv)"],
    horizontal=True
)

df_entrada = None

if opcion_carga == "Probar con catálogo de demostración":
    df_entrada = pd.DataFrame([
        {"SKU_Prov": "BICI-01", "Articulo": "soporte movil bici negro", "Info_Tecnica": "aluminio rotacion 360 grados manillar 22-32mm resistente agua"},
        {"SKU_Prov": "TERMO-02", "Articulo": "botella termica 500ml acero", "Info_Tecnica": "frio 24h calor 12h doble pared sin bpa gym senderismo"},
        {"SKU_Prov": "AUDIO-03", "Articulo": "auriculares bluetooth deportivos", "Info_Tecnica": "cancelacion ruido bateria 30h ipx7 sudor correr microfono"},
        {"SKU_Prov": "LUZ-04", "Articulo": "luz trasera bici recargable usb", "Info_Tecnica": "led alta potencia 5 modos impermeable bateria 10h facil montaje"},
        {"SKU_Prov": "MOCH-05", "Articulo": "mochila antirrobo impermeable portatil", "Info_Tecnica": "puerto carga usb compartimento 15.6 pulgadas cierre oculto viaje"}
    ])
else:
    archivo = st.file_uploader("Arrastra aquí el archivo de tu proveedor (.xlsx o .csv)", type=["xlsx", "csv"])
    if archivo:
        try:
            df_entrada = pd.read_csv(archivo) if archivo.name.endswith(".csv") else pd.read_excel(archivo)
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")

if df_entrada is not None and not df_entrada.empty:
    st.subheader("1️⃣ Vista previa del archivo original")
    st.dataframe(df_entrada.head(10), use_container_width=True)

    columnas = list(df_entrada.columns)

    st.subheader("2️⃣ Asigna las columnas de tu archivo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        col_id = st.selectbox("Columna de SKU / ID (Opcional)", ["(Generar automático)"] + columnas, index=1 if len(columnas) > 0 else 0)
    with col2:
        col_nombre = st.selectbox("Columna con el Nombre del Producto", columnas, index=1 if len(columnas) > 1 else 0)
    with col3:
        col_detalles = st.selectbox("Columna con Características / Detalles", columnas, index=2 if len(columnas) > 2 else (len(columnas)-1))

    # Aplicar el límite según si es usuario gratuito o de pago
    total_en_archivo = len(df_entrada)
    df_procesar = df_entrada.head(limite_productos)

    if not es_pro and total_en_archivo > limite_productos:
        st.info(f"🔒 Tu archivo tiene **{total_en_archivo} productos**. En el Modo Gratuito procesaremos los primeros **{limite_productos} productos** como demostración. Introduce una licencia Pro en el menú izquierdo para procesar el catálogo completo.")

    productos_para_ia = []
    for idx, row in df_procesar.iterrows():
        sku_val = str(row[col_id]) if col_id != "(Generar automático)" else f"SKU-{idx+1:03d}"
        productos_para_ia.append({
            "sku": sku_val,
            "nombre_original": str(row[col_nombre]),
            "detalles": str(row[col_detalles])
        })

    st.write("")
    if st.button(f"✨ Optimizar {len(productos_para_ia)} Productos para {plataforma.split()[0]}", type="primary"):
        with st.spinner("Redactando fichas SEO y estructurando código HTML..."):
            prompt = f"""
            Eres un experto en copywriting para e-commerce y SEO técnico.
            Transforma esta lista de productos en fichas de alta conversión.
            - Tono de marca: {tono}
            - Idioma obligatorio de salida: {idioma}

            Productos de entrada:
            {json.dumps(productos_para_ia, ensure_ascii=False)}

            Devuelve ÚNICAMENTE un array JSON válido (sin etiquetas markdown ```json) con esta estructura exacta para cada producto:
            [
              {{
                "sku": "repite el sku exacto de entrada",
                "nombre_original": "repite el nombre original",
                "seo_title": "título optimizado para SEO y clics (máximo 60 caracteres)",
                "meta_description": "meta descripción persuasiva con llamada a la acción (140-155 caracteres)",
                "beneficios_lista": ["Beneficio clave 1", "Beneficio clave 2", "Beneficio clave 3"],
                "descripcion_html": "<p>Párrafo inicial atractivo...</p><h3>Características principales</h3><ul><li>...</li></ul>",
                "tags": "palabra1, palabra2, palabra3, palabra4, palabra5"
              }}
            ]
            """

            resultados_ia = None
            for modelo in MODELOS_BACKUP:
                try:
                    response = client.models.generate_content(
                        model=modelo,
                        contents=prompt,
                    )
                    texto_limpio = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    resultados_ia = json.loads(texto_limpio)
                    break
                except Exception:
                    continue

            if resultados_ia:
                st.success(f"¡Catálogo generado con éxito para **{plataforma}**!")

                filas_exportar = []
                for item in resultados_ia:
                    bullets_html = "<ul>" + "".join([f"<li><strong>{b}</strong></li>" for b in item.get("beneficios_lista", [])]) + "</ul>"
                    html_completo = f"{bullets_html}\n{item.get('descripcion_html', '')}"
                    
                    if plataforma.startswith("Shopify"):
                        filas_exportar.append({
                            "Handle": crear_handle(item.get("seo_title", item.get("nombre_original", ""))),
                            "Title": item.get("seo_title", ""),
                            "Body (HTML)": html_completo,
                            "Vendor": "Mi Tienda",
                            "Tags": item.get("tags", ""),
                            "Published": "TRUE",
                            "Variant SKU": item.get("sku", ""),
                            "SEO Title": item.get("seo_title", ""),
                            "SEO Description": item.get("meta_description", "")
                        })
                    elif plataforma.startswith("WooCommerce"):
                        filas_exportar.append({
                            "SKU": item.get("sku", ""),
                            "Name": item.get("seo_title", ""),
                            "Short description": " | ".join(item.get("beneficios_lista", [])),
                            "Description": html_completo,
                            "Tags": item.get("tags", ""),
                            "Meta: _yoast_wpseo_title": item.get("seo_title", ""),
                            "Meta: _yoast_wpseo_metadesc": item.get("meta_description", "")
                        })
                    else:
                        filas_exportar.append({
                            "SKU": item.get("sku", ""),
                            "Producto_Original": item.get("nombre_original", ""),
                            "Título_SEO": item.get("seo_title", ""),
                            "Meta_Description": item.get("meta_description", ""),
                            "Beneficios_Clave": " | ".join(item.get("beneficios_lista", [])),
                            "Descripción_HTML": html_completo,
                            "Palabras_Clave (Tags)": item.get("tags", "")
                        })

                df_final = pd.DataFrame(filas_exportar)

                st.subheader("3️⃣ Catálogo listo para importar")
                st.dataframe(df_final, use_container_width=True)

                col_desc1, col_desc2 = st.columns(2)
                with col_desc1:
                    csv_bytes = df_final.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 Descargar CSV directo para {plataforma.split()[0]}",
                        data=csv_bytes,
                        file_name=f"importacion_{plataforma.split()[0].lower()}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with col_desc2:
                    buffer_excel = io.BytesIO()
                    df_final.to_excel(buffer_excel, index=False)
                    buffer_excel.seek(0)
                    st.download_button(
                        label="📊 Descargar en formato Excel (.xlsx)",
                        data=buffer_excel,
                        file_name="catalogo_optimizado_seo.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.error("Todos los servidores de IA están ocupados en este instante. Espera 10 segundos y vuelve a pulsar el botón.")