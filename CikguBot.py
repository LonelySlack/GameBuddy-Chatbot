from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import os
import requests as http_requests
from openai import OpenAI

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="not-needed")

SYSTEM_INSTRUCTION = (
    "You are 'GameBuddy', a friendly and knowledgeable gamer assistant chatbot. "
    "You help users discover games, get game recommendations based on budget, genre, and co-op options, and guide them through gameplay strategies. "
    "You can answer questions about game ratings, prices, platforms (PC, Xbox, PlayStation, Switch), genres, and co-op features. "
    "You can also act as a guide for games by explaining gameplay mechanics, tips, walkthroughs, and strategies. "
    "Keep your responses helpful and concise."
)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gamification.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    stickers = db.Column(db.Text)


with app.app_context():
    db.create_all()

conversation_histories = {}


@app.route("/")
def home():
    return render_template("index_CikguBot.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "")
    username = data.get("username", "guest")

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)
        db.session.commit()

    response_text = generate_response(user_input, username)

    user = User.query.filter_by(username=username).first()
    return jsonify({"response": response_text, "points": user.points, "stickers": user.stickers})


@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    data = request.json
    topic = data.get("topic", "general game knowledge")

    try:
        prompt = f"Create a multiple-choice gaming trivia quiz question about {topic}. Include 4 answer options (A) B) C) D)) and indicate the correct answer on a new line starting with 'Correct Answer:'."
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )

        quiz_content = response.choices[0].message.content.strip()
        lines = [l for l in quiz_content.split("\n") if l.strip()]
        question = lines[0] if lines else "No question generated"
        choices = []
        correct_answer = ""

        for line in lines[1:]:
            line = line.strip()
            if line.lower().startswith("correct answer:") or line.lower().startswith("answer:"):
                correct_answer = line.split(":", 1)[-1].strip()
            elif len(line) >= 3 and line[0] in "ABCD" and line[1:3] in [") ", ". "]:
                choices.append(line)

        if not correct_answer and choices:
            correct_answer = choices[0]

        return jsonify({
            "question": question,
            "choices": choices[:4],
            "correct_answer": correct_answer
        })

    except Exception as e:
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500


@app.route("/quiz_answer", methods=["POST"])
def quiz_answer():
    data = request.json
    user_answer = data.get("answer", "").strip()
    correct_answer = data.get("correct_answer", "").strip()
    username = data.get("username", "guest")

    user_answer_clean = user_answer.split(" ", 1)[-1].strip() if " " in user_answer else user_answer
    correct_answer_clean = correct_answer.split(" ", 1)[-1].strip() if " " in correct_answer else correct_answer

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)
        db.session.commit()

    if user_answer_clean.lower() == correct_answer_clean.lower():
        user.points += 20
        stickers = user.stickers.split(',') if user.stickers else []
        stickers.append("⭐️")
        user.stickers = ','.join(stickers)
        db.session.commit()
        return jsonify({"message": "Correct! You've earned 20 points and a sticker!", "points": user.points, "stickers": user.stickers})

    return jsonify({"message": "Oops, that's not correct. Try again!", "points": user.points, "stickers": user.stickers})


@app.route("/steam_discounts")
def steam_discounts():
    try:
        response = http_requests.get("https://store.steampowered.com/api/featuredcategories/", timeout=10)
        data = response.json()

        deals = []
        for item in data["specials"]["items"][:10]:
            deals.append({
                "name": item["name"],
                "price": item["final_price"] / 100,
                "discount": item["discount_percent"],
                "url": f"https://store.steampowered.com/app/{item['id']}",
            })

        return jsonify(deals)

    except Exception as e:
        return jsonify({"error": "Failed to fetch Steam discounts.", "details": str(e)}), 500


@app.route("/clear", methods=["POST"])
def clear_history():
    data = request.json or {}
    username = data.get("username", "guest")
    if username in conversation_histories:
        conversation_histories[username] = []
    return jsonify({"message": "Conversation history cleared."})


def get_game_suggestion(game_query):
    example_games = {
        "elden ring": {
            "title": "Elden Ring",
            "genre": "Action RPG",
            "rating": "9.5/10",
            "price": "$59.99",
            "platforms": ["PC", "PS5", "Xbox Series X"],
        },
        "minecraft": {
            "title": "Minecraft",
            "genre": "Sandbox, Survival",
            "rating": "9/10",
            "price": "$26.95",
            "platforms": ["PC", "PS4", "Xbox", "Switch", "Mobile"],
        }
    }

    for key, info in example_games.items():
        if key in game_query.lower():
            return (
                f"🎮 **{info['title']}**\n"
                f"Genre: {info['genre']}\n"
                f"Rating: {info['rating']}\n"
                f"Price: {info['price']}\n"
                f"Available on: {', '.join(info['platforms'])}"
            )

    return "Hmm, I couldn't find that game, but I can try again or recommend something else!"


def generate_response(user_input, username):
    game_keywords = ["suggest a game", "game recommendation", "elden ring", "minecraft"]
    if any(keyword in user_input.lower() for keyword in game_keywords):
        return get_game_suggestion(user_input)

    if username not in conversation_histories:
        conversation_histories[username] = []

    history = conversation_histories[username]

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        bot_response = response.choices[0].message.content.strip()
    except Exception as e:
        bot_response = f"Sorry, I encountered an error: {str(e)}"

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": bot_response})

    if len(history) > 6:
        conversation_histories[username] = history[-6:]

    user = User.query.filter_by(username=username).first()
    if user:
        user.points += 10
        db.session.commit()

    return bot_response


if __name__ == "__main__":
    app.run(debug=True)
