// adpcm_decoder.iwram.c — critical ADPCM decoder functions in IWRAM.
// Runs from Timer 1 ISR; IWRAM placement avoids ROM wait-state latency.
//
// Double-buffer scheme driven by Timer 1 (no VBlank dependency):
//
//   gMixBuf[0][HALF_BUF]   gMixBuf[1][HALF_BUF]
//   ┌──────────────────┐   ┌──────────────────┐
//   │  buffer 0        │   │  buffer 1        │
//   └──────────────────┘   └──────────────────┘
//         ▲                       ▲
//         └── DMA1 plays from gMixBuf[gPlayBuf]
//
//   Timer 0: overflows every (16777216/SAMPLE_RATE) cycles → DMA1 FIFO trigger
//   Timer 1: CASCADE from Timer 0, counts HALF_BUF overflows → IRQ
//
//   On each Timer 1 IRQ:
//     1. Swap: DMA1 switches to the freshly decoded buffer (gPlayBuf ^= 1)
//     2. Decode: fill the just-finished buffer with new samples
//
//   Explicit DMA re-arm is required because DMA_START_SPECIAL reloads the
//   source pointer to its original value every 16 bytes — no large-buffer wrap.

#include "gba/gba.h"
#include "audio_data.h"
#include "adpcm_decoder.h"

#if AUDIO_FORMAT == 1

// Tables in IWRAM for single-cycle access from the decoder.
static const signed char sIma9StepIndices[16] = {
    -1, -1, -1, -1, 2, 4, 7, 12,
    -1, -1, -1, -1, 2, 4, 7, 12
};

static const unsigned short sImaStepTable[89] = {
        7,    8,    9,   10,   11,   12,   13,   14,   16,   17,
       19,   21,   23,   25,   28,   31,   34,   37,   41,   45,
       50,   55,   60,   66,   73,   80,   88,   97,  107,  118,
      130,  143,  157,  173,  190,  209,  230,  253,  279,  307,
      337,  371,  408,  449,  494,  544,  598,  658,  724,  796,
      876,  963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
     2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
     5894, 6484, 7132, 7845, 8630, 9493,10442,11487,12635,13899,
    15289,16818,18500,20350,22385,24623,27086,29794,32767
};

// Step index lookup table and predictor state — defined in adpcm_decoder.c
extern int sLastSample;
extern int sLastIndex;

static inline int Ima9Rescale(int step, unsigned int code) {
    int diff = step >> 3;
    if (code & 1) diff += step >> 2;
    if (code & 2) diff += step >> 1;
    if (code & 4) diff += step;
    if ((code & 7) == 7) diff += step >> 1;
    if (code & 8) diff = -diff;
    return diff;
}

// Decode HALF_BUF ADPCM samples into dst.
// Called from Timer 1 ISR and from seek() for pre-fill.
// HALF_BUF = ADPCM_SAMPLES_PER_FRAME (exact nice rate from encoder).
// At ~100 cycles/sample, margin is wide even at the lowest nice rate (112 spf).
void AdpcmDecoder_decodeBlock(s8 *dst) {
    int last_sample = sLastSample;
    int index       = sLastIndex;
    unsigned int by = 0;
    u32 written     = 0;

    if (audio_data_len == 0 || gAdpcmOffset >= audio_data_len) {
        for (; written < HALF_BUF; written++)
            dst[written] = 0;
        return;
    }

    while (written < HALF_BUF) {
        int step, diff;
        unsigned int code;

        if (index < 0)  index = 0;
        if (index > 88) index = 88;
        step = sImaStepTable[index];

        if (written & 1) {
            code = by >> 4;
        } else {
            if (gAdpcmOffset >= audio_data_len) {
                for (; written < HALF_BUF; written++)
                    dst[written] = 0;
                break;
            }
            by   = audio_data[gAdpcmOffset++];
            code = by & 0x0F;
        }

        diff = Ima9Rescale(step, code);
        index += sIma9StepIndices[code & 0x07];

        last_sample += diff;
        if (last_sample < -32768) last_sample = -32768;
        if (last_sample >  32767) last_sample =  32767;

        dst[written++] = (s8)(last_sample >> 8);
    }

    sLastSample = last_sample;
    sLastIndex  = index;
}

// Timer 1 ISR (cascade from Timer 0).
// Called exactly every HALF_BUF samples consumed by DMA.
// 1. Swap DMA to the freshly decoded buffer.
// 2. Decode the buffer that just finished.
void AdpcmDecoder_timer1_isr(void) {
    gPlayBuf ^= 1;

    REG_DMA1CNT_H = 0;
    asm volatile("eor r0, r0; eor r0, r0" ::: "r0");
    REG_DMA1SAD   = (u32)gMixBuf[gPlayBuf];
    REG_DMA1DAD   = 0x040000A0;
    REG_DMA1CNT_L = 1;
    REG_DMA1CNT_H = DMA_DEST_FIXED | DMA_SRC_INC | DMA_REPEAT |
                    DMA_32BIT | DMA_START_SPECIAL | DMA_ENABLE;

    AdpcmDecoder_decodeBlock(gMixBuf[gPlayBuf ^ 1]);
}

#endif
