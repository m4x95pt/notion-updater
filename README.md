# Main Page Notion Updater

## Overview

This repository contains automation scripts in Python to update your Notion Main Page with data from personal workflows, including academic, books, tasks, expenses, and fitness activities.

## Features

- **Automatic Notion main page update:** Aggregates tasks, deadlines, reading, expenses, Strava activities, and journal entries and formats them into rich Notion blocks.
- **Scheduled automation:** Seamlessly run via GitHub Actions or cron jobs.
- **Task promotion:** Automatically moves tasks from "Inbox" to "To-Do" when their due date arrives.
- **Integration:** Connects to Notion API ([token-based]) and optional integrations (Strava, Slack commands).
- **Personal databases:** Uses custom Notion databases for tasks, expenses, books, journal, etc.

## Requirements

- Python 3.12+
- `requests` package
- Notion integration token

## Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/m4x95pt/notion-updater
   cd notion-updater
   pip install requests
   ```

2. Set up environment variables (`.env` or export):

   ```
   NOTION_TOKEN=...
   # Add integration tokens as needed (STRAVA, SLACK, etc)
   ```

3. Edit database IDs in the scripts if your Notion DBs differ.

4. Run manually:
   ```bash
   python update_notion.py
   python promote_tasks.py
   ```
   Or use the preconfigured GitHub Actions for automation.

## Notion Databases

| Purpose  | Database ID                        |
| -------- | ---------------------------------- |
| Tasks    | `2a7c4bee3163813cbf9acda129ead602` |
| Expenses | `30dc4bee316381e1b741d99f75355963` |
| Books    | `1abc4bee31638134a5d6f84162c5bd91` |
| Journal  | `30ac4bee3163818881aec20fa438d8b2` |
| Strava   | `a7aecc46c1454d9494d7cfb2d87ba57e` |
| Topics   | `2a5c4bee31638103a42ee9e2fa528806` |

## GitHub Actions Workflows

- **notion-updater.yml**: Updates your Notion page every 10 minutes.
- **promote-tasks.yml**: Promotes scheduled tasks daily at 6 AM UTC.

## License

MIT License

**Author:** [@m4x95pt](https://github.com/m4x95pt)
