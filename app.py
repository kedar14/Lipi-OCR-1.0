import base64
import re
from io import BytesIO
from PIL import Image as PILImage
import streamlit as st
from mistralai import Mistral

# ---- Web App Configuration ----
st.set_page_config(page_title="Mistral OCR & Translation Tool", page_icon="📄", layout="centered")

# ---- Custom Styles (Ancient Yellow Background) ----
st.markdown("""
    <style>
    .stApp { background-color: #FAE6A2; } /* Ancient Yellow */
    .main { text-align: center; }
    .big-font { font-size:20px !important; font-weight: bold; }
    .success-box { border: 2px solid green; padding: 10px; background-color: #e6ffe6; border-radius: 5px; }
    .error-box { border: 2px solid red; padding: 10px; background-color: #ffe6e6; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# ---- Sidebar Inputs ----
st.sidebar.header("🔑 API Configuration")

# Persistent API Key Storage
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""

api_key = st.sidebar.text_input("Enter Mistral API Key", type="password", value=st.session_state["api_key"])

if st.sidebar.button("💾 Save API Key"):
    st.session_state["api_key"] = api_key
    st.success("✅ API Key saved for this session!")

# Auto-initialize Mistral Client
if "client" not in st.session_state and api_key:
    st.session_state["client"] = Mistral(api_key=api_key)

st.sidebar.header("📁 File & Source Selection")
file_type = st.sidebar.radio("Select File Type", ["PDF", "Image"])
source_type = st.sidebar.radio("Choose Input Source", ["URL", "Local Upload"])

# ---- Main Header ----
st.markdown("<h1 class='main big-font'>📄 Mistral OCR & Translation Tool</h1>", unsafe_allow_html=True)

# ---- OCR Input Handling ----
if source_type == "URL":
    input_url = st.text_input("Enter File URL")
    uploaded_file = None
else:
    input_url = None
    uploaded_file = st.file_uploader("Upload File", type=["png", "jpg", "jpeg", "gif", "bmp", "pdf"])

# ---- Process Button ----
if st.button("🚀 Process Document"):
    if not st.session_state["api_key"]:
        st.markdown("<div class='error-box'>❌ Please enter and save a valid API Key.</div>", unsafe_allow_html=True)
    elif source_type == "URL" and not input_url:
        st.markdown("<div class='error-box'>❌ Please enter a valid URL.</div>", unsafe_allow_html=True)
    elif source_type == "Local Upload" and uploaded_file is None:
        st.markdown("<div class='error-box'>❌ Please upload a valid file.</div>", unsafe_allow_html=True)
    else:
        try:
            client = st.session_state["client"]

            # Handle Input Source
            if source_type == "URL":
                document = {"type": "document_url", "document_url": input_url} if file_type == "PDF" else {
                    "type": "image_url",
                    "image_url": input_url,
                }
            else:
                file_bytes = uploaded_file.read()
                encoded_file = base64.b64encode(file_bytes).decode("utf-8")

                if file_type == "PDF":
                    document = {"type": "document_url", "document_url": f"data:application/pdf;base64,{encoded_file}"}
                else:
                    img = PILImage.open(BytesIO(file_bytes))
                    format = img.format.lower()
                    if format not in ["jpeg", "png", "bmp", "gif"]:
                        st.markdown("<div class='error-box'>❌ Unsupported image format.</div>", unsafe_allow_html=True)
                        st.stop()
                    mime_type = f"image/{format}"
                    document = {"type": "image_url", "image_url": f"data:{mime_type};base64,{encoded_file}"}

            # Perform OCR
            with st.spinner("🔍 Processing document..."):
                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True,
                )
                pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                ocr_result = "\n\n".join(page.markdown for page in pages) or "⚠️ No result found"

            # Store OCR result
            st.session_state["ocr_result"] = ocr_result

            # Display OCR Result
            st.markdown("<div class='success-box'><h3>📃 OCR Result:</h3><pre>" + ocr_result + "</pre></div>", unsafe_allow_html=True)

        except Exception as e:
            st.markdown(f"<div class='error-box'>❌ Error: {str(e)}</div>", unsafe_allow_html=True)

# ---- Options After OCR ----
if "ocr_result" in st.session_state:
    action = st.radio("What would you like to do next?", ["🔧 Refine Input Text", "🌎 Translate to English"])

    if action == "🔧 Refine Input Text":
        if st.button("🔧 Refine Text Now"):
            try:
                client = st.session_state["client"]
                with st.spinner("🛠 Refining OCR Text..."):
                    response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[{"role": "user", "content": f"Improve the structure and readability of the following text in its original language without translating it:\n\n{st.session_state['ocr_result']}"}],
                    )
                    refined_text = response.choices[0].message.content

                st.session_state["refined_text"] = refined_text
                st.markdown("<div class='success-box'><h3>📑 Refined OCR Text:</h3><pre>" + refined_text + "</pre></div>", unsafe_allow_html=True)

            except Exception as e:
                st.markdown(f"<div class='error-box'>❌ Refinement error: {str(e)}</div>", unsafe_allow_html=True)

    if action == "🌎 Translate to English":
        if st.button("🌎 Translate Now"):
            try:
                client = st.session_state["client"]
                with st.spinner("🔄 Translating..."):
                    response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[{"role": "user", "content": f"Translate the following text to English:\n\n{st.session_state['ocr_result']}"}],
                    )
                    translated_text = response.choices[0].message.content

                st.session_state["translated_text"] = translated_text
                st.markdown("<div class='success-box'><h3>🌍 Translated Text:</h3><pre>" + translated_text + "</pre></div>", unsafe_allow_html=True)

            except Exception as e:
                st.markdown(f"<div class='error-box'>❌ Translation error: {str(e)}</div>", unsafe_allow_html=True)

# ---- Advanced Process (Summarize in 5 Points) ----
if "translated_text" in st.session_state and st.button("⚡ Advanced Process"):
    try:
        client = st.session_state["client"]
        with st.spinner("🔄 Summarizing text into key points..."):
            response = client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": f"Summarize the following translated text into 5 key bullet points:\n\n{st.session_state['translated_text']}"}],
            )
            summary_text = response.choices[0].message.content

        st.markdown("<div class='success-box'><h3>📌 Key Takeaways:</h3><pre>" + summary_text + "</pre></div>", unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"<div class='error-box'>❌ Summary error: {str(e)}</div>", unsafe_allow_html=True)
