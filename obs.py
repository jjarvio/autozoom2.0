import queue
import threading
from obswebsocket import obsws, requests as obsreq


class OBSController:
    def __init__(self, host: str, port: int, password: str):
        # OBS websocket
        self.obs = obsws(host, port, password)

        # async queue
        self.queue = queue.Queue()

        # worker thread
        self.thread = threading.Thread(
            target=self._worker,
            daemon=True
        )

        # connection state
        self._connected = False

        # ---- CACHE (estää turhat kutsut) ----
        self._current_scene = None
        self._text_cache = {}
        

    # CONNECTION
    def connect(self):
        if self._connected:
            return

        self.obs.connect()
        self.thread.start()
        self._connected = True

        print("[OBS] Connected")

    # WORKER
    def _worker(self):
        while True:
            req = self.queue.get()
            try:
                self.obs.call(req)
            except Exception as e:
                print("[OBS ERROR]", e)
            finally:
                self.queue.task_done()

    # PUBLIC API
    def switch_scene(self, scene: str):
        """
        Vaihda skene vain jos se oikeasti muuttuu
        """
        if scene == self._current_scene:
            return

        self._current_scene = scene
        self.queue.put(
            obsreq.SetCurrentProgramScene(sceneName=scene)
        )

    def set_text(self, source: str, text: str):
        """
        Päivitä FreeType2 / Text -lähteen teksti
        (käyttää SetInputSettings → toimii Linuxissa)
        """
        if self._text_cache.get(source) == text:
            return

        self._text_cache[source] = text
        self.queue.put(
            obsreq.SetInputSettings(
                inputName=source,
                inputSettings={"text": text},
                overlay=True
            )
        )


    def trigger_replay(self):
        """
        Trigger OBS Replay Buffer save.
        Replay Buffer must be enabled in OBS.
        """
        self.queue.put(
            obsreq.SaveReplayBuffer()
        )
        print("[OBS] Replay buffer save triggered")

    
    # OPTIONAL HELPERS
    def clear_text(self, source: str):
        """
        Tyhjennä teksti (esim. checkoutin jälkeen)
        """
        self.set_text(source, "")

    def reset_cache(self):
        """
        Pakota seuraavat kutsut menemään OBS:ään
        (hyödyllinen debugissa)
        """
        self._current_scene = None
        self._text_cache.clear()
