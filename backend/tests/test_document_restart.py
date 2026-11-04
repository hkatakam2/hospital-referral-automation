import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest


def test_document_survives_real_backend_process_restart(db_engine, document_storage, pdf_factory):
    environment = {
        **os.environ,
        "DATABASE_URL": db_engine.url.render_as_string(hide_password=False),
        "DOCUMENT_STORAGE_DIR": str(document_storage),
    }

    @contextmanager
    def running_api():
        # Pass a reserved socket to Uvicorn to avoid port collisions with local apps.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            listener.setblocking(False)
            port = listener.getsockname()[1]
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--fd", str(listener.fileno())],
                pass_fds=(listener.fileno(),), cwd=Path(__file__).parents[1], env=environment,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2) as api:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            pytest.fail("Temporary API process exited before startup")
                        try:
                            if api.get("/api/health").status_code == 200:
                                break
                        except httpx.RequestError:
                            pass
                        time.sleep(0.05)
                    else:
                        pytest.fail("Temporary API process did not become ready")
                    yield api
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    with running_api() as api:
        response = api.post("/api/referrals", json={
            "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
            "referring_organization": "Lakeside Primary Care", "requested_specialty": "cardiology",
            "referral_reason": "Recurrent palpitations",
        })
        assert response.status_code == 201
        url = f"/api/referrals/{response.json()['id']}/documents"
        original = pdf_factory()
        response = api.post(url, files={"file": ("referral.pdf", original, "application/pdf")})
        assert response.status_code == 201
        document = response.json()
        extraction_url = url.removesuffix("/documents") + "/extractions"
        response = api.post(extraction_url)
        assert response.status_code == 201
        extraction = response.json()
    with running_api() as restarted:
        response = restarted.get(f"{url}/{document['id']}")
        assert response.status_code == 200
        assert response.json() == document
        assert restarted.get(f"{extraction_url}/{extraction['id']}").json() == extraction
        assert restarted.get(url).json()[0]["sha256"] == document["sha256"]
    assert (document_storage / f"{document['id']}.pdf").read_bytes() == original
