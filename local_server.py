"""Forge3D's zero-dependency local Windows bridge.

Serves the web interface on localhost and launches Blender in the background.
No files are uploaded and no network APIs are called.
"""

from __future__ import annotations

import argparse
import glob
import json
import mimetypes
import os
import shutil
import subprocess
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
ENGINE = ROOT / "blender" / "forge3d_item_factory.py"
OUTPUT = ROOT / "output"
MAX_BODY = 1024 * 1024
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_blender() -> str | None:
    override = os.environ.get("FORGE3D_BLENDER", "").strip().strip('"')
    candidates = [override] if override else []
    path_match = shutil.which("blender")
    if path_match:
        candidates.append(path_match)
    if os.name == "nt":
        candidates.extend(
            sorted(
                glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"),
                reverse=True,
            )
        )
    return next((str(Path(candidate)) for candidate in candidates if candidate and Path(candidate).is_file()), None)


def safe_recipe(payload: dict) -> dict:
    allowed = {
        "name", "prompt", "template", "detail", "shell_profile", "visor",
        "face_cage", "luminous_vents", "import_path", "poly_budget",
        "render_size", "colorways",
    }
    recipe = {key: value for key, value in payload.items() if key in allowed}
    recipe["template"] = "futuristic_football_helmet"
    recipe["name"] = str(recipe.get("name", "Forge3D Item"))[:100]
    recipe["prompt"] = str(recipe.get("prompt", ""))[:2000]
    recipe["detail"] = max(0.2, min(1.0, float(recipe.get("detail", 0.7))))
    recipe["poly_budget"] = max(1000, min(500000, int(recipe.get("poly_budget", 80000))))
    recipe["render_size"] = max(256, min(2048, int(recipe.get("render_size", 720))))
    recipe["colorways"] = list(recipe.get("colorways", []))[:6]
    if recipe.get("import_path"):
        source = Path(str(recipe["import_path"])).expanduser()
        if source.suffix.lower() not in {".glb", ".gltf", ".fbx", ".obj"}:
            raise ValueError("Imported model must be GLB, GLTF, FBX, or OBJ.")
    return recipe


def run_job(job_id: str, recipe: dict, blender: str) -> None:
    job_dir = OUTPUT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = job_dir / "recipe.json"
    recipe_path.write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    command = [
        blender,
        "--background",
        "--python",
        str(ENGINE),
        "--",
        "--recipe",
        str(recipe_path),
        "--output",
        str(job_dir),
    ]
    with LOCK:
        JOBS[job_id].update(status="running", started_at=utc_now(), command="Blender background build")
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
        log_text = (process.stdout or "") + "\n" + (process.stderr or "")
        (job_dir / "blender.log").write_text(log_text, encoding="utf-8", errors="replace")
        files = [str(path.relative_to(job_dir)).replace("\\", "/") for path in job_dir.rglob("*") if path.is_file()]
        status = "complete" if process.returncode == 0 else "failed"
        with LOCK:
            JOBS[job_id].update(
                status=status,
                finished_at=utc_now(),
                return_code=process.returncode,
                files=files,
                log_tail="\n".join(log_text.splitlines()[-30:]),
            )
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status="failed", finished_at=utc_now(), error=str(exc))


class Handler(SimpleHTTPRequestHandler):
    server_version = "Forge3D/1.0"

    def log_message(self, format, *args):
        print(f"[Forge3D] {self.address_string()} — {format % args}")

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
        super().end_headers()

    def json_response(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = unquote(urlparse(self.path).path)
        if route == "/api/health":
            blender = find_blender()
            return self.json_response({
                "status": "ready" if blender else "needs_blender",
                "local": True,
                "blender_found": bool(blender),
                "blender_path": blender,
                "engine_found": ENGINE.is_file(),
            })
        if route.startswith("/api/jobs/"):
            job_id = route.removeprefix("/api/jobs/").strip("/")
            with LOCK:
                job = JOBS.get(job_id)
                snapshot = dict(job) if job else None
            return self.json_response(snapshot or {"error": "Job not found"}, 200 if snapshot else 404)
        if route.startswith("/artifacts/"):
            parts = route.removeprefix("/artifacts/").split("/", 1)
            if len(parts) != 2:
                return self.json_response({"error": "Artifact path required"}, 404)
            target = (OUTPUT / parts[0] / parts[1]).resolve()
            allowed_root = (OUTPUT / parts[0]).resolve()
            if allowed_root not in target.parents or not target.is_file():
                return self.json_response({"error": "Artifact not found"}, 404)
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
            self.end_headers()
            self.wfile.write(data)
            return
        return self.serve_static(route)

    def serve_static(self, route: str):
        relative = "index.html" if route in {"", "/"} else route.lstrip("/")
        target = (DIST / relative).resolve()
        if DIST.resolve() not in target.parents and target != DIST.resolve():
            self.send_error(403)
            return
        if not target.is_file():
            target = DIST / "index.html"
        data = target.read_bytes()
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8" if mime.startswith("text/") else mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        route = urlparse(self.path).path
        if route != "/api/build":
            return self.json_response({"error": "Not found"}, 404)
        blender = find_blender()
        if not blender:
            return self.json_response({"error": "Blender was not found. Install Blender or set FORGE3D_BLENDER."}, 503)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("Recipe request must be between 1 byte and 1 MB.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            recipe = safe_recipe(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            return self.json_response({"error": str(exc)}, 400)

        job_id = uuid.uuid4().hex[:12]
        with LOCK:
            JOBS[job_id] = {"id": job_id, "status": "queued", "created_at": utc_now(), "files": []}
        thread = threading.Thread(target=run_job, args=(job_id, recipe, blender), daemon=True)
        thread.start()
        return self.json_response(JOBS[job_id], 202)


def main():
    parser = argparse.ArgumentParser(description="Forge3D local web interface")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not DIST.is_dir() or not ENGINE.is_file():
        raise SystemExit("Run this file from the complete Forge3D starter folder.")
    OUTPUT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Forge3D is ready at {url}")
    print("Local-only server: nothing is uploaded.")
    if not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nForge3D stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
