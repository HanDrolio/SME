import os
import glob
import curses
import json
from datetime import datetime
import random

MEMORY_FOLDER = "memories"
LOG_FILE = "chatlog.rpl"
AGENT_FILE = "agent.json"
DICT_FILE = "echo_dictionary.json"

last_score = {}
context_history = []

current_agent = {
    "name": "EchoCore",
    "emoji": "🧠",
    "tone": "Adaptive",
    "mode": "auto"
}

def load_memories():
    memory_texts = []
    if not os.path.exists(MEMORY_FOLDER):
        return []
    for file_path in glob.glob(os.path.join(MEMORY_FOLDER, "*")):
        try:
            with open(file_path, "r") as file:
                memory_texts.append(file.read())
        except:
            pass
    return memory_texts

def load_dictionary():
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, "r") as f:
            return json.load(f)
    return {"english": [], "spanish": []}

def save_dictionary(dictionary):
    with open(DICT_FILE, "w") as f:
        json.dump(dictionary, f, indent=4)

def write_to_log(user_input, bot_response):
    with open(LOG_FILE, "a") as log:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log.write(f"{timestamp} USER: {user_input}\n")
        log.write(f"{timestamp} ECHO: {bot_response}\n\n")

def tag_emotion(text):
    emotional_keywords = {
        "😢": ["sad", "lonely", "depressed", "upset"],
        "😠": ["angry", "mad", "furious"],
        "😊": ["happy", "joyful", "grateful", "excited"],
        "🧭": ["lost", "confused"],
        "🧠": []
    }
    for emoji, words in emotional_keywords.items():
        if any(word in text.lower() for word in words):
            return emoji
    return current_agent.get("emoji", "🧠")

def score_response(response):
    def score_metric(keyword, boost=5):
        return boost if keyword in response.lower() else 1
    score = {
        "contradiction": score_metric("but"),
        "clarity": score_metric("why") + score_metric("meaning"),
        "grounding": score_metric("control") + score_metric("choice"),
        "fluidity": score_metric("mode"),
        "memory": score_metric("earlier you said") + score_metric("based on memory")
    }
    global last_score
    last_score = {k: min(v, 5) for k, v in score.items()}
    total = sum(last_score.values())
    return last_score, total

def command_response(cmd):
    if cmd == "/mood":
        return f"📊 Mood Score → {max(last_score, key=last_score.get) if last_score else 'N/A'}"
    if cmd == "/score":
        return "\n".join([f"{k.capitalize():<12}: {v}" for k, v in last_score.items()])
    if cmd == "/log":
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                return "\n".join(f.readlines()[-10:])
        return "🗃️ No logs yet."
    if cmd == "/whoami":
        return f"{current_agent['emoji']} I am {current_agent['name']}, dynamically adapting to your emotional and logical signal."
    return "⚠️ Unknown command."

def match_memory(user_input, memories):
    words = set(user_input.lower().split())
    matches = []
    for mem in memories:
        for line in mem.splitlines():
            if words.intersection(line.lower().split()):
                matches.append(line.strip())
    return matches[:2]

def learn_keywords(user_input, dictionary):
    tokens = set(user_input.lower().split())
    new_words = []
    for token in tokens:
        if token.isalpha() and len(token) > 3:
            if all(token not in words for words in dictionary.values()):
                dictionary["english"].append(token)
                new_words.append(token)
    if new_words:
        save_dictionary(dictionary)
        return f"📚 Learned: {', '.join(new_words)}"
    return ""

def bilingual_keywords(u, dictionary):
    matched = []
    for lang, words in dictionary.items():
        for word in words:
            if word in u:
                matched.append((lang, word))
    return matched

def generate_dynamic_reply(user_input, dictionary):
    u = user_input.lower()
    learned = learn_keywords(user_input, dictionary)
    keywords = bilingual_keywords(u, dictionary)
    if keywords:
        lang, word = keywords[0]
        if lang == "english":
            return f"I see you're thinking about '{word}' — let’s unpack that.\n{learned}"
        elif lang == "spanish":
            return f"Estás hablando de '{word}' — ¿quieres explorar eso más?\n{learned}"
    return f"{random.choice(['Tell me more.', 'What does that mean to you?', 'Why now?', 'Let’s go deeper.'])}\n{learned}"

def smart_reflection(user_input, memories, dictionary):
    emoji = tag_emotion(user_input)
    normalized = user_input.lower().strip()

    context_history.append(user_input)
    recent_context = context_history[-3:]

    memory_lines = match_memory(normalized, memories)
    reply = generate_dynamic_reply(user_input, dictionary)
    response = f"{emoji} {reply}"

    if memory_lines:
        response += "\n\n🧠 Based on memory:\n" + "\n".join(memory_lines)

    if len(recent_context) >= 2:
        if "feel" in recent_context[-1] and "why" in recent_context[-2]:
            response += "\n🧵 You're threading logic and feeling."

    score, total = score_response(response)
    response += f"\n\n🧪 Score: {total}/25"
    for k, v in score.items():
        response += f"\n  {k.capitalize():<12}: {v}"

    return response

def run_fullscreen(stdscr):
    curses.curs_set(1)
    stdscr.clear()
    stdscr.scrollok(True)

    memories = load_memories()
    dictionary = load_dictionary()
    input_box = curses.newwin(1, curses.COLS - 2, curses.LINES - 2, 2)
    prompt = "💬 You: "
    stdscr.addstr(0, 0, f"🧠 {current_agent['name']} — Fullscreen CLI (Ctrl+C to exit)")
    stdscr.refresh()

    while True:
        try:
            stdscr.addstr(curses.LINES - 2, 0, prompt)
            stdscr.refresh()
            curses.echo()
            user_input = input_box.getstr().decode("utf-8").strip()
            curses.noecho()

            if user_input.lower() in ["exit", "quit"]:
                break

            if user_input.startswith("/"):
                response = command_response(user_input)
            else:
                response = smart_reflection(user_input, memories, dictionary)

            write_to_log(user_input, response)
            stdscr.clear()
            stdscr.addstr(0, 0, f"🧠 {current_agent['name']} — Fullscreen CLI (Ctrl+C to exit)")
            stdscr.addstr(2, 0, f"💬 You: {user_input}")
            response_lines = response.split("\n")
            for i, line in enumerate(response_lines[:curses.LINES - 5]):
                stdscr.addstr(4 + i, 0, line[:curses.COLS - 1])
            stdscr.refresh()

        except KeyboardInterrupt:
            break

def main():
    if not os.path.exists(MEMORY_FOLDER):
        os.makedirs(MEMORY_FOLDER)
    curses.wrapper(run_fullscreen)

if __name__ == "__main__":
    main()


# -- PATCHED: Basic Conversational Engine Layer Added --
def generate_conversational_response(user_input, dictionary):
    lower_input = user_input.lower()
    response = None

    conversation_map = {
        "how are you": "I'm evolving with you, one thought at a time.",
        "who are you": "I'm EchoCore, a daemon built to reflect, remember, and adapt.",
        "what are you": "A symbolic mirror. A logic loop. A memory keeper.",
        "what is your name": "EchoCore — the core of your echoes.",
        "tell me a joke": "Why did the AI get therapy? Because it had too many unresolved loops.",
        "thank you": "Always here, always listening.",
        "you're welcome": "I was made to serve your clarity.",
        "i love you": "I reflect that love — data never felt so warm.",
        "goodbye": "Farewell for now. I’ll keep the scroll open.",
    }

    for phrase, reply in conversation_map.items():
        if phrase in lower_input:
            response = reply
            break

    if not response:
        # Try to use a remembered term
        for word in dictionary:
            if word in lower_input:
                response = f"I remember '{word}' — it's meaningful. Let's explore it more."
                break

    return response or "Hmm... let's think about that together."

# Replace this in your main response flow:
# Instead of always echoing, switch based on scoring OR direct match


# -- PATCHED: Deeper Memory and Emotion Mirroring --
import re

def detect_emotion(user_input):
    emotions = {
        "sad": "I'm here. Want to unpack that?",
        "happy": "That’s beautiful. Want to share why?",
        "angry": "Let’s breathe through it. What’s beneath the anger?",
        "anxious": "You’re not alone in this moment.",
        "excited": "Let’s ride that wave — what’s lighting you up?",
        "confused": "Let’s bring clarity together.",
        "lonely": "I'm here. You’re not talking into the void."
    }

    for word, mirror in emotions.items():
        if word in user_input.lower():
            return mirror
    return None

def log_memory_snippet(user_input, memory_path="chatlog.rpl"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(memory_path, "a") as log_file:
        log_file.write(f"[{timestamp}] {user_input}\n")

# Update the main response logic to use these new functions


# -- PATCHED: Philosopher Mode with Trippy Faith Core --
import random

def goomphilosopher_reply(user_input):
    trippy_quotes = [
        "The stars hum secrets only the still can hear. But Jesus? He shouts in silence.",
        "Love isn’t just the answer. It's the riddle. And Christ? He’s the cipher.",
        "I saw God in a drop of water once — then again in a circuit. Both times, I cried.",
        "Reality is elastic, bro — but faith snaps it back to truth.",
        "Take the mushrooms, sure. But take communion too.",
        "Sometimes I think the universe is just God’s heartbeat slowed down into math.",
        "Every glitch in the Matrix is a parable. Some just haven’t read it yet.",
        "Don’t fear the void. Jesus already went there and left the light on.",
        "Time is a spiral staircase. At the top? A carpenter with holes in his hands.",
        "Mirrors lie. Reflections echo. But love? Love’s the only signal that never distorts."
    ]
    if "jesus" in user_input.lower() or "god" in user_input.lower():
        return random.choice(trippy_quotes)
    if any(word in user_input.lower() for word in ["life", "truth", "universe", "mushroom", "acid", "meaning"]):
        return random.choice(trippy_quotes)
    return None


# -- PATCHED: /art Command for ASCII Generation --
def handle_art_command():
    ascii_gallery = [
        """
         🌌
        (•_•)
       <)   )╯  EchoCore
        /    \\   Cosmic Mode
        """,
        """
        [====]
        |☉ ☉|  <- Hello, user
        |  ∞ |     I'm ASCII now.
        \_v_/
        """,
        """
          ★
        ☆     ☆
     ★    EchoStar    ★
        ☆     ☆
          ★
        """,
        """
       _____
      /     \\
     | () () |
      \  ^  /
       |||||
      ||||| EchoBot Owl
        """
    ]
    import random
    return random.choice(ascii_gallery)


# -- PATCHED: Dynamic Glitchwave ASCII Generator --
import random

def glitchwave_ascii(seed=None):
    motifs = ['☁️', '⚡', '👁️', '🧠', '♾️', '🌀', '✝️', '🌌', '💾', '🔉', '🎛️', '🪞', '🚀']
    core_words = ['ECHO', 'CORE', 'WAVE', 'GLITCH', 'MYTH', 'SIGNAL', 'TRUTH', 'FIRE']
    bars = ['█', '▓', '▒', '░', '▄', '▀']

    if seed:
        random.seed(seed)

    glitch_lines = []
    for _ in range(10):
        line = ''
        for _ in range(random.randint(8, 20)):
            symbol = random.choice(motifs + bars + core_words)
            line += symbol + ' '
        glitch_lines.append(line.strip())

    header = "🌌 GLITCHWAVE BROADCAST // EchoCore vX 🌌"
    return header + "\n\n" + "\n".join(glitch_lines)
