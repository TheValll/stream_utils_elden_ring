"""Ctrl+Shift+\\ plays a fixed track through the Spotify Web API.

Run: python spotify_hotkey.py
The developer app must allow http://127.0.0.1:8765/callback.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import certifi
from pynput import keyboard


TRACK_URI = "spotify:track:4dHOnPucB5VBYq3gjRtYy9"
CLIENT_ID = "8d1f49a4c6d94b5eb2c6ff3408e0ca44"
HOTKEY = "<ctrl>+<shift>+\\"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPES = "user-modify-playback-state user-read-playback-state"
TOKEN_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StreamUtilsEldenRing" / "spotify_hotkey_token.json"
play_lock = threading.Lock()
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def post_form(url, values):
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=15, context=HTTPS_CONTEXT) as response:
        return json.load(response)


def save_token(token):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(token), encoding="utf-8")


def authorize(client_id):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    state = secrets.token_urlsafe(24)
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(url.query)
            if url.path != "/callback" or query.get("state", [None])[0] != state:
                self.send_error(400, "Invalid OAuth callback")
                return
            result["code"] = query.get("code", [None])[0]
            result["error"] = query.get("error", [None])[0]
            body = "Connexion Spotify terminée. Tu peux fermer cet onglet.".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
    })
    server = HTTPServer(("127.0.0.1", 8765), Callback)
    server.timeout = 180
    try:
        print("Connexion initiale : autorise l'application dans le navigateur.", flush=True)
        webbrowser.open("https://accounts.spotify.com/authorize?" + params)
        server.handle_request()
    finally:
        server.server_close()
    if not result.get("code"):
        raise RuntimeError(result.get("error") or "Connexion Spotify expirée.")
    token = post_form("https://accounts.spotify.com/api/token", {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    })
    token["client_id"] = client_id
    token["expires_at"] = time.time() + token["expires_in"]
    save_token(token)
    return token


def access_token(client_id):
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8")) if TOKEN_FILE.exists() else None
    if token is None or token.get("client_id") != client_id:
        token = authorize(client_id)
    if time.time() >= token["expires_at"] - 60:
        refreshed = post_form("https://accounts.spotify.com/api/token", {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        })
        refreshed["refresh_token"] = refreshed.get("refresh_token", token["refresh_token"])
        refreshed["client_id"] = client_id
        refreshed["expires_at"] = time.time() + refreshed["expires_in"]
        token = refreshed
        save_token(token)
    return token["access_token"]


def spotify_request(method, path, token, payload=None):
    request = urllib.request.Request(
        "https://api.spotify.com/v1" + path,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=15, context=HTTPS_CONTEXT) as response:
        return None if response.status == 204 else json.load(response)


def choose_computer(devices):
    computers = [
        d for d in devices
        if (d.get("type") or "").lower() == "computer"
        and d.get("id")
        and not d.get("is_restricted")
    ]
    active = next((d for d in computers if d.get("is_active")), None)
    if active:
        return active
    name = os.environ.get("COMPUTERNAME", "").lower()
    named = next((d for d in computers if d.get("name", "").lower() == name), None)
    if named:
        return named
    if len(computers) == 1:
        return computers[0]
    if not computers:
        raise RuntimeError("Ouvre Spotify sur ce PC, puis réessaie.")
    raise RuntimeError("Plusieurs ordinateurs Spotify sont visibles : active celui de ce PC.")


def play_track(client_id):
    if not play_lock.acquire(blocking=False):
        return
    try:
        token = access_token(client_id)
        devices = spotify_request("GET", "/me/player/devices", token)["devices"]
        device = choose_computer(devices)
        path = "/me/player/play?" + urllib.parse.urlencode({"device_id": device["id"]})
        spotify_request("PUT", path, token, {"uris": [TRACK_URI], "position_ms": 0})
        print("Lecture lancée sur " + device["name"] + ".", flush=True)
    except urllib.error.HTTPError as exc:
        print(f"Spotify a refusé la lecture (HTTP {exc.code}).", flush=True)
    except Exception as exc:
        print(f"Impossible de lancer le titre : {exc}", flush=True)
    finally:
        play_lock.release()


def main():
    parser = argparse.ArgumentParser(description="Raccourci Spotify sans changement de fenêtre")
    parser.add_argument("--client-id", help="Client ID de ton application Spotify Developer")
    args = parser.parse_args()
    client_id = args.client_id or os.environ.get("SPOTIFY_CLIENT_ID") or CLIENT_ID
    access_token(client_id)
    print("Raccourci actif : Ctrl+Shift+\\ (Ctrl+C pour quitter).", flush=True)
    with keyboard.GlobalHotKeys({
        HOTKEY: lambda: threading.Thread(target=play_track, args=(client_id,), daemon=True).start()
    }) as listener:
        listener.join()


if __name__ == "__main__":
    main()
