import streamlit as st
import requests
import time
from datetime import datetime
from pathlib import Path
import io

# Page configuration
st.set_page_config(
    page_title="AI Presentation Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_URL = API_URL

# Custom CSS for elegant styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1f2937;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-card {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    .success-box {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #065f46;
    }
    .error-box {
        background: #fef2f2;
        border: 1px solid #fca5a5;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #991b1b;
    }
    .info-box {
        background: #eff6ff;
        border: 1px solid #93c5fd;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'upload_status' not in st.session_state:
        st.session_state.upload_status = None
    if 'generation_status' not in st.session_state:
        st.session_state.generation_status = None
    if 'presentation_data' not in st.session_state:
        st.session_state.presentation_data = None
    if 'ppt_filename' not in st.session_state:
        st.session_state.ppt_filename = None

def make_api_request(method, endpoint, data=None, files=None):
    """Make API request with error handling"""
    try:
        url = f"{API_URL}{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url, timeout=30)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, files=files, timeout=120)
            else:
                response = requests.post(url, json=data, timeout=120)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"API Error ({response.status_code}): {response.text}"
            
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API server. Please ensure it's running on localhost:8000"
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again."
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    init_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">AI Presentation Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform PDF documents into professional PowerPoint presentations</p>', unsafe_allow_html=True)
    
    # Sidebar with system status
    with st.sidebar:
        st.header("System Status")
        
        # Check API health
        success, health_data = make_api_request("GET", "/health")
        
        if success:
            st.success("API Online")
            
            components = health_data.get("components", {})
            if components.get("llm") == "healthy":
                st.success("LLM Ready")
            else:
                st.error(f"LLM: {components.get('llm', 'Unknown')}")
            
            models = health_data.get("models", {})
            st.info(f"Fast Model: {models.get('fast', 'N/A')}")
            st.info(f"Smart Model: {models.get('smart', 'N/A')}")
            
            st.caption(f"Last check: {datetime.now().strftime('%H:%M:%S')}")
        else:
            st.error("API Offline")
            st.error(health_data)
        
        st.markdown("---")
        
        # Session info
        if st.session_state.current_session_id:
            st.header("Current Session")
            st.text(f"ID: {st.session_state.current_session_id}")
            
            if st.button("Clear Session", use_container_width=True):
                st.session_state.current_session_id = None
                st.session_state.upload_status = None
                st.session_state.generation_status = None
                st.session_state.presentation_data = None
                st.session_state.ppt_filename = None
                st.rerun()

    # Main content
    tab1, tab2, tab3 = st.tabs(["Upload & Generate", "View Results", "Instructions"])
    
    with tab1:
        st.header("Step 1: Upload PDF Document")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Select a PDF document to convert into a presentation"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Upload & Process PDF", 
                        type="primary", 
                        disabled=not uploaded_file,
                        use_container_width=True):
                
                if uploaded_file:
                    with st.spinner("Processing PDF document..."):
                        # Prepare file for upload
                        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')}
                        
                        success, result = make_api_request("POST", "/upload", files=files)
                        
                        if success:
                            st.session_state.current_session_id = result.get("session_id")
                            st.session_state.upload_status = result
                            
                            st.markdown('<div class="success-box">PDF processed successfully!</div>', unsafe_allow_html=True)
                            
                            # Show processing stats
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Content Length", f"{result.get('content_length', 0):,} chars")
                            with col_b:
                                st.metric("Document Chunks", result.get('chunks_count', 0))
                                
                        else:
                            st.error(result)
        
        with col2:
            generate_disabled = not st.session_state.current_session_id
            button_text = "Generate Presentation"
            if generate_disabled:
                button_text += " (Upload PDF first)"
            
            if st.button(button_text,
                        type="secondary", 
                        disabled=generate_disabled,
                        use_container_width=True):
                
                with st.spinner("Generating presentation... This may take 2-3 minutes."):
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    steps = [
                        "Analyzing document content...",
                        "Creating comprehensive summary...",
                        "Generating presentation outline...", 
                        "Creating slide content...",
                        "Building PowerPoint file...",
                        "Finalizing presentation..."
                    ]
                    
                    for i, step in enumerate(steps[:-1]):
                        status_text.text(step)
                        progress_bar.progress(int((i + 1) / len(steps) * 80))
                        time.sleep(1)
                    
                    # Make generation request
                    success, result = make_api_request(
                        "POST", 
                        "/generate",
                        {"session_id": st.session_state.current_session_id}
                    )
                    
                    status_text.text(steps[-1])
                    progress_bar.progress(100)
                    time.sleep(0.5)
                    
                    # Clear progress
                    progress_bar.empty()
                    status_text.empty()
                    
                    if success:
                        st.session_state.generation_status = "success"
                        st.session_state.presentation_data = result
                        st.session_state.ppt_filename = result["metadata"]["ppt_file"]
                        
                        st.markdown('<div class="success-box">Presentation generated successfully!</div>', unsafe_allow_html=True)
                        st.balloons()
                        
                        # Show generation stats
                        metadata = result["metadata"]
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Total Slides", metadata["total_slides"])
                        with col_b:
                            st.metric("Generated At", metadata["generated_at"][:16])
                        with col_c:
                            # Download button
                            ppt_file = metadata["ppt_file"]
                            download_url = f"{API_URL}/download/{ppt_file}"
                            st.markdown(f'<a href="{download_url}" target="_blank"><button style="background:#3b82f6;color:white;border:none;padding:0.5rem 1rem;border-radius:0.25rem;cursor:pointer;">Download PowerPoint</button></a>', unsafe_allow_html=True)
                            
                    else:
                        st.error(result)
        
        # Show upload status
        if st.session_state.upload_status:
            st.markdown("---")
            with st.expander("Processing Details", expanded=False):
                st.json(st.session_state.upload_status)

    with tab2:
        if st.session_state.presentation_data:
            display_results()
        else:
            st.markdown('<div class="info-box">No presentation data available. Please generate a presentation first.</div>', unsafe_allow_html=True)
            
            # Instructions for getting started
            st.markdown("### How to Get Started:")
            st.markdown("1. **Upload a PDF document** in the 'Upload & Generate' tab")
            st.markdown("2. **Process the document** to extract and analyze content")  
            st.markdown("3. **Generate presentation** using AI workflow")
            st.markdown("4. **Download PowerPoint file** and view results here")

    with tab3:
        st.header("Instructions & Features")
        
        st.markdown("### System Overview")
        st.markdown("This AI presentation orchestrator uses LangGraph workflows and multiple LLMs to transform PDF documents into professional PowerPoint presentations.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Workflow Steps")
            st.markdown("1. **Document Processing**: PDF is loaded and split into chunks")
            st.markdown("2. **Vector Storage**: Chunks are embedded and stored for retrieval")
            st.markdown("3. **Summarization**: Smart LLM creates comprehensive document summary")
            st.markdown("4. **Outline Creation**: Fast LLM generates presentation structure")
            st.markdown("5. **Content Generation**: Relevant chunks are retrieved for each slide")
            st.markdown("6. **PowerPoint Creation**: Professional slides are generated with python-pptx")
        
        with col2:
            st.markdown("### AI Models Used")
            st.markdown("- **llama-3.3-70b-versatile**: Document summarization (high quality)")
            st.markdown("- **llama-3.1-8b-instant**: Outline and content generation (fast)")
            st.markdown("- **HuggingFace Embeddings**: Semantic search and retrieval")
            
            st.markdown("### File Support")
            st.markdown("- **Input**: PDF documents only")
            st.markdown("- **Output**: PowerPoint (.pptx) presentations")
            st.markdown("- **Slide Count**: Typically 8-12 slides")

def display_results():
    """Display generated presentation results"""
    data = st.session_state.presentation_data
    metadata = data["metadata"]
    slides = data["slides"]
    
    st.header("Generated Presentation")
    
    # Metadata display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Slides", metadata["total_slides"])
    with col2:
        st.metric("Generated At", metadata["generated_at"][:16])
    with col3:
        # Main download button
        if st.session_state.ppt_filename:
            ppt_file = st.session_state.ppt_filename
            download_url = f"{API_URL}/download/{ppt_file}"
            st.markdown(f'<a href="{download_url}" target="_blank"><button style="background:#059669;color:white;border:none;padding:0.75rem 1.5rem;border-radius:0.5rem;cursor:pointer;font-weight:600;">Download PowerPoint</button></a>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Export options
    st.subheader("Export Options")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.ppt_filename:
            ppt_file = st.session_state.ppt_filename
            download_url = f"{API_URL}/download/{ppt_file}"
            st.markdown(f'<a href="{download_url}" target="_blank"><button style="background:#3b82f6;color:white;border:none;padding:0.5rem 1rem;border-radius:0.25rem;cursor:pointer;">PowerPoint File</button></a>', unsafe_allow_html=True)
    
    with col2:
        # JSON export
        import json
        json_data = json.dumps(data, indent=2, default=str)
        st.download_button(
            "Download JSON",
            json_data,
            f"presentation_{metadata['generated_at'][:10]}.json",
            "application/json",
            use_container_width=True
        )
    
    with col3:
        # Text export
        text_export = f"# Presentation Export\n\n"
        text_export += f"Generated: {metadata['generated_at']}\n"
        text_export += f"Total Slides: {metadata['total_slides']}\n\n"
        
        for i, slide in enumerate(slides, 1):
            text_export += f"## Slide {i}: {slide['title']}\n\n"
            text_export += f"{slide['content']}\n\n"
            text_export += "---\n\n"
        
        st.download_button(
            "Download Text",
            text_export,
            f"presentation_{metadata['generated_at'][:10]}.txt",
            "text/plain",
            use_container_width=True
        )
    
    with col4:
        if st.button("Generate New", use_container_width=True):
            st.session_state.presentation_data = None
            st.session_state.generation_status = None
            st.rerun()
    
    st.markdown("---")
    
    # Display slides
    st.subheader("Presentation Slides")
    
    # Slide navigation
    slide_options = ["All Slides"] + [f"Slide {i+1}: {slide['title']}" for i, slide in enumerate(slides)]
    selected_view = st.selectbox("View:", slide_options)
    
    if selected_view == "All Slides":
        # Display all slides
        for i, slide in enumerate(slides, 1):
            display_slide(i, slide)
    else:
        # Display selected slide
        slide_index = slide_options.index(selected_view) - 1
        display_slide(slide_index + 1, slides[slide_index], expanded=True)

def display_slide(slide_num, slide_data, expanded=False):
    """Display individual slide"""
    with st.container():
        # Slide header
        st.markdown(f"#### Slide {slide_num}: {slide_data['title']}")
        
        # Content
        with st.expander("Content", expanded=expanded):
            st.markdown("**Slide Content:**")
            st.write(slide_data['content'])
        
        # Slide type info
        slide_type = slide_data.get('slide_type', 'content')
        if slide_type == 'intro':
            st.info("Type: Introduction Slide")
        elif slide_type == 'conclusion':
            st.info("Type: Conclusion Slide") 
        else:
            st.info("Type: Content Slide")
        
        st.markdown("---")

if __name__ == "__main__":

    main()
