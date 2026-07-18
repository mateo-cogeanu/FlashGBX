// adpcm_decoder.c - IMA9 ADPCM
// Non-critical functions: seek, global state.
// Timer 1 ISR (timer1_isr) lives in adpcm_decoder.iwram.c for single-cycle access.

#include "gba/gba.h"
#include "audio_data.h"
#include "adpcm_decoder.h"

#if AUDIO_FORMAT == 1

// Double buffer: DMA1 plays from gMixBuf[gPlayBuf] while Timer 1 ISR
// decodes into gMixBuf[gPlayBuf ^ 1]. 4-byte aligned for 32-bit DMA transfers.
__attribute__((section(".sbss"), aligned(4))) s8 gMixBuf[2][HALF_BUF];

u32 gPlayBuf     = 0;
u32 gAdpcmOffset = 0;

// Predictor state — extern in adpcm_decoder.iwram.c
int sLastSample = 0;
int sLastIndex  = 0;

void AdpcmDecoder_seek(u32 offset) {
    u16 ime = REG_IME;
    REG_IME = 0;

    sLastSample = 0;
    sLastIndex  = 0;
    gPlayBuf    = 0;

    // Warm-up: step back N bytes before the target offset and decode into scratch
    // so the predictor converges before reaching the exact seek point.
    // 16 blocks * HALF_BUF/2 bytes = ~1.5-4 s of warmup audio depending on rate.
    // Kept short to minimize time with IRQs disabled.
    #define WARMUP_BLOCKS 16
    u32 warmup_bytes = (HALF_BUF / 2) * WARMUP_BLOCKS;

    gAdpcmOffset = (offset >= warmup_bytes) ? (offset - warmup_bytes) : 0;
    gAdpcmOffset &= ~1u;  // align to even byte (2 nibbles per byte)

    u32 i;
    for (i = 0; i < WARMUP_BLOCKS; i++)
        AdpcmDecoder_decodeBlock(gMixBuf[0]);

    // Clamp to exact offset if stream was shorter than warmup window.
    if (gAdpcmOffset < offset)
        gAdpcmOffset = offset & ~1u;

    // Pre-decode both playback buffers with converged predictor.
    // DMA starts from buffer 0 immediately; buffer 1 used on first swap.
    AdpcmDecoder_decodeBlock(gMixBuf[0]);
    AdpcmDecoder_decodeBlock(gMixBuf[1]);

    gPlayBuf = 0;
    REG_IME = ime;
}

#endif
