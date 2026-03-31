from memoryplane import MemoryPlaneClient


def test_sdk_write_and_search_flow(tmp_path):
    client = MemoryPlaneClient(root=tmp_path)
    client.init()

    candidate = client.write(
        type="preference",
        space="preference",
        entity="user",
        content="User prefers concise answers",
        source="chat:sess_001",
        durability="durable",
        dry_run=True,
    )["candidate"]
    committed = client.commit(candidate["candidate_id"])["memory"]
    results = client.search(query="concise", space="preference", limit=5)

    assert committed["content"] == "User prefers concise answers"
    assert len(results["results"]) == 1
    assert results["results"][0]["memory"]["memory_id"] == committed["memory_id"]


def test_sdk_write_batch_supports_partial_success(tmp_path):
    client = MemoryPlaneClient(root=tmp_path)
    client.init()

    payload = client.write_batch(
        [
            {
                "type": "preference",
                "space": "preference",
                "entity": "user",
                "content": "User prefers concise answers",
                "source": "chat:sess_001",
                "durability": "durable",
                "dry_run": True,
            },
            {
                "type": "preference",
                "space": "preference",
                "entity": "invalid-entity",
                "content": "This should fail validation",
                "source": "chat:sess_001",
                "durability": "durable",
                "dry_run": True,
            },
        ]
    )

    assert len(payload["results"]) == 2
    assert payload["results"][0]["ok"] is True
    assert payload["results"][1]["ok"] is False
    assert payload["results"][1]["error"]["code"] == "BATCH_ITEM_FAILED"


def test_sdk_search_batch_preserves_query_order(tmp_path):
    client = MemoryPlaneClient(root=tmp_path)
    client.init()
    candidate = client.write(
        type="preference",
        space="preference",
        entity="user",
        content="User prefers concise answers",
        source="chat:sess_001",
        durability="durable",
        dry_run=True,
    )["candidate"]
    client.commit(candidate["candidate_id"])

    payload = client.search_batch(["concise", "answers"], space="preference", limit=3)

    assert [item["query"] for item in payload["queries"]] == ["concise", "answers"]
    assert all(item["results"] for item in payload["queries"])
