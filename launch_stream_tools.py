"""Launch the stream tools and LiveSplit. Stop them all with Ctrl+C."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TWITCH_BOT = Path(r"C:\Users\Valentin\Documents\dev\cloud\twitch_bot")
LIVESPLIT = ROOT.parent / "LiveSplit_1.8.37" / "LiveSplit.exe"
JOBS = (
    ("LiveSplit", LIVESPLIT, LIVESPLIT.parent),
    ("Spotify overlay", ROOT / "spotify_overlay" / "overlay.py", ROOT / "spotify_overlay"),
    ("Spotify hotkey", ROOT / "spotify_hotkey" / "spotify_hotkey.py", ROOT / "spotify_hotkey"),
    ("Elden Ring leaderboard proxy", ROOT / "elden_ring_leaderboard" / "proxy.py", ROOT / "elden_ring_leaderboard"),
    ("Keyboard overlay", ROOT / "keyboard_overlay" / "overlay.py", ROOT / "keyboard_overlay"),
    ("Windows hotkey", TWITCH_BOT / "windows_hotkey.py", TWITCH_BOT),
)


def check_paths():
    missing = [str(script) for _, script, cwd in JOBS if not script.is_file() or not cwd.is_dir()]
    if missing:
        raise FileNotFoundError("Script ou dossier introuvable :\n" + "\n".join(missing))
    print(f"{len(JOBS)} programmes trouvés. Interpréteur Python : {sys.executable}", flush=True)


def stop_all(processes):
    for name, process in processes:
        if process.poll() is None:
            print("Arrêt : " + name, flush=True)
            process.terminate()
    for _, process in processes:
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description="Lance les outils de stream dans ce terminal")
    parser.add_argument("--check", action="store_true", help="Vérifie les chemins sans démarrer les outils")
    args = parser.parse_args()
    check_paths()
    if args.check:
        return 0

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    processes = []
    try:
        for name, script, cwd in JOBS:
            command = [sys.executable, "-u", str(script)] if script.suffix.lower() == ".py" else [str(script)]
            process = subprocess.Popen(
                command, cwd=cwd, env=env,
                creationflags=flags,
            )
            processes.append((name, process))
            print(f"Démarré : {name} (PID {process.pid})", flush=True)
        print("Tous les outils sont lancés. Ctrl+C pour tout arrêter.", flush=True)
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"{name} s'est arrêté (code {code}).", flush=True)
                    return 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Arrêt demandé.", flush=True)
        return 0
    finally:
        stop_all(processes)


if __name__ == "__main__":
    sys.exit(main())
