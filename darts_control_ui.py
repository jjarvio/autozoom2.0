import threading
import tkinter as tk
from darts_engine import DartsEngine
from tkinter import messagebox


# ENGINE
engine = DartsEngine()


def start_engine():
    engine.run()


threading.Thread(target=start_engine, daemon=True).start()

# UI
root = tk.Tk()
root.title("Darts Control")
root.geometry("300x500")
root.resizable(False, False)
reset_confirm_pending = False
reset_timer = None

def reset_button_reset():
    reset_button.config(
        text="Reset leg",
        bg=default_button_bg,
        fg=default_button_fg
    )


def reset_confirm_timeout():
    global reset_confirm_pending
    reset_confirm_pending = False
    reset_button_reset()


def reset_leg_confirm():
    global reset_confirm_pending, reset_timer

    if not reset_confirm_pending:
        # 1. painallus → varmistustila
        reset_confirm_pending = True
        reset_button.config(
            text="CONFIRM RESET",
            bg="red",
            fg="white"
        )

        # palaa normaaliksi 5 sekunnin kuluttua
        reset_timer = root.after(5000, reset_confirm_timeout)

    else:
        # 2. painallus → reset
        reset_confirm_pending = False

        if reset_timer:
            root.after_cancel(reset_timer)
            reset_timer = None

        engine.ui_reset_leg()
        reset_button_reset()



# REMAINING + THROW INDEX
remaining_var = tk.StringVar(value=f"Remaining: {engine.remaining}")
throw_var = tk.StringVar(value="Throw: 0 / 3")
last_throw_var = tk.StringVar(value="Last throw: -")


remaining_label = tk.Label(
    root,
    textvariable=remaining_var,
    font=("Arial", 20, "bold")
)
remaining_label.pack(pady=(10, 0))

throw_label = tk.Label(
    root,
    textvariable=throw_var,
    font=("Arial", 12)
)
throw_label.pack(pady=(0, 10))

last_throw_label = tk.Label(
    root,
    textvariable=last_throw_var,
    font=("Arial", 12, "italic")
)
last_throw_label.pack(pady=(0, 10))



def update_status():
    remaining_var.set(f"Remaining: {engine.remaining}")
    throw_var.set(f"Throw: {engine.throw_index} / 3")

    if engine.last_throw:
        if engine.last_throw_undone:
            last_throw_var.set(f"Last throw: {engine.last_throw} (undone)")
        else:
            last_throw_var.set(f"Last throw: {engine.last_throw}")
    else:
        last_throw_var.set("Last throw: -")

    root.after(200, update_status)

update_status()


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

# Nappi manuaaliselle heitolle
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

# päälimmäisenä checkbox
tk.Checkbutton(
    root,
    text="Always on top",
    variable=always_on_top,
    command=toggle_always_on_top
).pack(pady=5)

# Peru edellinen heitto
tk.Button(
    root,
    text="Undo last throw",
    width=25,
    command=engine.undo_last_throw
).pack(pady=5)

# RESET TURN (heittovuoro)
tk.Button(
    root,
    text="Reset turn (throw -> 0)",
    width=25,
    command=engine.ui_reset_turn
).pack(pady=5)


# RESET LEG
reset_button = tk.Button(
    root,
    text="Reset leg",
    width=25,
    command=reset_leg_confirm
)

# =========================
# HOTKEYS / STREAM DECK
# =========================

# Undo last throw
root.bind("<Control-z>", lambda e: engine.undo_last_throw())

# Reset turn (throw -> 0)
root.bind("<Control-r>", lambda e: engine.ui_reset_turn())

# Reset leg
root.bind("<Control-l>", lambda e: engine.ui_reset_leg())

# tallenna oletusvärit
default_button_bg = reset_button.cget("bg")
default_button_fg = reset_button.cget("fg")

reset_button.pack(pady=10)



# START UI
remaining_entry.focus_set()
root.mainloop()
