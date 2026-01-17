"""FastAPI web application for PDF Reducer."""

import asyncio
import io
import json
import tempfile
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from pdfreducer.core.options import ReductionOptions
from pdfreducer.web.queue import Job, processing_queue


# Temp directory for uploads and outputs
TEMP_DIR = Path(tempfile.mkdtemp(prefix="pdfreducer_"))
UPLOAD_DIR = TEMP_DIR / "uploads"
OUTPUT_DIR = TEMP_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    await processing_queue.start_worker()
    yield
    # Shutdown
    await processing_queue.stop_worker()
    # Clean up temp files
    import shutil
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


app = FastAPI(
    title="PDF Reducer",
    description="Reduce PDF file sizes",
    lifespan=lifespan,
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# WebSocket connections for real-time updates
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def job_update_callback(job: Job):
    """Callback for job updates - broadcasts to all WebSocket clients."""
    await manager.broadcast({
        "type": "job_update",
        "job": job.to_dict(),
    })


# Register the callback
processing_queue.on_update(job_update_callback)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text())


def parse_bool(value: str) -> bool:
    """Parse boolean from form data."""
    return value.lower() in ("true", "1", "yes", "on")


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    mode: str = Form("reduce"),
    extract_csv: str = Form("false"),
    dpi: int = Form(150),
    quality: int = Form(80),
    grayscale: str = Form("false"),
    remove_images: str = Form("false"),
    aggressive: str = Form("false"),
    strip_metadata: str = Form("false"),
):
    """Upload a PDF file for processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are allowed"}

    # Save uploaded file
    input_path = UPLOAD_DIR / f"{processing_queue.jobs.__len__()}_{file.filename}"

    # Set output path based on mode
    if mode == "extract":
        output_path = OUTPUT_DIR / f"{Path(file.filename).stem}.txt"
    else:
        output_path = OUTPUT_DIR / f"{input_path.stem}_reduced.pdf"

    content = await file.read()
    input_path.write_bytes(content)

    # Create options
    options = ReductionOptions(
        dpi=dpi,
        quality=quality,
        grayscale=parse_bool(grayscale),
        remove_images=parse_bool(remove_images),
        aggressive=parse_bool(aggressive),
        strip_metadata=parse_bool(strip_metadata),
    )

    # Add to queue
    job = await processing_queue.add_job(
        filename=file.filename,
        input_path=input_path,
        output_path=output_path,
        options=options,
        mode=mode,
        extract_csv=parse_bool(extract_csv),
    )

    return {"job_id": job.id, "job": job.to_dict()}


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    jobs = await processing_queue.get_all_jobs()
    return {"jobs": [job.to_dict() for job in jobs]}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job."""
    job = await processing_queue.get_job(job_id)
    if not job:
        return {"error": "Job not found"}
    return {"job": job.to_dict()}


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job."""
    success = await processing_queue.remove_job(job_id)
    return {"success": success}


@app.post("/api/jobs/clear-completed")
async def clear_completed():
    """Clear all completed jobs."""
    count = await processing_queue.clear_completed()
    return {"cleared": count}


@app.post("/api/process")
async def start_processing():
    """Start processing all pending jobs."""
    count = await processing_queue.start_processing()
    return {"queued": count}


@app.get("/api/download/{job_id}")
async def download_file(job_id: str):
    """Download a processed file (PDF or text)."""
    job = await processing_queue.get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    if not job.output_path.exists():
        return {"error": "Output file not found"}

    if job.mode == "extract":
        return FileResponse(
            path=job.output_path,
            filename=f"{Path(job.filename).stem}.txt",
            media_type="text/plain; charset=utf-8",
        )
    else:
        return FileResponse(
            path=job.output_path,
            filename=f"{Path(job.filename).stem}_reduced.pdf",
            media_type="application/pdf",
        )


@app.get("/api/download-csv/{job_id}")
async def download_csv(job_id: str):
    """Download CSV tables as a ZIP file."""
    job = await processing_queue.get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    if not job.csv_dir or not job.csv_dir.exists():
        return {"error": "No CSV files available"}

    # Create ZIP of CSV files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for csv_file in job.csv_dir.glob("*.csv"):
            zip_file.write(csv_file, csv_file.name)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={Path(job.filename).stem}_tables.zip"},
    )


@app.get("/api/download-all")
async def download_all():
    """Download all completed files as a ZIP file."""
    jobs = await processing_queue.get_all_jobs()
    completed_jobs = [
        job for job in jobs
        if job.status == "completed" and job.output_path.exists()
    ]

    if not completed_jobs:
        return {"error": "No completed files to download"}

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for job in completed_jobs:
            if job.mode == "extract":
                filename = f"{Path(job.filename).stem}.txt"
            else:
                filename = f"{Path(job.filename).stem}_reduced.pdf"
            zip_file.write(job.output_path, filename)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=processed_files.zip"},
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    # Send current jobs on connect
    jobs = await processing_queue.get_all_jobs()
    await websocket.send_json({
        "type": "initial_jobs",
        "jobs": [job.to_dict() for job in jobs],
    })

    try:
        while True:
            # Keep connection alive, handle any incoming messages
            data = await websocket.receive_text()
            # Could handle client messages here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
