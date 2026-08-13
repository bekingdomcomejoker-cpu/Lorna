#!/usr/bin/env python3
"""
op_skill.py -- Cross-Platform Autonomous Browser Operator (single file)

Drop this anywhere. Run: python3 op_skill.py rain_reboot

Platforms: Termux, Linux, macOS, Windows
"""

import os, sys, time, json, subprocess, platform as plat
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

# ============================================================
# PLATFORM DETECTION
# ============================================================
class Platform:
    TERMUX = os.path.exists("/data/data/com.termux/files/usr")
    LINUX = sys.platform.startswith("linux") and not TERMUX
    MACOS = sys.platform == "darwin"
    WINDOWS = sys.platform == "win32"

    @classmethod
    def home(cls): return Path.home()
    @classmethod
    def tmp(cls): 
        return Path("/data/data/com.termux/files/usr/tmp" if cls.TERMUX else os.environ.get("TMPDIR", "/tmp"))

    @classmethod
    def find_chrome(cls):
        candidates = []
        if cls.TERMUX:
            candidates = ["/data/data/com.termux/files/usr/bin/chromium-browser",
                          "/data/data/com.termux/files/usr/bin/chromium"]
        elif cls.LINUX:
            candidates = ["/usr/bin/chromium-browser", "/usr/bin/chromium",
                          "/usr/bin/google-chrome", "/usr/bin/chrome"]
        elif cls.MACOS:
            candidates = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                          "/Applications/Chromium.app/Contents/MacOS/Chromium"]
        elif cls.WINDOWS:
            candidates = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
        for c in candidates:
            if os.path.exists(c): return c
        for cmd in (["chromium-browser","chromium","google-chrome","chrome"] if not cls.WINDOWS else ["where","chrome"]):
            try:
                result = subprocess.run([cmd] if not cls.WINDOWS else ["where", cmd],
                    capture_output=True, text=True)
                path = result.stdout.strip().split("\n")[0]
                if path and os.path.exists(path): return path
            except: pass
        return None

    @classmethod
    def find_chromedriver(cls):
        candidates = []
        if cls.TERMUX:
            candidates = ["/data/data/com.termux/files/usr/bin/chromedriver"]
        elif cls.LINUX:
            candidates = ["/usr/bin/chromedriver", "/usr/local/bin/chromedriver"]
        elif cls.MACOS:
            candidates = ["/usr/local/bin/chromedriver", "/opt/homebrew/bin/chromedriver"]
        elif cls.WINDOWS:
            candidates = [r"C:\tools\chromedriver.exe"]
        for c in candidates:
            if os.path.exists(c): return c
        try:
            result = subprocess.run(["which" if not cls.WINDOWS else "where", "chromedriver"],
                capture_output=True, text=True)
            path = result.stdout.strip().split("\n")[0]
            if path and os.path.exists(path): return path
        except: pass
        return None

# ============================================================
# STATE & LOGGING
# ============================================================
@dataclass
class State:
    mission: str = "idle"
    step: str = "start"
    turn: int = 0
    history: List = None
    last_bot: str = ""
    metadata: Dict[str, Any] = None
    def __post_init__(self):
        if self.history is None: self.history = []
        if self.metadata is None: self.metadata = {}
    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f: json.dump(asdict(self), f, indent=2)
    @classmethod
    def load(cls, path: Path):
        if path.exists():
            with open(path) as f: return cls(**json.load(f))
        return cls()

class Logger:
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        if self.log_file:
            with open(self.log_file, "a") as f: f.write(line + "\n")

# ============================================================
# BROWSER DRIVER
# ============================================================
class BrowserDriver:
    def __init__(self, chrome_bin: Optional[str] = None, chromedriver_bin: Optional[str] = None):
        self.chrome_bin = chrome_bin or Platform.find_chrome()
        self.chromedriver_bin = chromedriver_bin or Platform.find_chromedriver()
        self.driver = None
        self._selenium = None

    def _import_selenium(self):
        if self._selenium is None:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            self._selenium = {"webdriver": webdriver, "Options": Options,
                "Service": Service, "By": By, "Keys": Keys}
        return self._selenium

    def start(self, headless: bool = True):
        if not self.chrome_bin: raise RuntimeError("Chrome not found. Set chrome_bin= path.")
        if not self.chromedriver_bin: raise RuntimeError("Chromedriver not found. Set chromedriver_bin= path.")
        s = self._import_selenium()
        opts = s["Options"]()
        opts.binary_location = self.chrome_bin
        if headless: opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1400,2200")
        service = s["Service"](executable_path=self.chromedriver_bin)
        self.driver = s["webdriver"].Chrome(service=service, options=opts)
        return self.driver

    def quit(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None

    def nav(self, url: str, wait: int = 5):
        if not self.driver: self.start()
        self.driver.get(url); time.sleep(wait)

    def find_shadow(self, tag: str = "ai-chat-bot"):
        s = self._import_selenium()
        h = self.driver.find_element(s["By"].TAG_NAME, tag)
        return self.driver.execute_script("return arguments[0].shadowRoot", h)

    def get_messages(self, tag: str = "ai-chat-bot") -> List[str]:
        root = self.find_shadow(tag)
        return self.driver.execute_script(
            """const o=[];arguments[0].querySelectorAll('.user-query,.ai-response').forEach(e=>{
            let t=(e.innerText||e.textContent||'').trim();if(!t){const p=e.querySelector('p');
            if(p)t=(p.innerText||p.textContent||'').trim()}if(!t)t=(e.innerHTML||'').trim();o.push(t)});return o;""", root)

    def send(self, text: str, tag: str = "ai-chat-bot"):
        s = self._import_selenium()
        root = self.find_shadow(tag)
        box = self.driver.execute_script("return arguments[0].querySelector('textarea')", root)
        box.click(); box.clear(); box.send_keys(text); box.send_keys(s["Keys"].ENTER)

    def wait_reply(self, previous_count: int = 0, timeout: int = 180) -> List[str]:
        dl = time.time() + timeout; last = ""; stable = 0; msgs = []
        while time.time() < dl:
            msgs = self.get_messages()
            if len(msgs) <= previous_count: time.sleep(1); continue
            cur = (msgs[-1] or "").strip()
            if not cur or "loader" in cur.lower(): time.sleep(2); continue
            if cur == last:
                stable += 1
                if stable >= 2: return msgs
            else: last = cur; stable = 0
            time.sleep(1)
        return msgs if msgs and msgs[-1].strip() else []

    def screenshot(self, path: str):
        try: self.driver.save_screenshot(path)
        except: pass

# ============================================================
# VOICE DRIVER
# ============================================================
class VoiceDriver:
    def __init__(self, whisper_path: Optional[str] = None, model_path: Optional[str] = None):
        self.whisper = whisper_path or "whisper.cpp/main"
        self.model = model_path or "whisper.cpp/models/ggml-tiny.en-q5_1.bin"
        self.recording = str(Platform.tmp() / "op_voice.wav")
        self.ok = os.path.exists(self.whisper) and os.path.exists(self.model)

    def record(self, seconds: int = 5):
        if Platform.TERMUX:
            subprocess.run(["termux-microphone-record", "-q"], capture_output=True)
            subprocess.Popen(["termux-microphone-record", "-f", self.recording, "-l", str(seconds * 1000)])
            time.sleep(seconds + 0.5)
            subprocess.run(["termux-microphone-record", "-q"], capture_output=True)
        else:
            try: subprocess.run(["arecord", "-d", str(seconds), "-f", "cd", self.recording], capture_output=True, timeout=seconds + 2)
            except: subprocess.run(["sox", "-d", self.recording, "trim", "0", str(seconds)], capture_output=True, timeout=seconds + 2)
        return self.recording

    def transcribe(self, wav: str) -> str:
        if not self.ok: return ""
        r = subprocess.run([self.whisper, "-m", self.model, "-f", wav,
            "--no-timestamps", "-t", "2", "-otxt", "-of", "/dev/stdout"],
            capture_output=True, text=True, timeout=15)
        for p in [wav, wav + ".txt"]:
            if os.path.exists(p): os.remove(p)
        return r.stdout.strip().lower()

    def listen(self, seconds: int = 5) -> str:
        wav = self.record(seconds)
        return self.transcribe(wav)

# ============================================================
# BRAIN (LLM)
# ============================================================
class Brain:
    def __init__(self, llama_path: Optional[str] = None, model_path: Optional[str] = None):
        self.llama = llama_path or "llama.cpp/build/bin/llama-cli"
        self.model = model_path
        self.ok = os.path.exists(self.llama) and (not self.model or os.path.exists(self.model))

    def decide(self, state: str, last_reply: str, options: Optional[list] = None) -> str:
        if not self.ok: return "ask"
        options = options or ["yes", "choice", "complete", "ask"]
        prompt = f"STATE:{state}\nREPLY:{last_reply[:200]}\nCOMMANDS:{','.join(options)}\nOUTPUT ONE WORD:"
        proc = subprocess.Popen([self.llama, "-m", self.model, "-n", "2", "--temp", "0.1",
            "--no-display-prompt", "--interactive"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        proc.stdin.write(prompt + "\n/exit\n")
        proc.stdin.flush()
        out = proc.communicate()[0]
        for line in reversed(out.splitlines()):
            w = line.strip().lower()
            if w in options: return w
        return "ask"

# ============================================================
# OPERATOR
# ============================================================
class Operator:
    def __init__(self, chrome_bin=None, chromedriver_bin=None, state_file=None, log_file=None):
        self.home = Platform.home()
        self.state_file = Path(state_file) if state_file else (self.home / ".op_skill_state.json")
        self.logger = Logger(Path(log_file) if log_file else (self.home / ".op_skill.log"))
        self.log = self.logger.log
        self.browser = BrowserDriver(chrome_bin, chromedriver_bin)
        self.voice = VoiceDriver()
        self.brain = Brain()
        self.state = State.load(self.state_file)

    def save_state(self): self.state.save(self.state_file)

    def classify(self, reply: str) -> str:
        r = reply.lower()
        if any(p in r for p in ["starting","started","underway","rebooting","done","completed"]): return "complete"
        if any(p in r for p in ["should i","shall i","can i","may i","do you want","permission"]): return "yes"
        if any(p in r for p in ["choose","select","option","factory reset"]): return "choice"
        return self.brain.decide(self.state.step, self.state.last_bot)

    def run_mission(self, mission: str):
        self.state = State(mission=mission, step="start")
        self.save_state()
        try:
            if mission == "rain_reboot": self._rain_reboot()
            elif mission == "check_router": self._check_router()
            else: self.log(f"Unknown mission: {mission}")
        except Exception as e:
            self.log(f"CRASH: {e}")
            self.save_state()
        finally:
            self.browser.quit()

    def _rain_reboot(self):
        url = "https://askrain.rain.co.za/?id=7yAzKgvD7I6wVGEHMrQazaYjlhAILGXzjTzvAx8nVWk%3D"
        self.browser.nav(url)
        self.log("Loaded Rain chat")
        self.browser.send("I need a remote router reset.")
        self.log(">>> I need a remote router reset.")

        turn = 0
        while self.state.step != "complete":
            turn += 1
            before = len(self.browser.get_messages())
            msgs = self.browser.wait_reply(before)
            if not msgs: self.log("Timeout"); break

            reply = msgs[-1].strip()
            self.state.last_bot = reply
            self.state.history.append(["BOT", reply])
            self.log(f"<<< {reply}")
            self.browser.screenshot(str(self.home / f"op_t{turn}.png"))

            d = self.classify(reply)
            self.log(f"Decision: {d}")

            if d == "complete":
                self.state.step = "complete"; self.log("Done")
            elif d == "yes":
                self.browser.send("Yes please"); self.log(">>> Yes please")
            elif d == "choice":
                self.browser.send("Just a reboot please, keep my settings")
                self.log(">>> Just a reboot please, keep my settings")
            else:
                self.log("Need human"); break

            self.state.turn = turn
            self.save_state()

        if self.state_file.exists(): self.state_file.unlink()

    def _check_router(self, host="192.168.100.2", user="admin", pwd=""):
        for cmd in ["/system resource print", "/interface print detail"]:
            c = f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{host} '{cmd}'"
            r = subprocess.run(c, shell=True, capture_output=True, text=True)
            self.log(r.stdout or r.stderr)

    def voice_loop(self):
        self.log("Voice loop. Say 'operator' then command.")
        while True:
            try:
                text = self.voice.listen(4)
                self.log(f"Heard: '{text}'")
                if "operator" in text or "computer" in text:
                    self.log("Wake. Command?")
                    cmd = self.voice.listen(5)
                    self.log(f"Command: '{cmd}'")
                    if "reboot" in cmd: self.run_mission("rain_reboot")
                    elif "router" in cmd: self.run_mission("check_router")
                    else: self.log("No intent")
                time.sleep(0.5)
            except KeyboardInterrupt: break
            except Exception as e: self.log(f"Voice err: {e}"); time.sleep(1)

# ============================================================
# CLI
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="op_skill -- Autonomous Browser Operator")
    parser.add_argument("command", nargs="?", help="Mission or --resume/--status/--voice")
    parser.add_argument("--chrome", help="Chrome binary path")
    parser.add_argument("--chromedriver", help="Chromedriver path")
    parser.add_argument("--state", help="State file")
    parser.add_argument("--log", help="Log file")
    args = parser.parse_args()

    op = Operator(chrome_bin=args.chrome, chromedriver_bin=args.chromedriver,
                  state_file=args.state, log_file=args.log)

    if not args.command:
        print("Usage: python3 op_skill.py <mission|--resume|--status|--voice>")
        print("Missions: rain_reboot, check_router")
        return

    if args.command == "--resume":
        op.log(f"Resuming {op.state.mission} at {op.state.step}")
        op.run_mission(op.state.mission)
    elif args.command == "--status":
        print(json.dumps({"mission": op.state.mission, "step": op.state.step,
            "turn": op.state.turn, "last": op.state.last_bot[:80]}, indent=2))
    elif args.command == "--voice":
        op.voice_loop()
    else:
        op.run_mission(args.command)

if __name__ == "__main__":
    main()
