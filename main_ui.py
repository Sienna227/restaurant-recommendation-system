import platform
import tkinter as tk
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "user_settings.txt"
FONT_NAME = "Malgun Gothic" if platform.system() == "Windows" else "AppleGothic"

FIELDS = [
    ("want_genre", "먹고 싶은 종류"),
    ("mood", "원하는 식당 분위기(기본 : 없음)"),
    ("left_time", "남은 시간(분)"),
    ("headcount", "인원 수"),
    ("hungriness", "배고픔 정도(1~5)"),
    ("poor", "가격 민감도(1~5)"),
    ("before_eat", "최근 먹은 종류"),
    ("next_route", "다음 목적지"),
]

DEFAULTS = ["한식", "없음", "60", "1", "3", "3", "없음", "학교"]


def choose(value):
    print(value, flush=True)
    window.destroy()


def load_settings():
    if not SETTINGS_FILE.exists():
        return DEFAULTS[:]
    values = SETTINGS_FILE.read_text(encoding="utf-8").splitlines()
    if len(values) == 7:
        values.insert(1, DEFAULTS[1])
    while len(values) < len(FIELDS):
        values.append(DEFAULTS[len(values)])
    values = values[:len(FIELDS)]
    if values[1] not in ["없음", "데이트", "혼밥", "술"]:
        values[1] = "없음"
    return values


def open_settings():
    settings_window = tk.Toplevel(window)
    settings_window.title("settings")
    settings_window.geometry("560x560")
    settings_window.minsize(480, 420)
    settings_window.resizable(True, True)

    old_values = load_settings()
    entries = []

    wrapper = tk.Frame(settings_window)
    wrapper.pack(fill="both", expand=True)

    canvas = tk.Canvas(wrapper, highlightthickness=0)
    scrollbar = tk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
    form = tk.Frame(canvas)

    form.bind(
        "<Configure>",
        lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
    )

    canvas_window = canvas.create_window((0, 0), window=form, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def resize_form(event):
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", resize_form)

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", on_mousewheel)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    guide = tk.Label(
        form,
        text="추천 조건을 입력해주세요.",
        justify="center",
        font=(FONT_NAME, 12, "bold"),
    )
    guide.grid(row=0, column=0, columnspan=2, padx=18, pady=(18, 16), sticky="ew")

    for i, (_, display_name) in enumerate(FIELDS):
        label = tk.Label(form, text=display_name, anchor="e", font=(FONT_NAME, 12))
        label.grid(row=i + 1, column=0, padx=(20, 12), pady=10, sticky="e")

        if FIELDS[i][0] == "mood":
            mood_var = tk.StringVar(value=old_values[i] if old_values[i] in ["없음", "데이트", "혼밥", "술"] else "없음")
            entry = tk.OptionMenu(form, mood_var, "없음", "데이트", "혼밥", "술")
            entry.config(width=27, font=(FONT_NAME, 12), anchor="w")
            entry.grid(row=i + 1, column=1, padx=(0, 20), pady=10, sticky="ew")
            entries.append(mood_var)
        else:
            entry = tk.Entry(form, width=30, font=(FONT_NAME, 12))
            entry.insert(0, old_values[i])
            entry.grid(row=i + 1, column=1, padx=(0, 20), pady=10, sticky="ew")
            entries.append(entry)

    form.grid_columnconfigure(1, weight=1)

    button_bar = tk.Frame(settings_window)
    button_bar.pack(fill="x", padx=12, pady=12)

    def save_settings():
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry.get().strip() + "\n")
        settings_window.destroy()

    save_button = tk.Button(button_bar, text="save", width=12, command=save_settings)
    save_button.pack(side="right", padx=5)

    close_button = tk.Button(button_bar, text="close", width=12, command=settings_window.destroy)
    close_button.pack(side="right", padx=5)


width = 600
height = 600

window = tk.Tk()
window.title("밥은 먹고 다니냐")
window.geometry(str(width) + "x" + str(height))
window.resizable(False, False)

canvas = tk.Canvas(window, width=width, height=height, highlightthickness=0)
canvas.pack(fill="both", expand=True)

bg_photo = None
try:
    from PIL import Image, ImageTk

    image_path = BASE_DIR / "main.png"
    if image_path.exists():
        bg_image = Image.open(image_path)
        bg_image = bg_image.resize((width, height))
        bg_photo = ImageTk.PhotoImage(bg_image)
        canvas.create_image(0, 0, image=bg_photo, anchor="nw")
    else:
        canvas.configure(bg="white")
except Exception:
    canvas.configure(bg="white")

canvas.create_text(
    width / 2,
    100,
    text="혜화에서 밥먹자!",
    font=(FONT_NAME, 40, "bold"),
    fill="black",
)

text_list = [("random", 0), ("favorites", 1), ("customize", 2)]

for i, (text, value) in enumerate(text_list):
    button = tk.Button(
        window,
        text=text,
        width=25,
        height=2,
        command=lambda value=value: choose(value),
    )
    canvas.create_window(width / 2, 305 + 72 * i, window=button)

settings_button = tk.Button(window, text="settings", width=10, height=1, command=open_settings)
canvas.create_window(width - 70, height - 40, window=settings_button)

quit_button = tk.Button(window, text="exit", width=10, height=1, command=lambda: choose(9))
canvas.create_window(70, height - 40, window=quit_button)

window.mainloop()
