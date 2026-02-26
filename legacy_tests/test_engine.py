from obswebsocket import obsws, requests as obsreq
import time
import threading


class DartsEngine:
    START_SCORE = 501
    AUTO_RESET_ON_WIN = True

    OBS_HOST = "localhost"
    OBS_PORT = 4455
    OBS_PASSWORD = "mysecret"

    SCENE_WIDE = "darts"
    SCENE_T20 = "darts20"

    CHECKOUT_TEXT_SOURCE = "checkout_text"

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

    # INIT
    def __init__(self):
        self.remaining = self.START_SCORE
        self.turn_start_remaining = self.START_SCORE

        self.throw_index = 0
        self.first_throw_t20 = False
        self.second_throw_t20 = False

        self.waiting_for_third = False
        self.t20_reset_timer = None

        self.checkout_available = False
        self.checkout_zoom_active = False
        self.checkout_reset_timer = None

        self.current_scene = self.SCENE_WIDE
        self.obs = obsws(self.OBS_HOST, self.OBS_PORT, self.OBS_PASSWORD)
        self.obs.connect()

    # OBS
    def switch_scene(self, scene: str):
        if self.current_scene != scene:
            print(f"[OBS] → {scene}")
            self.obs.call(
                obsreq.SetCurrentProgramScene(sceneName=scene)
            )
            self.current_scene = scene

    def reset_zoom(self):
        self.switch_scene(self.SCENE_WIDE)

    
    # TEXT (OBS v5)
    def set_checkout_text(self, text: str):
        self.obs.call(
            obsreq.SetInputSettings(
                inputName=self.CHECKOUT_TEXT_SOURCE,
                inputSettings={"text": text},
                overlay=True
            )
        )

    def clear_checkout_text(self):
        self.set_checkout_text("")

    # TIMERS
    def _cancel_t20_timer(self):
        if self.t20_reset_timer:
            self.t20_reset_timer.cancel()
            self.t20_reset_timer = None

    def _schedule_t20_reset(self, delay=5.0):
        self._cancel_t20_timer()
        self.t20_reset_timer = threading.Timer(delay, self._t20_reset)
        self.t20_reset_timer.daemon = True
        self.t20_reset_timer.start()

    def _t20_reset(self):
        if self.current_scene == self.SCENE_T20 and not self.checkout_zoom_active:
            self.reset_zoom()
        self.t20_reset_timer = None

    def _cancel_checkout_timer(self):
        if self.checkout_reset_timer:
            self.checkout_reset_timer.cancel()
            self.checkout_reset_timer = None

    def _schedule_checkout_reset(self, delay=5.0):
        self._cancel_checkout_timer()
        self.checkout_reset_timer = threading.Timer(delay, self._checkout_reset)
        self.checkout_reset_timer.daemon = True
        self.checkout_reset_timer.start()

    def _checkout_reset(self):
        self.checkout_zoom_active = False
        self.clear_checkout_text()
        self.reset_zoom()
        self.checkout_reset_timer = None

    
    # CONTROL (UI)
    def set_remaining(self, value: int):
        self._cancel_t20_timer()
        self._cancel_checkout_timer()
        self.checkout_zoom_active = False
        self.waiting_for_third = False

        self.remaining = value
        self.turn_start_remaining = value
        self.update_checkout_state()

        self.throw_index = 0
        self.first_throw_t20 = False
        self.second_throw_t20 = False

        double_scene = self.find_double_scene()
        if double_scene:
            self.checkout_zoom_active = True
            self.switch_scene(double_scene)
            target = self.get_target_double_text()
            if target:
                self.set_checkout_text(f"CHECKOUT: {target}")
        else:
            self.clear_checkout_text()
            self.reset_zoom()

    def reset_leg(self):
        self._cancel_t20_timer()
        self._cancel_checkout_timer()

        self.checkout_zoom_active = False
        self.waiting_for_third = False

        self.remaining = self.START_SCORE
        self.update_checkout_state()
        self.turn_start_remaining = self.START_SCORE

        self.throw_index = 0
        self.first_throw_t20 = False
        self.second_throw_t20 = False

        self.clear_checkout_text()
        self.reset_zoom()

    
    # LOGIIKKA
    @staticmethod
    def parse_throw(value: str):
        v = value.upper().strip()
        if v in ("DBULL", "50"):
            return 50, True, "DBULL"
        if v in ("SBULL", "25"):
            return 25, False, "SBULL"
        if v.startswith("T"):
            n = int(v[1:])
            return n * 3, False, f"T{n}"
        if v.startswith("D"):
            n = int(v[1:])
            return n * 2, True, f"D{n}"
        n = int(v)
        return n, False, f"S{n}"

    def find_double_scene(self):
        for scene, values in self.DOUBLE_SCENES.items():
            if self.remaining in values:
                return scene
        return None
    
    def update_checkout_state(self):
        self.checkout_available = (self.find_double_scene() is not None)


    def get_target_double_text(self):
        if self.remaining % 2 != 0:
            return None
        v = self.remaining // 2
        if v == 25:
            return "DBULL"
        if 1 <= v <= 20:
            return f"D{v}"
        return None
    



    # MANUAL THROW
    def manual_throw(self, value: str):
        score, is_double, segment = self.parse_throw(value)

        if self.throw_index == 0:
            self.turn_start_remaining = self.remaining
            self.first_throw_t20 = False
            self.second_throw_t20 = False
            self.waiting_for_third = False

        potential = self.remaining - score
        bust = (
            potential < 0 or
            potential == 1 or
            (potential == 0 and not is_double)
        )

        if bust:
            print(f"[BUST] {segment}")

            # Palauta pisteet
            self.remaining = self.turn_start_remaining
            self.update_checkout_state()

            # Nollaa vuorotila
            self.throw_index = 0
            self.first_throw_t20 = False
            self.second_throw_t20 = False
            self.waiting_for_third = False

            # Peru vain 180-ajastimet
            self._cancel_t20_timer()

            # ÄLÄ poista checkout-tilaa vielä
            double_scene = self.find_double_scene()
            if double_scene:
                # Ollaan yhä checkoutissa (esim. D1)
                self.checkout_zoom_active = True
                self.switch_scene(double_scene)

                target = self.get_target_double_text()
                if target:
                    self.set_checkout_text(f"CHECKOUT: {target}")
            else:
                # Ei checkoutia → normaali reset
                self._cancel_checkout_timer()
                self.checkout_zoom_active = False
                self.clear_checkout_text()
                self.reset_zoom()

            return


        self.remaining = potential
        self.update_checkout_state()
        print(f"[THROW] {segment} → remaining {self.remaining}")
        self.throw_index += 1

        if self.throw_index == 1:
            self.first_throw_t20 = (segment == "T20")
        elif self.throw_index == 2:
            self.second_throw_t20 = (segment == "T20")

        # WIN
        if self.remaining == 0 and is_double:
            print("[WIN]")
            self._cancel_t20_timer()
            self.checkout_zoom_active = True
            self.set_checkout_text(f"CHECKOUT: {segment}")
            self._schedule_checkout_reset(5.0)

            if self.AUTO_RESET_ON_WIN:
                time.sleep(1)
                self.reset_leg()
            return

        # ZOOM LOGIC
        if self.checkout_zoom_active:
            return

        double_scene = self.find_double_scene()
        if double_scene:
            self.switch_scene(double_scene)
            target = self.get_target_double_text()
            if target:
                self.set_checkout_text(f"CHECKOUT: {target}")

        elif self.throw_index == 2 and self.first_throw_t20 and self.second_throw_t20:
            self.switch_scene(self.SCENE_T20)
            self.waiting_for_third = True
            self.clear_checkout_text()

        elif self.waiting_for_third and self.throw_index == 3:
            self.waiting_for_third = False
            self._schedule_t20_reset(5.0)

        else:
            self.reset_zoom()

        if self.throw_index >= 3:
            self.throw_index = 0
            self.first_throw_t20 = False
            self.second_throw_t20 = False
