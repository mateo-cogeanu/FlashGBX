#encoder/audio_encoder.py

import subprocess
import tempfile
import os
import struct
import sys
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
from pydub import AudioSegment
import numpy as np


# ---------------------------------------------------------------------------
# IMA ADPCM encoder (IMA9 - compatible with Damian Yerrick's decoder)
# ---------------------------------------------------------------------------

_STEP_ADJ = [-1, -1, -1, -1, 2, 4, 7, 12]  # IMA9

_STEP_TAB = [
        7,    8,    9,   10,   11,   12,   13,   14,   16,   17,
       19,   21,   23,   25,   28,   31,   34,   37,   41,   45,
       50,   55,   60,   66,   73,   80,   88,   97,  107,  118,
      130,  143,  157,  173,  190,  209,  230,  253,  279,  307,
      337,  371,  408,  449,  494,  544,  598,  658,  724,  796,
      876,  963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
     2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
     5894, 6484, 7132, 7845, 8630, 9493,10442,11487,12635,13899,
    15289,16818,18500,20350,22385,24623,27086,29794,32767,
]

def ima9_rescale(step, code):
    diff = step >> 3
    if code & 1: diff += step >> 2
    if code & 2: diff += step >> 1
    if code & 4: diff += step
    if (code & 7) == 7: diff += step >> 1
    if code & 8: diff = -diff
    return diff

def encode_adpcm(pcm16: np.ndarray) -> bytes:
    predictor = 0
    step_idx  = 0
    out       = bytearray()
    cur_byte  = 0

    for i, raw_sample in enumerate(pcm16):
        sample = int(raw_sample)

        step_idx = max(0, min(88, step_idx))
        step = _STEP_TAB[step_idx]

        diff = sample - predictor
        sign = 0
        if diff < 0:
            sign = 8
            diff = -diff

        code = (4 * diff) // step
        if code > 7: code = 7
        if code == 7: code = 6

        recon = ima9_rescale(step, code | sign)
        predictor += recon
        if predictor < -32768: predictor = -32768
        if predictor >  32767: predictor =  32767
        step_idx += _STEP_ADJ[code]

        nibble = code | sign
        if i & 1:
            out.append((nibble << 4) | cur_byte)
        else:
            cur_byte = nibble

    if len(pcm16) & 1:
        out.append(cur_byte)

    while len(out) % 4 != 0:
        out.append(0x00)

    return bytes(out)


def parse_sample_rate(value):
    if isinstance(value, int):
        return value
    try:
        rate = int(str(value).strip())
    except ValueError:
        raise ValueError(
            f"Invalid sample rate: {value!r}. Use an integer between 6500 and 44100.")
    if rate < 6500 or rate > 44100:
        raise ValueError(
            f"Sample rate {rate} out of range. Must be between 6500 and 44100 Hz.")
    return rate


class AudioEncoder:
    FORMAT_PCM   = "pcm"
    FORMAT_ADPCM = "adpcm"

    def __init__(self, sample_rate: int = 11025, audio_format: str = "pcm"):
        self.sample_rate = parse_sample_rate(sample_rate)

        if audio_format not in (self.FORMAT_PCM, self.FORMAT_ADPCM):
            raise ValueError(
                f"audio_format must be 'pcm' or 'adpcm', got {audio_format!r}"
            )
        self.audio_format = audio_format

        TIMER_FREQ   = 16777216
        FRAME_CYCLES = 280896

        ADPCM_NICE_RATES = [
            ( 399, 42048.16, 704),
            ( 418, 40136.88, 672),
            ( 462, 36314.32, 608),
            ( 532, 31536.12, 528),
            ( 627, 26757.92, 448),
            ( 798, 21024.08, 352),
            ( 836, 20068.44, 336),
            ( 924, 18157.16, 304),
            (1254, 13378.96, 224),
            (1463, 11467.68, 192),
            (1596, 10512.04, 176),
            (2508,  6689.48, 112),
        ]

        if self.audio_format == self.FORMAT_ADPCM:
            best = min(ADPCM_NICE_RATES,
                       key=lambda r: abs(r[1] - self.sample_rate))
            self.timer_reload      = best[0]
            self.real_sample_rate  = best[1]
            self.samples_per_frame = best[2]
            if abs(self.real_sample_rate - self.sample_rate) > 1:
                print(f"  ADPCM: {self.sample_rate} Hz -> nice rate "
                      f"{self.real_sample_rate:.2f} Hz "
                      f"(reload={self.timer_reload}, spf={self.samples_per_frame})")
            else:
                print(f"  Sample rate: {self.real_sample_rate:.2f} Hz "
                      f"(reload={self.timer_reload}, spf={self.samples_per_frame})")
        else:
            self.timer_reload      = TIMER_FREQ // self.sample_rate
            if self.timer_reload == 0:
                self.timer_reload  = 1
            self.real_sample_rate  = TIMER_FREQ / self.timer_reload
            self.samples_per_frame = FRAME_CYCLES / self.timer_reload
            print(f"  Sample rate (nominal) : {self.sample_rate} Hz")
            print(f"  Sample rate (real GBA): {self.real_sample_rate:.2f} Hz  "
                  f"(reload={self.timer_reload})")

        if self.audio_format == self.FORMAT_PCM:
            self.bytes_per_second = self.real_sample_rate
        else:
            self.bytes_per_second = self.real_sample_rate / 2.0

    def extract_audio_from_video(
        self,
        video_path: str,
        duration: float,
        start_time: float = 0.0,
        i_frame_timestamps=None,
        frame_count=None,
        volume_percent: float = 100.0,
        temp_dir: str = None,
        video_fps_raw: int = None,
    ):
        print(f"Extracting audio from video...")
        print(f"  Sample rate : {self.sample_rate} Hz")
        print(f"  Format      : {self.audio_format.upper()}")
        print(f"  Duration    : {duration:.2f}s")
        print(f"  Volume      : {volume_percent}%")

        if temp_dir:
            Path(temp_dir).mkdir(parents=True, exist_ok=True)
            wav_path   = str(Path(temp_dir) / "audio.wav")
            keep_files = True
        else:
            _wav_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav_path   = _wav_tmp.name
            _wav_tmp.close()
            keep_files = False

        try:
            from ffmpeg_utils import get_ffmpeg
            cmd = [get_ffmpeg(), "-i", video_path]
            if start_time > 0:
                cmd.extend(["-ss", str(start_time)])
            if duration > 0:
                cmd.extend(["-t", str(duration)])
            cmd.extend([
                "-vn", "-acodec", "pcm_s16le",
                "-ac", "1", "-ar", str(int(round(self.real_sample_rate))),
                "-y", wav_path,
            ])
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    creationflags=_CREATE_NO_WINDOW)
            if result.returncode != 0:
                print(f"❌ ffmpeg failed: {result.stderr}")
                return None

            _real_sr_int = int(round(self.real_sample_rate))
            sound = (
                AudioSegment.from_file(wav_path)
                .set_channels(1)
                .set_frame_rate(_real_sr_int)
                .set_sample_width(2)
            )
            if volume_percent != 100.0:
                sound = sound + (20.0 * np.log10(volume_percent / 100.0))

            actual_dur = sound.duration_seconds
            if actual_dur < duration:
                print(f"⚠  Audio shorter than requested ({actual_dur:.2f}s). Trimming.")
                duration = actual_dur

            pcm16 = np.frombuffer(sound.raw_data, dtype=np.int16)

            if self.audio_format == self.FORMAT_PCM:
                pcm8 = (pcm16.astype(np.int32) >> 8).clip(-128, 127).astype(np.int8)
                audio_bytes = bytearray(pcm8.tobytes())
                while len(audio_bytes) % 4 != 0:
                    audio_bytes.append(0x00)
                audio_bytes = bytes(audio_bytes)
            else:
                audio_bytes = bytes(bytearray(encode_adpcm(pcm16)))

            total = len(audio_bytes)

            GBA_TIMER_FREQ  = 16777216
            GBA_LCD_FPS_RAW = 597275
            if video_fps_raw is not None:
                GBA_VIDEO_FPS_RAW = video_fps_raw
            else:
                GBA_VIDEO_FPS_RAW = int(round(frame_count / duration * 10000))

            frame_audio_offsets = []
            for i in range(frame_count):
                if self.audio_format == self.FORMAT_ADPCM:
                    vbl_i = (i * GBA_LCD_FPS_RAW) // GBA_VIDEO_FPS_RAW
                    samples_i = (vbl_i * GBA_TIMER_FREQ * 10000) // (self.timer_reload * GBA_LCD_FPS_RAW)
                    off = (samples_i // 2) & ~1
                else:
                    vbl_i = (i * GBA_LCD_FPS_RAW) // GBA_VIDEO_FPS_RAW
                    samples_i = (vbl_i * GBA_TIMER_FREQ * 10000) // (self.timer_reload * GBA_LCD_FPS_RAW)
                    off = samples_i & ~1
                frame_audio_offsets.append(min(off, total - 1))

            i_frame_audio_offsets = []
            if i_frame_timestamps:
                for ts in i_frame_timestamps:
                    off = int(ts * self.bytes_per_second)
                    if self.audio_format == self.FORMAT_ADPCM:
                        off &= ~1
                    i_frame_audio_offsets.append(min(off, total - 1))

            pcm_size = len(pcm16)
            print(f"✓ Audio ({self.audio_format.upper()}): {total} bytes  "
                  f"(vs {pcm_size} samples = {pcm_size} bytes PCM8 = "
                  f"{total / max(1, pcm_size) * 100:.0f}%)")
            return audio_bytes, i_frame_audio_offsets, frame_audio_offsets

        finally:
            if not keep_files and os.path.exists(wav_path):
                os.unlink(wav_path)

    def recalculate_frame_offsets(self, frame_count: int, audio_total_bytes: int,
                                   video_fps_raw: int) -> list:
        GBA_TIMER_FREQ  = 16777216
        GBA_LCD_FPS_RAW = 597275

        offsets = []
        for i in range(frame_count):
            vbl_i = (i * GBA_LCD_FPS_RAW) // video_fps_raw
            samples_i = (vbl_i * GBA_TIMER_FREQ * 10000) // (self.timer_reload * GBA_LCD_FPS_RAW)
            if self.audio_format == self.FORMAT_ADPCM:
                off = (samples_i // 2) & ~1
            else:
                off = samples_i & ~1
            offsets.append(min(off, audio_total_bytes - 1))
        return offsets

    def _write_binary(self, path: Path, data: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            f.write(data)

    def _write_int32_bin(self, path: Path, values: list):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            for v in values:
                f.write(struct.pack("<I", v))

    def write_audio_header(
        self,
        path_h: Path,
        audio_data: bytes,
        duration: float,
        i_frame_audio_offsets=None,
        frame_audio_offsets=None,
    ):
        guard   = "AUDIO_DATA_H"
        fmt_val = 0 if self.audio_format == self.FORMAT_PCM else 1

        with path_h.open("w", encoding="utf-8") as f:
            f.write(f"#ifndef {guard}\n#define {guard}\n\n")
            f.write("#include <gba_types.h>\n\n")
            f.write("// Audio parameters\n")
            f.write(f"#define SAMPLE_RATE            {self.sample_rate}\n")
            bps_int = int(self.bytes_per_second)
            f.write(f"#define AUDIO_BYTES_PER_SECOND {bps_int}\n")
            f.write(f"// GBA Timer 0 real rate: {self.real_sample_rate:.2f} Hz  "
                    f"(reload={self.timer_reload}, spf={self.samples_per_frame})\n")
            f.write(f"// HALF_BUF = spf = samples per video frame (exact integer for this rate)\n")
            f.write(f"#define ADPCM_TIMER_RELOAD     {self.timer_reload}\n")
            f.write(f"#define ADPCM_SAMPLES_PER_FRAME {self.samples_per_frame}\n")
            f.write(f"#define AUDIO_DURATION_MS      {int(duration * 1000)}\n")
            f.write(f"#define audio_data_len         {len(audio_data)}\n\n")
            f.write("// 0 = PCM 8-bit signed (DMA direct)\n")
            f.write("// 1 = IMA ADPCM 4-bit (decoded by Timer 1 ISR, DMA playback)\n")
            f.write(f"#define AUDIO_FORMAT {fmt_val}\n\n")
            f.write(f"#define I_FRAME_AUDIO_OFFSET_COUNT "
                    f"{len(i_frame_audio_offsets) if i_frame_audio_offsets else 0}\n\n")
            f.write(f"extern const unsigned char audio_data_bin[audio_data_len];\n")
            f.write(f"#define audio_data audio_data_bin\n")

            if i_frame_audio_offsets:
                n = len(i_frame_audio_offsets)
                f.write(f"extern const unsigned char i_frame_audio_offsets_bin[{n * 4}];\n")
                f.write("#define i_frame_audio_offsets "
                        "((const unsigned int *)i_frame_audio_offsets_bin)\n")

            if frame_audio_offsets:
                n = len(frame_audio_offsets)
                f.write(f"#define FRAME_AUDIO_OFFSET_COUNT {n}\n")
                f.write(f"extern const unsigned char frame_audio_offsets_bin[{n * 4}];\n")
                f.write("#define frame_audio_offsets "
                        "((const unsigned int *)frame_audio_offsets_bin)\n")

            f.write(f"\n#endif // {guard}\n")

    def write_audio_bin_files(
        self,
        output_dir: Path,
        audio_data: bytes,
        i_frame_audio_offsets=None,
        frame_audio_offsets=None,
    ):
        self._write_binary(output_dir / "audio_data.bin", audio_data)
        if i_frame_audio_offsets:
            self._write_int32_bin(
                output_dir / "i_frame_audio_offsets.bin", i_frame_audio_offsets
            )
        if frame_audio_offsets:
            self._write_int32_bin(
                output_dir / "frame_audio_offsets.bin", frame_audio_offsets
            )
