import json
from fastapi.testclient import TestClient
from server import app
from database.db import init_db, get_setting

client = TestClient(app)

def test_root_serves_miniapp():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Qabyldau AI" in resp.text
    assert "telegram-web-app.js" in resp.text

def test_settings_flow():
    # Проверка получения настроек
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_services" in data
    
    # Сохранение настроек связывания сервисов
    save_resp = client.post("/api/settings", json={
        "google_sheets_url": "https://script.google.com/macros/s/test-qabyldau",
        "telegram_chat_id": "999888777",
        "webhook_url": "https://webhook.site/test-1c"
    })
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "success"
    assert get_setting("google_sheets_url") == "https://script.google.com/macros/s/test-qabyldau"
    assert get_setting("telegram_chat_id") == "999888777"

def test_process_demo_invoice():
    client.post("/api/reset_demo")
    resp = client.post("/api/process/demo", json={"sample_id": "spike_milk_flour"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["spikes_count"] >= 1
    assert data["total_potential_loss_kzt"] > 0
    assert any("Родина" in it["product_name"] for it in data["items"])

def test_sync_to_services():
    demo_inv = client.post("/api/process/demo", json={"sample_id": "spike_milk_flour"}).json()
    sync_resp = client.post("/api/sync", json=demo_inv)
    assert sync_resp.status_code == 200
    res_data = sync_resp.json()
    assert res_data["status"] == "success"
    assert len(res_data["results"]) == 4

def test_catalog_and_radar_endpoints():
    prod_resp = client.get("/api/products")
    assert prod_resp.status_code == 200
    assert len(prod_resp.json()) >= 10
    
    radar_resp = client.get("/api/radar")
    assert radar_resp.status_code == 200
    r_data = radar_resp.json()
    assert "saved_margin_kzt" in r_data
    assert "recent_spikes" in r_data

def test_export_endpoints():
    for fmt in ["excel", "xml", "kaspi"]:
        resp = client.get(f"/api/export/{fmt}")
        assert resp.status_code == 200
        assert len(resp.content) > 50

if __name__ == "__main__":
    test_root_serves_miniapp()
    test_settings_flow()
    test_process_demo_invoice()
    test_sync_to_services()
    test_catalog_and_radar_endpoints()
    test_export_endpoints()
    print("ALL API AND MINI APP TESTS PASSED SUCCESSFULLY! 🚀")
