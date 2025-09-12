# AI Presentation Orchestrator

An intelligent system that converts PDF documents into professional PowerPoint presentations using AI. Upload a PDF document and get a well-structured, visually appealing presentation automatically generated.

## Features

- **PDF Processing**: Extract and analyze content from PDF documents
- **AI-Powered Content Generation**: Uses LangGraph workflow with Groq LLMs
- **Smart Document Summarization**: Comprehensive analysis using Llama models
- **Automatic Presentation Structure**: Creates logical slide outlines
- **Professional Styling**: Clean, business-ready PowerPoint layouts
- **Vector Search**: Retrieves relevant content for each slide using FAISS
- **RESTful API**: Easy integration with web applications
- **Streamlit Frontend**: User-friendly web interface

##  Technology Stack

### Backend
- **FastAPI**: High-performance web framework
- **LangGraph**: Workflow orchestration for AI agents
- **Groq**: Lightning-fast LLM inference
- **LangChain**: Document processing and embeddings
- **FAISS**: Vector similarity search
- **Python-pptx**: PowerPoint generation
- **HuggingFace**: Text embeddings

### Frontend
- **Streamlit**: Interactive web application
- **Requests**: HTTP client for API communication

##  Prerequisites

- Python 3.8+
- Groq API Key (free tier available)
- Git

##  Installation

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd ai-presentation-orchestrator
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

Get your free Groq API key from: https://console.groq.com/

##  Usage

### Running the Backend
```bash
python main.py
```
The API server will start at `http://localhost:8000`

### Running the Frontend
```bash
streamlit run frontend.py
```
The Streamlit app will open at `http://localhost:8501`

##  API Endpoints

### Core Endpoints
- `POST /upload` - Upload and process PDF document
- `POST /generate` - Generate presentation from processed PDF
- `GET /download/{filename}` - Download generated PowerPoint file

### Utility Endpoints
- `GET /` - API information and available endpoints
- `GET /sessions` - List all processing sessions
- `GET /health` - System health check

### API Usage Example
```python
import requests

# Upload PDF
with open('document.pdf', 'rb') as f:
    response = requests.post('http://localhost:8000/upload', files={'file': f})
    session_data = response.json()

# Generate presentation
response = requests.post('http://localhost:8000/generate', 
                        json={'session_id': session_data['session_id']})

# Download PowerPoint
filename = response.json()['metadata']['ppt_file']
ppt_response = requests.get(f'http://localhost:8000/download/{filename}')
```

## 🏗️ Architecture

### LangGraph Workflow
1. **Document Summarization**: Comprehensive analysis using Llama-3.3-70b
2. **Outline Creation**: Structure generation using Llama-3.1-8b-instant  
3. **Content Generation**: Slide content creation with vector-retrieved context

### Document Processing Pipeline
1. **PDF Loading**: Extract text from all pages
2. **Text Chunking**: Split into manageable pieces
3. **Vector Embedding**: Create searchable embeddings
4. **Similarity Search**: Retrieve relevant chunks for each slide

### PowerPoint Generation
- Professional layout with consistent styling
- Blue titles and gray content text
- Automatic bullet point formatting
- Text overflow prevention
- Clean, business-ready design

##  Deployment on Render

### Backend Deployment
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Use the included `render.yml` configuration
4. Set environment variable: `GROQ_API_KEY`

### Frontend Deployment  
1. Create a separate Web Service for Streamlit
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `streamlit run frontend.py --server.port $PORT`
4. Update API URL in frontend to your deployed backend

##  Configuration

### Model Configuration
- **Fast LLM**: `llama-3.1-8b-instant` (outline creation, content generation)
- **Smart LLM**: `llama-3.3-70b-versatile` (document summarization)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`

### Customization Options
- Adjust chunk sizes in `DocumentProcessor`
- Modify slide limits in workflow
- Customize PowerPoint styling in `PowerPointGenerator`
- Change model parameters for different outputs

##  Project Structure
```
├── main.py                 # FastAPI backend application
├── frontend.py             # Streamlit web interface
├── requirements.txt        # Python dependencies
├── render.yml             # Render deployment configuration
├── README.md              # Documentation
└── .env                   # Environment variables (not in repo)
```

##  Troubleshooting

### Common Issues
1. **Groq API Rate Limits**: Free tier has usage limits
2. **PDF Processing Errors**: Ensure PDF is text-extractable
3. **Memory Issues**: Large PDFs may need chunking adjustments
4. **PowerPoint Generation**: Some complex formatting may not render

### Debug Tips
- Check logs in console output
- Use `/health` endpoint to verify system status
- Test with smaller PDF files first
- Ensure all dependencies are installed

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Groq for lightning-fast LLM inference
- LangChain community for document processing tools
- Streamlit for the amazing web framework
- HuggingFace for open-source embeddings

## Support

If you encounter any issues or have questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Open an issue on GitHub
4. Check Groq API status and limits

---

