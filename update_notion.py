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

# ─── IDs das tuas bases de dados ───────────────────────────────────────────
TASKS_DB_ID      = "2a7c4bee3163813cbf9acda129ead602"
EXPENSES_DB_ID   = "30dc4bee316381e1b741d99f75355963"
BOOKS_DB_ID      = "1abc4bee31638134a5d6f84162c5bd91"
JOURNAL_DB_ID    = "30ac4bee3163818881aec20fa438d8b2"


# ─── Helpers ────────────────────────────────────────────────────────────────

def query_db(db_id, filter_body=None, sorts=None, page_size=10):
    body = {"page_size": page_size}
    if filter_body:
        body["filter"] = filter_body
    if sorts:
        body["sorts"] = sorts
    r = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=HEADERS,
        json=body,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def get_prop(page, name, fallback="—"):
    props = page.get("properties", {})
    p = props.get(name, {})
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
    if t == "checkbox":
        return p.get("checkbox", False)
    if t == "formula":
        f = p.get("formula", {})
        ft = f.get("type")
        if ft == "number":
            return f.get("number", fallback)
        if ft == "string":
            return f.get("string", fallback)
    return fallback


def page_url(page):
    return page.get("url", "").replace("https://www.notion.so/", "https://www.notion.so/")


def progress_bar(current, total, width=20):
    if not total or total == 0:
        return "░" * width + " 0%"
    pct = min(int(current / total * 100), 100)
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {pct}%"


def fmt_date(iso):
    if iso == "—" or not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%-d %b")   # ex: "9 Mar"
    except Exception:
        return iso


def days_until(iso):
    if iso == "—" or not iso:
        return None
    try:
        d = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
        delta = (d - datetime.now(timezone.utc)).days
        return delta
    except Exception:
        return None


# ─── Recolha de dados ───────────────────────────────────────────────────────

def get_pending_tasks():
    results = query_db(
        TASKS_DB_ID,
        filter_body={
            "and": [
                {"property": "Status", "status": {"does_not_equal": "Done"}},
                {"property": "Status", "status": {"does_not_equal": "Inbox"}},
            ]
        },
        sorts=[{"property": "Due Date", "direction": "ascending"}],
        page_size=8,
    )
    tasks = []
    for p in results:
        tasks.append({
            "name":     get_prop(p, "Name"),
            "status":   get_prop(p, "Status"),
            "priority": get_prop(p, "Priority"),
            "due":      get_prop(p, "Due Date"),
            "tag":      get_prop(p, "Tag"),
            "url":      page_url(p),
        })
    return tasks


def get_upcoming_deadlines():
    """Tarefas com due date nos próximos 14 dias, tag Study ou Work."""
    results = query_db(
        TASKS_DB_ID,
        filter_body={
            "and": [
                {"property": "Status", "status": {"does_not_equal": "Done"}},
                {"property": "Due Date", "date": {"is_not_empty": True}},
                {"or": [
                    {"property": "Tag", "select": {"equals": "Study"}},
                    {"property": "Tag", "select": {"equals": "Work"}},
                ]},
            ]
        },
        sorts=[{"property": "Due Date", "direction": "ascending"}],
        page_size=5,
    )
    deadlines = []
    for p in results:
        due = get_prop(p, "Due Date")
        d = days_until(due)
        if d is not None and d <= 14:
            deadlines.append({
                "name": get_prop(p, "Name"),
                "due":  due,
                "days": d,
                "url":  page_url(p),
            })
    return deadlines


def get_current_books():
    results = query_db(
        BOOKS_DB_ID,
        filter_body={"property": "Status", "select": {"equals": "Reading"}},
        page_size=5,
    )
    books = []
    for p in results:
        current = get_prop(p, "Current Page", 0) or 0
        total   = get_prop(p, "Total Pages", 0) or 0
        books.append({
            "title":   get_prop(p, "Title"),
            "author":  get_prop(p, "Author"),
            "current": current,
            "total":   total,
            "bar":     progress_bar(current, total),
            "url":     page_url(p),
        })
    return books


def get_recent_expenses():
    results = query_db(
        EXPENSES_DB_ID,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=5,
    )
    expenses = []
    for p in results:
        expenses.append({
            "source": get_prop(p, "Source"),
            "amount": get_prop(p, "Amount"),
            "tag":    get_prop(p, "Tags"),
            "date":   get_prop(p, "Date"),
        })
    return expenses


def get_last_journal_entry():
    results = query_db(
        JOURNAL_DB_ID,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=1,
    )
    if results:
        p = results[0]
        return {
            "name": get_prop(p, "Name"),
            "date": get_prop(p, "Date"),
            "url":  page_url(p),
        }
    return None


# ─── Build do conteúdo ──────────────────────────────────────────────────────

def build_content(tasks, deadlines, books, expenses, journal):
    now = datetime.now().strftime("%A, %-d de %B de %Y · %H:%M")
    lines = []

    # Cabeçalho
    lines.append(f"> 🗓️ Actualizado automaticamente · {now}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── TAREFAS PENDENTES ──
    lines.append("## ✅ Tarefas Pendentes")
    lines.append("")
    if tasks:
        for t in tasks:
            priority_icon = {"High": "🔴", "Medium": "🟡", "Low": "🔵"}.get(t["priority"], "⚪")
            status_label  = {"To-Do": "A fazer", "Doing": "Em curso"}.get(t["status"], t["status"])
            due_str = f" · Due: **{fmt_date(t['due'])}**" if t["due"] != "—" else ""
            tag_str = f" · `{t['tag']}`" if t["tag"] != "—" else ""
            lines.append(f"::: callout {{icon=\"{priority_icon}\"}}")
            lines.append(f"**{t['name']}** — {status_label}{due_str}{tag_str}")
            lines.append(f"[→ Abrir]({t['url']})")
            lines.append(":::")
            lines.append("")
    else:
        lines.append("::: callout {icon=\"✅\" color=\"green_bg\"}")
        lines.append("**Sem tarefas pendentes — bom trabalho!** 🎉")
        lines.append(":::")
        lines.append("")

    lines.append("[→ Ver todas as tarefas](https://www.notion.so/2a7c4bee3163806e97f4ca613d9f4e9b) · [→ Hoje](https://www.notion.so/2a7c4bee31638189b128ed40f4df896c) · [→ Esta semana](https://www.notion.so/2a7c4bee3163813fba6ef60ba8d14b50)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── PRÓXIMAS ENTREGAS ──
    lines.append("## 📅 Próximas Entregas")
    lines.append("")
    if deadlines:
        for d in deadlines:
            urgency = "🔴" if d["days"] <= 3 else ("🟡" if d["days"] <= 7 else "🟢")
            day_label = f"{d['days']} dia{'s' if d['days'] != 1 else ''}"
            lines.append(f"::: callout {{icon=\"{urgency}\"}}")
            lines.append(f"**{d['name']}** — {fmt_date(d['due'])} ({day_label})")
            lines.append(f"[→ Abrir]({d['url']})")
            lines.append(":::")
            lines.append("")
    else:
        lines.append("Sem entregas próximas nos próximos 14 dias. ✨")
        lines.append("")

    lines.append("[→ Ver Study Scheduler](https://www.notion.so/2a5c4bee31638067bdedffc59081dad8)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── LEITURA ──
    lines.append("## 📖 A Ler Agora")
    lines.append("")
    if books:
        for b in books:
            lines.append(f"::: callout {{icon=\"📗\" color=\"gray_bg\"}}")
            lines.append(f"**{b['title']}** — {b['author']}")
            lines.append(f"Página **{b['current']} / {b['total']}** · {b['bar']}")
            lines.append(f"[→ Actualizar progresso]({b['url']})")
            lines.append(":::")
            lines.append("")
    else:
        lines.append("Nenhum livro em leitura de momento.")
        lines.append("")

    lines.append("[→ Ver todos os livros](https://www.notion.so/1abc4bee316380a38e8bcfc45607b61c)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── GASTOS RECENTES ──
    lines.append("## 💸 Gastos Recentes")
    lines.append("")
    if expenses:
        lines.append("| Data | Descrição | Categoria | Valor |")
        lines.append("| --- | --- | --- | --- |")
        for e in expenses:
            val = f"{e['amount']:.2f} €" if isinstance(e["amount"], (int, float)) else "—"
            lines.append(f"| {fmt_date(e['date'])} | {e['source']} | {e['tag']} | {val} |")
    else:
        lines.append("Sem gastos registados.")
    lines.append("")
    lines.append("[→ Adicionar gasto](https://www.notion.so/30dc4bee3163805392f8de7349c811d3) · [→ Finance Tracker](https://www.notion.so/30dc4bee3163805392f8de7349c811d3)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── JOURNAL ──
    lines.append("## ✏️ Journal")
    lines.append("")
    if journal:
        lines.append(f"::: callout {{icon=\"✏️\" color=\"gray_bg\"}}")
        lines.append(f"**Última entrada:** {journal['name']} — {fmt_date(journal['date'])}")
        lines.append(f"[→ Ver entrada]({journal['url']})")
        lines.append(":::")
        lines.append("")
    lines.append("[→ Nova entrada](https://www.notion.so/30ac4bee3163803b929fe36123bc8f02) · [→ Morning Pages](https://www.notion.so/30ac4bee31638102a14cd5ddef187261) · [→ Daily Gratitude](https://www.notion.so/30ac4bee3163813989d5d45d3850bc2a)")

    return "\n".join(lines)


# ─── Actualizar a página no Notion ──────────────────────────────────────────

def update_main_page(content: str):
    """Apaga o conteúdo da página e escreve o novo."""
    # 1. Buscar os block IDs existentes
    r = requests.get(
        f"https://api.notion.com/v1/blocks/{MAIN_PAGE_ID}/children",
        headers=HEADERS,
    )
    r.raise_for_status()
    blocks = r.json().get("results", [])

    # 2. Apagar cada bloco
    for block in blocks:
        requests.delete(
            f"https://api.notion.com/v1/blocks/{block['id']}",
            headers=HEADERS,
        )

    # 3. Inserir novo conteúdo linha a linha como blocos de parágrafo
    #    (a API do Notion aceita até 100 blocos por chamada)
    notion_blocks = []
    for line in content.split("\n"):
        if line.startswith("## "):
            notion_blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
            })
        elif line.startswith("> "):
            notion_blocks.append({
                "object": "block", "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        elif line.startswith("---"):
            notion_blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.startswith("| "):
            # Tabela: acumular linhas depois
            notion_blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
            })
        elif line.strip() == "":
            notion_blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": []}
            })
        else:
            notion_blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
            })

    # Enviar em lotes de 100
    for i in range(0, len(notion_blocks), 100):
        batch = notion_blocks[i:i + 100]
        r = requests.patch(
            f"https://api.notion.com/v1/blocks/{MAIN_PAGE_ID}/children",
            headers=HEADERS,
            json={"children": batch},
        )
        r.raise_for_status()

    print(f"✅ Main Page actualizada com sucesso! ({datetime.now().strftime('%H:%M:%S')})")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 A recolher dados do Notion...")

    tasks     = get_pending_tasks()
    deadlines = get_upcoming_deadlines()
    books     = get_current_books()
    expenses  = get_recent_expenses()
    journal   = get_last_journal_entry()

    print(f"  ✓ {len(tasks)} tarefas pendentes")
    print(f"  ✓ {len(deadlines)} entregas próximas")
    print(f"  ✓ {len(books)} livros em leitura")
    print(f"  ✓ {len(expenses)} gastos recentes")
    print(f"  ✓ última entrada: {journal['name'] if journal else '—'}")

    content = build_content(tasks, deadlines, books, expenses, journal)

    print("📝 A actualizar a Main Page...")
    update_main_page(content)