import time

from fastapi.testclient import TestClient

from aiplaygame.api.app import app


def test_health_endpoint():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_import_botzone_replay():
    client = TestClient(app)
    payload = {
        "requests": [
            {
                "player": 0,
                "hand": ["3", "4", "5", "6", "7", "8"],
                "lastAction": {"player": 2, "kind": "play", "cards": ["3"]},
            }
        ],
        "responses": [],
    }
    response = client.post("/api/replays/botzone", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["match_id"]
    assert body["events"]


def test_create_local_match_returns_player_profiles():
    client = TestClient(app)
    response = client.post(
        "/api/matches/local",
        json={
            "players": ["douzero", "llm:local-a", "human"],
            "main_player": 1,
            "delay_seconds": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["main_player"] == 1
    assert body["player_profiles"]["0"]["kind"] == "douzero"
    assert body["player_profiles"]["1"]["kind"] == "llm"
    assert body["player_profiles"]["2"]["kind"] == "human"


def test_human_player_can_query_and_submit_legal_action():
    client = TestClient(app)
    response = client.post(
        "/api/matches/local",
        json={
            "players": ["human", "heuristic", "heuristic"],
            "main_player": 0,
            "seed": 4,
            "delay_seconds": 0,
        },
    )
    assert response.status_code == 200
    match_id = response.json()["match_id"]

    actions = []
    for _ in range(20):
        legal_response = client.get(f"/api/matches/{match_id}/legal-actions/0")
        assert legal_response.status_code == 200
        actions = legal_response.json()["actions"]
        if actions:
            break
        time.sleep(0.02)

    assert actions
    selected = actions[0]
    submit_response = client.post(
        f"/api/matches/{match_id}/actions",
        json={
            "player": 0,
            "kind": selected["kind"],
            "cards": selected["cards"],
        },
    )
    assert submit_response.status_code == 200
    assert submit_response.json() == {"status": "accepted"}


def test_create_room_requires_llm_api_config_and_hides_key():
    client = TestClient(app)
    missing = client.post(
        "/api/rooms",
        json={
            "name": "missing key",
            "players": [
                {"kind": "llm", "name": "LLM", "model": "gpt-test", "base_url": "http://llm"},
                {"kind": "douzero", "name": "D1"},
                {"kind": "empty", "name": "Open"},
            ],
        },
    )
    assert missing.status_code == 400

    response = client.post(
        "/api/rooms",
        json={
            "name": "configured llm",
            "players": [
                {
                    "kind": "llm",
                    "name": "LLM",
                    "avatar_url": "https://example.com/avatar.png",
                    "bio": "direct model player",
                    "model": "gpt-test",
                    "base_url": "http://llm",
                    "api_key": "secret-key",
                },
                {"kind": "douzero", "name": "D1", "bio": "model player"},
                {"kind": "empty", "name": "Open"},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["players"][0]["kind"] == "llm"
    assert body["players"][0]["name"] == "LLM"
    assert body["players"][0]["has_api_key"] is True
    assert "api_key" not in body["players"][0]


def test_room_join_approve_and_start_with_douzero_players():
    client = TestClient(app)
    response = client.post(
        "/api/rooms",
        json={
            "name": "room flow",
            "players": [
                {"kind": "douzero", "name": "D0"},
                {"kind": "douzero", "name": "D1"},
                {"kind": "empty", "name": "Open"},
            ],
            "delay_seconds": 0,
            "min_ai_turn_seconds": 0,
        },
    )
    assert response.status_code == 200
    room = response.json()
    join = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"display_name": "Alice"},
    )
    assert join.status_code == 200
    pending = next(seat for seat in join.json()["players"] if seat["status"] == "pending")

    approve = client.post(
        f"/api/rooms/{room['room_id']}/approve",
        json={"request_id": pending["request_id"]},
    )
    assert approve.status_code == 200
    assert approve.json()["players"][2]["kind"] == "human"

    start = client.post(f"/api/rooms/{room['room_id']}/start", json={"auto_restart": False})
    assert start.status_code == 200
    assert start.json()["match_id"]
