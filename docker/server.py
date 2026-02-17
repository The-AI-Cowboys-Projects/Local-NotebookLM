from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from enum import Enum
from typing import Optional
import tempfile
import os
import shutil
from pydantic import BaseModel
import uuid

# Import the processor
from local_notebooklm.processor import podcast_processor

# Create FastAPI app
app = FastAPI(
    title="Podcast Generator API",
    description="API for generating podcasts from PDF documents",
    version="1.1.1"
)

# Define enums for the choices
class FormatType(str, Enum):
    podcast = "podcast"
    interview = "interview"
    panel_discussion = "panel-discussion"
    debate = "debate"
    summary = "summary"
    narration = "narration"
    storytelling = "storytelling"
    explainer = "explainer"
    lecture = "lecture"
    tutorial = "tutorial"
    q_and_a = "q-and-a"
    news_report = "news-report"
    executive_brief = "executive-brief"
    meeting_minutes = "meeting-minutes"
    analysis = "analysis"
    three_people_podcast = "three-people-podcast"
    three_people_panel_discussion = "three-people-panel-discussion"
    three_people_debate = "three-people-debate"
    four_people_podcast = "four-people-podcast"
    four_people_panel_discussion = "four-people-panel-discussion"
    four_people_debate = "four-people-debate"
    five_people_podcast = "five-people-podcast"
    five_people_panel_discussion = "five-people-panel-discussion"
    five_people_debate = "five-people-debate"

class ContentLength(str, Enum):
    short = "short"
    medium = "medium"
    long = "long"
    very_long = "very-long"

class ContentStyle(str, Enum):
    normal = "normal"
    friendly = "friendly"
    professional = "professional"
    academic = "academic"
    casual = "casual"
    technical = "technical"
    gen_z = "gen-z"
    funny = "funny"

class ProcessStep(int, Enum):
    step1 = 1
    step2 = 2
    step3 = 3
    step4 = 4

# Response models
class PodcastResponse(BaseModel):
    job_id: str
    status: str
    message: str

class PodcastStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    audio_url: Optional[str] = None
    infographic_url: Optional[str] = None
    pptx_url: Optional[str] = None

# Dictionary to store job statuses
job_status = {}

# Function to process podcast in background
def process_podcast(
    job_id: str,
    pdf_path: str,
    config_path: Optional[str] = None,
    format_type: FormatType = FormatType.summary,
    length: ContentLength = ContentLength.medium,
    style: ContentStyle = ContentStyle.normal,
    preference: Optional[str] = None,
    output_dir: str = "./output",
    skip_to: Optional[ProcessStep] = None
):
    try:
        success, result = podcast_processor(
            input_path=pdf_path,
            config_path=config_path,
            format_type=format_type,
            length=length,
            style=style,
            preference=preference,
            output_dir=output_dir,
            skip_to=skip_to
        )
        
        if success:
            # Copy the final audio file to a persistent location
            audio_filename = f"{job_id}_podcast.wav"
            final_audio_path = os.path.join(output_dir, audio_filename)

            # Check for infographic
            infographic_path = os.path.join(output_dir, "step5", "infographic.html")
            infographic_url = None
            if os.path.exists(infographic_path):
                infographic_url = f"/download-infographic/{job_id}"

            # Check for PPTX
            pptx_path = os.path.join(output_dir, "step5", "infographic.pptx")
            pptx_url = None
            if os.path.exists(pptx_path):
                pptx_url = f"/download-pptx/{job_id}"

            # Check if the audio file exists
            podcast_audio_path = os.path.join(output_dir, "step3/podcast.wav")
            if os.path.exists(podcast_audio_path):
                shutil.copy(podcast_audio_path, final_audio_path)
                job_status[job_id] = {
                    "status": "completed",
                    "result": result,
                    "audio_path": final_audio_path,
                    "audio_url": f"/download-podcast/{job_id}",
                    "infographic_path": infographic_path if infographic_url else None,
                    "infographic_url": infographic_url,
                    "pptx_path": pptx_path if pptx_url else None,
                    "pptx_url": pptx_url,
                }
            else:
                job_status[job_id] = {
                    "status": "completed",
                    "result": result,
                    "infographic_path": infographic_path if infographic_url else None,
                    "infographic_url": infographic_url,
                    "pptx_path": pptx_path if pptx_url else None,
                    "pptx_url": pptx_url,
                    "error": "Audio file not found",
                }
        else:
            job_status[job_id] = {"status": "failed", "error": "Processing failed"}
            
    except Exception as e:
        job_status[job_id] = {"status": "failed", "error": str(e)}
    
    # Clean up the temporary files
    try:
        # Clean up input files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if config_path and os.path.exists(config_path):
            os.remove(config_path)
            
        # Clean up processing files, but preserve final audio
        job_output_dir = os.path.join(output_dir, "step1")
        if os.path.exists(job_output_dir):
            shutil.rmtree(job_output_dir)
            
        job_output_dir = os.path.join(output_dir, "step2")
        if os.path.exists(job_output_dir):
            shutil.rmtree(job_output_dir)
            
        # For step3, remove everything except the final podcast.wav which we already copied
        job_output_dir = os.path.join(output_dir, "step3")
        if os.path.exists(job_output_dir):
            segments_dir = os.path.join(job_output_dir, "segments")
            if os.path.exists(segments_dir):
                shutil.rmtree(segments_dir)
                
            # Remove data pkl file
            data_file = os.path.join(job_output_dir, "podcast_ready_data.pkl")
            if os.path.exists(data_file):
                os.remove(data_file)
                
            # Don't remove podcast.wav here as we've already copied it
    except Exception as e:
        print(f"Error cleaning up: {str(e)}")

@app.post("/generate-podcast/", response_model=PodcastResponse)
async def generate_podcast(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(...),
    config_file: Optional[UploadFile] = None,
    format_type: FormatType = Form(FormatType.summary),
    length: ContentLength = Form(ContentLength.medium),
    style: ContentStyle = Form(ContentStyle.normal),
    preference: Optional[str] = Form(None),
    output_dir: str = Form("./output"),
    skip_to: Optional[ProcessStep] = Form(None)
):
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Create temp directory if it doesn't exist
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save the uploaded PDF to a temporary file
    pdf_path = os.path.join(temp_dir, f"{job_id}_{pdf_file.filename}")
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf_file.file, buffer)
    
    # Save the config file if provided
    config_path = None
    if config_file:
        config_path = os.path.join(temp_dir, f"{job_id}_{config_file.filename}")
        with open(config_path, "wb") as buffer:
            shutil.copyfileobj(config_file.file, buffer)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Update job status
    job_status[job_id] = {"status": "processing"}
    
    # Add the task to background tasks
    background_tasks.add_task(
        process_podcast,
        job_id=job_id,
        input_path=pdf_path,
        config_path=config_path,
        format_type=format_type,
        length=length,
        style=style,
        preference=preference,
        output_dir=output_dir,
        skip_to=skip_to
    )
    
    return PodcastResponse(
        job_id=job_id,
        status="processing",
        message="Your podcast generation job has been started"
    )

@app.get("/job-status/{job_id}", response_model=PodcastStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = job_status[job_id]
    
    return PodcastStatusResponse(
        job_id=job_id,
        status=job_info["status"],
        result=job_info.get("result"),
        audio_url=job_info.get("audio_url"),
        infographic_url=job_info.get("infographic_url"),
        pptx_url=job_info.get("pptx_url"),
    )

@app.get("/download-infographic/{job_id}")
async def download_infographic(job_id: str):
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = job_status[job_id]

    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    infographic_path = job_info.get("infographic_path")
    if not infographic_path or not os.path.exists(infographic_path):
        raise HTTPException(status_code=404, detail="Infographic not found")

    return FileResponse(
        path=infographic_path,
        filename=f"infographic_{job_id}.html",
        media_type="text/html",
    )

@app.get("/download-pptx/{job_id}")
async def download_pptx(job_id: str):
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = job_status[job_id]

    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    pptx_path = job_info.get("pptx_path")
    if not pptx_path or not os.path.exists(pptx_path):
        raise HTTPException(status_code=404, detail="PPTX not found")

    return FileResponse(
        path=pptx_path,
        filename=f"infographic_{job_id}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )

@app.get("/download-podcast/{job_id}")
async def download_podcast(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = job_status[job_id]
    
    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    
    if "audio_path" not in job_info:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_path = job_info["audio_path"]
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found on server")
    
    # Schedule file deletion after response is sent
    def delete_file_after_download():
        try:
            # Wait a bit to ensure file is fully sent
            import time
            time.sleep(60)  # Give 60 seconds buffer
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
    
    # Add deletion task to background tasks
    background_tasks.add_task(delete_file_after_download)
    
    return FileResponse(
        path=audio_path, 
        filename=f"podcast_{job_id}.wav", 
        media_type="audio/wav"
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Root endpoint with API information
@app.get("/")
async def root():
    return {
        "api": "Podcast Generator",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/generate-podcast/", "method": "POST", "description": "Generate a podcast from PDF"},
            {"path": "/job-status/{job_id}", "method": "GET", "description": "Check status of a job"},
            {"path": "/download-podcast/{job_id}", "method": "GET", "description": "Download the generated podcast audio file"},
            {"path": "/download-infographic/{job_id}", "method": "GET", "description": "Download the generated infographic HTML"},
            {"path": "/download-pptx/{job_id}", "method": "GET", "description": "Download the generated PPTX slide deck"},
            {"path": "/health", "method": "GET", "description": "API health check"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)