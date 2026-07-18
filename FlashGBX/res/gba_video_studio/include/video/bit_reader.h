#ifndef GUARD_BIT_READER_H
#define GUARD_BIT_READER_H

#include "gba/gba.h"
#include "gba_video.h"

// Inline fixed-width bitstream reader.
// Reads 4, 6, or 8-bit fields from a byte stream.
// Call BitReader_finish() when done to flush remaining bits
// and update the caller's src pointer.

typedef struct {
    const u8 **srcPtr;    // pointer to the caller's src pointer
    const u8  *innerSrc;  // local copy to reduce double-pointer overhead
    u32        bitBuf;    // 32-bit buffer holding pending bits
    u8         bitsLeft;  // number of valid bits in bitBuf
    u8         bitLen;    // bits per read (4, 6, or 8)
    u8         bitMask;   // mask = (1 << bitLen) - 1
} BitReader;

// Refill the buffer when fewer than 24 bits remain
static inline void BitReader_fill(BitReader *r) {
    while (r->bitsLeft <= 24) {
        r->bitBuf  |= ((u32)(*r->innerSrc)) << r->bitsLeft;
        r->innerSrc++;
        r->bitsLeft += 8;
    }
}

// Initialize a BitReader
static inline void BitReader_init(BitReader *r, const u8 **src, s32 bits) {
    r->srcPtr   = src;
    r->innerSrc = *src;
    r->bitBuf   = 0;
    r->bitsLeft = 0;
    r->bitLen   = (u8)bits;
    r->bitMask  = (u8)((1 << bits) - 1);
    if (bits < 8)
        BitReader_fill(r);
}

// Read one field of bitLen bits
IWRAM_CODE static inline u8 BitReader_read(BitReader *r) {
    if (r->bitLen == 8)
        return *r->innerSrc++;

    if (r->bitsLeft < r->bitLen)
        BitReader_fill(r);

    u8 result    = (u8)(r->bitBuf & r->bitMask);
    r->bitBuf  >>= r->bitLen;
    r->bitsLeft -= r->bitLen;
    return result;
}

// Flush remaining bits and update the caller's src pointer
static inline void BitReader_finish(BitReader *r) {
    if (r->bitsLeft > 0)
        r->innerSrc -= (r->bitsLeft >> 3);
    *r->srcPtr = r->innerSrc;
}

#endif // GUARD_BIT_READER_H
