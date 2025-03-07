import streamlit as st
import base64
import requests
from mistralai import Mistral
from io import BytesIO

# Streamlit Page Config
st.set_page_config(page_title="Mistral OCR Web App", page_icon="📄", layout="centered")

# Title
st.title("📄 Mistral OCR Web App")

# API Key Input
api_key = st.text_input("Enter your Mistral API Key", type="password")

# File Type Selection
file_type = st.radio("Select File Type", ["PDF", "Image"], horizontal=True)

# Source Type Selection
source_type = st.radio("Select Source", ["URL", "Local Upload"], horizontal=True)

# URL Input
input_url = ""
if source_type == "URL":
    input_url = st.text_input("Enter File URL")

# File Upload
uploaded_file = None
if source_type == "Local Upload":
    uploaded_file = st.file_uploader("Upload your file", type=["pdf", "png", "jpg", "jpeg"])

# Process Button
process_btn = st.button("Process Document")

# Initialize Variables
ocr_result = ""
translated_text = ""

# Process File Function
if process_btn:
    if not api_key:
        st.error("Please enter your API key")
    else:
        client = Mistral(api_key=api_key)
        document = {}
        preview_src = None
        
        if source_type == "URL":
            if not input_url:
                st.error("Please enter a valid URL")
            else:
                document = {"type": "document_url", "document_url": input_url} if file_type == "PDF" else {"type": "image_url", "image_url": input_url}
                preview_src = input_url
        else:
            if not uploaded_file:
                st.error("Please upload a file")
            else:
                file_bytes = uploaded_file.getvalue()
                encoded = base64.b64encode(file_bytes).decode("utf-8")
                document = {"type": "document_base64", "document_base64": encoded} if file_type == "PDF" else {"type": "image_url", "image_url": f"data:image/jpeg;base64,{encoded}"}
                preview_src = file_bytes
        
        # Perform OCR
        with st.spinner("Processing document..."):
            try:
                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True
                )
                pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                ocr_result = "\n\n".join(page.markdown for page in pages) or "No result found"
                
                # Display Preview
                if file_type == "PDF":
                    st.write("### Document Preview")
                    st.write("(URL preview not available for PDFs)")
                else:
                    st.image(preview_src, caption="Uploaded Image", use_column_width=True)
                
                st.write("### OCR Result:")
                st.text_area("Extracted Text", ocr_result, height=250)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Translate Button
if st.button("Translate to English"):
    if not ocr_result:
        st.error("No text to translate")
    else:
        with st.spinner("Translating..."):
            try:
                response = client.chat(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": f"Translate the following to English:\n\n{ocr_result}"}]
                )
                translated_text = response.choices[0].message.content
                st.write("### Translated Text:")
                st.text_area("Translation", translated_text, height=250)
            except Exception as e:
                st.error(f"Translation error: {str(e)}")
