#ifndef DEBUG_H
#define DEBUG_H

#include "gba/types.h"

// Use IWRAM for debug (0x03007000 - 0x03007FFF)
// First 32KB of IWRAM are safe
#define DEBUG_BASE ((vu32*)0x03007000)
#define DEBUG_SIZE 256

#define DEBUG_PUT(offset, value) (DEBUG_BASE[offset] = (value))
#define DEBUG_GET(offset) (DEBUG_BASE[offset])

static inline void Debug_Clear(void) {
    for (int i = 0; i < 64; i++) {
        DEBUG_BASE[i] = 0;
    }
}

static inline void Debug_PutByte(u32 offset, u8 value) {
    ((vu8*)DEBUG_BASE)[offset] = value;
}

static inline void Debug_PutHalf(u32 offset, u16 value) {
    ((vu16*)DEBUG_BASE)[offset] = value;
}

static inline void Debug_PutWord(u32 offset, u32 value) {
    DEBUG_BASE[offset] = value;
}

#endif