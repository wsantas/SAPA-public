# SAPA — Set Apart Personal Assistant

**A self-hosted family dashboard for people who take health, land, and learning seriously.**

SAPA is a plugin-based personal assistant that runs on a Raspberry Pi (or any machine with Python). No cloud. No subscriptions. No one mining your health data. Just a single-page app that watches your filesystem, extracts knowledge, tracks your gaps, plans your meals, and keeps your family's health and homestead goals organized — all from one screen.

Built by a family. For a family. Open-sourced because the best tools shouldn't require a monthly fee or a terms-of-service agreement.

---

## What It Actually Does

**Drop a markdown file. SAPA does the rest.**

Write up what you learned about soil amendments, or paste in a deep dive on mobility training, or save your favorite bone broth recipe as a `.md` file. Drop it in your inbox folder. SAPA's file watcher picks it up instantly, extracts topics, logs it to your learning history, updates your knowledge gaps, and pushes a real-time notification to every connected device. No buttons to click. No forms to fill out.

### Health Tracking (Per-Person)
- **Knowledge gap analysis** — Define what you want to learn. SAPA tracks what you've covered and tells you what's missing. Click a gap, get a ready-made AI prompt to fill it.
- **311 recipes** across 6 dietary frameworks (paleo, dairy-free, gluten-free, performance, chef collections). Auto-filters by dietary needs per profile.
- **Cooking mode** — Full-screen, step-by-step, hands-free. Arrow keys or tap to navigate. Screen stays awake.
- **Meal planning** — Family meal requests, weekly calendar, auto-generated grocery lists with smart ingredient merging.
- **HULK training log** — Workouts, exercises, PRs, volume tracking, readiness scores from daily recovery metrics.
- **Protocols & reminders** — Multi-phase plans (rehab protocols, supplement cycles, training blocks) with recurring reminders.
- **Interactive body maps** — SVG anatomy with clickable muscles, color-coded status, and linked exercises. Custom maps per person.
- **Spaced repetition** — Topics decay over time. SAPA surfaces what's due for review.
- **Protein tracking** — Quick-add buttons on the dashboard, daily goals, streak counter.

### Homestead Knowledge Base (Family-Shared)
- **Same gap analysis system** for gardening, livestock, preservation, permaculture, off-grid skills, and more.
- **Topic extraction** from 300+ homesteading terms — drop a guide on chicken health or rainwater harvesting and watch your coverage climb.
- **Shared learning history** — Everyone contributes, everyone benefits.

### Calendar
- ICS feed integration (Google Calendar, any `.ics` URL).
- Today's schedule widget on the dashboard. Full week view in the calendar panel.

### Family Profiles
Two demo profiles out of the box — one focused on strength training, another on mobility. Each person gets their own:
- Learning history and knowledge gaps
- Dietary filters and recipe favorites
- Training logs, recovery metrics, body measurements
- Custom dashboard tabs
- Cookie-based switching — no login required on a home network

### Real-Time Everything
- **WebSocket** push on every file event — new session, modified, deleted
- **PWA** — install on your phone's home screen, works offline
- **Email notifications** — get an email when new content is processed (configurable per profile, SMTP-based)

---

## Architecture

```
~/.sapa/
├── config.json              # SMTP, calendar URLs, preferences
├── learning.db              # Single SQLite database (all plugins)
└── plugins/
    ├── health/
    │   └── inbox/
    │       ├── john/         # Drop .md files here → John's profile
    │       └── jane/
    └── homestead/
        └── inbox/            # Family-shared content
```

SAPA is a **FastAPI** app that assembles a single HTML page at startup from plugin contributions. Each plugin provides its own CSS, JS, HTML panels, API routes, and database migrations. The page is cached and served on every request — zero client-side routing, zero build step, zero JavaScript framework.

**Plugins are the whole game:**

| Plugin | Scope | What It Does |
|--------|-------|--------------|
| `health` | Per-person | Training, nutrition, recipes, protocols, gap analysis, body maps |
| `homestead` | Family | Gardening, livestock, preservation, land management knowledge |
| `calendar` | Family | ICS feed display, schedule widgets |

**Adding a new plugin** = create a folder with `plugin.py`, `routes.py`, `tracker.py`, and a `static/` directory. Register it in `app.py`. Done. The framework handles migrations, routing, and page assembly.

### Tech Stack
- **Backend:** FastAPI + Uvicorn + SQLite
- **Frontend:** Vanilla JS (no framework, no build step, no node_modules)
- **File watching:** Watchdog (filesystem events → topic extraction → WebSocket broadcast)
- **Deployment:** Raspberry Pi + systemd + rsync
- **Notifications:** stdlib `smtplib` (no external email service required)

### No External Dependencies Worth Worrying About
No Redis. No Postgres. No Docker (unless you want it). No cloud functions. No API keys required (unless you connect a calendar feed). The entire app runs on a $35 Pi with a SQLite file and a folder full of markdown.

---

## Getting Started

### Prerequisites
- Python 3.11+
- A machine to run it on (Raspberry Pi, old laptop, VM, whatever)

### Install

```bash
git clone git@github.com:wsantas/SAPA-public.git
cd sapa
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run

```bash
PYTHONPATH=. .venv/bin/python -m sapa.app --port 8001
```

Open `http://localhost:8001`. That's it.

### Feed Content

Drop a `.md` file into the inbox:

```bash
# Health content for a specific person
cp my-article.md ~/.sapa/plugins/health/inbox/john/

# Homestead content (shared)
cp gardening-guide.md ~/.sapa/plugins/homestead/inbox/
```

SAPA's watchdog picks it up, extracts topics, saves to history, and pushes a WebSocket update to connected browsers.

### Deploy to a Pi

```bash
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  ~/dev/sapa/ user@your-pi:~/sapa/

# On the Pi — set up as a systemd service
# (see templates/ directory for example unit file)
```

---

## Configuration

Copy `config.example.json` to `~/.sapa/config.json` and customize:

```json
{
  "user_name": "Your Name",
  "email": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "you@example.com",
    "smtp_password": "your-app-password",
    "smtp_tls": true,
    "from_address": "sapa@example.com",
    "recipients": {
      "1": "person1@example.com",
      "2": "person2@example.com"
    },
    "homestead_recipients": ["person1@example.com", "person2@example.com"]
  }
}
```

Email is optional. If the config block is missing, notifications silently skip.

---

## Customizing for Your Family

SAPA ships with two demo profiles as examples. To make it yours:

1. **Profiles** — Edit `sapa/db.py` `ensure_default_profiles()` to set your family members' names.
2. **Gap targets** — Edit `sapa/plugins/health/gap_targets.py` to define what each person wants to learn.
3. **Extraction terms** — Edit `sapa/plugins/health/content.py` and `sapa/plugins/homestead/content.py` to add terms relevant to your family's topics.
4. **Recipes** — Add/remove JSON recipe files in `sapa/plugins/health/data/recipes/`.
5. **Body maps** — Customize the SVG anatomy maps in the health plugin's panels HTML.
6. **Profile tabs** — Edit the plugin's `get_profile_tabs()` to control which tabs each person sees.

---

## The Content Pipeline

```
You write (or AI generates) a .md file
        │
        ▼
Drop it in an inbox folder
        │
        ▼
Watchdog detects the new file (0.3s delay for write flush)
        │
        ▼
Parse frontmatter (YAML) + extract body
        │
        ▼
Route to correct profile (based on subdirectory name)
        │
        ▼
Extract topics via keyword matching against term list
        │
        ▼
Record topics in DB (with confidence scores)
        │
        ▼
Save full content to history table
        │
        ▼
Broadcast WebSocket event → all connected browsers refresh
        │
        ▼
Send email notification (if configured)
        │
        ▼
Gap analysis updates automatically
```

**The feedback loop:** Gap analysis shows you what you don't know → click a gap to get an AI prompt → feed the response back as a `.md` file → gap closes → new gaps surface. Your knowledge base grows with every file you drop.

---

## Why "Set Apart"?

The name comes from the Hebrew word *qadash* — to be set apart, consecrated, dedicated to a purpose. This app exists because we believe families should own their health data, their learning, and their tools. Not rent them. Not hand them to a corporation. Not hope the service doesn't shut down or change its pricing.

SAPA is set apart from the SaaS treadmill. It runs on hardware you own, stores data in files you control, and works without an internet connection. It's built for families who grow their own food, train in their garage, and take responsibility for their own health.

---

## Contributing

This project started as a personal tool and grew into something worth sharing. Contributions are welcome.

**Good first contributions:**
- New recipe JSON files (follow the existing format in `sapa/plugins/health/data/recipes/`)
- New homestead extraction terms in `content.py`
- Bug fixes and performance improvements
- New plugins (the plugin system makes this straightforward)
- Mobile UI improvements
- Documentation

**Before submitting a PR:**
- Test locally with `PYTHONPATH=. .venv/bin/python -m sapa.app --port 8001`
- Keep it simple — this project values clarity over cleverness
- No new JavaScript frameworks. Vanilla JS is a feature, not a limitation.

---

## License

[MIT](LICENSE) — Use it, fork it, modify it, sell it, deploy it for your family, your church, your community. Just don't blame us if your sourdough starter dies.

---

## Screenshots

*Coming soon — contributions welcome.*

---

<p align="center">
  <em>Built with FastAPI, SQLite, vanilla JS, and the conviction that your family's data belongs to your family.</em>
</p>
