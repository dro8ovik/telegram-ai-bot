import time
import requests
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_URL = f"https://api.telegram.org/bot{TOKEN}/"
user_state = {}


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


def detect_task_plan(task_text):
    text = task_text.lower()

    if "ролик" in text or "reel" in text or "video" in text or "видео" in text:
        return [
            "Create or open the project file.",
            "Set the camera or phone in position.",
            "Clear the frame: keep only what should be visible.",
            "Shoot one 3-second test clip.",
            "Watch the clip once.",
            "Shoot one real clip.",
        ]

    if "сценар" in text or "script" in text:
        return [
            "Open a blank note or document.",
            "Write the title only.",
            "Write one line about the main problem.",
            "Write one line about the turning point.",
            "Write one line about the ending.",
            "Stop and review what you already have.",
        ]

    if "тест" in text or "test" in text or "таск" in text or "task" in text:
        return [
            "Open the project.",
            "Open the task.",
            "Read only the title.",
            "Read the expected result.",
            "Write one tiny check or test idea.",
            "Run or note the first check.",
        ]

    return [
        "Open the place where this task lives.",
        "Look only at the title.",
        "Do one tiny action.",
        "Continue for one minute.",
    ]


def get_speed_step(step_text, mode):
    if mode == "fast":
        return step_text + "\n\nFast mode on."
    if mode == "slow":
        return step_text + "\n\nTiny step only."
    return step_text


def fallback_logic(chat_id, user_text):
    state = user_state.setdefault(chat_id, {
        "task": None,
        "steps": [],
        "current": 0,
        "mode": "normal",
    })

    text = user_text.strip()
    lower = text.lower()

    if lower == "/start":
        state["task"] = None
        state["steps"] = []
        state["current"] = 0
        state["mode"] = "normal"
        return (
            "Starter is on.\n\n"
            "Send me a task.\n"
            "You can also use:\n"
            "+  → done\n"
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
            return (
                "Okay. Smaller.\n\n"
                f"Just do this part:\n{current_step.split('.')[0]}.\n\n"
                "Type + when done."
            )
        return "Okay. Send me the task again, and I’ll make it smaller."

    if lower in ["+", "done"]:
        if not state["steps"]:
            return "No task yet. Send me a task first."

        state["current"] += 1

        if state["current"] < len(state["steps"]):
            step = get_speed_step(state["steps"][state["current"]], state["mode"])
            progress = f"{state['current'] + 1}/{len(state['steps'])}"
            return f"Nice. Moving.\n\nStep {progress}:\n{step}\n\nType + when done."

        return (
            "Nice. You moved.\n\n"
            "You finished this flow.\n"
            "Send a new task when you want."
        )

    # new task
    state["task"] = text
    state["steps"] = detect_task_plan(text)
    state["current"] = 0
    state["mode"] = "normal"

    first_step = get_speed_step(state["steps"][0], state["mode"])
    return (
        f"Got it.\n\n"
        f"Task: {text}\n\n"
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
