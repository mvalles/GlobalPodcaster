import requests
import json

FEED_MONITOR_URL = "http://localhost:8000/call_tool"


def call_feed_monitor(tool_name, arguments=None):
    payload = {
        "name": tool_name,
        "arguments": arguments or {}
    }
    response = requests.post(FEED_MONITOR_URL, json=payload)
    response.raise_for_status()
    return response.json()


def main():
    print("[Orchestrator] Llamando a get_feed_list...")
    feeds_result = call_feed_monitor("get_feed_list")
    print(json.dumps(feeds_result, indent=2, ensure_ascii=False))

    print("\n[Orchestrator] Llamando a get_new_episodes...")
    episodes_result = call_feed_monitor("get_new_episodes", {"page": 1, "per_page": 50})
    print(json.dumps(episodes_result, indent=2, ensure_ascii=False))

    # Si hay episodios nuevos, marcarlos como procesados
    episodes = episodes_result.get("episodes", [])
    if episodes:
        print(f"\n[Orchestrator] Marcando {len(episodes)} episodios como procesados...")
        mark_result = call_feed_monitor("mark_episodes_processed", {"episodes": [
            {
                "guid": ep["guid"],
                "feed_url": ep["feed_url"],
                "feed_id": ep["feed_id"]
            } for ep in episodes
        ]})
        print(json.dumps(mark_result, indent=2, ensure_ascii=False))
    else:
        print("\n[Orchestrator] No hay episodios nuevos para marcar.")

if __name__ == "__main__":
    main()
