#!/usr/bin/env python3
"""
=============================================================
  🎙️  SPEECH → TEXT → ESP32 ROBOTIC ARM CONTROLLER
=============================================================
  Commands recognized:  pick | drop | right | left | home
  False reading filter: keyword match only — ignores all
                        other speech (no false triggers)

  Requirements:
    pip install SpeechRecognition pyaudio requests

  Linux extra:
    sudo apt-get install portaudio19-dev python3-pyaudio
=============================================================
"""

import sys
import time
import threading
import requests

try:
    import speech_recognition as sr
except ImportError:
    print("\n❌  Missing: pip install SpeechRecognition\n")
    sys.exit(1)

try:
    import pyaudio
except ImportError:
    print("\n❌  Missing: pip install pyaudio\n")
    sys.exit(1)


# ═══════════════════════════════════════════════
#   ⚙️  CONFIGURATION  — Edit these
# ═══════════════════════════════════════════════
ESP32_IP   = "10.166.251.80"     # ← Paste IP from ESP32 Serial Monitor
ESP32_PORT = 80
LANGUAGE   = "en-IN"           # Change: en-US, hi-IN, etc.

# What you say → which /endpoint is called on ESP32
COMMAND_MAP = {
    # PICK
    "pick"       : "pick",
    "pickup"     : "pick",
    "pick up"    : "pick",
    "grab"       : "pick",
    "take"       : "pick",
    "lift"       : "pick",

    # DROP
    "drop"       : "drop",
    "release"    : "drop",
    "place"      : "drop",
    "put"        : "drop",
    "put down"   : "drop",
    "leave"      : "drop",

    # RIGHT
    "right"      : "right",
    "move right" : "right",
    "go right"   : "right",
    "turn right" : "right",

    # LEFT
    "left"       : "left",
    "move left"  : "left",
    "go left"    : "left",
    "turn left"  : "left",

    # HOME
    "home"       : "home",
    "reset"      : "home",
    "center"     : "home",
    "go home"    : "home",
    "return"     : "home",
}

# ── ANSI Colors ──────────────────────────────
GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"
MAGENTA = "\033[95m"


# ═══════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════
def banner():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════╗
║   🤖  ROBOTIC ARM — Voice Controller via ESP32       ║
║       Say: pick | drop | right | left | home         ║
╚══════════════════════════════════════════════════════╝{RESET}
""")


# ═══════════════════════════════════════════════
#  MIC DETECTION
# ═══════════════════════════════════════════════
def list_microphones():
    p = pyaudio.PyAudio()
    mics = []
    print(f"{BOLD}📋  Audio Input Devices:{RESET}")
    print(f"{'─'*52}")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            name = info["name"]
            mics.append((i, name))
            print(f"  [{CYAN}{i}{RESET}] {name}")
    if not mics:
        print(f"  {RED}No input devices found!{RESET}")
    print(f"{'─'*52}")
    p.terminate()
    return mics


def find_usb_mic(mics):
    keywords = ["usb", "USB Audio", "USB Microphone",
                "USB PnP", "USB Device", "USB Mic"]
    for idx, name in mics:
        if any(kw.lower() in name.lower() for kw in keywords):
            return idx, name
    return None


def show_mic_status(usb_result):
    print(f"\n{BOLD}🔌  USB Microphone:{RESET}")
    print(f"{'─'*52}")
    if usb_result:
        idx, name = usb_result
        print(f"  Status : {GREEN}{BOLD}✅  CONNECTED{RESET}")
        print(f"  Name   : {GREEN}{name}{RESET}")
        print(f"  Index  : [{CYAN}{idx}{RESET}]")
    else:
        print(f"  Status : {YELLOW}⚠️   USB mic not found — using default mic{RESET}")
    print(f"{'─'*52}")


# ═══════════════════════════════════════════════
#  ESP32 STATUS CHECK
# ═══════════════════════════════════════════════
def check_esp32():
    url = f"http://{ESP32_IP}:{ESP32_PORT}/status"
    print(f"\n{BOLD}🌐  ESP32 Connection:{RESET}")
    print(f"{'─'*52}")
    print(f"  Target : http://{ESP32_IP}:{ESP32_PORT}")
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            print(f"  Status : {GREEN}{BOLD}✅  ONLINE{RESET}  —  {r.text}")
            print(f"{'─'*52}\n")
            return True
    except Exception:
        pass
    print(f"  Status : {RED}{BOLD}❌  UNREACHABLE{RESET}")
    print(f"  {YELLOW}⚠️   Check IP, WiFi, and ESP32 power.{RESET}")
    print(f"{'─'*52}\n")
    return False


# ═══════════════════════════════════════════════
#  FALSE READING FILTER
# ═══════════════════════════════════════════════
def extract_command(transcript: str):
    """
    Returns (endpoint, matched_phrase) or (None, None).
    Only exact keyword matches are accepted.
    All other speech is rejected as a false reading.
    """
    text = transcript.lower().strip()
    # Try longest phrases first (more specific wins)
    for phrase in sorted(COMMAND_MAP.keys(), key=len, reverse=True):
        if phrase in text:
            return COMMAND_MAP[phrase], phrase
    return None, None


# ═══════════════════════════════════════════════
#  SEND COMMAND TO ESP32
# ═══════════════════════════════════════════════
def send_command(endpoint: str):
    url = f"http://{ESP32_IP}:{ESP32_PORT}/{endpoint}"
    try:
        print(f"  {CYAN}→  Sending: GET {url}{RESET}")
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            print(f"  {GREEN}✅  ESP32: {r.text}{RESET}")
            return True
        else:
            print(f"  {RED}❌  ESP32 error {r.status_code}: {r.text}{RESET}")
    except requests.exceptions.ConnectionError:
        print(f"  {RED}❌  Cannot reach ESP32 at {ESP32_IP}{RESET}")
    except requests.exceptions.Timeout:
        print(f"  {RED}❌  Request timed out (arm may still be moving){RESET}")
    except Exception as e:
        print(f"  {RED}❌  Error: {e}{RESET}")
    return False


# ═══════════════════════════════════════════════
#  SPINNER
# ═══════════════════════════════════════════════
_spinner_active = False

def _spin(msg):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while _spinner_active:
        print(f"\r  {CYAN}{frames[i % len(frames)]}{RESET}  {msg}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r{' '*60}\r", end="", flush=True)

def start_spinner(msg):
    global _spinner_active
    _spinner_active = True
    threading.Thread(target=_spin, args=(msg,), daemon=True).start()

def stop_spinner():
    global _spinner_active
    _spinner_active = False
    time.sleep(0.15)


# ═══════════════════════════════════════════════
#  LISTEN ONCE
# ═══════════════════════════════════════════════
def listen_once(recognizer, mic_index=None):
    """
    Records one utterance.
    Returns (transcript_str, error_str | None)
    """
    mic_kwargs = {"device_index": mic_index} if mic_index is not None else {}

    with sr.Microphone(**mic_kwargs) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        start_spinner("🎤  Listening — say a command ...")
        try:
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            stop_spinner()
            return None, "timeout"
        finally:
            stop_spinner()

    try:
        text = recognizer.recognize_google(audio, language=LANGUAGE)
        return text, None
    except sr.UnknownValueError:
        return None, "unclear"
    except sr.RequestError as e:
        return None, f"api_error:{e}"


# ═══════════════════════════════════════════════
#  SESSION STATS
# ═══════════════════════════════════════════════
class Stats:
    def __init__(self):
        self.heard     = 0
        self.matched   = 0
        self.rejected  = 0
        self.sent_ok   = 0
        self.sent_fail = 0

    def show(self):
        print(f"\n{CYAN}{BOLD}{'═'*52}")
        print(f"  📊  SESSION STATS")
        print(f"{'═'*52}{RESET}")
        print(f"  Utterances heard  : {self.heard}")
        print(f"  Commands matched  : {GREEN}{self.matched}{RESET}")
        print(f"  False readings    : {YELLOW}{self.rejected}{RESET}  ← filtered, not sent")
        print(f"  Sent successfully : {GREEN}{self.sent_ok}{RESET}")
        print(f"  Send failures     : {RED}{self.sent_fail}{RESET}")
        print(f"{CYAN}{BOLD}{'═'*52}{RESET}\n")


# ═══════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════
def main():
    banner()

    # ── Mic setup ────────────────────────────
    mics       = list_microphones()
    usb_result = find_usb_mic(mics)
    show_mic_status(usb_result)
    mic_index  = usb_result[0] if usb_result else None

    # ── ESP32 ping ───────────────────────────
    esp_online = check_esp32()
    if not esp_online:
        ans = input(f"  {YELLOW}Continue anyway? (y/n): {RESET}").strip().lower()
        if ans != "y":
            print("  Exiting.\n")
            sys.exit(0)

    # ── Recognizer config ─────────────────────
    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 0.6  # faster response

    stats = Stats()

    print(f"{BOLD}{'═'*52}")
    print(f"  🎙️   VOICE CONTROL ACTIVE")
    print(f"  Commands: pick | drop | right | left | home")
    print(f"  Press  Ctrl+C  to quit")
    print(f"{'═'*52}{RESET}\n")

    while True:
        try:
            transcript, err = listen_once(recognizer, mic_index)

            # ── Handle errors ─────────────────
            if err == "timeout":
                print(f"  {DIM}(silence — still listening){RESET}")
                continue

            if err == "unclear":
                print(f"  {YELLOW}⚠️   Could not understand. Try again.{RESET}\n")
                continue

            if err and err.startswith("api_error"):
                print(f"  {RED}❌  API Error: {err.split(':',1)[-1]}{RESET}")
                print(f"  {YELLOW}   Check internet connection.{RESET}\n")
                continue

            # ── Got a transcript ──────────────
            stats.heard += 1
            ts = time.strftime("%H:%M:%S")
            print(f"\n  [{DIM}{ts}{RESET}] 🗣️  Heard: {BOLD}\"{transcript}\"{RESET}")

            # ── False reading filter ──────────
            command, phrase = extract_command(transcript)

            if command is None:
                stats.rejected += 1
                print(f"  {YELLOW}🚫  No command keyword found — IGNORED{RESET}\n")
                continue

            # ── Valid command → send to ESP32 ─
            stats.matched += 1
            print(f"  {MAGENTA}🔍  Matched: \"{phrase}\"  →  /{command}{RESET}")

            ok = send_command(command)
            if ok:
                stats.sent_ok += 1
            else:
                stats.sent_fail += 1
            print()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n  {RED}Unexpected error: {e}{RESET}\n")
            continue

    stats.show()


if __name__ == "__main__":
    main()
