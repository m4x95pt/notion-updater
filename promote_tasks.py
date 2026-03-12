import os
import requests
from datetime import date

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
TASKS_DB_ID  = "2a7c4bee3163813cbf9acda129ead602"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

today = date.today().isoformat()

# Buscar todas as tarefas em Inbox com Due Date <= hoje
resp = requests.post(
    f"https://api.notion.com/v1/databases/{TASKS_DB_ID}/query",
    headers=HEADERS,
    json={
        "filter": {
            "and": [
                {"property": "Status",   "status": {"equals": "Inbox"}},
                {"property": "Due Date", "date":   {"on_or_before": today}},
            ]
        },
        "page_size": 50,
    }
)
resp.raise_for_status()
tasks = resp.json().get("results", [])

if not tasks:
    print("✅ Nenhuma tarefa para promover hoje.")
else:
    print(f"📋 {len(tasks)} tarefa(s) a promover para To-Do...")
    for task in tasks:
        name = ""
        title = task.get("properties", {}).get("Name", {}).get("title", [])
        if title:
            name = title[0]["plain_text"]

        r = requests.patch(
            f"https://api.notion.com/v1/pages/{task['id']}",
            headers=HEADERS,
            json={"properties": {"Status": {"status": {"name": "To-Do"}}}},
        )
        r.raise_for_status()
        print(f"  ✓ '{name}' → To-Do")

    print("✅ Concluído!")
