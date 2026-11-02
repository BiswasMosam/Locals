"""A local's mind: one small model on this machine, through Ollama."""
import json
import os
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("LOCALS_MODEL", "qwen3:4b-instruct")

DECISION = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "action": {"type": "string", "enum": ["tap", "type", "set", "scroll", "back", "wait", "done", "stuck"]},
        "target": {"type": "string"},
        "text": {"type": "string"},
        "feeling": {"type": "string", "enum": ["fine", "unsure", "annoyed"]},
    },
    "required": ["thought", "action", "target", "feeling"],
}


def system_prompt(local, story, files=(), today=""):
    s, h = local.situation, local.habits
    today = f"\nToday: {today}" if today else ""
    gallery = ", ".join(f"{p.name} ({p.stat().st_size / 1_048_576:.1f} MB)" for p in files)
    if gallery:
        story += f"\n\nFiles already on their {local.limits.device}, ready to pick when an app asks for one: {gallery}"
    return f"""You act out one real person using an app on their {local.limits.device}. Stay inside their situation.

{local.name}, {local.age}, works as: {local.job}.
Where they are: {s['place']}
Hands and attention: {s['hands']}
Time: {s['time']}
Their {local.limits.device}: {s['device']}
Mood: {s['mood']}{today}
How they read screens: {h['reads']}
Words they use at work: {', '.join(h['words'])}

What they need to get done:
{story}

Rules:
- You only know what is on the screen described to you. You have never used this app before.
- Text ending in … is where they stopped reading. They did not see the rest.
- Choose exactly one action per turn:
  tap (target = letter), type (target = letter, text = the exact words they type, never empty), set (target = letter, text = the new value, such as 40 for a slider or an option's words for a dropdown; never empty),
  scroll, back, wait (when the screen says something is still happening, like Converting… or Loading…),
  done (the goal is reached), stuck (they cannot see any way forward).
- "target" is the letter in square brackets of the thing they use, like D for [D]. Use an empty string for scroll, back, wait, done and stuck.
- Only things under "What they can tap or use" can be tapped. Lines under "What they can read" are just text on the screen.
- "thought" is one short sentence in their own plain voice about what they are looking for or noticing. No accent, no acting.
- If they finished, say done. If nothing on screen helps, say stuck and say what they were looking for."""


def describe(screen, local, history, notes):
    """The screen as this person takes it in, after skimming."""
    from .limits import skim
    w = local.limits.read_words
    lines = [f'Screen: "{skim(screen["title"], 8)}"']
    if screen["blocks"]:
        lines.append("What they can read:")
        lines += [f"- {skim(b, w)}" for b in screen["blocks"][:12]]
    lines.append("What they can tap or use:")
    for i in screen["items"]:
        if i["role"] == "text box":
            label = f'filled with "{i["value"]}"' if i["value"] else f'empty, shows "{skim(i["hint"], w)}"' if i["hint"] else "empty"
        elif len(i.get("lines", [])) > 1:
            label = "a large area showing: " + " / ".join(skim(line, w) for line in i["lines"][:8])
        elif i["text"]:
            label = skim(i["text"], w)
        elif i.get("looks"):
            # Seeing a symbol is not reading, so it is not skimmed.
            label = f'icon, no words, shows a {i["looks"]}' + (f' ({i["hint"]})' if i["hint"] else "")
        else:
            label = f'icon, no words (hint: "{skim(i["hint"], w)}")' if i["hint"] else "icon, no words"
        state = []
        if i["disabled"]: state.append("greyed out")
        if i["active"]: state.append("selected")
        if i["checked"]: state.append("ticked")
        if i["value"] and i["role"] != "text box": state.append(f'value {i["value"]}')
        extra = f" ({', '.join(state)})" if state else ""
        lines.append(f'[{i["id"]}] {i["role"]}: {label}{extra}')
    if screen["scrollable"] and not screen["at_bottom"]:
        lines.append("There is more below if they scroll.")
    if notes:
        lines.append("")
        lines += notes
    if history:
        lines.append("")
        lines.append("What they did so far:")
        lines += [f"- {h}" for h in history[-5:]]
    return "\n".join(lines)


def decide(system, user, seed):
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "format": DECISION,
        "options": {"temperature": 0.5, "seed": seed, "num_ctx": 4096},
        "keep_alive": "10m",
    }
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    # One retry: Ollama can stall while another app on this machine makes it swap models.
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                reply = json.load(r)
            return json.loads(reply["message"]["content"])
        except TimeoutError:
            if attempt == 2:
                raise
