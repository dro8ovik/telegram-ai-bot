import time
import requests
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_URL = f"https://api.telegram.org/bot{TOKEN}/"

user_state = {}

TIME_CHOICES = {
    "1": "5-10 min",
    "2": "20-30 min",
    "3": "1 hour+",
}

def get_updates(offset=None):
    url = TG_URL + "getUpdates"
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=40)
    return response.json()

def send_message(chat_id, text):
    url = TG_URL + "sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data, timeout=20)

def classify_task(task_text):
    text = task_text.lower()

    small_keywords = [
        "помыть", "wash", "убрать кружку", "чашку", "cup", "стакан",
        "налить", "take medicine", "выпить", "позвонить", "call"
    ]
    medium_keywords = [
        "сварить", "приготовить", "cook", "борщ", "суп", "ужин",
        "собрать", "купить", "shopping"
    ]
    big_keywords = [
        "сценар", "script", "ролик", "video", "reel", "спектак",
        "проект", "project", "презентац", "presentation",
        "тест", "test", "таск", "task", "фича", "feature"
    ]

    if any(k in text for k in big_keywords):
        return "big"
    if any(k in text for k in medium_keywords):
        return "medium"
    if any(k in text for k in small_keywords):
        return "small"
    return "medium"

def detect_task_plan(task_text, time_bucket=None):
    text = task_text.lower()

    # BORSH / COOKING
    if "борщ" in text:
        if time_bucket == "1":
            return [
                "Open the kitchen and take out one pot.",
                "Put water on the stove.",
                "Peel potatoes only.",
                "Decide: quick version today. Skip anything non-essential.",
            ]
        elif time_bucket == "2":
            return [
                "Put water on the stove.",
                "Peel potatoes and one carrot.",
                "Cut onion and carrot.",
                "Start the base: put vegetables in.",
                "Do the next ingredient only after this is done.",
            ]
        else:
            return [
                "Take out all main ingredients.",
                "Put water or broth on the stove.",
                "Peel and chop the vegetables.",
                "Build the soup base step by step.",
                "Taste and adjust at the end.",
            ]

    # SCRIPT / PLAY
    if "сценар" in text or "script" in text or "спектак" in text:
        if time_bucket == "1":
            return [
                "Open a blank note.",
                "Write the title only.",
                "Write one sentence: what is this story about?",
            ]
        elif time_bucket == "2":
            return [
                "Open a blank note.",
                "Write the title.",
                "Write the main problem.",
                "Write 3 bullet points: beginning, middle, end.",
            ]
        else:
            return [
                "Open a blank note.",
                "Write the title and audience age.",
                "Write the main conflict.",
                "Draft beginning, middle, end.",
                "Add 1-2 character beats.",
            ]

    # VIDEO / REEL
    if "ролик" in text or "reel" in text or "video" in text or "видео" in text:
        if time_bucket == "1":
            return [
                "Open the project or notes.",
                "Write the hook only.",
                "Shoot one 3-second test clip.",
            ]
        elif time_bucket == "2":
            return [
                "Open the project.",
                "Write hook and ending.",
                "Set camera and frame.",
                "Shoot one real clip.",
            ]
        else:
            return [
                "Open the project.",
                "Outline hook, middle, ending.",
                "Set frame and light.",
                "Shoot 2-3 clips.",
                "Review once.",
            ]

    # TEST / TASK
    if "тест" in text or "test" in text or "таск" in text or "task" in text or "фича" in text:
        if time_bucket == "1":
            return [
                "Open the task.",
                "Read only the title.",
                "Read expected result only.",
                "Write one check idea.",
            ]
        elif time_bucket == "2":
            return [
                "Open the task.",
                "Read title and expected result.",
                "List 3 checks.",
                "Run the first check.",
            ]
        else:
            return [
                "Open the task.",
                "Read title, expected result, and notes.",
                "Break testing into areas.",
                "Start with the highest-risk check.",
            ]

    # DEFAULT
    if time_bucket == "1":
        return [
            "Open the place where this task lives.",
            "Read only the title.",
            "Do one tiny action.",
        ]
    elif time_bucket == "2":
        return [
            "Open the place where this task lives.",
            "Understand the first concrete action.",
            "Do the first useful piece.",
        ]
    else:
        return [
            "Open the place where this task lives.",
            "Break it into beginning / middle / end.",
            "Start with the first concrete action.",
        ]

def get_speed_step(step_text, mode):
    if mode == "fast":
        return step_text + "\n\nFast mode."
    if mode == "slow":
        return step_text + "\n\nTiny step only."
    return step_text

def ask_for_time(task_text):
    return (
        f"Okay.\n\n"
        f'"{task_text}" looks bigger than a one-step task.\n\n'
        f"How much time do you have right now?\n"
        f"1 — 5–10 min\n"
        f"2 — 20–30 min\n"
        f"3 — 1 hour+\n\n"
        f"Reply with 1, 2, or 3."
    )

def fallback_logic(chat_id, user_text):
    state = user_state.setdefault(chat_id, {
        "task": None,
        "steps": [],
        "current": 0,
        "mode": "normal",
        "awaiting_time": False,
        "time_bucket": None,
        "task_size": None,
    })

    text = user_text.strip()
    lower = text.lower()

    if lower == "/start":
        state["task"] = None
        state["steps"] = []
        state["current"] = 0
        state["mode"] = "normal"
        state["awaiting_time"] = False
        state["time_bucket"] = None
        state["task_size"] = None
        return (
            "Starter is on.\n\n"
            "Send me a task.\n"
            "You can also use:\n"
            "+ → done\n"
            "faster → bigger steps\n"
            "slower → smaller steps\n"
            "stuck → make it easier"
        )

    if lower == "faster":
        state["mode"] = "fast"
        if state["steps"] and state["current"] < len(state["steps"]):
            step = get_speed_step(state["steps"][state["current"]], state["mode"])
            return f"⚡ Faster.\n\n{step}\n\nType + when done."
        return "⚡ Faster mode on. Send me a task."

    if lower == "slower":
        state["mode"] = "slow"
        if state["steps"] and state["current"] < len(state["steps"]):
            step = get_speed_step(state["steps"][state["current"]], state["mode"])
            return f"🧩 Slower.\n\n{step}\n\nType + when done."
        return "🧩 Slower mode on. Send me a task."

    if lower == "stuck":
        state["mode"] = "slow"
        if state["steps"] and state["current"] < len(state["steps"]):
            current_step = state["steps"][state["current"]]
            short_step = current_step.split(".")[0].strip() + "."
            return (
                "Okay. Smaller.\n\n"
                f"Just this:\n{short_step}\n\n"
                "Type + when done."
            )
        return "Okay. Send me the task again, and I’ll make it smaller."

    if state["awaiting_time"]:
        if text in TIME_CHOICES:
            state["time_bucket"] = text
            state["awaiting_time"] = False
            state["steps"] = detect_task_plan(state["task"], state["time_bucket"])
            state["current"] = 0
            first_step = get_speed_step(state["steps"][0], state["mode"])
            return (
                f"Good. We’ll fit it into {TIME_CHOICES[text]}.\n\n"
                f"Step 1/{len(state['steps'])}:\n{first_step}\n\n"
                f"Type + when done."
            )
        return "Reply with 1, 2, or 3."

    if lower in ["+", "done"]:
        if not state["steps"]:
            return "No active task yet. Send me a task first."

        state["current"] += 1

        if state["current"] < len(state["steps"]):
            step = get_speed_step(state["steps"][state["current"]], state["mode"])
            progress = f"{state['current'] + 1}/{len(state['steps'])}"
            return f"Nice. Moving.\n\nStep {progress}:\n{step}\n\nType + when done."

        return (
            "Nice. You moved.\n\n"
            "This flow is done.\n"
            "Send a new task when you want."
        )

    # NEW TASK
    state["task"] = text
    state["steps"] = []
    state["current"] = 0
    state["mode"] = "normal"
    state["time_bucket"] = None

    task_size = classify_task(text)
    state["task_size"] = task_size

    # Variant 2:
    # small -> immediate first step
    # medium/big -> ask time only when useful
    if task_size == "small":
        state["steps"] = detect_task_plan(text, "1")
        first_step = get_speed_step(state["steps"][0], state["mode"])
        return (
            f"Got it.\n\n"
            f"Step 1/{len(state['steps'])}:\n{first_step}\n\n"
            f"Type + when done."
        )

    if task_size == "medium":
        state["awaiting_time"] = True
        return ask_for_time(text)

    if task_size == "big":
        state["awaiting_time"] = True
        return ask_for_time(text)

    state["steps"] = detect_task_plan(text, "2")
    first_step = get_speed_step(state["steps"][0], state["mode"])
    return (
        f"Got it.\n\n"
        f"Step 1/{len(state['steps'])}:\n{first_step}\n\n"
        f"Type + when done."
    )

def main():
    offset = None

    while True:
        try:
            updates = get_updates(offset)

            if not updates.get("ok"):
                print("Telegram error:", updates)
                time.sleep(2)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                if not text:
                    continue

                print("Incoming:", text)
                reply = fallback_logic(chat_id, text)
                print("Reply:", reply)
                send_message(chat_id, reply)

        except Exception as e:
            print("ERROR:", repr(e))
            time.sleep(2)

if __name__ == "__main__":
    main()
