import io
import asyncio
import threading
from spotify_reader import poll
import tkinter as tk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageTk, ImageDraw, ImageChops
    HAS_PIL = True
except Exception:
    HAS_PIL = False

PAD = 10
W = 480
H = 130
CARD = (PAD, PAD, W - PAD, H - PAD)
RADIUS = 16

ART = (20, 20, 100, 100)
ART_RADIUS = 0

TEXT_X = 120
TITLE_Y = 32
ARTIST_Y = 58

BAR_X0 = TEXT_X
BAR_X1 = W - 55
BAR_Y = 72
BAR_H = 28
BAR_RADIUS = 4

KEY = "#ff00ff"
CARD_BG = "#ff00ff"
CARD_BORDER = "#ff00ff"
TITLE_COLOR = "#ce82ef"
ARTIST_COLOR = "#a37dde"
BAR_TRACK = "#1a1a1a"
BAR_BORDER = "#ffffff"
ART_BORDER = "#9b68e6"
FILL_LEFT = "#a37dde"
FILL_RIGHT = "#ce82ef"

state = {
    "title": "En attente de Spotify...",
    "artist": "",
    "cover": b"",
    "track": None,
    "position_revision": 0,
    "elapsed": 0.0,
    "duration": 0.0,
    "playing": False,
    "stamp": 0.0,
}
state_lock = threading.Lock()


def _now():
    import time
    return time.monotonic()


def start_reader():
    threading.Thread(target=lambda: asyncio.run(poll(state, state_lock)), daemon=True).start()


class Overlay:
    def __init__(self, root):
        self.root = root
        root.title("Spotify Overlay")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        root.geometry(f"{W}x{H}+120+120")
        root.configure(bg=KEY)

        self.canvas = tk.Canvas(root, width=W, height=H, bg=KEY,
                                highlightthickness=0)
        self.canvas.pack()

        self.title_font = tkfont.Font(family="Poppins", size=14, weight="bold")
        self.artist_font = tkfont.Font(family="Poppins", size=10, weight="bold")

        self._cover_url = None
        self._cover_img = None
        self._placeholder = self._make_placeholder()
        self._progress_track = None
        self._progress_elapsed = 0.0
        self._progress_stamp = _now()
        self._progress_playing = False
        self._position_revision = 0

        root.bind("<Escape>", lambda e: root.destroy())

        self._dx = self._dy = 0
        self.render()

    def round_rect(self, x0, y0, x1, y1, r, **kw):
        if r <= 0:
            return self.canvas.create_rectangle(x0, y0, x1, y1, **kw)
        pts = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def _make_placeholder(self):
        if not HAS_PIL:
            return None
        w = ART[2] - ART[0]
        h = ART[3] - ART[1]
        img = Image.new("RGB", (w, h), (40, 30, 55))
        d = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            r = int(60 + 120 * t)
            g = int(20 + 30 * t)
            b = int(90 + 120 * t)
            d.line([(0, y), (w, y)], fill=(r, g, b))
        return self._rounded_photo(img)

    def _rounded_photo(self, img):
        w = ART[2] - ART[0]
        h = ART[3] - ART[1]
        img = img.convert("RGBA").resize((w, h), Image.LANCZOS)
        if ART_RADIUS > 0:
            mask = Image.new("L", (w, h), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], ART_RADIUS, fill=255)
            img.putalpha(mask)
        return ImageTk.PhotoImage(img)

    def _load_cover(self, data):
        if not HAS_PIL or data == self._cover_url:
            return
        self._cover_url = data
        self._cover_img = None
        if data:
            try:
                self._cover_img = self._rounded_photo(Image.open(io.BytesIO(data)))
            except Exception as e:
                print("[cover] lecture impossible:", e)

    def _make_bar_image(self, width, height, frac, radius):
        width = max(1, int(width))
        height = max(1, int(height))
        frac = max(0.0, min(1.0, frac))

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, width - 1, height - 1], radius, fill=255)

        fill_w = int(round(width * frac))
        if fill_w > 0:
            cl = self._hex(FILL_LEFT)
            cr = self._hex(FILL_RIGHT)
            fill = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            fd = ImageDraw.Draw(fill)
            denom = max(1, fill_w - 1)
            for x in range(fill_w):
                t = x / denom
                color = (
                    int(cl[0] + (cr[0] - cl[0]) * t),
                    int(cl[1] + (cr[1] - cl[1]) * t),
                    int(cl[2] + (cr[2] - cl[2]) * t),
                    255,
                )
                fd.line([(x, 0), (x, height)], fill=color)
            fa = ImageChops.multiply(fill.split()[3], mask)
            fill.putalpha(fa)
            img = Image.alpha_composite(img, fill)

        ImageDraw.Draw(img).rounded_rectangle(
            [1, 1, width - 2, height - 2], radius,
            outline=(255, 255, 255, 255), width=2)

        return ImageTk.PhotoImage(img)

    def _draw_gradient_bar(self, x0, y0, x1, y1, frac):
        frac = max(0.0, min(1.0, frac))
        fill_w = (x1 - x0) * frac
        if fill_w < 2:
            return
        steps = max(1, int(fill_w))
        cl = self._hex(FILL_LEFT)
        cr = self._hex(FILL_RIGHT)
        for i in range(steps):
            t = i / max(1, fill_w)
            color = "#%02x%02x%02x" % (
                int(cl[0] + (cr[0] - cl[0]) * t),
                int(cl[1] + (cr[1] - cl[1]) * t),
                int(cl[2] + (cr[2] - cl[2]) * t),
            )
            self.canvas.create_line(x0 + i, y0, x0 + i, y1, fill=color)

    @staticmethod
    def _hex(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def render(self):
        c = self.canvas
        c.delete("all")

        with state_lock:
            title = state["title"]
            artist = state["artist"]
            cover = state["cover"]
            elapsed = state["elapsed"]
            duration = state["duration"]
            playing = state["playing"]
            stamp = state["stamp"]
            track = state["track"]
            position_revision = state["position_revision"]

        now = _now()
        predicted = self._progress_elapsed
        if self._progress_playing:
            predicted += max(0.0, now - self._progress_stamp)
        if track != self._progress_track:
            self._progress_elapsed = elapsed
            self._progress_stamp = now
        elif playing != self._progress_playing:
            self._progress_elapsed = predicted
            self._progress_stamp = now
        elif position_revision != self._position_revision and abs(elapsed - predicted) > 3.0:
            # A real seek or replay; unchanged Windows positions must never rewind the bar.
            self._progress_elapsed = elapsed
            self._progress_stamp = now
        self._progress_track = track
        self._progress_playing = playing
        self._position_revision = position_revision
        elapsed = self._progress_elapsed
        if playing and duration > 0:
            elapsed = min(duration, elapsed + max(0.0, now - self._progress_stamp))
        frac = (elapsed / duration) if duration > 0 else 0.0

        x0, y0, x1, y1 = CARD
        self.round_rect(x0, y0, x1, y1, RADIUS, fill=CARD_BG, outline=CARD_BORDER, width=0)

        self._load_cover(cover)
        img = self._cover_img or self._placeholder
        if img is not None:
            c.create_image(ART[0], ART[1], image=img, anchor="nw")
        else:
            self.round_rect(*ART, ART_RADIUS, fill="#3a2c50", outline="")

        c.create_rectangle(ART[0]-2, ART[1]-2, ART[2]+2, ART[3]+2, outline=ART_BORDER, width=3)

        c.create_text(TEXT_X, TITLE_Y, text=self._clip(title, 30),
                      anchor="w", fill=TITLE_COLOR, font=self.title_font)
        c.create_text(TEXT_X, ARTIST_Y, text=self._clip(artist, 38),
                      anchor="w", fill=ARTIST_COLOR, font=self.artist_font)

        if HAS_PIL:
            self._bar_img = self._make_bar_image(
                BAR_X1 - BAR_X0, BAR_H, frac, BAR_RADIUS)
            c.create_image(BAR_X0, BAR_Y, image=self._bar_img, anchor="nw")
        else:
            if frac > 0:
                fx1 = BAR_X0 + (BAR_X1 - BAR_X0) * frac
                self._draw_gradient_bar(BAR_X0 + 2, BAR_Y + 2, fx1,
                                        BAR_Y + BAR_H - 2, 1.0)
            self.round_rect(BAR_X0, BAR_Y, BAR_X1, BAR_Y + BAR_H, BAR_RADIUS,
                            fill="", outline=BAR_BORDER, width=2)

        self.root.after(60, self.render)

    @staticmethod
    def _clip(s, n):
        s = s or ""
        return s if len(s) <= n else s[: n - 1] + "…"


def main():
    start_reader()
    root = tk.Tk()
    Overlay(root)
    root.mainloop()


if __name__ == "__main__":
    main()
