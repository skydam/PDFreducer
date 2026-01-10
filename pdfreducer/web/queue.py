"""Processing queue for PDF reduction jobs."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pdfreducer.core.options import ReductionOptions
from pdfreducer.core.reducer import PDFReducer


class JobStatus(str, Enum):
    """Status of a processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a PDF reduction job."""

    id: str
    filename: str
    input_path: Path
    output_path: Path
    options: ReductionOptions
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = "Waiting..."
    original_size: int = 0
    reduced_size: int = 0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert job to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "original_size": self.original_size,
            "reduced_size": self.reduced_size,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ProcessingQueue:
    """Manages a queue of PDF reduction jobs."""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.update_callbacks: List[Callable[[Job], None]] = []
        self._lock = asyncio.Lock()

    def on_update(self, callback: Callable[[Job], None]):
        """Register a callback for job updates."""
        self.update_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Job], None]):
        """Remove an update callback."""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)

    async def _notify_update(self, job: Job):
        """Notify all registered callbacks of a job update."""
        for callback in self.update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception:
                pass

    async def add_job(
        self,
        filename: str,
        input_path: Path,
        output_path: Path,
        options: ReductionOptions,
        auto_process: bool = False,
    ) -> Job:
        """Add a new job to the queue."""
        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            filename=filename,
            input_path=input_path,
            output_path=output_path,
            options=options,
            original_size=input_path.stat().st_size,
        )

        async with self._lock:
            self.jobs[job_id] = job

        if auto_process:
            await self.queue.put(job_id)
        await self._notify_update(job)

        return job

    async def start_processing(self) -> int:
        """Start processing all pending jobs. Returns number of jobs queued."""
        count = 0
        async with self._lock:
            for job_id, job in self.jobs.items():
                if job.status == JobStatus.PENDING:
                    await self.queue.put(job_id)
                    count += 1
        return count

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    async def get_all_jobs(self) -> List[Job]:
        """Get all jobs."""
        return list(self.jobs.values())

    async def remove_job(self, job_id: str) -> bool:
        """Remove a job and its files."""
        async with self._lock:
            if job_id not in self.jobs:
                return False

            job = self.jobs[job_id]

            # Clean up files
            try:
                if job.input_path.exists():
                    job.input_path.unlink()
            except Exception:
                pass

            try:
                if job.output_path.exists():
                    job.output_path.unlink()
            except Exception:
                pass

            del self.jobs[job_id]
            return True

    async def clear_completed(self) -> int:
        """Remove all completed jobs."""
        to_remove = [
            job_id
            for job_id, job in self.jobs.items()
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
        ]

        for job_id in to_remove:
            await self.remove_job(job_id)

        return len(to_remove)

    async def start_worker(self):
        """Start the background worker."""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())

    async def stop_worker(self):
        """Stop the background worker."""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self):
        """Background worker that processes jobs."""
        while True:
            try:
                job_id = await self.queue.get()

                if job_id not in self.jobs:
                    continue

                job = self.jobs[job_id]
                job.status = JobStatus.PROCESSING
                job.message = "Starting..."
                await self._notify_update(job)

                try:
                    await self._process_job(job)
                    job.status = JobStatus.COMPLETED
                    job.progress = 100.0
                    job.message = "Complete!"
                    job.completed_at = datetime.now()

                    if job.output_path.exists():
                        job.reduced_size = job.output_path.stat().st_size

                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.message = f"Error: {e}"

                await self._notify_update(job)
                self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception:
                continue

    async def _process_job(self, job: Job):
        """Process a single job."""
        loop = asyncio.get_event_loop()

        def progress_callback(pct: float, msg: str):
            job.progress = pct
            job.message = msg
            # Schedule notification in the event loop
            asyncio.run_coroutine_threadsafe(self._notify_update(job), loop)

        reducer = PDFReducer(job.options)

        # Run the reduction in a thread pool to avoid blocking
        await loop.run_in_executor(
            None,
            lambda: reducer.reduce(job.input_path, job.output_path, progress_callback),
        )


# Global queue instance
processing_queue = ProcessingQueue()
