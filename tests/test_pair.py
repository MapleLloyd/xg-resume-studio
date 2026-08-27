# -*- coding: utf-8 -*-
"""局域网配对码门卫回归（RESUME_LAN=1 时，非本机设备需持配对 Cookie）。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
from app import app  # noqa: E402

CODE = "AB2345"


@pytest.fixture()
def lan_client(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_LAN", "1")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "pair.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    db.set_setting("pair_code", CODE)
    return TestClient(app, follow_redirects=False, client=("192.168.1.20", 50000))


@pytest.fixture()
def local_client(monkeypatch, tmp_path):
    monkeypatch.delenv("RESUME_LAN", raising=False)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "local.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    db.set_setting("pair_code", CODE)
    return TestClient(app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_unpaired_remote_redirected_to_pair(lan_client):
    r = lan_client.get("/")
    assert r.status_code in (302, 307)
    assert r.headers["location"].startswith("/pair")


def test_unpaired_api_blocked(lan_client):
    r = lan_client.get("/api/items")
    assert r.status_code == 403
    assert r.json()["need_pair"] is True


def test_wrong_code_rejected(lan_client):
    r = lan_client.post("/api/pair", json={"code": "ZZZZ99", "next": "/"})
    assert r.status_code == 400


def test_correct_code_grants_access(lan_client):
    r = lan_client.post("/api/pair", json={"code": CODE, "next": "/items"})
    assert r.status_code == 200 and r.json()["next"] == "/items"
    assert "pair" in r.cookies
    home = lan_client.get("/items")
    assert home.status_code == 200


def test_open_redirect_blocked(lan_client):
    r = lan_client.post("/api/pair", json={"code": CODE, "next": "//evil.example"})
    assert r.status_code == 200
    assert r.json()["next"] == "/"


def test_lan_is_enabled_by_default(local_client):
    r = local_client.get("/api/mobile/link")
    assert r.status_code == 200
    assert r.json()["lan"] is True
    assert r.json()["can_manage"] is True


def test_mobile_link_uses_path_token_without_query(local_client):
    """直传链接应把令牌放路径（无 ?t=），避免 iOS/部分相机扫码丢令牌。"""
    r = local_client.get("/api/mobile/link")
    assert r.status_code == 200
    body = r.json()
    url = body["url"]
    assert url.endswith(f"/m/{body['token']}")
    assert "?" not in url


def test_local_user_can_disable_lan_and_remote_access_is_blocked(local_client):
    r = local_client.post("/api/mobile/lan", json={"enabled": False})
    assert r.status_code == 200
    assert db.get_setting("lan_enabled") == "0"
    assert local_client.get("/").status_code == 200

    remote = TestClient(app, follow_redirects=False, client=("192.168.1.20", 50000))
    blocked = remote.get("/")
    assert blocked.status_code == 403
    assert "扫码直传已关闭" in blocked.text


def test_remote_device_cannot_change_lan_setting(local_client):
    remote = TestClient(app, follow_redirects=False, client=("192.168.1.20", 50000))
    remote.cookies.set("pair", db.get_setting("pair_code"))
    r = remote.post("/api/mobile/lan", json={"enabled": False})
    assert r.status_code == 403


def test_lan_ip_skips_tunnel_and_virtual_networks(monkeypatch):
    """选择局域网 IP 时不得落在隧道/基准测试网段（如 198.18.x 或 100.x）。"""
    import app as appmod

    candidates = [
        "198.18.0.1",   # Meta Tunnel
        "100.90.51.6",  # Tailscale / CGNAT
        "172.27.192.1", # Hyper-V
        "192.168.228.1",# VMware VMnet1
        "192.168.233.1",# VMware VMnet8
        "192.168.10.99",# 真实 Wi-Fi 网卡
        "192.168.10.4", # 真实有线网卡
    ]
    monkeypatch.setattr(
        appmod,
        "_default_gateway",
        lambda: "192.168.10.1",
    )
    monkeypatch.setattr(appmod.socket, "getaddrinfo", lambda *a, **k: [])
    monkeypatch.setattr(
        appmod.socket, "gethostbyname_ex",
        lambda *a, **k: ("host", [], candidates),
    )
    # 屏蔽 UDP 兜底探测，避免受真实网络影响
    monkeypatch.setattr(appmod.socket, "socket", lambda *a, **k: _raise())
    got = appmod._lan_ip()
    assert got in ("192.168.10.99", "192.168.10.4")


def _raise():
    raise OSError("no udp")
