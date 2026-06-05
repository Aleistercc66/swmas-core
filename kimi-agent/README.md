# Kimi Telegram Agent 🤖

An intelligent Telegram bot that analyzes texts, photos, URLs, and news — performing deep research and verification before answering. Powered by LLM reasoning + real-time web research.

## Features

- **Text Analysis** — Summarize, extract key points, detect claims
- **Deep Research** (`/research`) — Multi-step research with source verification
- **Photo OCR** — Extract text from images + analyze visual content
- **URL Analysis** — Scrape webpages, verify claims, check sources
- **News Aggregation** (`/news`) — Multi-source news with fact-checking
- **Fact Verification** (`/verify`) — Cross-reference claims against sources
- **Per-User Memory** — SQLite conversation history and preferences
- **Greek + English** — Bilingual support

## Architecture

```
kimi-agent/
├── bot.py                 # Telegram bot entrypoint + dispatcher
├── config/               # Configuration
│   ├── __init__.py
│   └── settings.py       # Pydantic settings
├── handlers/             # Message handlers
│   ├── text.py          # Text analysis + research
│   ├── photo.py         # OCR + image analysis
│   ├── url.py           # URL scraping + verification
│   └── news.py          # News search + aggregation
├── research/            # Research engine
│   ├── search.py        # Web search (DuckDuckGo, Bing, Google)
│   ├── scraper.py       # Async web scraping
│   ├── verifier.py      # Fact verification engine
│   └── analyzer.py      # Analysis orchestrator
├── brain/               # LLM + memory
│   ├── llm.py          # OpenAI-compatible LLM interface
│   ├── memory.py       # SQLite conversation memory
│   └── prompt_builder.py # System prompts
├── utils/               # Utilities
│   └── helpers.py       # Formatting, rate limiting
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Install dependencies

```bash
# System dependencies (for OCR)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ell tesseract-ocr-eng

# Python dependencies
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

Required:
- `BOT_TOKEN` — From @BotFather
- `OPENAI_API_KEY` — From OpenAI or compatible provider

Optional:
- `BING_API_KEY` — For Bing search
- `GOOGLE_CSE_ID` + `GOOGLE_API_KEY` — For Google Custom Search

### 3. Run

```bash
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome + help |
| `/research <query>` | Deep research mode |
| `/verify <text>` | Fact-check text |
| `/analyze <text>` | Analyze text |
| `/news <topic>` | Latest news analysis |
| `/analyze_url <url>` | Analyze URL |
| `/analyze_photo` | Analyze replied photo |
| `/status` | Bot status |
| `/clear` | Clear memory |
| `/help` | Show help |

## Auto-Detection

The bot automatically detects:
- **Questions** → Triggers research mode
- **URLs** → Auto-analyzes webpage
- **Photos** → Auto OCR + analysis

## Output Format

All responses follow:

```
📊 Analysis Summary
[Main answer]

📚 Sources
1. [Title] — [URL]
2. ...

✅ Verification
- Claim 1: Verified (confidence: 85%)
- Claim 2: Uncertain

⚠️ Caveats
[Limitations noted]
```

## Tech Stack

- Python 3.11+
- python-telegram-bot (async)
- httpx + BeautifulSoup4
- duckduckgo-search (free)
- pytesseract / easyocr (OCR)
- SQLAlchemy (memory)
- pydantic (settings)
- Pillow (images)
- OpenAI API (LLM)

## Safety

- No hallucination: all claims backed by sources
- Uncertainty flag when confidence < 70%
- Bias detection for one-sided sources
- Rate limiting on searches
- No personal data beyond conversation memory

## License

MIT
