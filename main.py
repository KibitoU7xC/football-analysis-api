import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import requests

app = FastAPI()
COLAB_WORKER_URL = os.getenv("COLAB_WORKER_URL", "https://your-colab-worker-url")
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
UPLOAD_DIR = "uploads"
CHART_DIR = "charts"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

jobs: Dict[str, dict] = {}

class PlayerRequest(BaseModel):
    job_id: str
    player_id: int

@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = ""
):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    job_id = str(uuid.uuid4())
    video_path = f"{UPLOAD_DIR}/{job_id}.mp4"

    try:
        with open(video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        jobs[job_id] = {
            "status": "queued",
            "video_path": video_path,
            "players": None,
            "error": None
        }

        background_tasks.add_task(notify_colab_worker, job_id, video_path)
        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Error uploading file: {str(e)}"}
        )

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/players/{job_id}")
async def get_players(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        return {"status": job["status"]}

    return {
        "status": "completed",
        "players": [
            {"id": p["id"], "position": p.get("position", None)}
            for p in job["players"]
        ]
    }

@app.get("/analyze/{job_id}/{player_id}")
async def analyze_player(job_id: str, player_id: int):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        return {"status": job["status"]}

    player = next((p for p in job["players"] if p["id"] == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return {
        "status": "completed",
        "analysis": player.get("analysis", {}),
        "chart_url": f"/charts/{job_id}/{player_id}.png"
    }

@app.get("/charts/{job_id}/{player_id}.png")
async def get_chart(job_id: str, player_id: int):
    chart_path = f"{CHART_DIR}/{job_id}_{player_id}.png"
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(chart_path)

def notify_colab_worker(job_id: str, video_path: str):
    try:
        with open(video_path, "rb") as f:
            files = {'file': (f"{job_id}.mp4", f, 'video/mp4')}
            response = requests.post(
                f"{COLAB_WORKER_URL}/process",
                headers={"Authorization": f"Bearer {API_KEY}"},
                files=files,
                data={"job_id": job_id}
            )
        if response.status_code != 200:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Failed to notify worker"
        else:
            jobs[job_id]["status"] = "processing"
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
