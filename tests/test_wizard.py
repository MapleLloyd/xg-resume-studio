# -*- coding: utf-8 -*-
"""HTTP 层：首启向导门卫 + 示例数据 + 多账户隔离（需要 httpx，缺省跳过）。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_fresh_db_redirects_to_setup(client):
    if db.get_setting("initialized") == "1":
        pytest.skip("数据库已初始化（其他测试先跑），仅验证未初始化分支")
    r = client.get("/")
    assert r.status_code in (302, 307)
    assert r.headers["location"].startswith("/setup")


def test_api_blocked_before_setup(client):
    if db.get_setting("initialized") == "1":
        pytest.skip("同上")
    r = client.get("/api/items")
    assert r.status_code == 403
    assert r.json()["need_setup"] is True


def test_finish_wizard_loads_demo_and_unlocks(client):
    if db.get_setting("initialized") != "1":
        # 未初始化的全新库：走一遍向导完成
        r = client.post("/api/setup/finish", json={
            "account_name": "测试君", "skip_ai": True, "load_demo": True})
        assert r.status_code == 200
        assert db.get_setting("initialized") == "1"
    home = client.get("/", follow_redirects=True)
    assert home.status_code == 200


def test_demo_reload_rejected_when_not_empty(client):
    uid = db.all_rows("users")[0]["id"]
    if db.get_rows_where("awards", "user_id=?", (uid,)):
        r = client.post("/api/demo/load")
        assert r.status_code == 400
