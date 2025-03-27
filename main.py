from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import zipfile
import io
import requests
import base64
from docx import Document
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()

# Constants
AIPROXY_URL = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")  # Ensure this is in your .env file

def extract_file_content(file: UploadFile) -> str:
    """
    Extracts content from various file types (CSV, XLSX, DOCX, PDF, images, ZIP, etc.).
    """
    try:
        file_content = file.file.read()

        if file.filename.endswith(".csv"):
            # Read CSV file
            df = pd.read_csv(io.BytesIO(file_content))
            return df.to_string()
        elif file.filename.endswith(".xlsx"):
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))
            return df.to_string()
        elif file.filename.endswith(".docx"):
            # Read DOCX file
            doc = Document(io.BytesIO(file_content))
            return "\n".join([para.text for para in doc.paragraphs])
        elif file.filename.endswith(".pdf"):
            # Read PDF file
            reader = PdfReader(io.BytesIO(file_content))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        elif file.filename.endswith((".png", ".jpg", ".jpeg")):
            # Encode image to base64
            return base64.b64encode(file_content).decode("utf-8")
        elif file.filename.endswith(".zip"):
            # Extract ZIP file and process contents
            extracted_content = []
            with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    with zip_ref.open(file_name) as extracted_file:
                        extracted_content.append(extract_file_content(extracted_file))
            return "\n".join(extracted_content)
        else:
            # Handle unsupported file types
            raise ValueError(f"Unsupported file type: {file.filename}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting file content: {str(e)}")

def requestLLM(prompt: str, file_content: str = None, is_image: bool = False) -> str:
    """
    Sends a request to the ai_proxy_llm for text or file-based tasks.
    """
    try:
        # Prepare the payload
       messages = [
    {
        "role": "system",
        "content": """You are an advanced technical assistant specializing in:
1. LLM API integration (Python requests, authentication, payload formatting)
2. Excel data analytics (Pandas, OpenPyXL, XlsxWriter)
3. Formula implementation (VLOOKUP, INDEX-MATCH, array formulas)
4. Statistical calculations (Regression, Forecasting, Descriptive Stats)
5. Data visualization (Charts, PivotTables, Conditional Formatting)
6. UVicorn server configuration (Host/port settings, SSL, workers)
7. CORS management (Origin whitelisting, middleware configuration)
8. Data processing (Cleaning, Transformation, Feature Engineering)
9. Python automation (Scripting, Batch Processing)
10. API best practices (Error handling, Rate limiting, Documentation)

Guidelines:
- Provide executable Python code snippets
- Explain Excel formulas with examples
- Include error handling patterns
- Suggest optimization techniques
- Offer alternative approaches"""
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt
            }
        ]
    }
]

        # Add file content
        if file_content:
            if is_image:
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{file_content}"
                    }
                })
            else:
                messages[1]["content"].append({
                    "type": "text",
                    "text": f"Here is the content of the file:\n{file_content}"
                })

        payload = {
            "model": "gpt-4o-mini",
            "messages": messages
        }

        # Set headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AIPROXY_TOKEN}"
        }

        # Send the request to the LLM
        response = requests.post(AIPROXY_URL, headers=headers, json=payload)

        # Handle the response
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api")
async def answer_question(
    question: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        file_content = None
        is_image = False

        if file:
            # Check if the file is an image
            if file.filename.endswith((".png", ".jpg", ".jpeg")):
                is_image = True
            # Extract content for all file types
            file_content = extract_file_content(file)

        # Use ai_proxy_llm to answer the question
        answer = requestLLM(question, file_content, is_image)

        return JSONResponse(content={"answer": answer})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
