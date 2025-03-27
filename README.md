# TDSProject_2 - FastAPI LLM Integration with File Processing

## API Endpoint
POST `/api` - Process questions with optional file attachments

## Authentication
Requires `AIPROXY_TOKEN` in environment variables

## Sample cURL Requests

### 1. Text-only Question
```bash
curl -X POST "https://your-deployment-url/api" \
  -H "Content-Type: multipart/form-data" \
  -F "question=Explain linear regression in simple terms"
```

### 1. With-File Questions
```bash
curl -X POST "https://your-deployment-url/api" \
  -H "Content-Type: multipart/form-data" \
  -F "question=Analyze this sales data" \
  -F "file=@sales_data.csv"
