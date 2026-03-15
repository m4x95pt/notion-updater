# notion-updater

Servidor Express.js auto-hospedado que centraliza automações pessoais via Notion API. Corre num servidor Debian doméstico gerido com pm2, exposto externamente via Cloudflare Tunnel.

## O que faz

- **Slash commands Slack** para adicionar tarefas, livros e despesas diretamente ao Notion
- **Sincronização automática** de dados do Strava (corridas, atividades)
- **Sync do Inforestudante** (UC) — importação de dados académicos para o Notion
- **Agendamento via cron** — atualizações a cada 10 minutos

## Stack

- **Runtime:** Node.js + Express.js
- **Process manager:** pm2
- **Hosting:** Servidor Debian doméstico (IP estático `192.168.1.158`)
- **Tunnel:** Cloudflare Tunnel → `pedrosmachine.site`
- **Integrações:** Notion API, Slack Webhooks

## Estrutura

```
notion-updater/
├── server.js          # Servidor principal + slash commands Slack
├── ecosystem.config.js # Configuração pm2
└── .env               # Variáveis de ambiente (não incluído)
```

## Variáveis de ambiente

```env
NOTION_TOKEN=...
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=...
STRAVA_CLIENT_ID=...
STRAVA_CLIENT_SECRET=...
STRAVA_REFRESH_TOKEN=...
GMAIL_APP_PASSWORD=...
```

## Instalação

```bash
git clone https://github.com/m4x95pt/notion-updater
cd notion-updater
npm install
cp .env.example .env
# Preenche as variáveis no .env
pm2 start ecosystem.config.js
pm2 save
```

## Slash Commands Slack disponíveis

| Comando | Descrição |
|---------|-----------|
| `/task [nome]` | Adiciona tarefa à DB de Tasks |
| `/book [título]` | Adiciona livro à DB de Books |
| `/expense [valor] [categoria] [descrição]` | Regista despesa na DB de Expenses |

## Bases de dados Notion

| DB | ID |
|----|----|
| Expenses | `30dc4bee316381e1b741d99f75355963` |
| Months | `30dc4bee316381e1a2b2e1f2c0fc42e9` |

## GitHub Actions (workflows automáticos)

| Workflow | Schedule |
|----------|----------|
| Notion Updater | A cada 10 minutos |
| Strava Sync | 9h e 10h diariamente |
| Infoestudante Sync | De hora em hora |
