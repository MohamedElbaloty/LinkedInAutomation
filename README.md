# ai_news_agent 🤖📰

An automated AI news agent pipeline built in Python that tracks high-impact Artificial Intelligence breakthroughs, generates engaging LinkedIn-style posts in technical Arabic (with industry-standard English terminology), generates matching clean editorial tech visualizations using Google Imagen 3 via the official Google GenAI SDK (`google-genai`), and publishes the bundle to a Telegram channel or chat on an automated schedule (twice daily at 09:00 and 18:00).

---

## 🌟 Key Features

- **Automated RSS Ingestion**: Scrapes curated AI news sources (TechCrunch AI, VentureBeat AI, MIT Technology Review, Google News AI, The Verge AI).
- **Intelligent HTML Cleaning**: Sanitizes feeds using `BeautifulSoup` to extract clean, unpolluted article text.
- **Duplicate Prevention**: Tracks processed articles in a local SQLite database (`posted_news` table with `id`, `title`, `published_at`).
- **Technical Arabic Post Generation**: Uses Gemini models to produce LinkedIn posts crafted for developers and tech executives:
  - 🚀 **Catchy Hook**: Punchy opener highlighting the core disruption.
  - 🔬 **Technical Breakdown**: Bullet points detailing architecture, mechanism, benchmarks, and engineering impact.
  - 💬 **Strategic Call-to-Action (CTA)**: Provocative technical question for comment section debate.
  - 🏷️ **Hashtags**: Standardized tags (`#AI #SoftwareEngineering #AgenticAI`) + context tags.
- **Editorial Visuals with Imagen 3**: Synthesizes an English prompt and invokes `imagen-3.0-generate-002` via `google-genai` for a modern, minimalist 3D editorial visual asset.
- **Smart Telegram Delivery**: Uses `python-telegram-bot` with automatic caption limit detection:
  - Captions $\le$ 1024 chars are sent directly with the photo.
  - Posts $>$ 1024 chars send the photo with the hook banner followed immediately by the complete formatted post text.
- **Automated Scheduling**: Executes an immediate check on startup, followed by recurring execution twice daily (09:00 and 18:00) using `APScheduler`.

---

## 📁 Project Structure

```
LinkedInWorkFlow/
├── config.py             # Configuration, environment variables, RSS feeds list
├── fetcher.py            # RSS parsing, HTML cleaning, relevance scoring, SQLite deduplication
├── ai_generator.py       # Google GenAI SDK (Gemini post & prompt drafting, Imagen 3 generation)
├── telegram_bot.py       # Telegram publisher with caption limit & markdown error handling
├── main.py               # Orchestrator with CLI flags and APScheduler (09:00 & 18:00)
├── requirements.txt      # Project dependencies
├── .env.example          # Environment variables template
├── .env                  # Your private environment variables (create from .env.example)
└── README.md             # Documentation and usage guide
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.11)
- A **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))
- A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- A **Telegram Chat ID** or Channel Username (e.g. `@your_channel` or `-1001234567890`)

### 2. Clone / Open Directory & Create Virtual Environment

```bash
# Create and activate a virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# (Linux / macOS)
# python3 -m venv venv
# source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

Open `.env` and fill in your credentials:

```ini
# Google Gemini & Imagen API Key
GEMINI_API_KEY=AIzaSy...

# Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...

# Telegram Target Chat / Channel ID
TELEGRAM_CHAT_ID=-1001234567890

# Optional Settings (Defaults shown)
TEXT_MODEL=gemini-2.5-flash
IMAGE_MODEL=imagen-3.0-generate-002
DB_PATH=news_history.db
IMAGES_DIR=output_images
SCHEDULE_HOURS=9,18
```

> **Tip for finding Telegram Chat ID**:
> - For a channel: add your bot as an Administrator to the channel, then use the `@channel_username` (e.g., `@my_ai_channel`) or forward a message from the channel to `@userinfobot` / `@getidsbot` to get the numeric channel ID (e.g. `-100...`).
> - For a personal chat: send a message to `@userinfobot` to get your Telegram user ID.

---

## 💻 Usage Instructions

### Single-Run Mode (Run Once & Exit)
Executes a single check, generates the post/image, dispatches to Telegram, and exits immediately:

```bash
python main.py --run-once
```

### Dry-Run Mode (Testing without Telegram/DB)
Fetches articles and generates content using the AI models, logs the post and image location, but does **not** publish to Telegram or mark the article as posted:

```bash
python main.py --run-once --dry-run
```

### Scheduled Daemon Mode (Default)
Runs an initial check immediately upon launch, then keeps running in the background, triggering automatically at **09:00** and **18:00** every day:

```bash
python main.py
```

To exit scheduled mode, press `Ctrl+C`.

---

## 🛠️ Module Walkthrough

| Module | Responsibility |
|---|---|
| [`config.py`](file:///c:/Users/lenovo/Downloads/LinkedInWorkFlow/config.py) | Loads `.env`, defines `AI_RSS_FEEDS`, models, database paths, and scheduler hours. |
| [`fetcher.py`](file:///c:/Users/lenovo/Downloads/LinkedInWorkFlow/fetcher.py) | Fetches RSS feeds, cleans HTML with `BeautifulSoup`, scores AI relevance, and prevents duplicate processing with SQLite `posted_news`. |
| [`ai_generator.py`](file:///c:/Users/lenovo/Downloads/LinkedInWorkFlow/ai_generator.py) | Calls `google-genai` with `gemini-2.5-flash` for the Arabic LinkedIn copy and English image prompt, and `imagen-3.0-generate-002` for the visual. |
| [`telegram_bot.py`](file:///c:/Users/lenovo/Downloads/LinkedInWorkFlow/telegram_bot.py) | Dispatches the image and text bundle asynchronously via `python-telegram-bot` with caption limit logic. |
| [`main.py`](file:///c:/Users/lenovo/Downloads/LinkedInWorkFlow/main.py) | Orchestrates the pipeline and manages `APScheduler` cron jobs for twice-daily runs. |

---

## 🛡️ License

MIT License. Feel free to modify and deploy for personal or production channels.
