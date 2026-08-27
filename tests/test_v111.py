# -*- coding: utf-8 -*-
"""v1.1 其它新功能：手动 IP 覆盖、更新日志页、SSE 流式帧、上传诊断。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
import app as appmod  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_NO_BACKUP", "1")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "v111.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    appmod.seed_builtin_templates()
    return TestClient(appmod.app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_manual_ip_override(client):
    r = client.post("/api/mobile/manual-ip", json={"ip": "192.168.5.99"})
    assert r.status_code == 200
    info = client.get("/api/mobile/link").json()
    assert info["manual_ip"] == "192.168.5.99"
    assert info["ip"] == "192.168.5.99"

    assert client.post("/api/mobile/manual-ip", json={"ip": "999.1.1.1"}).status_code == 400
    assert client.post("/api/mobile/manual-ip", json={"ip": "127.0.0.1"}).status_code == 400

    client.post("/api/mobile/manual-ip", json={"ip": ""})
    assert client.get("/api/mobile/link").json()["manual_ip"] == ""


def test_remote_device_cannot_set_manual_ip(client):
    remote = TestClient(appmod.app, follow_redirects=False, client=("192.168.1.20", 50000))
    r = remote.post("/api/mobile/manual-ip", json={"ip": "192.168.5.99"})
    assert r.status_code == 403


def test_changelog_page_local(client):
    r = client.get("/changelog")
    assert r.status_code == 200
    assert "更新日志" in r.text
    assert "1.1.0" in r.text


def test_chat_stream_emits_sse_frames(client, monkeypatch):
    db.set_setting("api_key", "sk-test")

    def fake_stream(messages, temperature=0.5):
        yield "你"
        yield "好"
        yield "！"

    monkeypatch.setattr(appmod, "_llm_chat_stream", fake_stream)
    r = client.post("/api/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    body = r.text
    assert "data: " in body and "[DONE]" in body
    for part in ("你", "好", "！"):
        assert part in body


def test_chat_stream_requires_api_key(client):
    db.set_setting("api_key", "")
    r = client.post("/api/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400


def test_upload_diagnosis_hints():
    d = appmod._upload_diagnosis(".pdf", "", 12)
    assert "12" in d and "扫描" in d
    d2 = appmod._upload_diagnosis(".jpg", "", 0)
    assert "旋转重试" in d2
    assert appmod._upload_diagnosis(".docx", "一段完全正常的文字内容测试测试测试") == ""
    short = appmod._upload_diagnosis(".docx", "太少了")
    assert short and "少" in short