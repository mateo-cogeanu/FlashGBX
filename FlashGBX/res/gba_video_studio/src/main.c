// main.c
#include "gba/gba.h"
#include <string.h>
#include "gba_video.h"
#include "video_data.h"
#include "video_renderer.h"
#include "video_decoder.h"
#include "audio_data.h"
#include "sound.h"
#include "debug.h"

#if AUDIO_FORMAT == 1
#include "adpcm_decoder.h"
#endif


static volatile u32   sVbl            = 0;
static volatile u32   sAcc            = 0;
static volatile bool8 sShouldCopy     = FALSE;
static volatile bool8 sForceAudioSync = TRUE;
#if AUDIO_FORMAT != 2
static bool8 sAudioMuted              = FALSE;
#endif
static u16   sPrevKeys                = 0;
static s32   sFrame                   = 0;
static bool8 sControlsEnabled         = TRUE;
static bool8 sPaused                  = FALSE;

#if AUDIO_FORMAT != 1
#define SEEK_SECONDS(sec) ((sec) * VIDEO_FPS / 10000)
#endif
#define LCD_FPS 597275

void VBlankIntrHandler(void) {
    u32 flags = REG_IF;

    if (flags & INTR_FLAG_VBLANK) {
        ++sVbl;
        sAcc += VIDEO_FPS;
        if (sAcc >= LCD_FPS) {
            sShouldCopy = TRUE;
            sAcc -= LCD_FPS;
        }
        REG_IF = INTR_FLAG_VBLANK;
        INTR_CHECK |= INTR_FLAG_VBLANK;
    }

#if AUDIO_FORMAT == 1
    if (flags & INTR_FLAG_TIMER1) {
        AdpcmDecoder_timer1_isr();
        REG_IF = INTR_FLAG_TIMER1;
        INTR_CHECK |= INTR_FLAG_TIMER1;
    }
#endif

    if (flags & INTR_FLAG_DMA1) {
        REG_IF = INTR_FLAG_DMA1;
    }
}

void RunVideoPlayer(void) {
    SoundInit();
    VideoDecoder_reset_codebook();
    sForceAudioSync = TRUE;

    while (TRUE) {
        const u8 *frameData;
        u16 keys;
        u16 pressed;

        /* --- Input handling (top of loop so pause blocks before decode) --- */
        REG_KEYINPUT;
        keys    = ~REG_KEYINPUT & KEY_MASK_ALL;
        pressed = keys & ~sPrevKeys;

#if AUDIO_FORMAT == 0
        /* PCM: full controls — pause, mute, seek, SELECT toggle */
        if (pressed & KEY_SELECT) {
            sControlsEnabled = !sControlsEnabled;
            /* Unpausing forced when controls are locked — free-play resumes */
            if (!sControlsEnabled && sPaused) {
                sPaused = FALSE;
                if (!sAudioMuted) sForceAudioSync = TRUE;
            }
        }
        if (sControlsEnabled) {
            if (pressed & (KEY_START | KEY_A)) {
                sPaused = !sPaused;
                if (sPaused) {
                    SoundStop();
                } else {
                    if (!sAudioMuted) sForceAudioSync = TRUE;
                }
            }
            if (pressed & KEY_B) {
                sAudioMuted = !sAudioMuted;
                if (sAudioMuted) SoundMute(); else SoundUnmute();
            }
        }

        /* Pause loop — freeze frame, keep reading input */
        if (sPaused) {
            sPrevKeys = keys;
            while (TRUE) {
                VBlankIntrWait();
                REG_KEYINPUT;
                keys    = ~REG_KEYINPUT & KEY_MASK_ALL;
                pressed = keys & ~sPrevKeys;
                if (pressed & KEY_SELECT) {
                    sControlsEnabled = !sControlsEnabled;
                    if (!sControlsEnabled) {
                        /* Locked while paused — force resume and exit pause loop */
                        sPaused = FALSE;
                        if (!sAudioMuted) sForceAudioSync = TRUE;
                        sPrevKeys = keys;
                        break;
                    }
                }
                if (sControlsEnabled) {
                    if (pressed & (KEY_START | KEY_A)) {
                        sPaused = FALSE;
                        if (!sAudioMuted) sForceAudioSync = TRUE;
                        sPrevKeys = keys;
                        break;
                    }
                    if (pressed & KEY_B) {
                        sAudioMuted = !sAudioMuted;
                        if (sAudioMuted) SoundMute(); else SoundUnmute();
                    }
                }
                sPrevKeys = keys;
            }
            continue; /* re-read input at top */
        }

        /* Seek controls (PCM only — ADPCM cannot seek) */
        if (sControlsEnabled) {
            if (pressed & KEY_RIGHT) {
                s32 target = sFrame + SEEK_SECONDS(3);
                if (target >= VIDEO_FRAME_COUNT) target = VIDEO_FRAME_COUNT - 1;
                /* Find nearest I-frame at or after target, wrapping to start */
                sFrame = target;
                while (sFrame < VIDEO_FRAME_COUNT &&
                       !VideoDecoder_is_i_frame(video_data + frame_offsets[sFrame]))
                    sFrame++;
                if (sFrame >= VIDEO_FRAME_COUNT) sFrame = 0;
                SoundStop();
                sShouldCopy = FALSE;
                VideoDecoder_reset_codebook();
                VideoDecoder_preload_codebook_blocking(video_data + frame_offsets[sFrame]);
#ifdef FRAME_AUDIO_OFFSET_COUNT
                SoundPlay(audio_data + frame_audio_offsets[sFrame]);
#endif
                sForceAudioSync = FALSE;
                sPrevKeys = keys;
                continue;
            }
            if (pressed & KEY_LEFT) {
                s32 target = sFrame - SEEK_SECONDS(3);
                if (target < 0) target = 0;
                /* Find nearest I-frame at or before target */
                sFrame = target;
                while (sFrame > 0 &&
                       !VideoDecoder_is_i_frame(video_data + frame_offsets[sFrame]))
                    sFrame--;
                SoundStop();
                sShouldCopy = FALSE;
                VideoDecoder_reset_codebook();
                VideoDecoder_preload_codebook_blocking(video_data + frame_offsets[sFrame]);
#ifdef FRAME_AUDIO_OFFSET_COUNT
                SoundPlay(audio_data + frame_audio_offsets[sFrame]);
#endif
                sForceAudioSync = FALSE;
            }
        }

#elif AUDIO_FORMAT == 1
        /* ADPCM: pause, mute, and SELECT lock/unlock available; seek disabled */
        if (pressed & KEY_SELECT) {
            sControlsEnabled = !sControlsEnabled;
            /* Locked while paused — force resume */
            if (!sControlsEnabled && sPaused) {
                sPaused = FALSE;
                if (!sAudioMuted) SoundResumeTimer();
            }
        }
        if (sControlsEnabled) {
            if (pressed & (KEY_START | KEY_A)) {
                sPaused = !sPaused;
                if (sPaused) {
                    SoundStop();
                } else {
                    if (!sAudioMuted) SoundResumeTimer();
                }
            }
            if (pressed & KEY_B) {
                sAudioMuted = !sAudioMuted;
                if (sAudioMuted) SoundMute(); else SoundUnmute();
            }
        }

        /* Pause loop for ADPCM — audio stopped, ADPCM decoder keeps state */
        if (sPaused) {
            sPrevKeys = keys;
            while (TRUE) {
                VBlankIntrWait();
                REG_KEYINPUT;
                keys    = ~REG_KEYINPUT & KEY_MASK_ALL;
                pressed = keys & ~sPrevKeys;
                if (pressed & KEY_SELECT) {
                    sControlsEnabled = !sControlsEnabled;
                    if (!sControlsEnabled) {
                        /* Locked while paused — force resume and exit pause loop */
                        sPaused = FALSE;
                        if (!sAudioMuted) SoundResumeTimer();
                        sPrevKeys = keys;
                        break;
                    }
                }
                if (sControlsEnabled) {
                    if (pressed & (KEY_START | KEY_A)) {
                        sPaused = FALSE;
                        if (!sAudioMuted) SoundResumeTimer();
                        sPrevKeys = keys;
                        break;
                    }
                    if (pressed & KEY_B) {
                        sAudioMuted = !sAudioMuted;
                        if (sAudioMuted) SoundMute(); else SoundUnmute();
                    }
                }
                sPrevKeys = keys;
            }
            continue;
        }
#else
        /* No audio: SELECT lock/unlock, pause, seek — no mute controls */
        if (pressed & KEY_SELECT) {
            sControlsEnabled = !sControlsEnabled;
            if (!sControlsEnabled && sPaused) {
                sPaused = FALSE;
            }
        }
        if (sControlsEnabled) {
            if (pressed & (KEY_START | KEY_A)) {
                sPaused = !sPaused;
            }
        }

        if (sPaused) {
            sPrevKeys = keys;
            while (TRUE) {
                VBlankIntrWait();
                REG_KEYINPUT;
                keys    = ~REG_KEYINPUT & KEY_MASK_ALL;
                pressed = keys & ~sPrevKeys;
                if (pressed & KEY_SELECT) {
                    sControlsEnabled = !sControlsEnabled;
                    if (!sControlsEnabled) {
                        sPaused = FALSE;
                        sPrevKeys = keys;
                        break;
                    }
                }
                if (sControlsEnabled) {
                    if (pressed & (KEY_START | KEY_A)) {
                        sPaused = FALSE;
                        sPrevKeys = keys;
                        break;
                    }
                }
                sPrevKeys = keys;
            }
            continue;
        }

        /* Seek controls (no audio — no SoundPlay needed) */
        if (sControlsEnabled) {
            if (pressed & KEY_RIGHT) {
                s32 target = sFrame + SEEK_SECONDS(3);
                if (target >= VIDEO_FRAME_COUNT) target = VIDEO_FRAME_COUNT - 1;
                sFrame = target;
                while (sFrame < VIDEO_FRAME_COUNT &&
                       !VideoDecoder_is_i_frame(video_data + frame_offsets[sFrame]))
                    sFrame++;
                if (sFrame >= VIDEO_FRAME_COUNT) sFrame = 0;
                sShouldCopy = FALSE;
                VideoDecoder_reset_codebook();
                VideoDecoder_preload_codebook_blocking(video_data + frame_offsets[sFrame]);
                sPrevKeys = keys;
                continue;
            }
            if (pressed & KEY_LEFT) {
                s32 target = sFrame - SEEK_SECONDS(3);
                if (target < 0) target = 0;
                sFrame = target;
                while (sFrame > 0 &&
                       !VideoDecoder_is_i_frame(video_data + frame_offsets[sFrame]))
                    sFrame--;
                sShouldCopy = FALSE;
                VideoDecoder_reset_codebook();
                VideoDecoder_preload_codebook_blocking(video_data + frame_offsets[sFrame]);
            }
        }
#endif
        sPrevKeys = keys;

        /* --- Decode and display current frame --- */
        frameData = video_data + frame_offsets[sFrame];
        VideoRenderer_render_frame(frameData);

        while (!sShouldCopy) {
            if (VideoDecoder_is_rgb555_codebook_preloaded()) {
                VBlankIntrWait();
                continue;
            }
            s32 next = VideoDecoder_get_next_i_frame();
            if (next == -1) {
                VideoDecoder_find_next_i_frame(video_data, sFrame + 1);
                if (!sShouldCopy)
                    VBlankIntrWait();
                continue;
            }
            VideoDecoder_preload_codebook(video_data + frame_offsets[next]);
        }
        sShouldCopy = FALSE;

        CpuFastCopy(VideoRenderer_get_buffer(), (void *)VRAM,
                    DISPLAY_WIDTH * DISPLAY_HEIGHT * sizeof(u16));

#ifdef FRAME_AUDIO_OFFSET_COUNT
        if (sForceAudioSync) {
#if AUDIO_FORMAT == 0
            SoundPlay(audio_data + frame_audio_offsets[sFrame]);
#elif AUDIO_FORMAT == 1
            AdpcmDecoder_seek(frame_audio_offsets[sFrame]);
            VBlankIntrWait();
            SoundResumeTimer();
#endif
            if (sAudioMuted) SoundMute();
            sForceAudioSync = FALSE;
        }
#endif

        sFrame++;
        if (sFrame >= VIDEO_FRAME_COUNT) {
            sFrame = 0;
            SoundStop();
            VideoDecoder_reset_codebook();
            sForceAudioSync = TRUE;
        }
    }
}

int main(void) {
    REG_DISPCNT = DISPCNT_MODE_3 | DISPCNT_BG2_ON;
    INTR_VECTOR = VBlankIntrHandler;
    REG_DISPSTAT |= DISPSTAT_VBLANK_INTR;
    REG_IE = INTR_FLAG_VBLANK | INTR_FLAG_DMA1 | INTR_FLAG_TIMER1;
    REG_IME = 1;
    VideoRenderer_init();
    RunVideoPlayer();
    return 0;
}
