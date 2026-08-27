# -*- coding: utf-8 -*-
"""服务端 PDF 导出（#1）：端点返回合法 PDF，且能跟随版本/语言。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
import app as appmod  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_NO_BACKUP", "1")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "pdf.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    appmod.seed_builtin_templates()
    return TestClient(appmod.app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_resume_pdf_endpoint_returns_pdf(client):
    r = client.get("/resume.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert b"%%EOF" in r.content


def test_resume_pdf_en_and_version(client):
    vid = client.post("/api/versions", json={"name": "英文版"}).json()["version"]["id"]
    for url in (f"/resume.pdf?lang=en&v={vid}", f"/resume.pdf?v={vid}"):
        r = client.get(url)
        assert r.status_code == 200 and r.content[:5] == b"%PDF-"


def test_pdf_module_builds_from_context(client):
    import pdf_export
    ctx = appmod.resume_context(1, "en")
    data = pdf_export.build_resume_pdf(ctx, "en")
    assert data[:5] == b"%PDF-"