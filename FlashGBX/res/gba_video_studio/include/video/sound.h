#ifndef GUARD_SOUND_H
#define GUARD_SOUND_H

#include "gba/gba.h"
#include "gba_video.h"
#include "audio_data.h"

#define TIMER_FREQ 16777216

static inline u16 TimerReload(u32 sampleRate) {
    return (u16)(0x10000 - (TIMER_FREQ / sampleRate));
}
void SoundInit(void);

// Stop audio DMA and both timers.
static inline void SoundStop(void) {
    REG_DMA1CNT_H = 0;
    REG_TM1CNT_H  = 0;
    REG_TM0CNT_H  = 0;
}

static inline void SoundMute(void) {
    REG_SOUNDCNT_X = 0;
}

static inline void SoundUnmute(void) {
    REG_SOUNDCNT_X = SOUND_MASTER_ENABLE;
}

#if AUDIO_FORMAT == 0   // PCM 8-bit signed
static inline void SoundPlay(const u8 *data) {
    SoundStop();
    REG_TM0CNT_L = TimerReload(SAMPLE_RATE);
    REG_TM0CNT_H = TIMER_ENABLE;
    DmaSet(1, data, &REG_FIFO_A,
        (DMA_ENABLE | DMA_START_SPECIAL | DMA_32BIT |
         DMA_SRC_INC | DMA_DEST_FIXED | DMA_REPEAT) << 16);
}

#elif AUDIO_FORMAT == 1   // IMA ADPCM 4-bit
#include "adpcm_decoder.h"

// Resume playback after AdpcmDecoder_seek().
// Seek already pre-filled both buffers with correct data.
// Timer 1 fires the IRQ exactly every HALF_BUF samples consumed by DMA.
// Startup order is critical to avoid the race condition that caused desync at start:
//   1. Stop both timers — guaranteed clean state.
//   2. Arm DMA with buffer 0.
//   3. Load Timer 1 reload WITHOUT enabling it yet.
//   4. Start Timer 0 — begins counting from 0.
//   5. Enable Timer 1 — now counts Timer 0 overflows,
//      starting from the first complete overflow. First IRQ arrives
//      exactly HALF_BUF samples after start.
static inline void SoundResumeTimer(void) {
    REG_SOUNDCNT_H = SOUND_A_MIX_FULL | SOUND_A_RIGHT_OUTPUT |
                     SOUND_A_LEFT_OUTPUT | SOUND_A_FIFO_RESET;

    // 1. Stop both timers.
    REG_TM1CNT_H = 0;
    REG_TM0CNT_H = 0;

    // 2. Arm DMA with buffer 0.
    REG_DMA1CNT_H = 0;
    REG_DMA1SAD   = (u32)gMixBuf[0];
    REG_DMA1DAD   = 0x040000A0;
    REG_DMA1CNT_L = 1;
    REG_DMA1CNT_H = DMA_DEST_FIXED | DMA_SRC_INC | DMA_REPEAT |
                    DMA_32BIT | DMA_START_SPECIAL | DMA_ENABLE;

    // 3. Load Timer 1 reload without enabling it.
    REG_TM1CNT_L = (u16)(0x10000 - HALF_BUF);

    // 4. Start Timer 0 — uses exact ADPCM_TIMER_RELOAD from encoder (nice rate).
    REG_TM0CNT_L = (u16)(0x10000 - ADPCM_TIMER_RELOAD);
    REG_TM0CNT_H = TIMER_ENABLE;

    // 5. Enable Timer 1 — counts from the first complete Timer 0 overflow.
    REG_TM1CNT_H = TIMER_CASCADE | TIMER_INTR_ENABLE | TIMER_ENABLE;
}

#endif

#endif // GUARD_SOUND_H
