import sys
import tkinter as tk

try:
    from pynput import keyboard, mouse
except ImportError:
    print("Le module 'pynput' est requis.\n  ->  pip install pynput")
    sys.exit(1)

UNIT_W = 40
UNIT_H = 36
MARGIN = 2
PAD    = 4

TRANSPARENT = "#ff00ff"
PANEL_BG   = "#00ff00"
KEY_FILL   = "#000000"
KEY_BORDER = "#8d79d6"
KEY_TEXT   = "#9381ff"
ON_FILL    = "#a37dde"
ON_BORDER  = "#a37dde"
ON_TEXT    = "#000000"

KEYS = [
    ("esc", "ESC", 0, 0.0, 1.5),
    ("1", "1", 0, 1.5, 1), ("2", "2", 0, 2.5, 1),
    ("3", "3", 0, 3.5, 1), ("4", "4", 0, 4.5, 1),
    ("z", "Z", 0, 5.5, 1), ("up", "↑", 0, 6.5, 1), ("x", "X", 0, 7.5, 1),
    ("m1", "M1", 0, 8.5, 1), ("m2", "M2", 0, 9.5, 1),
    ("tab", "TAB", 1, 0.0, 1.5),
    ("r", "R", 1, 1.5, 1), ("w", "W", 1, 2.5, 1),
    ("e", "E", 1, 3.5, 1), ("f", "F", 1, 4.5, 1),
    ("left", "←", 1, 5.5, 1), ("down", "↓", 1, 6.5, 1), ("right", "→", 1, 7.5, 1),
    ("m3", "M3", 1, 8.5, 1), ("m4", "M4", 1, 9.5, 1),
    ("shift", "SHIFT", 2, 0.0, 1.5),
    ("a", "A", 2, 1.5, 1), ("s", "S", 2, 2.5, 1),
    ("d", "D", 2, 3.5, 1), ("g", "G", 2, 4.5, 1),
    ("space", "SPACE", 2, 5.5, 3.0),
    ("rctrl", "RCTRL", 2, 8.5, 2.0),
]

TOTAL_UNITS = 10.5
CANVAS_W = int(PAD * 2 + TOTAL_UNITS * UNIT_W)
CANVAS_H = int(PAD * 2 + 3 * UNIT_H)

CHAR_KEYS = {"1", "2", "3", "4", "z", "x", "r", "w", "e", "f", "a", "s", "d", "g"}

SPECIAL_KEYS = {
    keyboard.Key.esc: "esc",
    keyboard.Key.tab: "tab",
    keyboard.Key.space: "space",
    keyboard.Key.up: "up",
    keyboard.Key.down: "down",
    keyboard.Key.left: "left",
    keyboard.Key.right: "right",
    keyboard.Key.shift: "shift",
    keyboard.Key.shift_l: "shift",
    keyboard.Key.shift_r: "shift",
    keyboard.Key.ctrl_r: "rctrl",
}

MOUSE_KEYS = {
    mouse.Button.left: "m1",
    mouse.Button.right: "m2",
}
for _name, _id in (("x1", "m4"), ("x2", "m3")):
    _btn = getattr(mouse.Button, _name, None)
    if _btn is not None:
        MOUSE_KEYS[_btn] = _id


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


class KeyOverlay:
    def __init__(self):
        self.pressed = set()
        self.rendered = set()
        self.mods = set()
        self.quit_flag = False
        self.lock_flag = False
        self.locked = False
        self._drag = (0, 0)

        self.root = tk.Tk()
        self.root.title("keyboard_overlay")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.geometry(f"{CANVAS_W}x{CANVAS_H}+200+200")
        self.root.protocol("WM_DELETE_WINDOW", self._request_quit)
        self.root.configure(bg=PANEL_BG)

        self.canvas = tk.Canvas(
            self.root, width=CANVAS_W, height=CANVAS_H,
            bg=PANEL_BG, highlightthickness=0,
        )
        self.canvas.pack()

        self.items = {}
        self._build_keys()

        self.canvas.bind("<ButtonPress-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._do_move)

        self.kb_listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release)
        self.ms_listener = mouse.Listener(on_click=self._on_click)
        self.kb_listener.daemon = True
        self.ms_listener.daemon = True
        self.kb_listener.start()
        self.ms_listener.start()

        self._poll()

    def _build_keys(self):
        big = {"esc", "tab", "shift"}
        for kid, label, row, xu, wu in KEYS:
            x1 = PAD + xu * UNIT_W + MARGIN
            y1 = PAD + row * UNIT_H + MARGIN
            x2 = PAD + xu * UNIT_W + wu * UNIT_W - MARGIN
            y2 = PAD + row * UNIT_H + UNIT_H - MARGIN
            rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=KEY_FILL, outline=KEY_BORDER, width=1)
            fsize = 13 if kid in big else 12
            txt = self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2, text=label,
                fill=KEY_TEXT, font=("Poppins", fsize, "bold"))
            self.items[kid] = (rect, txt)

    def _start_move(self, e):
        self._drag = (e.x, e.y)

    def _do_move(self, e):
        if self.locked:
            return
        x = self.root.winfo_x() + (e.x - self._drag[0])
        y = self.root.winfo_y() + (e.y - self._drag[1])
        self.root.geometry(f"+{x}+{y}")

    def _on_key_press(self, key):
        vk = getattr(key, "vk", None)
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.mods.add("ctrl")
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, getattr(keyboard.Key, "alt_gr", None)):
            self.mods.add("alt")

        if "ctrl" in self.mods and "alt" in self.mods and vk is not None:
            if vk == 0x51:
                self._request_quit()
                return
            if vk == 0x4C:
                self.lock_flag = True

        kid = self._key_id(key)
        if kid:
            self.pressed.add(kid)

    def _on_key_release(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.mods.discard("ctrl")
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, getattr(keyboard.Key, "alt_gr", None)):
            self.mods.discard("alt")
        kid = self._key_id(key)
        if kid:
            self.pressed.discard(kid)

    def _on_click(self, x, y, button, pressed):
        kid = MOUSE_KEYS.get(button)
        if not kid:
            return
        if pressed:
            self.pressed.add(kid)
        else:
            self.pressed.discard(kid)

    @staticmethod
    def _key_id(key):
        if key in SPECIAL_KEYS:
            return SPECIAL_KEYS[key]
        ch = getattr(key, "char", None)
        if ch:
            ch = ch.lower()
            if ch in CHAR_KEYS:
                return ch
        return None

    def _request_quit(self):
        self.quit_flag = True

    def _poll(self):
        if self.quit_flag:
            self._shutdown()
            return

        if self.lock_flag:
            self.lock_flag = False
            self._toggle_clickthrough()

        snapshot = set(self.pressed)
        if snapshot != self.rendered:
            for kid in snapshot - self.rendered:
                self._set_key(kid, True)
            for kid in self.rendered - snapshot:
                self._set_key(kid, False)
            self.rendered = snapshot

        self.root.after(16, self._poll)

    def _set_key(self, kid, on):
        item = self.items.get(kid)
        if not item:
            return
        rect, txt = item
        if on:
            self.canvas.itemconfig(rect, fill=ON_FILL, outline=ON_BORDER, width=2)
            self.canvas.itemconfig(txt, fill=ON_TEXT)
        else:
            self.canvas.itemconfig(rect, fill=KEY_FILL, outline=KEY_BORDER, width=1)
            self.canvas.itemconfig(txt, fill=KEY_TEXT)

    def _toggle_clickthrough(self):
        if sys.platform != "win32":
            return
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        if not hwnd:
            hwnd = self.root.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        self.locked = not self.locked
        if self.locked:
            style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _shutdown(self):
        try:
            self.kb_listener.stop()
            self.ms_listener.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    KeyOverlay().run()
