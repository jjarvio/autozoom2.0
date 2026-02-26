import os
import threading
from flask import Flask, request, redirect, url_for, render_template_string
from darts_engine import DartsEngine

app = Flask(__name__)
engine = DartsEngine()

HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darts Control</title>

<style>
body {
    font-family: Arial, sans-serif;
    background: #111;
    color: #fff;
    padding: 20px;
    margin: 0;
}

/* Container keeps everything centered and same width */
.container {
    max-width: 360px;
    margin: 0 auto;
}

h1 {
    font-size: 42px;
    text-align: center;
    margin-bottom: 30px;
}

/* SAME SIZE for inputs and buttons */
.control {
    width: 100%;
    max-width: 320px;
    padding: 14px;
    font-size: 20px;
    margin: 10px auto;
    display: block;
    box-sizing: border-box;
    border-radius: 8px;
    border: none;
}

input.control {
    background: #fff;
    color: #000;
}

button.control {
    background: #6a736d;
    color: #000;
    font-weight: bold;
}

button.reset {
    background: #e74c3c;
}

.section {
    margin-top: 50px;
}
</style>
</head>

<body>
<div class="container">

    <h1>Remaining: <span id="remaining">{{ remaining }}</span></h1>

    <div class="section">
        <form method="post" action="/set_remaining">
            <input
                class="control"
                name="value"
                inputmode="numeric"
                placeholder="Set remaining (e.g. 40)"
                autofocus
            >
            <button class="control">Set remaining</button>
        </form>
    </div>

    <div class="section">
        <form method="post" action="/throw">
            <input
                class="control"
                name="value"
                placeholder="Manual throw (T20, D16, 50)"
            >
            <button class="control">Send throw</button>
        </form>
    </div>

    <div class="section">
        <form method="post" action="/reset">
            <button class="control reset">Reset leg</button>
        </form>
    </div>

</div>

<script>
async function refreshState() {
    try {
        const response = await fetch('/state', { cache: 'no-store' });
        if (!response.ok) return;
        const data = await response.json();
        const remainingEl = document.getElementById('remaining');
        if (remainingEl && typeof data.remaining === 'number') {
            remainingEl.textContent = data.remaining;
        }
    } catch (_) {
        // no-op: keep previous value
    }
}

setInterval(refreshState, 400);
refreshState();
</script>

</body>
</html>
"""

def _start_engine_polling():
    try:
        engine.run()
    except Exception as exc:
        print(f"[WEB_UI] Engine polling stopped: {exc}")


threading.Thread(target=_start_engine_polling, daemon=True).start()


@app.route("/")
def index():
    return render_template_string(HTML, remaining=engine.remaining)


@app.route("/health")
def health():
    return {"status": "ok", "remaining": engine.remaining}


@app.route("/state")
def state():
    return {"remaining": engine.remaining, "throw_index": engine.throw_index}


@app.route("/set_remaining", methods=["POST"])
def set_remaining():
    try:
        engine.ui_set_remaining(int(request.form["value"]))
    except Exception:
        pass
    return redirect(url_for("index"))


@app.route("/throw", methods=["POST"])
def throw():
    value = request.form.get("value", "").strip()
    if value:
        engine.manual_throw(value)
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset():
    engine.ui_reset_leg()
    return redirect(url_for("index"))


if __name__ == "__main__":
    host = os.getenv("DARTS_UI_HOST", "0.0.0.0")
    port = int(os.getenv("DARTS_UI_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
