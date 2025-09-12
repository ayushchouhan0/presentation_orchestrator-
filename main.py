import os
import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
from pathlib import Path
import tempfile
import json

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# LangChain imports
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

# PowerPoint generation
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

# State definition for LangGraph
class PresentationState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    document_content: str
    document_chunks: List[str]
    summary: str
    outline: List[Dict[str, str]]
    slides_content: List[Dict[str, Any]]
    session_id: str
    status: str

# Document processor with vectorstore
class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        # Use free HuggingFace embeddings
        self.embeddings = HuggingFaceEndpointEmbeddings(
            model='sentence-transformers/all-mpnet-base-v2',
            task="feature-extraction",
            huggingfacehub_api_token=os.getenv('HUGGINGFACEHUB_API_TOKEN'))
        
        self.vectorstore = None
    
    def process_pdf(self, file_path: str) -> tuple[str, List[str]]:
        """Load PDF and create chunks"""
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Combine all pages
        full_content = "\n".join([doc.page_content for doc in documents])
        
        # Create chunks
        chunks = self.text_splitter.split_text(full_content)
        
        # Create vectorstore
        self.vectorstore = FAISS.from_texts(chunks, self.embeddings)
        
        logger.info(f"PDF processed: {len(chunks)} chunks created")
        return full_content, chunks
    
    def retrieve_relevant_chunks(self, query: str, k: int = 3) -> List[str]:
        """Retrieve relevant chunks using similarity search"""
        if not self.vectorstore:
            return []
        
        docs = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]

# PowerPoint generator
class PowerPointGenerator:
    def __init__(self):
        self.presentation = None
    
    def create_presentation(self, slides_data: List[Dict[str, Any]], title: str = "AI Generated Presentation") -> str:
        """Create PowerPoint presentation from slides data"""
        # Create new presentation
        prs = Presentation()
        
        # Title slide
        title_slide_layout = prs.slide_layouts[0]
        title_slide = prs.slides.add_slide(title_slide_layout)
        title_slide.shapes.title.text = title
        title_slide.placeholders[1].text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Style title slide
        title_shape = title_slide.shapes.title
        for paragraph in title_shape.text_frame.paragraphs:
            paragraph.font.size = Pt(40)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(31, 73, 125)  # Professional blue
        
        subtitle_shape = title_slide.placeholders[1]
        for paragraph in subtitle_shape.text_frame.paragraphs:
            paragraph.font.size = Pt(18)
            paragraph.font.color.rgb = RGBColor(89, 89, 89)  # Gray
        
        # Content slides
        for slide_data in slides_data:
            self._add_content_slide(prs, slide_data)
        
        # Save presentation
        output_path = f"temp_presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        prs.save(output_path)
        
        logger.info(f"PowerPoint created: {output_path}")
        return output_path
    
    def _add_content_slide(self, prs: Presentation, slide_data: Dict[str, Any]):
        """Add a content slide to presentation with simple formatting"""
        # Use title and content layout
        content_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(content_layout)
        
        # Set title
        title = slide.shapes.title
        title.text = slide_data.get("title", "Slide Title")
        
        # Style title
        for paragraph in title.text_frame.paragraphs:
            paragraph.font.size = Pt(32)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(31, 73, 125)  # Professional blue
        
        # Set content
        content_placeholder = slide.placeholders[1]
        raw_content = slide_data.get("content", "")
        formatted_content = self._format_slide_content(raw_content)
        
        # Clear existing content
        content_placeholder.text = ""
        text_frame = content_placeholder.text_frame
        text_frame.clear()
        
        # Add formatted content
        for i, point in enumerate(formatted_content):
            if i == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()
            
            p.text = point
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor(64, 64, 64)  # Dark gray
            p.space_after = Pt(6)
    
    def _format_slide_content(self, content: str) -> List[str]:
        """Format content into clean, readable bullet points"""
        if not content:
            return ["No content available"]
        
        # Clean up the content
        content = content.strip()
        
        # Split into lines and clean up
        lines = content.replace('\n\n', '\n').split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove existing bullet symbols
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                line = line[1:].strip()
            
            # Truncate long lines to prevent overflow
            if len(line) > 100:
                line = line[:97] + "..."
            
            # Add bullet point
            formatted_lines.append(f"• {line}")
        
        # If no proper lines, split by sentences
        if len(formatted_lines) == 0:
            sentences = [s.strip() for s in content.split('.') if s.strip() and len(s.strip()) > 10]
            for sentence in sentences[:5]:  # Max 5 bullets
                if len(sentence) > 100:
                    sentence = sentence[:97] + "..."
                formatted_lines.append(f"• {sentence}.")
        
        # Limit to maximum 6 bullet points
        return formatted_lines[:6]

# LangGraph workflow
class PresentationWorkflow:
    def __init__(self):
        # Use different models for different tasks
        self.fast_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=GROQ_API_KEY,
            temperature=0.3
        )
        self.smart_llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            groq_api_key=GROQ_API_KEY,
            temperature=0.5
        )
        
        self.doc_processor = DocumentProcessor()
        self.ppt_generator = PowerPointGenerator()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the presentation generation workflow"""
        workflow = StateGraph(PresentationState)
        
        # Add nodes
        workflow.add_node("summarize", self.summarize_document)
        workflow.add_node("create_outline", self.create_presentation_outline)  
        workflow.add_node("generate_content", self.generate_slide_content)
        
        # Define flow
        workflow.set_entry_point("summarize")
        workflow.add_edge("summarize", "create_outline")
        workflow.add_edge("create_outline", "generate_content")
        workflow.add_edge("generate_content", END)
        
        return workflow.compile()
    
    def summarize_document(self, state: PresentationState) -> PresentationState:
        """Summarize the entire document using smart LLM"""
        try:
            content = state["document_content"]
            
            # Use smart LLM for comprehensive summarization
            summary_prompt = ChatPromptTemplate.from_template(
                """Analyze the following document and create a comprehensive summary that captures:
1. Main topic and purpose
2. Key findings or arguments
3. Important data points or evidence
4. Conclusions or recommendations

Document:
{content}

Provide a detailed summary in 300-500 words that will serve as the foundation for creating a presentation."""
            )
            
            # Truncate content if too long (roughly 8000 tokens for safety)
            truncated_content = content[:32000] if len(content) > 32000 else content
            
            response = self.smart_llm.invoke(
                summary_prompt.format(content=truncated_content)
            )
            
            state["summary"] = response.content
            state["status"] = "summarized"
            logger.info("Document summarized successfully")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            state["status"] = "error"
            return state
    
    def create_presentation_outline(self, state: PresentationState) -> PresentationState:
        """Create presentation structure using fast LLM"""
        try:
            summary = state["summary"]
            
            outline_prompt = ChatPromptTemplate.from_template(
                """Based on this document summary, create a presentation outline with 8-12 slides.

Summary:
{summary}

Return ONLY a JSON array with this exact format:
[
  {{"title": "Introduction", "description": "Overview of the topic", "slide_type": "intro"}},
  {{"title": "Background", "description": "Context and background", "slide_type": "content"}},
  {{"title": "Key Findings", "description": "Main discoveries", "slide_type": "content"}},
  {{"title": "Conclusion", "description": "Summary and next steps", "slide_type": "conclusion"}}
]

Include variety: intro slide, 6-10 content slides covering main points, conclusion slide.
Each title should be concise (2-6 words). Descriptions should be brief (5-10 words)."""
            )
            
            response = self.fast_llm.invoke(
                outline_prompt.format(summary=summary)
            )
            
            # Parse JSON response
            try:
                parser = JsonOutputParser()
                outline = parser.parse(response.content)
                
                # Validate and ensure we have reasonable number of slides
                if not isinstance(outline, list) or len(outline) < 5:
                    raise ValueError("Invalid outline format")
                    
                state["outline"] = outline[:12]  # Max 12 slides
                
            except Exception as parse_error:
                logger.warning(f"JSON parsing failed: {parse_error}, using fallback")
                # Fallback outline
                state["outline"] = [
                    {"title": "Introduction", "description": "Document overview", "slide_type": "intro"},
                    {"title": "Background", "description": "Context and setting", "slide_type": "content"}, 
                    {"title": "Main Points", "description": "Key information", "slide_type": "content"},
                    {"title": "Analysis", "description": "Detailed examination", "slide_type": "content"},
                    {"title": "Findings", "description": "Important discoveries", "slide_type": "content"},
                    {"title": "Implications", "description": "What this means", "slide_type": "content"},
                    {"title": "Recommendations", "description": "Suggested actions", "slide_type": "content"},
                    {"title": "Conclusion", "description": "Summary and next steps", "slide_type": "conclusion"}
                ]
            
            state["status"] = "outlined"
            logger.info(f"Outline created with {len(state['outline'])} slides")
            
            return state
            
        except Exception as e:
            logger.error(f"Error creating outline: {e}")
            state["status"] = "error"
            return state
    
    def generate_slide_content(self, state: PresentationState) -> PresentationState:
        """Generate content for each slide using retrieved chunks"""
        try:
            outline = state["outline"]
            slides_content = []
            
            content_prompt = ChatPromptTemplate.from_template(
                """Create slide content for this presentation slide:

Title: {title}
Description: {description}
Relevant Information: {context}

Generate clear, concise slide content with:
- 3-5 bullet points or key statements
- Professional language suitable for presentation
- Specific details from the relevant information when applicable
- Appropriate length for a slide (100-200 words)

Format as readable text suitable for PowerPoint. Use bullet points or clear paragraphs."""
            )
            
            for slide_info in outline:
                title = slide_info["title"]
                description = slide_info["description"]
                
                # Retrieve relevant chunks for this slide topic
                query = f"{title} {description}"
                relevant_chunks = self.doc_processor.retrieve_relevant_chunks(query, k=3)
                context = "\n".join(relevant_chunks) if relevant_chunks else state["summary"]
                
                # Generate content using fast LLM
                response = self.fast_llm.invoke(
                    content_prompt.format(
                        title=title,
                        description=description,
                        context=context[:2000]  # Limit context length
                    )
                )
                
                slide_content = {
                    "title": title,
                    "content": response.content.strip(),
                    "slide_type": slide_info.get("slide_type", "content")
                }
                
                slides_content.append(slide_content)
            
            state["slides_content"] = slides_content
            state["status"] = "completed"
            logger.info(f"Generated content for {len(slides_content)} slides")
            
            return state
            
        except Exception as e:
            logger.error(f"Error generating slide content: {e}")
            state["status"] = "error"
            return state

# Main orchestrator
class PresentationOrchestrator:
    def __init__(self):
        self.workflow = PresentationWorkflow()
        self.sessions = {}
    
    def process_pdf(self, file_path: str, session_id: str) -> Dict[str, Any]:
        """Process PDF document"""
        try:
            content, chunks = self.workflow.doc_processor.process_pdf(file_path)
            
            self.sessions[session_id] = {
                "content": content,
                "chunks": chunks,
                "processed_at": datetime.now(),
                "file_path": file_path
            }
            
            return {
                "status": "success",
                "message": "PDF processed successfully", 
                "content_length": len(content),
                "chunks_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def generate_presentation(self, session_id: str) -> tuple[str, Dict[str, Any]]:
        """Generate presentation and return PowerPoint file path"""
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = self.sessions[session_id]
        
        # Initial state
        initial_state = PresentationState(
            messages=[],
            document_content=session_data["content"],
            document_chunks=session_data["chunks"], 
            summary="",
            outline=[],
            slides_content=[],
            session_id=session_id,
            status="started"
        )
        
        try:
            logger.info(f"Starting presentation generation for session {session_id}")
            
            # Run the workflow
            final_state = self.workflow.graph.invoke(initial_state)
            
            if final_state["status"] != "completed":
                raise HTTPException(
                    status_code=500,
                    detail=f"Generation failed at status: {final_state['status']}"
                )
            
            # Create PowerPoint
            ppt_path = self.workflow.ppt_generator.create_presentation(
                final_state["slides_content"],
                title="AI Generated Presentation"
            )
            
            result_data = {
                "slides": final_state["slides_content"],
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_slides": len(final_state["slides_content"]),
                    "session_id": session_id,
                    "ppt_file": ppt_path
                }
            }
            
            logger.info(f"Presentation generated: {len(final_state['slides_content'])} slides")
            return ppt_path, result_data
            
        except Exception as e:
            logger.error(f"Error generating presentation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# FastAPI setup
app = FastAPI(
    title="Simple AI Presentation Orchestrator",
    description="Generate PowerPoint presentations from PDF documents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = PresentationOrchestrator()

# Pydantic models
class GenerateRequest(BaseModel):
    session_id: str

# API Routes
@app.get("/")
async def root():
    return {
        "message": "Simple AI Presentation Orchestrator",
        "version": "1.0.0",
        "endpoints": ["/upload", "/generate", "/download/{filename}", "/health"]
    }

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate session ID
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        result = orchestrator.process_pdf(tmp_file_path, session_id)
        result["session_id"] = session_id
        return result
        
    except Exception as e:
        # Clean up temp file
        Path(tmp_file_path).unlink(missing_ok=True)
        raise e

@app.post("/generate")
async def generate_presentation(request: GenerateRequest):
    """Generate presentation from processed PDF"""
    ppt_path, result_data = orchestrator.generate_presentation(request.session_id)
    return result_data

@app.get("/download/{filename}")
async def download_presentation(filename: str):
    """Download generated PowerPoint file"""
    file_path = Path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

@app.get("/sessions")
async def list_sessions():
    """List all sessions"""
    sessions_info = {}
    for session_id, data in orchestrator.sessions.items():
        sessions_info[session_id] = {
            "processed_at": data["processed_at"].isoformat(),
            "content_length": len(data["content"]),
            "chunks_count": len(data["chunks"])
        }
    return {"sessions": sessions_info}

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        test_response = orchestrator.workflow.fast_llm.invoke("test")
        llm_status = "healthy"
    except Exception as e:
        llm_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "healthy",
            "llm": llm_status,
            "sessions": len(orchestrator.sessions)
        },
        "models": {
            "fast": "llama-3.1-8b-instant",
            "smart": "llama-3.3-70b-versatile"
        }
    }

if __name__ == "__main__":
    logger.info("Starting Simple AI Presentation Orchestrator...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

