from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="AI Tech Radar")
ROOT = Path(__file__).parent


@app.get("/")
def index():
    return FileResponse(ROOT / "index.html")


@app.get("/reports/{name}")
def report(name: str):
    name = Path(name).name
    path = ROOT / "reports" / name
    if not path.exists() or not path.is_file():
        return {"error": "report not found"}
    return FileResponse(path, media_type="text/markdown")


@app.get("/reports/")
def report_list():
    files = sorted((ROOT / "reports").glob("*.md"), reverse=True)
    return {"files": [f.name for f in files]}
