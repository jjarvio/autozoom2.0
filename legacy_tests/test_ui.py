import threading
import tkinter as tk
from darts_engine import DartsEngine

# ENGINE
engine = DartsEngine(mode=DartsEngine.MODE_TEST)


def start_engine():
    engine.run()


threading.Thread(target=start_engine, daemon=True).start()

# UI
root = tk.Tk()
root.title("Darts Control")
root.geometry("300x300")
root.resizable(False, False)

# REMAINING DISPLAY
remaining_var = tk.StringVar(value="Remaining: 501")

remaining_label = tk.Label(
    root,
    textvariable=remaining_var,
    font=("Arial", 20, "bold")
)
remaining_label.pack(pady=10)


def update_remaining():
    remaining_var.set(f"Remaining: {engine.remaining}")
    root.after(200, update_remaining)


update_remaining()


# SET REMAINING
set_frame = tk.LabelFrame(root, text="Set remaining")
set_frame.pack(padx=10, pady=5, fill="x")

remaining_entry = tk.Entry(set_frame, justify="center")
remaining_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")


def set_remaining(event=None):
    try:
        value = int(remaining_entry.get())
        engine.ui_set_remaining(value)
        remaining_entry.delete(0, tk.END)
        remaining_entry.focus_set()
    except ValueError:
        pass


remaining_entry.bind("<Return>", set_remaining)

tk.Button(
    set_frame,
    text="Send",
    width=8,
    command=set_remaining
).pack(side="right", padx=5)

# MANUAL THROW
throw_frame = tk.LabelFrame(root, text="Manual throw")
throw_frame.pack(padx=10, pady=10, fill="x")

throw_entry = tk.Entry(throw_frame, justify="center")
throw_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")


def manual_throw(event=None):
    value = throw_entry.get().strip()
    if value:
        engine.manual_throw(value)
        throw_entry.delete(0, tk.END)
        throw_entry.focus_set()


throw_entry.bind("<Return>", manual_throw)

tk.Button(
    throw_frame,
    text="Send",
    width=8,
    command=manual_throw
).pack(side="right", padx=5)

# ALWAYS ON TOP
always_on_top = tk.BooleanVar(value=False)


def toggle_always_on_top():
    root.attributes("-topmost", always_on_top.get())


tk.Checkbutton(
    root,
    text="Always on top",
    variable=always_on_top,
    command=toggle_always_on_top
).pack(pady=5)

# RESET TURN
tk.Button(
    root,
    text="Reset turn (throw -> 0)",
    width=25,
    command=engine.ui_reset_turn
).pack(pady=5)


# RESET LEG
tk.Button(
    root,
    text="Reset leg",
    width=25,
    command=engine.ui_reset_leg
).pack(pady=10)

# START UI
remaining_entry.focus_set()
root.mainloop()
