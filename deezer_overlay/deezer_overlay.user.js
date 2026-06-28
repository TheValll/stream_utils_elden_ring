// ==UserScript==
// @name         Deezer Overlay Bridge
// @namespace    local.deezer.overlay
// @version      1.2
// @description  Envoie le morceau Deezer en cours au widget Python (overlay.py)
// @match        https://www.deezer.com/*
// @match        https://deezer.com/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// ==/UserScript==

(function () {
    "use strict";

    const ENDPOINT = "http://127.0.0.1:7654";
    const INTERVAL_MS = 1000;

    let badge = null;
    function makeBadge() {
        badge = document.createElement("div");
        badge.textContent = "Overlay: démarrage…";
        badge.style.cssText = [
            "position:fixed", "top:8px", "right:8px", "z-index:2147483647",
            "background:#222", "color:#fff", "font:12px/1.4 Segoe UI, sans-serif",
            "padding:4px 8px", "border-radius:6px", "border:2px solid #888",
            "pointer-events:none", "opacity:0.9",
        ].join(";");
        (document.body || document.documentElement).appendChild(badge);
    }
    function setBadge(text, color) {
        if (!badge) return;
        badge.textContent = "Overlay: " + text;
        badge.style.borderColor = color;
    }

    function parseTime(str) {
        if (!str) return 0;
        const parts = String(str).trim().split(":").map(Number);
        if (parts.some(isNaN)) return 0;
        return parts.reduce((acc, n) => acc * 60 + n, 0);
    }

    function pickArtwork(artwork) {
        if (!artwork || !artwork.length) return "";
        let best = artwork[0];
        let bestSize = 0;
        for (const a of artwork) {
            const s = parseInt((a.sizes || "0").split("x")[0], 10) || 0;
            if (s >= bestSize) { bestSize = s; best = a; }
        }
        return best.src || "";
    }

    function getProgress() {
        const elEl = document.querySelector('[data-testid="elapsed_time"]');
        const remEl = document.querySelector('[data-testid="remaining_time"]');
        if (elEl && remEl) {
            const elapsed = parseTime(elEl.textContent);
            const remaining = parseTime(remEl.textContent);
            const duration = elapsed + remaining;
            if (duration > 0) return { elapsed: elapsed, duration: duration };
        }

        const cur = document.querySelector(
            '[data-testid="elapsed_time"], [data-testid="elapsed"], .slider-counter-current'
        );
        const dur = document.querySelector(
            '[data-testid="track_duration"], [data-testid="duration"], .slider-counter-max'
        );
        if (cur && dur) {
            const e = parseTime(cur.textContent);
            const d = parseTime(dur.textContent);
            if (d > 0) return { elapsed: e, duration: d };
        }

        const slider = document.querySelector('[role="slider"][aria-valuemax]');
        if (slider) {
            const now = parseFloat(slider.getAttribute("aria-valuenow"));
            const max = parseFloat(slider.getAttribute("aria-valuemax"));
            if (!isNaN(now) && !isNaN(max) && max > 0) {
                return { elapsed: now, duration: max };
            }
        }

        const audio = document.querySelector("audio");
        if (audio && audio.duration && !isNaN(audio.duration)) {
            return { elapsed: audio.currentTime, duration: audio.duration };
        }

        return { elapsed: 0, duration: 0 };
    }

    function isPlaying() {
        if (navigator.mediaSession && navigator.mediaSession.playbackState) {
            return navigator.mediaSession.playbackState === "playing";
        }
        const btn = document.querySelector(
            '[data-testid="pause_button"], [aria-label="Pause"], [aria-label="Mettre en pause"]'
        );
        return !!btn;
    }

    function getMeta() {
        let title = "", artist = "", cover = "";

        const md = navigator.mediaSession && navigator.mediaSession.metadata;
        if (md) {
            title = md.title || "";
            artist = md.artist || "";
            cover = pickArtwork(md.artwork);
        }

        if (!title) {
            const t = document.querySelector(
                '[data-testid="item_title"], .track-link, .player-track-title'
            );
            if (t) title = t.textContent.trim();
        }
        if (!artist) {
            const a = document.querySelector(
                '[data-testid="item_subtitle"], .track-artists, .player-track-artists'
            );
            if (a) artist = a.textContent.trim();
        }
        if (!cover) {
            const img = document.querySelector(
                '.player-track .cover img, [data-testid="player"] img, .player-cover img'
            );
            if (img && img.src) cover = img.src;
        }

        return { title, artist, cover };
    }

    function send() {
        const meta = getMeta();
        const prog = getProgress();
        const payload = {
            title: meta.title,
            artist: meta.artist,
            cover: meta.cover,
            elapsed: prog.elapsed,
            duration: prog.duration,
            playing: isPlaying(),
        };

        const sig = JSON.stringify(payload);

        const label = meta.title ? (meta.title + " — " + meta.artist) : "rien en lecture";
        GM_xmlhttpRequest({
            method: "POST",
            url: ENDPOINT,
            data: sig,
            headers: { "Content-Type": "application/json" },
            timeout: 3000,
            onload: () => setBadge("✓ " + label, "#3ad07a"),
            onerror: () => setBadge("widget injoignable (lancer overlay.py)", "#e0533a"),
            ontimeout: () => setBadge("widget injoignable (lancer overlay.py)", "#e0533a"),
        });
    }

    makeBadge();
    console.log("[Deezer Overlay] bridge actif -> " + ENDPOINT);
    setBadge("script actif", "#d0b03a");
    setInterval(send, INTERVAL_MS);
    send();
})();
