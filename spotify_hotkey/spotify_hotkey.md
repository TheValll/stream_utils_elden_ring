# Raccourci Spotify

Ce script lance **You See Big Girl / T:T** avec `Ctrl+Shift+\` via l'API Spotify. Pendant le raccourci, il ne change pas la fenêtre active.

## Première configuration

1. Ouvre le [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) avec ton compte Premium et crée une application.
2. Dans le formulaire, choisis **Web API**. Dans **Redirect URIs**, ajoute exactement `http://127.0.0.1:8765/callback`, puis enregistre.
3. Le **Client ID** fourni est déjà configuré dans le script. Le **Client Secret** n'est pas nécessaire.
4. Lance `SpotifyHotkey.exe`, ou installe les dépendances avec `python -m pip install -r requirements.txt` puis lance `python spotify_hotkey.py`. Une page Spotify s'ouvre une seule fois pour autoriser l'application.

Les fois suivantes, lance simplement le script ou l'EXE. Laisse la fenêtre ouverte pendant le jeu et ferme-la avec `Ctrl+C`. Le jeton de connexion est conservé dans `%LOCALAPPDATA%\StreamUtilsEldenRing\spotify_hotkey_token.json`.

Spotify pour Windows doit être ouvert et visible comme appareil Spotify Connect. La commande utilise l'ordinateur actif, ou l'unique ordinateur disponible.
