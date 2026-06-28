import io
import json
import ssl
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tkinter as tk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageTk, ImageDraw, ImageChops
    HAS_PIL = True
except Exception:
    HAS_PIL = False

PORT = 7654

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
    "title": "En attente de Deezer...",
    "artist": "",
    "cover": "",
    "elapsed": 0.0,
    "duration": 0.0,
    "playing": False,
    "stamp": 0.0,
}
state_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            data = {}

        with state_lock:
            state["title"] = data.get("title") or "—"
            state["artist"] = data.get("artist") or ""
            state["cover"] = data.get("cover") or ""
            try:
                state["elapsed"] = float(data.get("elapsed") or 0)
            except (TypeError, ValueError):
                state["elapsed"] = 0.0
            try:
                state["duration"] = float(data.get("duration") or 0)
            except (TypeError, ValueError):
                state["duration"] = 0.0
            state["playing"] = bool(data.get("playing"))
            state["stamp"] = _now()

        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *args):
        pass


def _now():
    import time
    return time.monotonic()


def start_server():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


class Overlay:
    def __init__(self, root):
        self.root = root
        root.title("Deezer Overlay")
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

    def _load_cover(self, url):
        if not HAS_PIL or not url or url == self._cover_url:
            return
        self._cover_url = url

        def worker():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                raw = urllib.request.urlopen(req, timeout=8, context=ctx).read()
                img = Image.open(io.BytesIO(raw))
                photo = self._rounded_photo(img)
                self._cover_img = photo
            except Exception as e:
                print("[cover] echec telechargement:", e)
                self._cover_img = None

        threading.Thread(target=worker, daemon=True).start()

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

        if playing and duration > 0:
            elapsed = min(duration, elapsed + (_now() - stamp))
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
    start_server()
    root = tk.Tk()
    Overlay(root)
    root.mainloop()


if __name__ == "__main__":
    main()
