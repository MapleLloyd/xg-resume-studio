# -*- coding: utf-8 -*-
"""安全加固回归：CSRF Origin 校验。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # 独立临时库，避免与其他测试互相干扰
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "sec.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    return TestClient(app, client=("127.0.0.1", 50000))


def test_mutation_without_origin_allowed(client):
    r = client.post("/api/items", json={"item_type": "award", "title": "t1"})
    assert r.status_code == 200
    assert r.json()["id"] >= 1


def test_cross_site_origin_rejected(client):
    r = client.post("/api/items", json={"item_type": "award", "title": "evil"},
                    headers={"Origin": "http://evil.example"})
    assert r.status_code == 403


def test_same_site_origin_allowed(client):
    r = client.post("/api/items", json={"item_type": "award", "title": "ok"},
                    headers={"Origin": "http://testserver"})
    assert r.status_code == 200


def test_qr_length_capped(client):
    r = client.get("/qr.svg", params={"d": "x" * 600})
    assert r.status_code == 400


def test_qr_defaults_to_png_with_complete_payload(client):
    """二维码默认返回 PNG，且内容必须是完整 URL（避免相机截断令牌）。"""
    import io
    import cv2
    from PIL import Image

    url = "http://192.168.10.99:8000/m/abc123def456ghij789klmn0"
    r = client.get("/qr.svg", params={"fmt": "png", "d": url})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    img = Image.open(io.BytesIO(r.content))
    cv_img = cv2.cvtColor(
        __import__("numpy").asarray(img.convert("RGB")),
        cv2.COLOR_RGB2BGR,
    )
    det = cv2.QRCodeDetector()
    data, _, _ = det.detectAndDecode(cv_img)
    assert data == url
