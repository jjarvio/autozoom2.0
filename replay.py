import time
import threading


class ReplayManager:
    def __init__(self, obs, cooldown=5.0):
        self.obs = obs
        self.cooldown = cooldown
        self._last_replay_time = 0
        self._lock = threading.Lock()

    def trigger(self, reason: str):
        if not self.obs:
            return

        now = time.time()
        with self._lock:
            if now - self._last_replay_time < self.cooldown:
                return
            self._last_replay_time = now

        print(f"[REPLAY] Triggered ({reason})")
        self.obs.trigger_replay()

    def checkout_win(self):
        self.trigger("checkout")

    def score_180(self):
        self.trigger("180")
