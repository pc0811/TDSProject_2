from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import zipfile
import os
import requests
import base64
from docx import Document
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Constants
AIPROXY_URL = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")  # Ensure this is in your .env file

def extract_file_content(file_path: str) -> str:
    """
    Extracts content from various file types (CSV, XLSX, DOCX, PDF, images, ZIP, etc.).
    """
    try:
        if file_path.endswith(".csv"):
            # Read CSV file
            df = pd.read_csv(file_path)
            return df.to_string()
        elif file_path.endswith(".xlsx"):
            # Read Excel file
            df = pd.read_excel(file_path)
            return df.to_string()
        elif file_path.endswith(".docx"):
            # Read DOCX file
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        elif file_path.endswith(".pdf"):
            # Read PDF file
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        elif file_path.endswith((".png", ".jpg", ".jpeg")):
            # Encode image to base64
            with open(file_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        elif file_path.endswith(".zip"):
            # Extract ZIP file and process contents
            extracted_content = []
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall("extracted_files")
                for root, _, files in os.walk("extracted_files"):
                    for file in files:
                        file_path = os.path.join(root, file)
                        extracted_content.append(extract_file_content(file_path))
            return "\n".join(extracted_content)
        else:
            # Handle unsupported file types
            raise ValueError(f"Unsupported file type: {file_path}")
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
                "content": "You are a helpful assistant that provides detailed and accurate responses."
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

def process_question(question: str, file_path: str = None):
    """
    Process the question and file (if any) to generate an answer.
    """
    try:
        file_content = None
        is_image = False

        if file_path:
            # Check if the file is an image
            if file_path.endswith((".png", ".jpg", ".jpeg")):
                is_image = True
            # Extract content for all file types
            file_content = extract_file_content(file_path)

        # Use ai_proxy_llm to answer the question
        return requestLLM(question, file_content, is_image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/")
async def answer_question(
    question: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        file_path = None
        if file:
            # Save the uploaded file temporarily
            file_path = f"temp_{file.filename}"
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())

        # Process the question and file
        answer = process_question(question, file_path)

        # Clean up temporary files
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            if os.path.exists("extracted_files"):
                for root, dirs, files in os.walk("extracted_files", topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir("extracted_files")

        return JSONResponse(content={"answer": answer})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
