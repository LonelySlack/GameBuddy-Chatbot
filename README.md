# GameBuddy (CikguBot) — AI Gaming Assistant

A Flask web chatbot for gamers. It answers gaming questions with a large language model, generates trivia quizzes, shows live Steam discounts and rewards players with points and stickers.

## Features

- **LLM chat** about games, running locally through [Ollama](https://ollama.com) (default model `gemma3:1b`) via its OpenAI-compatible API. The project started on OpenAI GPT-3.5.
- **AI-generated trivia quizzes**: the model writes a multiple-choice question on any topic; the app parses the options and answer key and checks the player's reply.
- **Live Steam discounts** from the Steam Store API, shown as a table and a Chart.js chart.
- **Voice input and output** with the browser's Web Speech API.
- **Gamification**: points and stickers for chatting and correct answers, stored in SQLite.

## Tech stack

Python · Flask · Flask-SQLAlchemy (SQLite) · OpenAI Python SDK · Ollama · Steam Store API · Chart.js · Web Speech API

## Running it

```bash
# 1. Start a local model
ollama pull gemma3:1b

# 2. Install and run
pip install -r requirements.txt
python CikguBot.py
```

Open http://localhost:5000.

Optional environment variables:

| Variable | Default |
| --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | `gemma3:1b` |

## API

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/chat` | Send a message, get the model's reply and updated points |
| POST | `/generate_quiz` | Generate a trivia question on a topic |
| POST | `/quiz_answer` | Check an answer and award points |
| GET | `/steam_discounts` | Current Steam specials |
| POST | `/clear` | Reset the conversation |
