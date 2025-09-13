#!/usr/bin/env python3
# Conjurer — RAW-first capture + post-processing with user's clean_ansi
#
# Usage:
#   ./conjurer.py run -- claude
#   ./conjurer.py run -- codex
#   ./conjurer.py run --history "claude" -- claude
#
# Outputs (default base: logs/%Y%m%d_%H%M%S_<cmd>):
#   <base>.raw.txt   - RAW bytes (everything)
#   <base>.txt       - CLEAN text (via clean_ansi, from RAW)
#   <base>.meta.txt  - Session metadata (start/end, stats)

import argparse, os, pty, select, sys, time, uuid, signal, tty, termios, re, struct, fcntl
import json
import requests
from datetime import datetime
from pathlib import Path
from hashlib import blake2b
from dotenv import load_dotenv


def clean_ansi(text: str) -> str:
    """Strip ANSI colors, OSC, CSI, DCS, and most control chars. Keep tabs/newlines."""
    # Normalize CR to newline so spinner redraws become separate lines
    text = text.replace('\r', '\n')
    # Remove OSC (Operating System Command) sequences: ESC ] ... BEL or ESC \ (ST)
    text = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', text)
    # Remove DCS (Device Control String) and SOS/PM/APC: ESC P / ESC ^ / ESC _ / ESC X ... ESC \
    text = re.sub(r'\x1bP.*?\x1b\\', '', text, flags=re.DOTALL)          # DCS
    text = re.sub(r'\x1b[\^_X].*?\x1b\\', '', text, flags=re.DOTALL)     # SOS(^), PM(_), APC(X)
    # Remove CSI (Control Sequence Introducer) sequences: ESC [ ... final byte in @-~
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    # Remove 8-bit C1 control codes (0x80–0x9F) including 8-bit CSI/OSC/DCS
    text = re.sub(r'[\x80-\x9F]', '', text)
    # Remove remaining control chars except newline and tab
    text = re.sub(r'[\x00-\x1F\x7F]', lambda m: '' if m.group(0) not in '\n\t' else m.group(0), text)
    # Normalize non-breaking spaces
    text = text.replace('\xa0', ' ')
    # Trim trailing whitespace on lines
    text = re.sub(r'[ \t]+\n', '\n', text)
    # Collapse 3+ blank lines to 1
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ---------------- helpers ----------------
def iso_now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")

def base_paths(log_arg: str|None, cmd_argv: list[str]):
    if log_arg:
        base = Path(datetime.now().strftime(log_arg)).expanduser().resolve()
    else:
        tag = (cmd_argv[0] if cmd_argv else "session").strip()
        tag = re.sub(r"\s+", "_", tag)
        tag = re.sub(r"[^A-Za-z0-9._-]+", "", tag) or "session"
        base = Path(datetime.now().strftime(f"logs/%Y%m%d_%H%M%S_{tag}")).expanduser().resolve()
    base.parent.mkdir(parents=True, exist_ok=True)
    return base.with_suffix(".raw.txt"), base.with_suffix(".txt")

def send_to_gemini(content: str) -> str:
    """Send cleaned content to Gemini Pro 2.5 API and get summary"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return "Error: GEMINI_API_KEY not found in .env file"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Please analyze this terminal session and provide a concise summary of what the user accomplished. Focus on the main actions, commands used, and outcomes. Keep it under 200 words:\n\n{content}"
            }]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Error: No response from Gemini API"
    except Exception as e:
        return f"Error calling Gemini API: {str(e)}"

def store_in_jsonl(summary: str, original_content: str, session_info: dict):
    """Store the summary and metadata in a JSONL file"""
    jsonl_file = Path("session_summaries.jsonl")
    
    entry = {
        "content": summary,
        "metadata": {
            "original_content": original_content,
            "session_id": session_info.get("session_id"),
            "command": session_info.get("command"),
            "started_at": session_info.get("started_at"),
            "ended_at": session_info.get("ended_at"),
            "exit_code": session_info.get("exit_code"),
            "duration_sec": session_info.get("duration_sec")
        }
    }
    
    with jsonl_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def search_jsonl_hyperdb(query: str, max_results: int = 5) -> list:
    """Search through JSONL hyperDB for sessions matching the query string"""
    jsonl_file = Path("session_summaries.jsonl")
    
    if not jsonl_file.exists():
        return []
    
    results = []
    query_lower = query.lower()
    
    try:
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    
                    # Search in summary content
                    content_match = query_lower in entry.get("content", "").lower()
                    
                    # Search in command
                    command_match = query_lower in entry.get("metadata", {}).get("command", "").lower()
                    
                    # Search in original content (for deeper matching)
                    original_match = query_lower in entry.get("metadata", {}).get("original_content", "").lower()
                    
                    if content_match or command_match or original_match:
                        results.append({
                            "line_number": line_num,
                            "session_id": entry.get("metadata", {}).get("session_id", ""),
                            "summary": entry.get("content", ""),
                            "command": entry.get("metadata", {}).get("command", ""),
                            "started_at": entry.get("metadata", {}).get("started_at", ""),
                            "duration_sec": entry.get("metadata", {}).get("duration_sec", 0),
                            "original_content": entry.get("metadata", {}).get("original_content", ""),
                            "match_type": "content" if content_match else ("command" if command_match else "original")
                        })
                        
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"Error reading JSONL file: {e}", file=sys.stderr)
        return []
    
    # Sort by relevance (content matches first, then by recency)
    results.sort(key=lambda x: (
        0 if x["match_type"] == "content" else 1,
        -x["line_number"]
    ))
    
    return results[:max_results]

def get_original_content_by_session_id(session_id: str) -> str:
    """Retrieve original content for a specific session ID"""
    jsonl_file = Path("session_summaries.jsonl")
    
    if not jsonl_file.exists():
        return ""
    
    try:
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("metadata", {}).get("session_id") == session_id:
                        return entry.get("metadata", {}).get("original_content", "")
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading JSONL file: {e}", file=sys.stderr)
    
    return ""

def get_parent_winsize():
    for stream in (sys.stdout, sys.stdin):
        try:
            ws = fcntl.ioctl(stream.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))
            rows, cols, _, _ = struct.unpack('HHHH', ws)
            if rows and cols:
                return rows, cols
        except Exception:
            pass
    return 24, 80

def set_pty_winsize(master_fd, rows, cols):
    try:
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    except Exception:
        pass

# ---------------- core ----------------
def run(args):
    # Parse command after the '--'
    cmd_argv = args.command[1:] if (args.command and args.command[0] == "--") else args.command
    if not cmd_argv:
        print("Usage: conjurer.py run -- <command>", file=sys.stderr)
        sys.exit(2)
    cmdline = " ".join(cmd_argv)

    # Files
    raw_path, clean_path = base_paths(args.log, cmd_argv)
    # raw_fp = raw_path.open("wb")  # Commented out - no longer saving raw file

    # Session metadata
    session_id = str(uuid.uuid4())
    session_info = {
        "session_id": session_id,
        "name": args.name or '',
        "command": cmdline,
        "started_at": iso_now()
    }

    # Inject hyperDB content if history parameter is provided
    if args.history:
        print(f"\n[conjurer] Searching hyperDB for: {args.history}", file=sys.stderr)
        results = search_jsonl_hyperdb(args.history, max_results=3)
        
        if results:
            print(f"[conjurer] Found {len(results)} relevant sessions:", file=sys.stderr)
            for i, result in enumerate(results, 1):
                print(f"\n--- Session {i} (ID: {result['session_id'][:8]}...) ---", file=sys.stderr)
                print(f"Command: {result['command']}", file=sys.stderr)
                print(f"Started: {result['started_at']}", file=sys.stderr)
                print(f"Duration: {result['duration_sec']}s", file=sys.stderr)
                print(f"Summary: {result['summary'][:200]}{'...' if len(result['summary']) > 200 else ''}", file=sys.stderr)
                
                # Display the original content to terminal
                print(f"\n--- Original Terminal Content ---", file=sys.stderr)
                print(result['original_content'][:1000] + ('...[truncated]' if len(result['original_content']) > 1000 else ''), file=sys.stderr)
                print(f"--- End of Session {i} ---\n", file=sys.stderr)
        else:
            print(f"[conjurer] No sessions found matching '{args.history}'", file=sys.stderr)
        
        print("[conjurer] Press Enter to continue with your command...", file=sys.stderr)
        input()

    # Parent TTY size → child PTY
    rows, cols = get_parent_winsize()
    os.environ["LINES"], os.environ["COLUMNS"] = str(rows), str(cols)

    # Set stdin raw
    old_tty = termios.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin.fileno())

    started_ts = time.time()
    byte_count = 0
    h = blake2b(digest_size=16)
    child_pid = None
    raw_buf = bytearray()

    # Signal pass-through
    def passthru(sig, _frame):
        if child_pid:
            try: os.kill(child_pid, sig)
            except Exception: pass

    # Resize propagation (fix half-width TUIs)
    master_fd_box = {"fd": None}
    def on_winch(_sig, _frame):
        if master_fd_box["fd"] is None: return
        r, c = get_parent_winsize()
        set_pty_winsize(master_fd_box["fd"], r, c)
        if child_pid:
            try: os.kill(child_pid, signal.SIGWINCH)
            except Exception: pass

    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, passthru)
    signal.signal(signal.SIGWINCH, on_winch)

    exit_code = 0
    try:
        child_pid, master_fd = pty.fork()
        if child_pid == 0:
            os.execvp("/bin/bash", ["/bin/bash", "-lc", cmdline])
            os._exit(127)

        master_fd_box["fd"] = master_fd
        set_pty_winsize(master_fd, rows, cols)
        try: os.kill(child_pid, signal.SIGWINCH)
        except Exception: pass

        detach_prompt = False
        idle = max(0.01, (args.idle_flush_ms / 1000.0))

        while True:
            r, _, _ = select.select([sys.stdin.fileno(), master_fd], [], [], idle)

            if master_fd in r:
                try:
                    chunk = os.read(master_fd, 16384)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                # Echo to user terminal
                os.write(sys.stdout.fileno(), chunk)
                # RAW mirror + stats (raw file save commented out)
                # raw_fp.write(chunk); raw_fp.flush()
                raw_buf += chunk
                byte_count += len(chunk); h.update(chunk)

            if sys.stdin.fileno() in r:
                ch = os.read(sys.stdin.fileno(), 1)
                if detach_prompt:
                    if ch in (b"d", b"D"):
                        break
                    elif ch in (b"k", b"K"):
                        try: os.kill(child_pid, signal.SIGTERM)
                        except Exception: pass
                        break
                    else:
                        detach_prompt = False
                        os.write(master_fd, ch)
                elif ch == b"\x1d":  # Ctrl-]
                    sys.stdout.write("\r\n[conjurer] Detach: (d)etach  (k)ill  (other=continue)\r\n")
                    sys.stdout.flush()
                    detach_prompt = True
                else:
                    os.write(master_fd, ch)

        # Reap child
        try:
            _, status = os.waitpid(child_pid, 0)
            if os.WIFEXITED(status): exit_code = os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status): exit_code = 128 + os.WTERMSIG(status)
        except ChildProcessError:
            pass

    finally:
        # Restore terminal
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_tty)
        except Exception:
            pass

        # Close RAW writer (commented out)
        # raw_fp.flush(); raw_fp.close()

        # POST-PROCESS: clean from RAW using clean_ansi
        cleaned = ""
        try:
            cleaned = clean_ansi(raw_buf.decode("utf-8", "replace"))
            with clean_path.open("w", encoding="utf-8", newline="\n") as cfp:
                cfp.write(cleaned + ("\n" if cleaned and not cleaned.endswith("\n") else ""))
        except Exception as e:
            cleaned = f"[conjurer] CLEAN generation failed: {e}\n"
            with clean_path.open("w", encoding="utf-8") as cfp:
                cfp.write(cleaned)

        # Complete session info
        session_info.update({
            "ended_at": iso_now(),
            "exit_code": exit_code,
            "bytes_captured": byte_count,
            "content_blake2b": h.hexdigest(),
            "duration_sec": round(time.time() - started_ts, 3)
        })

        # Send to Gemini and store in JSONL
        if cleaned.strip():
            print("\n[conjurer] Sending session to Gemini for analysis...", file=sys.stderr)
            summary = send_to_gemini(cleaned)
            store_in_jsonl(summary, cleaned, session_info)
            print(f"[conjurer] Session summary stored in session_summaries.jsonl", file=sys.stderr)

# ---------------- CLI ----------------
if __name__ == "__main__":
    ap  = argparse.ArgumentParser(prog="conjurer", description="Capture terminal output via PTY (RAW-first; clean after).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    runp = sub.add_parser("run", help="Run a command under Conjurer")

    runp.add_argument("--name", default=None, help="Session name (meta only)")
    runp.add_argument("--log",  default=None, help="Base path (strftime ok). Default logs/%%Y%%m%%d_%%H%%M%%S_<cmd>")
    runp.add_argument("--idle-flush-ms", type=int, default=250, help="Read-loop timeout (ms)")
    runp.add_argument("--history", default=None, help="Search term to inject relevant hyperDB content to terminal before running command")
    runp.add_argument("command", nargs=argparse.REMAINDER, help="Use -- to separate conjurer args from your command")

    args = ap.parse_args()
    if args.cmd == "run":
        run(args)
