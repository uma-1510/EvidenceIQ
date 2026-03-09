# fastapi backend
#All API routes: upload, analyze, chat, report

import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from s3_handler import upload_video, get_presigned_url
from pipeline import run_full_pipeline, chat_with_evidence
from report_generator import generate_pdf_report

app= FastAPI(
    title= "EvidenceIQ API",
    description= "Multimodal video incident analysis powered by Amazon Nova",
    version= "1.0.0",
)

#connecting to frontend through cors
app.add_middleware(
    CORSMiddleware,
    allow_origins= ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict={}

class ChatRequest(BaseModel):
    job_id: str
    quetsion: str
    chat_history: list=[]

@app.get("/")
def health_check():
    return {"status": "EvidenceIQ API is running", "version": "1.0.0"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Step 1: Upload video to S3.
    Returns job_id and presigned URL for frontend video preview.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower()
    supported = {"mp4", "mov", "avi", "mkv", "webm"}
    if ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: .{ext}. Use: {supported}"
        )

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > 500 * 1024 * 1024:  # 500MB limit
        raise HTTPException(status_code=400, detail="File too large. Max 500MB.")

    # Upload to S3
    try:
        upload_result = upload_video(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    job_id = upload_result["job_id"]

    # Store job state
    jobs[job_id] = {
        "s3_uri":   upload_result["s3_uri"],
        "s3_key":   upload_result["s3_key"],
        "format":   upload_result["format"],
        "filename": upload_result["filename"],
        "status":   "uploaded",
        "timeline": None,
        "causal":   None,
        "report":   None,
        "error":    None,
    }

    # Generate presigned URL for frontend preview
    preview_url = get_presigned_url(upload_result["s3_key"])

    return {
        "job_id":      job_id,
        "preview_url": preview_url,
        "filename":    file.filename,
        "status":      "uploaded",
        "message":     "Video uploaded. Call /analyze/{job_id} to start analysis.",
    }


@app.post("/analyze/{job_id}")
async def analyze(job_id: str):
    """
    Step 2: Run the three-model Nova pipeline on the uploaded video.
    This streams progress updates back to the frontend as server-sent events.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] == "analyzing":
        raise HTTPException(status_code=409, detail="Analysis already in progress")
    if job["status"] == "complete":
        return {"status": "complete", "message": "Already analyzed"}

    async def stream_progress():
        """Stream progress updates as Server-Sent Events (SSE)."""
        job["status"] = "analyzing"

        def send(event: str, data: dict):
            return f"data: {json.dumps({'event': event, **data})}\n\n"

        try:
            yield send("start", {"message": "Analysis started", "passes": 3})

            # Pass 1 — Nova Lite 2
            yield send("pass_start", {
                "pass": 1,
                "model": "Nova Lite 2",
                "description": "Scanning video for events..."
            })
            from pipeline import pass1_temporal_scan
            timeline = pass1_temporal_scan(job["s3_uri"], job["format"])
            job["timeline"] = timeline
            yield send("pass_complete", {
                "pass": 1,
                "events_found": len(timeline.get("events", [])),
                "critical_events": len(timeline.get("critical_events", [])),
                "timeline": timeline,
            })

            # Pass 2 — Nova Pro
            yield send("pass_start", {
                "pass": 2,
                "model": "Nova Pro",
                "description": "Performing causal analysis..."
            })
            from pipeline import pass2_causal_analysis
            causal = pass2_causal_analysis(job["s3_uri"], job["format"], timeline)
            job["causal"] = causal
            yield send("pass_complete", {
                "pass": 2,
                "causal": causal,
            })

            # Pass 3 — Nova Premier
            yield send("pass_start", {
                "pass": 3,
                "model": "Nova Premier",
                "description": "Synthesizing evidence report..."
            })
            from pipeline import pass3_synthesis
            report = pass3_synthesis(job["s3_uri"], job["format"], timeline, causal)
            job["report"] = report
            job["status"] = "complete"
            yield send("complete", {
                "pass": 3,
                "report": report,
                "message": "Analysis complete. You can now chat with your evidence.",
            })

        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
            yield send("error", {"message": str(e)})

    return StreamingResponse(
        stream_progress(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/job/{job_id}")
def get_job(job_id: str):
    """Get the current status and results of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Step 3: Ask questions about the analyzed video.
    Uses Nova Lite 2 with pre-built context — no re-analysis.
    """
    job_id = request.job_id
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not complete yet. Status: {job['status']}"
        )

    try:
        answer = chat_with_evidence(
            question=request.question,
            timeline=job["timeline"],
            causal=job["causal"],
            report=job["report"],
            chat_history=request.chat_history,
        )
        return {"answer": answer, "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/report/{job_id}/pdf")
def download_report(job_id: str):
    """Generate and download a PDF evidence report."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Analysis not complete")

    try:
        pdf_bytes = generate_pdf_report(
            timeline=job["timeline"],
            causal=job["causal"],
            report=job["report"],
            filename=job.get("filename", "video"),
        )
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="evidenceiq_report_{job_id[:8]}.pdf"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)