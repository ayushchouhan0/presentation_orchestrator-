import streamlit as st
import requests
import time
from datetime import datetime
from pathlib import Path
import io
import json

# Page configuration
st.set_page_config(
    page_title="AI Presentation Generator",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_URL = "http://localhost:8000"

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
    .warning-box {
        background: #fffbeb;
        border: 1px solid #fcd34d;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #92400e;
    }
    .progress-container {
        background: #f9fafb;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
        margin: 1rem 0;
    }
    .slide-preview {
        background: #ffffff;
        border: 2px solid #e5e7eb;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .slide-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f4985;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 0.5rem;
    }
    .content-block {
        margin: 0.75rem 0;
        padding: 0.5rem;
        border-radius: 0.25rem;
    }
    .content-heading {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1f4985;
        margin: 0.5rem 0;
    }
    .content-paragraph {
        font-size: 1rem;
        color: #374151;
        line-height: 1.6;
        margin: 0.5rem 0;
    }
    .content-bullet {
        font-size: 0.95rem;
        color: #374151;
        margin: 0.25rem 0 0.25rem 1rem;
    }
    .content-quote {
        font-size: 1rem;
        font-style: italic;
        color: #4472ca;
        text-align: center;
        border-left: 4px solid #3b82f6;
        padding-left: 1rem;
        margin: 1rem 0;
    }
    .enhancement-badge {
        background: linear-gradient(45deg, #3b82f6, #10b981);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
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
    if 'async_generation_active' not in st.session_state:
        st.session_state.async_generation_active = False
    if 'generation_completed' not in st.session_state:
        st.session_state.generation_completed = False

def make_api_request(method, endpoint, data=None, files=None):
    """Make API request with error handling and appropriate timeouts"""
    try:
        url = f"{API_URL}{endpoint}"
        
        # Set timeout based on endpoint
        if endpoint == "/generate":
            timeout = 600  # 10 minutes for synchronous generation
        elif endpoint.startswith("/generate_async"):
            timeout = 30   # Quick start for async generation
        elif files:
            timeout = 300  # 5 minutes for file upload
        else:
            timeout = 30   # 30 seconds for other requests
        
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, files=files, timeout=timeout)
            else:
                response = requests.post(url, json=data, timeout=timeout)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"API Error ({response.status_code}): {response.text}"
            
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API server. Please ensure it's running on localhost:8000"
    except requests.exceptions.Timeout:
        return False, f"Request timed out after {timeout} seconds. The process may still be running in the background."
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_api_capabilities():
    """Check if API supports enhanced generation"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("version", "1.0.0").startswith("2."), data.get("features", [])
    except:
        pass
    return False, []

def handle_sync_generation(session_id):
    """Handle synchronous generation with enhanced progress tracking"""
    
    with st.spinner("Generating enhanced presentation... This may take 5-10 minutes."):
        # Enhanced progress simulation
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            "Analyzing document content...",
            "Creating comprehensive summary...",
            "Generating presentation outline...", 
            "Processing slide 1-3 with styling...",
            "Processing slide 4-6 with styling...",
            "Processing slide 7-10 with styling...",
            "Building enhanced PowerPoint file...",
            "Applying professional formatting...",
            "Finalizing styled presentation..."
        ]
        
        # Simulate progress for first few steps
        for i, step in enumerate(steps[:-3]):
            status_text.text(step)
            progress_bar.progress(int((i + 1) / len(steps) * 50))
            time.sleep(0.8)
        
        status_text.text("Generating enhanced slides with styling... (This takes the longest)")
        progress_bar.progress(60)
        
        # Make generation request with extended timeout
        success, result = make_api_request(
            "POST", 
            "/generate",
            {"session_id": session_id}
        )
        
        # Complete progress
        for i, step in enumerate(steps[-3:]):
            status_text.text(step)
            progress_bar.progress(70 + (i + 1) * 10)
            time.sleep(0.5)
        
        # Clear progress UI
        progress_bar.empty()
        status_text.empty()
        
        if success:
            st.session_state.generation_status = "success"
            st.session_state.presentation_data = result
            st.session_state.generation_completed = True  # Mark as completed
            
            # Check if enhanced
            is_enhanced = result.get("metadata", {}).get("enhanced", False)
            
            if is_enhanced:
                st.markdown(
                    '<div class="success-box"> Enhanced presentation generated successfully with professional styling!</div>', 
                    unsafe_allow_html=True
                )
                st.markdown('<span class="enhancement-badge">Enhanced v2.0</span>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="success-box">Presentation generated successfully!</div>', 
                    unsafe_allow_html=True
                )
            
            st.balloons()
            
            # Show generation stats
            metadata = result.get("metadata", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Slides", metadata.get("total_slides", "N/A"))
            with col2:
                st.metric("Generated At", metadata.get("generated_at", "")[:16])
            with col3:
                session_id_val = metadata.get("session_id")
                if session_id_val:
                    download_url = f"{API_URL}/download_ppt/{session_id_val}"
                    st.markdown(
                        f'<a href="{download_url}" target="_blank">'
                        '<button style="background:#059669;color:white;border:none;'
                        'padding:0.75rem 1.5rem;border-radius:0.5rem;cursor:pointer;font-weight:600;">'
                        ' Download Enhanced PPT</button></a>',
                        unsafe_allow_html=True
                    )
            return True
        else:
            st.error(f"Generation failed: {result}")
            return False

def main():
    init_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">AI Presentation Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform PDF documents into professionally styled PowerPoint presentations</p>', unsafe_allow_html=True)


    
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
            
            
            # Show enhanced features
            features = health_data.get("features", [])
            if features:
                st.markdown("**Features:**")
                for feature in features:
                    st.markdown(f"• {feature}")
            
            st.caption(f"Last check: {datetime.now().strftime('%H:%M:%S')}")
        else:
            st.error("API Offline")
            st.error(health_data)
        
        st.markdown("---")
        
        # Session info
        if st.session_state.current_session_id:
            st.header("Current Session")
            st.text(f"ID: {st.session_state.current_session_id}")
            
            # Show generation status
            if st.session_state.generation_completed:
                st.success("Presentation Ready")
            elif st.session_state.generation_status == "success":
                st.success("Generation Complete")
            
            if st.button("Clear Session", use_container_width=True):
                st.session_state.current_session_id = None
                st.session_state.upload_status = None
                st.session_state.generation_status = None
                st.session_state.presentation_data = None
                st.session_state.ppt_filename = None
                st.session_state.generation_completed = False
                st.rerun()

    # Main content
    if st.session_state.generation_completed and st.session_state.presentation_data:
        # Show results directly when generation is complete
        display_enhanced_results()
    else:
        # Show upload and generate interface
        tab1, tab2, tab3 = st.tabs(["Upload & Generate", "View Results", "Instructions"])
        
        with tab1:
            st.header("Step 1: Upload PDF Document")
            
            # File upload
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=['pdf'],
                help="Select a PDF document to convert into a styled presentation"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(" Upload & Process PDF", 
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
                                st.session_state.generation_completed = False  # Reset generation status
                                
                                st.markdown('<div class="success-box"> PDF processed successfully!</div>', unsafe_allow_html=True)
                                
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
                button_text = " Generate Presentation"
                if generate_disabled:
                    button_text += " (Upload PDF first)"
                
                if st.button(button_text,
                            type="secondary", 
                            disabled=generate_disabled,
                            use_container_width=True):
                    
                    session_id = st.session_state.current_session_id
                    success = handle_sync_generation(session_id)
                    
                    if success:
                        st.rerun()

            # Show upload status
            if st.session_state.upload_status:
                st.markdown("---")
                with st.expander("Processing Details", expanded=False):
                    st.json(st.session_state.upload_status)

        with tab2:
            if st.session_state.presentation_data:
                display_enhanced_results()
            else:
                st.markdown('<div class="info-box">No presentation data available. Please generate a presentation first.</div>', unsafe_allow_html=True)
                
                # Instructions for getting started
                st.markdown("### How to Get Started:")
                st.markdown("1. **Upload a PDF document** in the 'Upload & Generate' tab")
                st.markdown("2. **Process the document** to extract and analyze content")  
                st.markdown("3. **Generate presentation** using AI workflow with styling")
                st.markdown("4. **Download styled PowerPoint file** and view results here")

        with tab3:
            st.header("Features & Instructions")
            
            st.markdown("### System Overview")
            st.markdown("This AI presentation orchestrator uses advanced LangGraph workflows and multiple LLMs to transform PDF documents into professionally styled PowerPoint presentations with mixed content types and proper formatting.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Workflow Steps")
                st.markdown("1. **Document Processing**: PDF is loaded and split into semantic chunks")
                st.markdown("2. **Vector Storage**: Chunks are embedded for intelligent retrieval")
                st.markdown("3. **Smart Summarization**: High-quality LLM creates comprehensive summary")
                st.markdown("4. **Structured Outline**: Fast LLM generates presentation architecture")
                st.markdown("5. **Styled Content Generation**: Mixed content types with styling metadata")
                st.markdown("6. **PowerPoint**: Professional slides with proper formatting")
            
            with col2:
                st.markdown("### Features")
                st.markdown("- **Mixed Content Types**: Headings, paragraphs, bullet points, quotes")
                st.markdown("- **Professional Styling**: Font sizes, weights, colors, alignment")  
                st.markdown("- **Character Encoding Fixes**: No more garbled bullet points")
                st.markdown("- **JSON Structure**: Structured content with styling metadata")
                st.markdown("- **Visual Hierarchy**: Proper heading levels and spacing")
                st.markdown("- **Improved Layouts**: Better slide organization and flow")
            
            # Performance expectations
            st.markdown("---")
            st.markdown("### Performance & Quality")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Generation Time**: 5-10 minutes typical")
                st.markdown("**Document Size**: Works best with documents under 50 pages")
                st.markdown("**Output Quality**: Professional presentation format")
            with col2:
                st.markdown("**Content Variety**: Mixed formatting types")
                st.markdown("**Styling**: Consistent professional appearance")
                st.markdown("**Format Support**: .pptx with proper encoding")

def display_enhanced_results():
    """Display presentation results with proper styling preview"""
    data = st.session_state.presentation_data
    metadata = data.get("metadata", {})
    slides = data.get("slides", [])
    
    st.header("Presentation Results")
    
    # Check if enhanced
    is_enhanced = metadata.get("enhanced", False)
    if is_enhanced:
        st.markdown('<span class="enhancement-badge">Enhanced v2.0</span>', unsafe_allow_html=True)
    
    # Metadata display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Slides", metadata.get("total_slides", "N/A"))
    with col2:
        st.metric("Generated At", metadata.get("generated_at", "")[:16])
    with col3:
        # Main download button using session_id
        session_id = metadata.get("session_id")
        if session_id:
            download_url = f"{API_URL}/download_ppt/{session_id}"
            st.markdown(
                f'<a href="{download_url}" target="_blank">'
                '<button style="background:#059669;color:white;border:none;'
                'padding:0.75rem 1.5rem;border-radius:0.5rem;cursor:pointer;font-weight:600;">'
                ' Download Enhanced PowerPoint</button></a>', 
                unsafe_allow_html=True
            )
    
    st.markdown("---")
    
    # Export options
    st.subheader("Export Options")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # PowerPoint download button
        if session_id:
            download_url = f"{API_URL}/download_ppt/{session_id}"
            st.markdown(
                f'<a href="{download_url}" target="_blank">'
                '<button style="background:#3b82f6;color:white;border:none;'
                'padding:0.5rem 1rem;border-radius:0.25rem;cursor:pointer;">'
                'PowerPoint File</button></a>', 
                unsafe_allow_html=True
            )
    
    with col2:
        # JSON export
        json_data = json.dumps(data, indent=2, default=str)
        st.download_button(
            "Download JSON",
            json_data,
            f"enhanced_presentation_{metadata.get('generated_at', 'unknown')[:10]}.json",
            "application/json",
            use_container_width=True
        )
    
    with col3:
        # Enhanced text export
        text_export = create_enhanced_text_export(slides, metadata)
        st.download_button(
            "Download Text",
            text_export,
            f"enhanced_presentation_{metadata.get('generated_at', 'unknown')[:10]}.txt",
            "text/plain",
            use_container_width=True
        )
    
    with col4:
        if st.button("Generate New", use_container_width=True):
            st.session_state.presentation_data = None
            st.session_state.generation_status = None
            st.session_state.generation_completed = False
            st.rerun()
    
    st.markdown("---")
    
    # Display slides with enhanced preview
    st.subheader("Presentation Preview")
    
    if slides:
        # Slide navigation
        slide_options = ["All Slides"] + [f"Slide {i+1}: {slide.get('title', 'Untitled')}" for i, slide in enumerate(slides)]
        selected_view = st.selectbox("View:", slide_options)
        
        if selected_view == "All Slides":
            # Display all slides
            for i, slide in enumerate(slides, 1):
                display_enhanced_slide(i, slide)
        else:
            # Display selected slide
            slide_index = slide_options.index(selected_view) - 1
            if 0 <= slide_index < len(slides):
                display_enhanced_slide(slide_index + 1, slides[slide_index], expanded=True)
    else:
        st.warning("No slides data available")

def display_enhanced_slide(slide_num, slide_data, expanded=False):
    """Display individual slide with enhanced formatting preview"""
    with st.container():
        # Slide container with styling
        slide_html = f'<div class="slide-preview">'
        
        # Slide header
        slide_title = slide_data.get('title', 'Untitled')
        slide_html += f'<div class="slide-title">Slide {slide_num}: {slide_title}</div>'
        
        # Content blocks
        content_blocks = slide_data.get('content_blocks', [])
        
        if content_blocks:
            for block in content_blocks:
                block_type = block.get('type', 'paragraph')
                block_text = block.get('text', '')
                block_style = block.get('style', {})
                
                if block_type == 'heading':
                    slide_html += f'<div class="content-heading">{block_text}</div>'
                elif block_type == 'paragraph':
                    slide_html += f'<div class="content-paragraph">{block_text}</div>'
                elif block_type == 'bullet_list':
                    items = parse_list_items(block_text)
                    for item in items:
                        slide_html += f'<div class="content-bullet">• {item}</div>'
                elif block_type == 'numbered_list':
                    items = parse_list_items(block_text)
                    for i, item in enumerate(items, 1):
                        slide_html += f'<div class="content-bullet">{i}. {item}</div>'
                elif block_type == 'quote':
                    slide_html += f'<div class="content-quote">"{block_text}"</div>'
        else:
            # Fallback for old format
            slide_content = slide_data.get('content', 'No content available')
            slide_html += f'<div class="content-paragraph">{slide_content}</div>'
        
        slide_html += '</div>'
        
        # Display the styled slide
        st.markdown(slide_html, unsafe_allow_html=True)
        
        # Additional info in expander
        with st.expander(f"Slide {slide_num} Technical Details", expanded=False):
            slide_type = slide_data.get('slide_type', 'content')
            layout = slide_data.get('layout', 'title_content')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"Type: {slide_type.title()}")
            with col2:
                st.info(f"Layout: {layout.replace('_', ' ').title()}")
            with col3:
                if content_blocks:
                    st.info(f"Content Blocks: {len(content_blocks)}")
                else:
                    st.info("Format: Legacy")
            
            # Show content blocks structure
            if content_blocks:
                st.markdown("**Content Structure:**")
                for i, block in enumerate(content_blocks):
                    block_type = block.get('type', 'unknown')
                    block_style = block.get('style', {})
                    st.markdown(f"- Block {i+1}: {block_type} ({block_style.get('font_size', 'default')}pt, {block_style.get('font_weight', 'normal')})")
        
        st.markdown("---")

def parse_list_items(text):
    """Parse list items from text, handling various formats"""
    if not text:
        return []
    
    # Clean up common issues
    text = str(text).replace("•", "\n").replace("*", "\n").replace("-", "\n")
    text = str(text).replace("Ã¢â‚¬Â¢", "\n")  # Fix encoding issues
    
    items = []
    for line in str(text).split('\n'):
        line = line.strip()
        if line and len(line) > 3:
            # Remove leading numbers
            if line[0].isdigit() and '. ' in line[:5]:
                line = line.split('. ', 1)[1]
            items.append(line)
    
    return items[:6]  # Limit items

def create_enhanced_text_export(slides, metadata):
    """Create enhanced text export with formatting indicators"""
    text_export = f"# Enhanced Presentation Export\n\n"
    text_export += f"Generated: {metadata.get('generated_at', 'Unknown')}\n"
    text_export += f"Total Slides: {metadata.get('total_slides', 'Unknown')}\n"
    text_export += f"Enhanced: {'Yes' if metadata.get('enhanced') else 'No'}\n\n"
    
    for i, slide in enumerate(slides, 1):
        text_export += f"## Slide {i}: {slide.get('title', 'Untitled')}\n\n"
        
        # Check if enhanced format with content blocks
        content_blocks = slide.get('content_blocks', [])
        if content_blocks:
            for block in content_blocks:
                block_type = block.get('type', 'paragraph')
                block_text = block.get('text', '')
                
                if block_type == 'heading':
                    text_export += f"### {block_text}\n\n"
                elif block_type == 'paragraph':
                    text_export += f"{block_text}\n\n"
                elif block_type == 'bullet_list':
                    items = parse_list_items(block_text)
                    for item in items:
                        text_export += f"- {item}\n"
                    text_export += "\n"
                elif block_type == 'numbered_list':
                    items = parse_list_items(block_text)
                    for j, item in enumerate(items, 1):
                        text_export += f"{j}. {item}\n"
                    text_export += "\n"
                elif block_type == 'quote':
                    text_export += f"> \"{block_text}\"\n\n"
        else:
            # Fallback for legacy format
            text_export += f"{slide.get('content', 'No content')}\n\n"
        
        text_export += "---\n\n"
    
    return text_export

if __name__ == "__main__":
    main()
