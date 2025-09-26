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
    print("[Orchestrator] Llamando a get_all_feeds...")
    feeds_result = call_feed_monitor("get_all_feeds")
    print(json.dumps(feeds_result, indent=2, ensure_ascii=False))





if __name__ == "__main__":
    main()
