# app/utils.py
import uuid
import threading
from typing import Dict
from time import time

# Simple in-memory progress tracker.
# NOTE: This is process-local. It's fine for testing in Codespaces/Replit/local.
_progress_store: Dict[str, Dict] = {}
_lock = threading.Lock()

def create_task_id() -> str:
    return str(uuid.uuid4())

def set_progress(task_id: str, progress: float, status: str, message: str = ""):
    """
    progress: 0.0 - 100.0
    status: e.g., 'started', 'parsing', 'importing', 'completed', 'failed'
    message: optional message
    """
    with _lock:
        _progress_store[task_id] = {
            "task_id": task_id,
            "progress": float(progress),
            "status": status,
            "message": message,
            "updated_at": time()
        }

def get_progress(task_id: str):
    with _lock:
        data = _progress_store.get(task_id)
        if not data:
            return {"task_id": task_id, "progress": 0.0, "status": "pending", "message": ""}
        return data
