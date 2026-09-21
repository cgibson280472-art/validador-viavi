import streamlit as st
from google import genai
from PIL import Image

# Configuración de la página
st.set_page_config(
    page_title="Validador Inteligente HFC (Lápida vs. Viavi ONX-630)",
    layout="wide"
)

# Barra lateral para credenciales y parámetros
st.sidebar.title("🔑 Configuración de IA")

api_key = st.sidebar.text_input(
    "Gemini API Key", 
    type="password", 
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""
)

tolerancia = st.sidebar.slider("Tolerancia Permitida (dB)", 0.5, 5.0, 2.0, 0.25)

st.title("📡 Validador Inteligente HFC (Lápida vs. Viavi ONX-630)")
st.markdown("Sube la foto de la lápida del nodo y las capturas del medidor. La IA extraerá los valores y evaluará la tolerancia de $\\pm 2.0\\text{ dB}$.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Lápida de Referencia")
    archivo_lapida = st.file_uploader("Sube la imagen de la lápida del nodo", type=["png", "jpg", "jpeg"], key="lapida")

with col2:
    st.subheader("2. Capturas del Viavi ONX-630")
    archivos_viavi = st.file_uploader("Sube las capturas de los puertos (P1, P2, P3, P4)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="viavi")

if archivo_lapida:
    img_lapida = Image.open(archivo_lapida)
    st.image(img_lapida, caption="Lápida cargada", use_container_width=True)

if archivos_viavi:
    for idx, img_file in enumerate(archivos_viavi):
        img = Image.open(img_file)
        st.image(img, caption=f"Medición #{idx+1}", use_container_width=True)

if st.button("🚀 Procesar Imágenes con IA y Validar", type="primary"):
    if not api_key:
        st.error("Por favor, ingresa tu API Key de Gemini en la barra lateral o en los Secrets.")
    elif not archivo_lapida or not archivos_viavi:
        st.warning("Debes subir tanto la foto de la lápida como al menos una captura del medidor Viavi.")
    else:
        try:
            with st.spinner("Analizando imágenes con Inteligencia Artificial..."):
                client = genai.Client(api_key=api_key)
                
                contents = [
                    f"Actúa como un ingeniero experto en redes HFC. Analiza la imagen de la lápida del nodo para extraer los valores de referencia y compáralos con las capturas de los puertos del medidor Viavi ONX-630 proporcionadas. Evalúa si las desviaciones se encuentran dentro de la tolerancia permitida de ±{tolerancia} dB.",
                    Image.open(archivo_lapida)
                ]
                
                for f in archivos_viavi:
                    contents.append(Image.open(f))
                
                # Usando el identificador con el formato correcto requerido por el SDK nuevo
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents
                )
                
                st.success("¡Validación completada con éxito!")
                st.markdown("### Resultados del Análisis:")
                st.write(response.text)
                
        except Exception as e:
            # Intento de respaldo automático con otro identificador si el primero falla
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=contents
                )
                st.success("¡Validación completada con éxito!")
                st.markdown("### Resultados del Análisis:")
                st.write(response.text)
            except Exception as e2:
                st.error(f"Ocurrió un error al procesar las imágenes con la IA: {e2}")
                st.info("Consejo: Asegúrate de que tu API Key sea correcta y de que las imágenes muestren claramente los números y puertos.")
