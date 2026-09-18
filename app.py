import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

load_dotenv()

app = FastAPI(title="NetHeal Agent")

BASE = Path(__file__).parent
SCENARIOS_DIR = BASE / "scenarios"
UI_FILE = BASE / "ui" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(UI_FILE.read_text())


@app.get("/api/scenarios")
async def list_scenarios():
    result = []
    for d in sorted(SCENARIOS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_file = d / "metadata.json"
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        meta["id"] = d.name
        result.append(meta)
    return JSONResponse(result)


@app.get("/api/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    d = SCENARIOS_DIR / scenario_id
    if not d.exists():
        raise HTTPException(404, "Scenario not found")
    return JSONResponse(
        {
            "metadata": json.loads((d / "metadata.json").read_text()),
            "incident": json.loads((d / "incident.json").read_text()),
        }
    )


@app.get("/api/run/{scenario_id}")
async def run_scenario(scenario_id: str):
    scenario_path = SCENARIOS_DIR / scenario_id
    if not scenario_path.exists():
        raise HTTPException(404, "Scenario not found")

    incident = json.loads((scenario_path / "incident.json").read_text())

    async def event_stream():
        from agent import AgentLoop

        loop = AgentLoop(scenario_path)
        async for event in loop.run(incident):
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.05)
        yield 'data: {"type":"stream_end"}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
