import cv2
import time

from ui.qt_compat import QTimer, QThread, QMediaPlayer, QAudioOutput, Signal, QObject


class _DecoderThread(QThread):
    frame_decoded = Signal(int, object)
    playback_ended = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cap = None
        self._fps = 30.0
        self._start_frame = 0
        self._end_frame = 0
        self._running = False
        self._display_w = 640
        self._display_h = 427

    def setup(self, cap, fps, start_frame, end_frame, display_w, display_h):
        self._cap = cap
        self._fps = fps
        self._start_frame = start_frame
        self._end_frame = end_frame
        self._display_w = display_w
        self._display_h = display_h

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        cap = self._cap
        fps = self._fps
        interval = 1.0 / fps if fps > 0 else 1.0 / 30.0

        play_start = time.perf_counter()
        play_start_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        while self._running:
            elapsed = time.perf_counter() - play_start
            target_frame = play_start_frame + int(elapsed * fps)

            if target_frame > self._end_frame:
                self.playback_ended.emit()
                break

            target_frame = max(self._start_frame, target_frame)

            cv_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if abs(target_frame - cv_pos) > 1:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = cap.read()
            if not ret:
                self.playback_ended.emit()
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w = frame_rgb.shape[:2]
            scale = min(self._display_w / w, self._display_h / h)
            nw, nh = int(w * scale), int(h * scale)
            if (nw, nh) != (w, h):
                frame_rgb = cv2.resize(frame_rgb, (nw, nh),
                                       interpolation=cv2.INTER_LINEAR)

            self.frame_decoded.emit(target_frame, frame_rgb)

            next_frame_time = play_start + (target_frame - play_start_frame + 1) * interval
            sleep_s = next_frame_time - time.perf_counter()
            if sleep_s > 0.001:
                time.sleep(sleep_s)


class VideoController(QObject):
    frame_ready = Signal(int, object)
    playback_state_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.video_path = None
        self.cap = None

        self.total_frames = 0
        self.fps = 0
        self.width = 0
        self.height = 0

        self.current_frame = 0
        self.start_frame = 0
        self.end_frame = 0
        self.is_playing = False
        self._is_closing = False

        self._decoder = None
        self._display_w = 640
        self._display_h = 427

        self.media_player = QMediaPlayer()
        if QAudioOutput:
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
        else:
            self.audio_output = None

        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

    def set_display_size(self, w, h):
        self._display_w = w
        self._display_h = h

    def load_video(self, path):
        if self.is_playing:
            self._stop_playback()
        if self._decoder is not None:
            self._decoder.stop()
            self._decoder.wait(500)
            self._decoder = None
            
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            return False

        self.video_path = path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.current_frame = 0
        self.start_frame = 0
        self.end_frame = self.total_frames - 1
        return True

    def get_frame(self, frame_num):
        if not self.cap:
            return None
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None

    def seek(self, frame_num):
        frame_num = max(0, min(frame_num, self.total_frames - 1))
        self.current_frame = frame_num
        return self.get_frame(frame_num)

    def toggle_playback(self):
        if self.is_playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        if self.fps <= 0 or not self.cap:
            return

        self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

        target_ms = int((self.current_frame / self.fps) * 1000)

        self.media_player.setPosition(target_ms)
        self.media_player.play()

        self._decoder = _DecoderThread(self)
        self._decoder.setup(
            self.cap, self.fps,
            self.start_frame, self.end_frame,
            self._display_w, self._display_h,
        )
        self._decoder.frame_decoded.connect(self._on_frame_decoded)
        self._decoder.playback_ended.connect(self._on_playback_ended)
        self._decoder.start()

        self.is_playing = True
        self.playback_state_changed.emit(True)

    def _stop_playback(self):
        if self._decoder is not None:
            self._decoder.stop()
            self._decoder.wait(500)
            self._decoder = None
        self.media_player.stop()
        self.is_playing = False
        self.playback_state_changed.emit(False)

    def _on_frame_decoded(self, frame_num, frame_rgb):
        if self._is_closing:
            return
        self.current_frame = frame_num
        self.frame_ready.emit(frame_num, frame_rgb)

    def _on_playback_ended(self):
        self._stop_playback()

    def _on_media_status_changed(self, status):
        from ui.qt_compat import QT_BACKEND
        try:
            if QT_BACKEND == "PySide6":
                from PySide6.QtMultimedia import QMediaPlayer as _MP
                is_end = (status == _MP.MediaStatus.EndOfMedia)
            else:
                from PySide2.QtMultimedia import QMediaPlayer as _MP
                is_end = (status == _MP.EndOfMedia)
            if is_end and self.is_playing:
                self._stop_playback()
        except Exception:
            pass

    def close(self):
        self._is_closing = True
        if self._decoder is not None:
            self._decoder.stop()
            self._decoder.wait(500)
            self._decoder = None
        self.media_player.stop()
        self.is_playing = False
        if self.cap:
            self.cap.release()
