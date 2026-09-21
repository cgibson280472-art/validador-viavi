import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Validador IA HFC - Viavi ONX-630", layout="wide"
)

st.title("📡 Validador Inteligente HFC (Lápida vs. Viavi ONX-630)")
st.markdown(
    "Sube la foto de la **lápida del nodo** y las **capturas del medidor**. La IA extraerá los valores y evaluará la tolerancia de **±2.0 dB**."
)

# --- CONFIGURACIÓN DE LA API KEY EN LA BARRA LATERAL ---
st.sidebar.header("🔑 Configuración de IA")
api_key_input = st.sidebar.text_input(
    "Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", "")
)
tolerancia = st.sidebar.slider(
    "Tolerancia Permitida (dB)", min_value=0.5, max_value=5.0, value=2.0, step=0.5
)

# --- SECCIÓN DE CARGA DE ARCHIVOS ---
col_l, col_m = st.columns(2)

with col_l:
    st.subheader("1. Lápida de Referencia")
    img_lapida = st.file_uploader(
        "Sube la imagen de la lápida del nodo",
        type=["png", "jpg", "jpeg"],
        key="lapida",
    )
    if img_lapida:
        st.image(img_lapida, caption="Lápida cargada", use_container_width=True)

with col_m:
    st.subheader("2. Capturas del Viavi ONX-630")
    imgs_medicion = st.file_uploader(
        "Sube las capturas de los puertos (P1, P2, P3, P4)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="mediciones",
    )
    if imgs_medicion:
        for idx, img in enumerate(imgs_medicion):
            st.image(img, caption=f"Medición #{idx+1}", use_container_width=True)

st.markdown("---")

# --- PROCESAMIENTO CON INTELIGENCIA ARTIFICIAL ---
if st.button("🚀 Procesar Imágenes con IA y Validar", type="primary"):
    if not api_key_input:
        st.error(
            "⚠️ Por favor, ingresa tu API Key de Gemini en la barra lateral."
        )
    elif not img_lapida or not imgs_medicion:
        st.warning(
            "⚠️ Debes subir tanto la imagen de la lápida como al menos una captura de medición."
        )
    else:
        with st.spinner(
            "🤖 Analizando píxeles de las imágenes y extrayendo niveles..."
        ):
            try:
                client = genai.Client(api_key=api_key_input)
                contents = []

                # Añadir la lápida
                img_lapida_bytes = img_lapida.getvalue()
                contents.append(
                    types.Part.from_bytes(
                        data=img_lapida_bytes, mime_type="image/jpeg"
                    )
                )

                # Añadir las mediciones
                for img_med in imgs_medicion:
                    contents.append(
                        types.Part.from_bytes(
                            data=img_med.getvalue(), mime_type="image/jpeg"
                        )
                    )

                prompt = """
                Analiza estas imágenes de una red HFC. La primera imagen es la "lápida de referencia" que contiene los valores teóricos de diseño por puerto y frecuencia (por ejemplo, P1, P2, P3, P4 y frecuencias como 379.250 MHz y 865.250 MHz). Las siguientes imágenes son capturas de pantalla del equipo de medición Viavi ONX-630 de los puertos correspondientes.
                
                Tu tarea es extraer los datos y devolverlos estrictamente en formato JSON válido (un array de objetos), sin texto adicional antes ni después, con esta estructura exacta para cada registro comparado:
                [
                  {
                    "Puerto": "P1",
                    "Frecuencia": 379.25,
                    "Ref_Lapida": 28.2,
                    "Medido_Viavi": 26.5
                  }
                ]
                Extrae toda la información de puertos y frecuencias que logres identificar en ambas fuentes.
                """
                contents.append(prompt)

                response = client.models.generate_content(
                    model="gemini-1.5-flash", contents=contents
                )

                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]

                datos_extraidos = json.loads(texto_respuesta.strip())
                df_res = pd.DataFrame(datos_extraidos)

                # Calcular diferencias y validar tolerancia
                df_res["Diferencia (dB)"] = (
                    df_res["Medido_Viavi"] - df_res["Ref_Lapida"]
                ).round(2)
                df_res["Dif Absoluta"] = df_res["Diferencia (dB)"].abs()
                df_res["Estado"] = df_res["Dif Absoluta"].apply(
                    lambda x: (
                        "✅ En Rango" if x <= tolerancia else "❌ Fuera de Rango"
                    )
                )

                st.success("✨ ¡Extracción y análisis completados con éxito!")

                st.subheader("📊 Tabla Comparativa de Validación")
                st.dataframe(
                    df_res[
                        [
                            "Puerto",
                            "Frecuencia",
                            "Ref_Lapida",
                            "Medido_Viavi",
                            "Diferencia (dB)",
                            "Estado",
                        ]
                    ],
                    use_container_width=True,
                )

                fuera_de_rango = len(
                    df_res[df_res["Estado"] == "❌ Fuera de Rango"]
                )
                if fuera_de_rango > 0:
                    st.error(
                        f"⚠️ El nodo NO APROBÓ. Hay {fuera_de_rango} puntos que superan la tolerancia de ±{tolerancia} dB."
                    )
                else:
                    st.success(
                        "🎉 ¡APROBADO! Todas las mediciones cumplen perfectamente con la lápida."
                    )

            except Exception as e:
                st.error(
                    f"❌ Ocurrió un error al procesar las imágenes con la IA: {e}"
                )
                st.info(
                    "Consejo: Asegúrate de que tu API Key sea correcta y de que las imágenes muestren claramente los números y puertos."
                )
