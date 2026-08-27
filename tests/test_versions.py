# -*- coding: utf-8 -*-
"""多份简历版本（#2）：CRUD、按版本布局、版本级简介/自我评价覆盖、导出跟随版本。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
import app as appmod  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_NO_BACKUP", "1")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "ver.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    appmod.seed_builtin_templates()
    return TestClient(appmod.app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_default_version_created(client):
    versions = client.get("/api/versions").json()
    assert len(versions) == 1
    assert versions[0]["is_default"] == 1
    assert versions[0]["name"] == "默认简历"


def test_create_update_delete_version(client):
    r = client.post("/api/versions", json={"name": "保研版"})
    assert r.status_code == 200
    vid = r.json()["version"]["id"]

    r = client.put(f"/api/versions/{vid}", json={
        "summary": "保研专属简介", "self_eval": "专注科研",
        "self_tags": ["严谨", "执行力强"],
    })
    assert r.status_code == 200
    row = db.get_row("resume_versions", vid)
    assert row["summary"] == "保研专属简介"
    assert row["self_tags"] == '["严谨", "执行力强"]'

    assert client.delete(f"/api/versions/{vid}").status_code == 200
    # 默认版本不可删
    dv = client.get("/api/versions").json()[0]
    assert client.delete(f"/api/versions/{dv['id']}").status_code == 400


def test_layout_isolated_per_version(client):
    v0 = client.get("/api/versions").json()[0]
    r = client.post("/api/versions", json={"name": "求职版"})
    vid = r.json()["version"]["id"]

    client.put("/api/layout?v=" + str(vid), json={"order": ["awards", "positions"], "hidden": ["papers"]})
    got = client.get("/api/layout?v=" + str(vid)).json()
    assert got["order"][:2] == ["awards", "positions"]
    assert "papers" in got["hidden"]

    default_layout = client.get("/api/layout?v=" + str(v0["id"])).json()
    assert "papers" not in default_layout["hidden"]


def test_version_overrides_apply_in_context(client):
    versions = client.get("/api/versions").json()
    default_id = versions[0]["id"]
    vid = client.post("/api/versions", json={"name": "奖学金版"}).json()["version"]["id"]
    client.put(f"/api/versions/{vid}", json={
        "summary": "版本专属简介", "self_eval": "认真负责", "self_tags": ["团队协作"],
    })

    ctx_v = appmod.resume_context(1, "zh", db.get_row("resume_versions", vid))
    assert ctx_v["profile"]["summary"] == "版本专属简介"
    assert ctx_v["profile"]["self_eval"] == "认真负责"
    assert ctx_v["profile"]["self_tags"] == ["团队协作"]

    ctx_d = appmod.resume_context(1, "zh", db.get_row("resume_versions", default_id))
    assert ctx_d["profile"]["summary"] != "版本专属简介"


def test_resume_page_and_exports_follow_version(client):
    vid = client.post("/api/versions", json={"name": "求职版"}).json()["version"]["id"]
    r = client.get("/resume?v=" + str(vid))
    assert r.status_code == 200
    assert "求职版" in r.text

    for url in (f"/resume.docx?v={vid}", f"/resume.pdf?v={vid}", f"/resume.docx?lang=en&v={vid}"):
        r = client.get(url)
        assert r.status_code == 200, url