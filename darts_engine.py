import time
import threading
import requests

from config import Config
from obs import OBSController
from replay import ReplayManager


class DartsEngine:
    # =========================
    # MODES
    # =========================
    MODE_LIVE = "live"
    MODE_AUTODARTS = "autodarts"
    MODE_TEST = "test"

    # =========================
    # CONSTANTS
    # =========================

    DOUBLE_SCENES = {
        "tupla20_1": [40, 2],
        "tupla18_4": [36, 8],
        "tupla13_6": [26, 12],
        "tupla10_15": [20, 30],
        "tupla2_17": [4, 34],
        "tupla3_19": [6, 38],
        "tupla7_16": [14, 32],
        "tupla8_11": [16, 22],
        "tupla14_9": [28, 18],
        "tupla12_5": [24, 10],
        "tupla_bull": [50],
    }

    # =========================
    # INIT
    # =========================
    def __init__(self, mode=MODE_LIVE):
        self.config = Config()

        # override test mode from config
        if self.config.get("mode", "test", default=False):
            mode = self.MODE_TEST

        self.mode = mode

        # =========================
        # GAME CONFIG
        # =========================
        game_cfg = self.config.get("game", default={})

        self.START_SCORE = game_cfg.get("start_score", 501)
        self.AUTO_RESET_ON_WIN = game_cfg.get("auto_reset_on_win", True)


        # -------------------------
        # CONFIG VALUES
        # -------------------------
        obs_cfg = self.config.get("obs")

        self.SCENE_WIDE = obs_cfg["scenes"]["wide"]
        self.SCENE_T20 = obs_cfg["scenes"]["t20"]
        self.SCENE_T20_FIRST = obs_cfg["scenes"]["t20_first"]
        self.CHECKOUT_TEXT_SOURCE = obs_cfg["text_sources"]["checkout"]

        self.T20_RESET_DELAY = self.config.get(
            "zoom", "t20_reset_delay", default=5.0
        )
        self.CHECKOUT_RESET_DELAY = self.config.get(
            "zoom", "checkout_reset_delay", default=5.0
        )

        self.AUTODARTS_API = self.config.get(
            "autodarts", "api_url"
        )
        self.POLL_INTERVAL = self.config.get(
            "autodarts", "poll_interval", default=0.2
        )

        # -------------------------
        # GAME STATE
        # -------------------------
        self.remaining = self.START_SCORE
        self.turn_start_remaining = self.START_SCORE

        self.throw_index = 0
        self.first_throw_t20 = False
        self.second_throw_t20 = False
        self.waiting_for_third = False

        self.checkout_zoom_active = False

        self.last_snapshot = None
        self.last_throw = None
        self.last_throw_undone = False

        self.last_num_throws = None

        self._lock = threading.Lock()

        # -------------------------
        # OBS
        # -------------------------
        self.current_scene = self.SCENE_WIDE
        self.obs = OBSController(
            host=obs_cfg["host"],
            port=obs_cfg["port"],
            password=obs_cfg["password"],
        )
        self.obs.connect()

        # -------------------------
        # REPLAY
        # -------------------------
        if self.config.get("replay", "enabled", default=True):
            self.replay = ReplayManager(
                self.obs,
                cooldown=self.config.get("replay", "cooldown", default=5.0),
            )
        else:
            self.replay = None

        print(f"[ENGINE] Started in {self.mode.upper()} mode")

    # =========================
    # MAIN LOOP
    # =========================
    def run(self):
        if self.mode == self.MODE_TEST:
            print("[ENGINE] Test mode – AutoDarts disabled")
            return

        print("[ENGINE] AutoDarts polling started")

        while True:
            try:
                state = requests.get(self.AUTODARTS_API, timeout=2).json()
            except Exception:
                time.sleep(self.POLL_INTERVAL)
                continue

            num_throws = state.get("numThrows")
            throws = state.get("throws", [])

            if not throws or num_throws == self.last_num_throws:
                time.sleep(self.POLL_INTERVAL)
                continue

            self.last_num_throws = num_throws

            # new turn
            if num_throws % 3 == 1:
                with self._lock:
                    self.turn_start_remaining = self.remaining
                    self.throw_index = 0
                    self.first_throw_t20 = False
                    self.second_throw_t20 = False
                    self.waiting_for_third = False

            segment = throws[-1]["segment"]["name"]
            self.process_throw(segment)

            time.sleep(self.POLL_INTERVAL)

    # =========================
    # OBS HELPERS
    # =========================
    def switch_scene(self, scene):
        if self.current_scene != scene:
            self.obs.switch_scene(scene)
            self.current_scene = scene

    def reset_zoom(self):
        self.switch_scene(self.SCENE_WIDE)
        self.obs.set_text(self.CHECKOUT_TEXT_SOURCE, "")
        self.checkout_zoom_active = False

    # =========================
    # CHECKOUT HELPERS
    # ========================
    def is_double_checkout_possible(self, remaining=None) -> bool:
        """
        Checkout window:
        - DBULL (50)
        - Even numbers 2..40
        """
        r = self.remaining if remaining is None else remaining
        if r == 50:
            return True
        return (2 <= r <= 40) and (r % 2 == 0)

    def find_double_scene(self, remaining=None):
        r = self.remaining if remaining is None else remaining
        for scene, values in self.DOUBLE_SCENES.items():
            if r in values:
                return scene
        return None

    def get_target_double_text(self):
        r = self.remaining
        if r == 50:
            return "BULL"
        if 2 <= r <= 40 and r % 2 == 0:
            return f"D{r // 2}"
        return None


    # =========================
    # TIMERS
    # =========================
    def _schedule(self, delay, fn):
        t = threading.Timer(delay, fn)
        t.daemon = True
        t.start()
        return t

    def _schedule_zoom_reset(self, delay):
        self._schedule(delay, self._reset_zoom_delayed)

    def _reset_zoom_delayed(self):
        with self._lock:
            self.reset_zoom()

    # =========================
    # LEG / TURN CONTROL
    # =========================
    def reset_leg(self):
        with self._lock:
            self.remaining = self.START_SCORE
            self.turn_start_remaining = self.START_SCORE

            self.throw_index = 0
            self.first_throw_t20 = False
            self.second_throw_t20 = False
            self.waiting_for_third = False

            self.checkout_zoom_active = False
            self.last_snapshot = None
            self.last_throw = None
            self.last_throw_undone = False

            self.reset_zoom()

            print(f"[ENGINE] Leg reset (start score: {self.START_SCORE})")


    def ui_reset_leg(self):
        self.reset_leg()

    def reset_turn(self):
        with self._lock:
            self.turn_start_remaining = self.remaining
            self.throw_index = 0
            self.first_throw_t20 = False
            self.second_throw_t20 = False
            self.waiting_for_third = False

            self.last_throw = None
            self.last_throw_undone = False
            self.checkout_zoom_active = False

            print("[ENGINE] Turn reset")

    def ui_reset_turn(self):
        self.reset_turn()

    def undo_last_throw(self):
        if not self.last_snapshot:
            return

        with self._lock:
            self.remaining = self.last_snapshot["remaining"]
            self.throw_index = self.last_snapshot["throw_index"]
            self.turn_start_remaining = self.last_snapshot["turn_start_remaining"]
            self.first_throw_t20 = self.last_snapshot["first_throw_t20"]
            self.second_throw_t20 = self.last_snapshot["second_throw_t20"]
            self.waiting_for_third = self.last_snapshot["waiting_for_third"]
            self.switch_scene(self.last_snapshot["current_scene"])

            self.last_throw_undone = True

        print("[ENGINE] Last throw undone")

    def ui_set_remaining(self, value):
        try:
            v = int(value)
        except Exception:
            return

        if v < 0 or v > self.START_SCORE:
            return

        with self._lock:
            self.remaining = v
            self.turn_start_remaining = v

            # nollaa vuoron tila
            self.throw_index = 0
            self.first_throw_t20 = False
            self.second_throw_t20 = False
            self.waiting_for_third = False

            self.checkout_zoom_active = False

            # 🔴 TÄRKEÄ OSA: checkout-visualit käsin asetettaessa
            if self.is_double_checkout_possible():
                scene = self.find_double_scene()
                if scene:
                    self.switch_scene(scene)

                    target = self.get_target_double_text()
                    if target:
                        self.obs.set_text(
                            self.CHECKOUT_TEXT_SOURCE,
                            f"CHECKOUT: {target}"
                        )

                    self.checkout_zoom_active = True
            else:
                self.reset_zoom()

            print(f"[ENGINE] Remaining forced -> {v}")


    # =========================
    # THROW LOGIC
    # =========================
    @staticmethod
    def segment_to_score(segment):
        if not segment:
            return 0

        s = segment.upper()

        if s.startswith("M") or s == "MISS":
            return 0
        if s in ("DBULL", "50"):
            return 50
        if s in ("SBULL", "25"):
            return 25
        if s.startswith("T"):
            return int(s[1:]) * 3
        if s.startswith("D"):
            return int(s[1:]) * 2
        if s.startswith("S"):
            return int(s[1:])

        try:
            return int(s)
        except ValueError:
            return 0

    @staticmethod
    def is_double(segment):
        s = segment.upper()
        return s.startswith("D") or s in ("DBULL", "50")

    def _take_snapshot(self):
        self.last_snapshot = {
            "remaining": self.remaining,
            "throw_index": self.throw_index,
            "turn_start_remaining": self.turn_start_remaining,
            "first_throw_t20": self.first_throw_t20,
            "second_throw_t20": self.second_throw_t20,
            "waiting_for_third": self.waiting_for_third,
            "current_scene": self.current_scene,
            "was_checkout": self.is_double_checkout_possible(),
        }

    def process_throw(self, segment):
        self._take_snapshot()
        

        self.last_throw = segment
        self.last_throw_undone = False

        with self._lock:
            score = self.segment_to_score(segment)
            is_double = self.is_double(segment)

            potential = self.remaining - score

            bust = (
                potential < 0
                or potential == 1
                or (potential == 0 and not is_double)
            )

            if bust:
                self.remaining = self.turn_start_remaining
                self.throw_index = 0
                self.reset_zoom()
                return

            self.remaining = potential
            self.throw_index += 1
           
            # Winning double
            if self.remaining == 0 and is_double:
                self.checkout_zoom_active = True
                if self.replay:
                    self.replay.checkout_win()

                self._schedule_zoom_reset(self.CHECKOUT_RESET_DELAY)

                if self.AUTO_RESET_ON_WIN:
                    threading.Timer(
                        self.CHECKOUT_RESET_DELAY, self.reset_leg
                    ).start()
                return
            
            print(
                f"[THROW] #{self.throw_index} | {segment} | "
                f"remaining: {self.last_snapshot['remaining']}"
            )


            # --- CHECKOUT -> NOT CHECKOUT transition ---
            was_checkout = bool(
                self.last_snapshot and self.last_snapshot.get("was_checkout")
            )
            now_checkout = self.is_double_checkout_possible()

            if was_checkout and not now_checkout:
                # checkout menetettiin normaalilla heitolla -> zoom pois heti
                self.checkout_zoom_active = False
                self.reset_zoom()
                # EI returnia, peli jatkuu normaalisti


            # If we are (still) in checkout window, update scene/text to match new remaining
            if now_checkout:
                scene = self.find_double_scene()
                if scene:
                    self.switch_scene(scene)
                    target = self.get_target_double_text()
                    self.obs.set_text(self.CHECKOUT_TEXT_SOURCE, f"CHECKOUT: {target}" if target else "")
                    self.checkout_zoom_active = True    

            # 180 replay
            if (
                self.throw_index == 3
                and self.first_throw_t20
                and self.second_throw_t20
                and segment.upper() == "T20"
                and self.replay
            ):
                self.replay.score_180()

            # T20 logic
            if self.throw_index == 1:
                self.first_throw_t20 = segment.upper() == "T20"
                if self.first_throw_t20 and self.remaining >= 140:
                    self.switch_scene(self.SCENE_T20_FIRST)

            elif self.throw_index == 2:
                self.second_throw_t20 = segment.upper() == "T20"
                if self.first_throw_t20 and not self.second_throw_t20:
                    self.reset_zoom()

                # T20 + T20 -> darts20 zoom, odota kolmatta tikkaa
                if (
                    self.throw_index == 2
                    and self.first_throw_t20
                    and self.second_throw_t20
                    and self.remaining >= 140
                ):
                    self.switch_scene(self.SCENE_T20)
                    self.waiting_for_third = True
                    return  # 🔴 TÄRKEÄ
                 

            # --- THIRD DART RESOLUTION (after T20 + T20) ---
            if self.waiting_for_third and self.throw_index >= 3:
                self.waiting_for_third = False

                # 180 handled earlier (T20 + T20 + T20)
                # otherwise: schedule outzoom
                self._schedule_zoom_reset(self.T20_RESET_DELAY)

            # End turn
            if self.throw_index >= 3:
                self.throw_index = 0
                self.first_throw_t20 = False
                self.second_throw_t20 = False

    # =========================
    # TEST MODE
    # =========================
    def manual_throw(self, segment):
        if self.mode != self.MODE_TEST:
            return

        with self._lock:
            if self.throw_index == 0:
                self.turn_start_remaining = self.remaining

        self.process_throw(segment)
