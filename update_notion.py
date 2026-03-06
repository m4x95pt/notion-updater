import os
import requests
from datetime import datetime, timezone

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
MAIN_PAGE_ID = "31bc4bee-3163-81c4-93db-c02608cab7dd"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ─── IDs das bases de dados ─────────────────────────────────────────────────
TASKS_DB_ID    = "2a7c4bee3163813cbf9acda129ead602"
EXPENSES_DB_ID = "30dc4bee316381e1b741d99f75355963"
BOOKS_DB_ID    = "1abc4bee31638134a5d6f84162c5bd91"
JOURNAL_DB_ID  = "30ac4bee3163818881aec20fa438d8b2"


# ─── Helpers de dados ────────────────────────────────────────────────────────

def query_db(db_id, filter_body=None, sorts=None, page_size=10):
    body = {"page_size": page_size}
    if filter_body:
        body["filter"] = filter_body
    if sorts:
        body["sorts"] = sorts
    r = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=HEADERS, json=body,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def get_prop(page, name, fallback="—"):
    p = page.get("properties", {}).get(name, {})
    t = p.get("type")
    if t == "title":
        items = p.get("title", [])
        return items[0]["plain_text"] if items else fallback
    if t == "rich_text":
        items = p.get("rich_text", [])
        return items[0]["plain_text"] if items else fallback
    if t == "select":
        s = p.get("select")
        return s["name"] if s else fallback
    if t == "status":
        s = p.get("status")
        return s["name"] if s else fallback
    if t == "number":
        v = p.get("number")
        return v if v is not None else fallback
    if t == "date":
        d = p.get("date")
        return d["start"] if d else fallback
    if t == "formula":
        f = p.get("formula", {})
        ft = f.get("type")
        return f.get(ft, fallback)
    return fallback


def page_url(page):
    return page.get("url", "")


def fmt_date(iso):
    if not iso or iso == "—":
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%-d %b")
    except Exception:
        return iso


def days_until(iso):
    if not iso or iso == "—":
        return None
    try:
        d = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
        return (d - datetime.now(timezone.utc)).days
    except Exception:
        return None


def progress_bar(current, total, width=15):
    if not total:
        return "░" * width + " 0%"
    pct = min(int(current / total * 100), 100)
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled) + f"  {pct}%"


# ─── Recolha de dados ────────────────────────────────────────────────────────

def safe(fn, name):
    try:
        result = fn()
        print(f"  ✓ {name}")
        return result
    except Exception as e:
        print(f"  ⚠️  {name} falhou: {e}")
        return [] if name != "journal" else None


def get_pending_tasks():
    results = query_db(
        TASKS_DB_ID,
        filter_body={"and": [
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Inbox"}},
        ]},
        sorts=[{"property": "Due Date", "direction": "ascending"}],
        page_size=6,
    )
    return [{"name": get_prop(p, "Name"), "status": get_prop(p, "Status"),
             "priority": get_prop(p, "Priority"), "due": get_prop(p, "Due Date"),
             "tag": get_prop(p, "Tag"), "url": page_url(p)} for p in results]


def get_upcoming_deadlines():
    results = query_db(
        TASKS_DB_ID,
        filter_body={"and": [
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Due Date", "date": {"is_not_empty": True}},
            {"or": [
                {"property": "Tag", "select": {"equals": "Study"}},
                {"property": "Tag", "select": {"equals": "Work"}},
            ]},
        ]},
        sorts=[{"property": "Due Date", "direction": "ascending"}],
        page_size=5,
    )
    out = []
    for p in results:
        due = get_prop(p, "Due Date")
        d = days_until(due)
        if d is not None and d <= 14:
            out.append({"name": get_prop(p, "Name"), "due": due, "days": d, "url": page_url(p)})
    return out


def get_current_books():
    results = query_db(
        BOOKS_DB_ID,
        filter_body={"property": "Status", "select": {"equals": "Reading"}},
        page_size=5,
    )
    return [{"title": get_prop(p, "Title"), "author": get_prop(p, "Author"),
             "current": get_prop(p, "Current Page", 0) or 0,
             "total": get_prop(p, "Total Pages", 0) or 0,
             "url": page_url(p)} for p in results]


def get_recent_expenses():
    results = query_db(
        EXPENSES_DB_ID,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=5,
    )
    return [{"source": get_prop(p, "Source"), "amount": get_prop(p, "Amount"),
             "tag": get_prop(p, "Tags"), "date": get_prop(p, "Date")} for p in results]


def get_last_journal_entry():
    results = query_db(
        JOURNAL_DB_ID,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=1,
    )
    if results:
        p = results[0]
        return {"name": get_prop(p, "Name"), "date": get_prop(p, "Date"), "url": page_url(p)}
    return None


# ─── Helpers para construir blocos Notion ────────────────────────────────────

def rt(text, bold=False, url=None):
    obj = {"type": "text", "text": {"content": text}}
    if url:
        obj["text"]["link"] = {"url": url}
    if bold:
        obj["annotations"] = {"bold": True}
    return obj


def heading2(text):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [rt(text)]}}


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


def paragraph(parts):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": parts}}


def callout(parts, icon="💡", color="default"):
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": parts,
            "icon": {"type": "emoji", "emoji": icon},
            "color": color,
        }
    }


def table_block(headers, rows):
    all_rows = [{"type": "table_row", "table_row": {"cells": [[rt(h, bold=True)] for h in headers]}}]
    for row in rows:
        all_rows.append({"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}})
    return {
        "object": "block", "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": all_rows,
        }
    }


# ─── Construção da página ────────────────────────────────────────────────────

def build_blocks(tasks, deadlines, books, expenses, journal):
    now = datetime.now().strftime("%-d de %B de %Y · %H:%M")
    blocks = []

    # Cabeçalho
    blocks.append({"object": "block", "type": "quote",
                   "quote": {"rich_text": [rt(f"🗓️ Actualizado automaticamente · {now}")]}})
    blocks.append(divider())

    # ── TAREFAS PENDENTES ──────────────────────────────────────────────────
    blocks.append(heading2("✅ Tarefas Pendentes"))
    if tasks:
        for t in tasks:
            icon = {"High": "🔴", "Medium": "🟡", "Low": "🔵"}.get(t["priority"], "⚪")
            status = {"To-Do": "A fazer", "Doing": "Em curso"}.get(t["status"], t["status"])
            due_str = f"  ·  Due: {fmt_date(t['due'])}" if t["due"] != "—" else ""
            tag_str = f"  ·  {t['tag']}" if t["tag"] != "—" else ""
            blocks.append(callout(
                [rt(t["name"], bold=True),
                 rt(f"  —  {status}{due_str}{tag_str}  "),
                 rt("→ Abrir", url=t["url"])],
                icon=icon
            ))
    else:
        blocks.append(callout([rt("Sem tarefas pendentes — bom trabalho! 🎉")],
                               icon="✅", color="green_background"))

    blocks.append(paragraph([
        rt("→ Ver todas as tarefas", url="https://www.notion.so/2a7c4bee3163806e97f4ca613d9f4e9b"),
        rt("  ·  "),
        rt("→ Hoje", url="https://www.notion.so/2a7c4bee31638189b128ed40f4df896c"),
        rt("  ·  "),
        rt("→ Esta semana", url="https://www.notion.so/2a7c4bee3163813fba6ef60ba8d14b50"),
    ]))
    blocks.append(divider())

    # ── PRÓXIMAS ENTREGAS ──────────────────────────────────────────────────
    blocks.append(heading2("📅 Próximas Entregas"))
    if deadlines:
        for d in deadlines:
            icon = "🔴" if d["days"] <= 3 else ("🟡" if d["days"] <= 7 else "🟢")
            color = "red_background" if d["days"] <= 3 else ("yellow_background" if d["days"] <= 7 else "green_background")
            day_label = f"{d['days']} dia{'s' if d['days'] != 1 else ''}"
            blocks.append(callout(
                [rt(d["name"], bold=True),
                 rt(f"  —  {fmt_date(d['due'])} ({day_label})  "),
                 rt("→ Abrir", url=d["url"])],
                icon=icon, color=color
            ))
    else:
        blocks.append(paragraph([rt("Sem entregas próximas nos próximos 14 dias. ✨")]))

    blocks.append(paragraph([
        rt("→ Study Scheduler", url="https://www.notion.so/2a5c4bee31638067bdedffc59081dad8"),
    ]))
    blocks.append(divider())

    # ── LEITURA ────────────────────────────────────────────────────────────
    blocks.append(heading2("📖 A Ler Agora"))
    if books:
        for b in books:
            bar = progress_bar(b["current"], b["total"])
            blocks.append(callout(
                [rt(f"{b['title']}", bold=True),
                 rt(f"  —  {b['author']}\n"),
                 rt(f"Página {b['current']} / {b['total']}  ·  {bar}\n"),
                 rt("→ Actualizar progresso", url=b["url"])],
                icon="📗", color="gray_background"
            ))
    else:
        blocks.append(paragraph([rt("Nenhum livro em leitura de momento.")]))

    blocks.append(paragraph([
        rt("→ Ver todos os livros", url="https://www.notion.so/1abc4bee316380a38e8bcfc45607b61c"),
    ]))
    blocks.append(divider())

    # ── GASTOS RECENTES ────────────────────────────────────────────────────
    blocks.append(heading2("💸 Gastos Recentes"))
    if expenses:
        rows = []
        for e in expenses:
            val = f"{e['amount']:.2f} €" if isinstance(e["amount"], (int, float)) else "—"
            rows.append([fmt_date(e["date"]), e["source"], e["tag"], val])
        blocks.append(table_block(["Data", "Descrição", "Categoria", "Valor"], rows))
    else:
        blocks.append(paragraph([rt("Sem gastos registados.")]))

    blocks.append(paragraph([
        rt("→ Adicionar gasto", url="https://www.notion.so/30dc4bee3163805392f8de7349c811d3"),
        rt("  ·  "),
        rt("→ Finance Tracker", url="https://www.notion.so/30dc4bee3163805392f8de7349c811d3"),
    ]))
    blocks.append(divider())

    # ── JOURNAL ────────────────────────────────────────────────────────────
    blocks.append(heading2("✏️ Journal"))
    if journal:
        blocks.append(callout(
            [rt("Última entrada:  ", bold=True),
             rt(f"{journal['name']}  —  {fmt_date(journal['date'])}  "),
             rt("→ Ver entrada", url=journal["url"])],
            icon="✏️", color="gray_background"
        ))
    blocks.append(paragraph([
        rt("→ Nova entrada", url="https://www.notion.so/30ac4bee3163803b929fe36123bc8f02"),
        rt("  ·  "),
        rt("→ Morning Pages", url="https://www.notion.so/30ac4bee31638102a14cd5ddef187261"),
        rt("  ·  "),
        rt("→ Daily Gratitude", url="https://www.notion.so/30ac4bee3163813989d5d45d3850bc2a"),
    ]))

    return blocks


# ─── Actualizar a página no Notion ──────────────────────────────────────────

def update_main_page(blocks):
    # 1. Apagar blocos existentes
    r = requests.get(f"https://api.notion.com/v1/blocks/{MAIN_PAGE_ID}/children", headers=HEADERS)
    r.raise_for_status()
    for block in r.json().get("results", []):
        requests.delete(f"https://api.notion.com/v1/blocks/{block['id']}", headers=HEADERS)

    # 2. Inserir novos blocos em lotes de 100
    for i in range(0, len(blocks), 100):
        r = requests.patch(
            f"https://api.notion.com/v1/blocks/{MAIN_PAGE_ID}/children",
            headers=HEADERS,
            json={"children": blocks[i:i + 100]},
        )
        r.raise_for_status()

    print(f"✅ Main Page actualizada! ({datetime.now().strftime('%H:%M:%S')})")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 A recolher dados do Notion...")
    tasks     = safe(get_pending_tasks,      "tarefas pendentes")
    deadlines = safe(get_upcoming_deadlines, "entregas próximas")
    books     = safe(get_current_books,      "livros em leitura")
    expenses  = safe(get_recent_expenses,    "gastos recentes")
    journal   = safe(get_last_journal_entry, "journal")

    print("📝 A construir blocos...")
    blocks = build_blocks(tasks or [], deadlines or [], books or [], expenses or [], journal)

    print("🚀 A actualizar a Main Page...")
    update_main_page(blocks)
