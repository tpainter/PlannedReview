import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import tempfile
import threading
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
import uvicorn

from plannedreview import PlannedReview


_storage = tempfile.TemporaryDirectory(prefix="plannedreview-")
_jobs: dict[str, "ReviewJob"] = {}
_jobs_lock = threading.Lock()


@dataclass
class ReviewJob:
    job_id: str
    directory: Path
    status: str = "uploading"
    output_path: Path | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: threading.Condition = field(default_factory=threading.Condition)

    def publish(self, event_type: str, **data: Any) -> None:
        with self.condition:
            self.events.append({"type": event_type, **data})
            self.condition.notify_all()


def _active_job_exists() -> bool:
    return any(job.status in {"uploading", "running"} for job in _jobs.values())


def _safe_filename(filename: str | None) -> str:
    normalized = (filename or "").replace("\\", "/")
    name = Path(normalized).name
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="A PDF filename is required.")
    if Path(name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    return name


def _fail_job(job: ReviewJob, message: str) -> None:
    with job.condition:
        job.status = "failed"
        job.events.append({"type": "failed", "message": message})
        job.condition.notify_all()


def _run_review(job: ReviewJob, pdf_path: Path) -> None:
    job.status = "running"
    job.publish("output", text=f"Starting review for {pdf_path.name}...\n")
    try:
        output_path = PlannedReview(
            str(pdf_path),
            "None",
            output_callback=lambda text: job.publish("output", text=text),
        )
        if output_path is None or not output_path.is_file():
            raise RuntimeError("The review did not produce a reviewed PDF.")

        job.output_path = output_path
        with job.condition:
            job.status = "completed"
            job.events.append(
                {
                    "type": "completed",
                    "filename": output_path.name,
                }
            )
            job.condition.notify_all()
    except Exception as error:
        logging.exception("Review job %s failed", job.job_id)
        _fail_job(job, str(error))


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    _storage.cleanup()


app = FastAPI(title="PlannedReview", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    page_path = Path(__file__).resolve().parent / "web" / "index.html"
    return page_path.read_text(encoding="utf-8")


@app.post("/api/reviews", status_code=202)
async def create_review(file: UploadFile = File(...)) -> dict[str, str]:
    filename = _safe_filename(file.filename)
    with _jobs_lock:
        if _active_job_exists():
            raise HTTPException(
                status_code=409,
                detail="A review is already running. Wait for it to finish before starting another.",
            )

        job_id = uuid4().hex
        job_directory = Path(_storage.name) / job_id
        job_directory.mkdir()
        job = ReviewJob(job_id=job_id, directory=job_directory)
        _jobs[job_id] = job

    pdf_path = job_directory / filename
    try:
        first_chunk = await file.read(1024 * 1024)
        if not first_chunk.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

        with pdf_path.open("wb") as uploaded_pdf:
            uploaded_pdf.write(first_chunk)
            while chunk := await file.read(1024 * 1024):
                uploaded_pdf.write(chunk)
    except HTTPException as error:
        _fail_job(job, error.detail)
        raise
    except OSError as error:
        _fail_job(job, f"Could not save uploaded PDF: {error}")
        raise HTTPException(status_code=500, detail="Could not save the uploaded PDF.") from error
    except Exception as error:
        _fail_job(job, f"Could not process uploaded PDF: {error}")
        raise HTTPException(status_code=500, detail="Could not process the uploaded PDF.") from error
    finally:
        await file.close()

    job.publish("output", text=f"Uploaded {filename}.\n")
    threading.Thread(target=_run_review, args=(job, pdf_path), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/reviews/{job_id}/events")
async def review_events(job_id: str, request: Request) -> StreamingResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review job not found.")

    try:
        last_event_id = max(0, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        last_event_id = 0

    def stream():
        event_index = last_event_id
        while True:
            with job.condition:
                if event_index >= len(job.events):
                    job.condition.wait(timeout=15)
                pending = job.events[event_index:]
                terminal = job.status in {"completed", "failed"}

            if not pending and not terminal:
                yield ": keep-alive\n\n"
                continue

            for event in pending:
                event_index += 1
                yield (
                    f"id: {event_index}\n"
                    f"event: {event['type']}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )
                if event["type"] in {"completed", "failed"}:
                    return

            if terminal:
                return

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/reviews/{job_id}/download")
async def download_review(job_id: str) -> FileResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review job not found.")
    if job.status != "completed" or job.output_path is None:
        raise HTTPException(status_code=409, detail="The reviewed PDF is not ready to download.")
    if not job.output_path.is_file():
        raise HTTPException(status_code=404, detail="The reviewed PDF is no longer available.")

    return FileResponse(
        job.output_path,
        media_type="application/pdf",
        filename=job.output_path.name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local PlannedReview web interface.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind to (default: localhost).")
    parser.add_argument("--port", type=int, default=8000, help="Local web server port.")
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("The web server must bind to localhost.")

    url = f"http://{args.host}:{args.port}"
    print(f"PlannedReview web interface: {url}")
    print("Press Ctrl+C to stop the server.")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
