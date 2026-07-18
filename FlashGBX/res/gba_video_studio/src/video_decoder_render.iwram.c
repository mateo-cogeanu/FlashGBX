// video_decoder_render.iwram.c
#include "gba/gba.h"
#include "gba_video.h"
#include "video_decoder.h"
#include "bit_reader.h"

// ---------------------------------------------------------------------------
// Extern state from video_decoder.c
// ---------------------------------------------------------------------------
extern bool8        sCodebookLoaded;
extern bool8        sRgb555Loaded;
extern s32          sRgb555Idx;
extern Rgb555Block  sRgb555Buf[2][UNIFIED_CODEBOOK_SIZE];
extern Rgb555Block *sRgb555Codebook;

// Declared in video_decoder.c — called via long_call (IWRAM→ROM cross-section)
extern void VideoDecoder_load_codebook_and_convert(const u8 *src)
    __attribute__((long_call));
extern void VideoDecoder_reset_codebook(void)
    __attribute__((long_call));

// ROM lookup tables — declared in video_decoder.h
// gBigBlockOffsets, gZoneBlockOffsets, gZoneMotionBlockOffsets : const u16[]
// gClipLookupTable                                             : const u8[]

// ---------------------------------------------------------------------------
// Inline 2x2 block renderer
// ---------------------------------------------------------------------------
static inline void RenderBlock(const Rgb555Block *cb, u16 *dst) {
    *(u32 *)(&dst[0])             = cb->row[0].u32_val;
    *(u32 *)(&dst[DISPLAY_WIDTH]) = cb->row[1].u32_val;
}

// ---------------------------------------------------------------------------
// 4x4 color block: upsample 2x2 -> 4x4
// ---------------------------------------------------------------------------
static void RenderColorBlock(const Rgb555Block *cb, u16 *dst) {
    u16 c0 = cb->rgb[0][0], c1 = cb->rgb[0][1];
    u16 c2 = cb->rgb[1][0], c3 = cb->rgb[1][1];

    typedef union { u16 v[2]; u32 u; } Pair;
    Pair p0 = {{ c0, c0 }}, p1 = {{ c1, c1 }};
    Pair p2 = {{ c2, c2 }}, p3 = {{ c3, c3 }};

    *(u32 *)(dst)     = p0.u;  *(u32 *)(dst + 2) = p1.u;
    dst += DISPLAY_WIDTH;
    *(u32 *)(dst)     = p0.u;  *(u32 *)(dst + 2) = p1.u;
    dst += DISPLAY_WIDTH;
    *(u32 *)(dst)     = p2.u;  *(u32 *)(dst + 2) = p3.u;
    dst += DISPLAY_WIDTH;
    *(u32 *)(dst)     = p2.u;  *(u32 *)(dst + 2) = p3.u;
}

// ---------------------------------------------------------------------------
// 4x4 texture block: 4 separate 2x2 sub-blocks
// ---------------------------------------------------------------------------
static void RenderTextureBlock(const Rgb555Block *cb, const u8 idx[4], u16 *dst) {
    RenderBlock(&cb[idx[0]], dst);
    RenderBlock(&cb[idx[1]], dst + 2);
    RenderBlock(&cb[idx[2]], dst + DISPLAY_WIDTH * 2);
    RenderBlock(&cb[idx[3]], dst + DISPLAY_WIDTH * 2 + 2);
}

// ---------------------------------------------------------------------------
// Partial 4x4 block update from bitstream
// ---------------------------------------------------------------------------
static void DecodePartial4x4Block(u8 *validBitmap, BitReader *reader,
                                   u16 *dst, const Rgb555Block *cb) {
    static const u16 kSubOffsets[4] = {
        0, 2, DISPLAY_WIDTH * 2, DISPLAY_WIDTH * 2 + 2
    };
    u8 i;
    for (i = 0; i < 4; i++) {
        if (*validBitmap & 1) {
            u8 idx = BitReader_read(reader);
            RenderBlock(&cb[idx], dst + kSubOffsets[i]);
        }
        *validBitmap >>= 1;
    }
}

// ---------------------------------------------------------------------------
// Segment decoder (small / medium / full codebook modes)
// ---------------------------------------------------------------------------
static void DecodeSegment(u8 cbSize, u8 bitLen, u8 bitMask,
                           u16 segIdx, const u8 **src,
                           u16 *zoneDst, const Rgb555Block *cb) {
    const Rgb555Block *segCb = cb + ((u32)segIdx << bitLen);

    u8 numBlocks = *(*src)++;
    const u8 *bmpPtr = *src;

    *src += (numBlocks >> 1) * 3;
    if (numBlocks & 1) *src += 2;

    BitReader reader;
    BitReader_init(&reader, src, bitLen);

    const u8 *bp = bmpPtr;
    bool8 isOdd  = (numBlocks & 1) != FALSE;
    numBlocks >>= 1;

    while (numBlocks--) {
        u8   vbm  = *bp++;
        u8   zi   = *bp++;
        u16 *dst1 = zoneDst + gZoneBlockOffsets[zi];
        DecodePartial4x4Block(&vbm, &reader, dst1, segCb);

        zi = *bp++;
        u16 *dst2 = zoneDst + gZoneBlockOffsets[zi];
        DecodePartial4x4Block(&vbm, &reader, dst2, segCb);
    }

    if (isOdd) {
        u8   vbm  = *bp++;
        u8   zi   = *bp++;
        u16 *dst1 = zoneDst + gZoneBlockOffsets[zi];
        DecodePartial4x4Block(&vbm, &reader, dst1, segCb);
    }

    BitReader_finish(&reader);
}

// ---------------------------------------------------------------------------
// Motion compensation
// ---------------------------------------------------------------------------
static void ApplyMotionCompensation(const u8 **src, u16 *dst, u16 *vramSrc) {
    u8  zoneBitmap = *(*src)++;
    s32 zoneIdx    = 0;
    u16 *zSrc = vramSrc;
    u16 *zDst = dst;

    while (zoneBitmap) {
        if (zoneBitmap & 1) {
            u8 stripCount = *(*src)++;
            u8 i;
            for (i = 0; i < stripCount; i++) {
                u8 blockIdx  = (*src)[0];
                u8 encodedMv = (*src)[1];
                u8 contCount = (*src)[2];
                *src += 3;

                s32 dx = (encodedMv & 0x0F) - MOTION_RANGE;
                s32 dy = ((encodedMv >> 4) & 0x0F) - MOTION_RANGE;

                s32 dstOff = gZoneMotionBlockOffsets[blockIdx];
                s32 srcOff = dstOff + dy * DISPLAY_WIDTH + dx;
                s32 stripW = MOTION_BLOCK_8X8_SIZE * contCount;
                s32 y;

                for (y = 0; y < MOTION_BLOCK_8X8_SIZE; y++) {
                    DmaCopy32(3, &zSrc[srcOff], &zDst[dstOff],
                              stripW * sizeof(u16));
                    dstOff += DISPLAY_WIDTH;
                    srcOff += DISPLAY_WIDTH;
                }
            }
        }
        zoneIdx++;
        zoneBitmap >>= 1;
        const s32 kZoneOffset = MOTION_BLOCK_8X8_SIZE * MOTION_BLOCK_8X8_SIZE * 240;
        zSrc += kZoneOffset;
        zDst += kZoneOffset;
    }
}

// ---------------------------------------------------------------------------
// I-frame decoder
// ---------------------------------------------------------------------------
static void DecodeIFrame(const u8 *src, u16 *dst) {
    if (!sRgb555Loaded)
        VideoDecoder_load_codebook_and_convert(src);

    VideoDecoder_reset_codebook();

    src += UNIFIED_CODEBOOK_SIZE * BYTES_PER_BLOCK;

    sRgb555Idx     ^= 1;
    sRgb555Codebook = sRgb555Buf[sRgb555Idx];

    const u16 kTotalBlocks =
        (VIDEO_WIDTH / (BLOCK_WIDTH * 2)) * (VIDEO_HEIGHT / (BLOCK_HEIGHT * 2));

    u16 idx;
    for (idx = 0; idx < kTotalBlocks; idx++) {
        u16 *bigDst = dst + gBigBlockOffsets[idx];
        u8   first  = *src++;

        if (first == COLOR_BLOCK_MARKER) {
            u8 ci = *src++;
            RenderColorBlock(&sRgb555Codebook[ci], bigDst);
        } else {
            u8 qi[4] = { first, *src++, *src++, *src++ };
            RenderTextureBlock(sRgb555Codebook, qi, bigDst);
        }
    }
}

// ---------------------------------------------------------------------------
// P-frame decoder
// ---------------------------------------------------------------------------
static void DecodePFrame(const u8 *src, u16 *dst) {
    ApplyMotionCompensation(&src, dst, (u16 *)VRAM);

    u16 detailBitmap = src[0] | ((u16)src[1] << 8);
    u16 colorBitmap  = src[2] | ((u16)src[3] << 8);
    src += 4;

    u8  zoneIdx = 0;
    u16 bmp     = detailBitmap;
    while (bmp) {
        if (bmp & 1) {
            u16  zoneBase = zoneIdx * ZONE_HEIGHT_PIXELS * DISPLAY_WIDTH;
            u16 *zDst     = dst + zoneBase;

            u16 smallBmp = src[0] | ((u16)src[1] << 8);
            src += 2;
            u16 seg;
            for (seg = 0; seg < 16; seg++) {
                if (smallBmp & (1u << seg))
                    DecodeSegment(MINI_CODEBOOK_SIZE, 4, 0xF,
                                  seg, &src, zDst, sRgb555Codebook);
            }

            u8 medBmp = *src++;
            u8 mseg;
            for (mseg = 0; mseg < 4; mseg++) {
                if (medBmp & (1u << mseg))
                    DecodeSegment(MEDIUM_CODEBOOK_SIZE, 6, 0x3F,
                                  mseg, &src, zDst, sRgb555Codebook);
            }

            DecodeSegment(0, 8, 0xFF, 0, &src, zDst, sRgb555Codebook);
        }
        bmp >>= 1;
        zoneIdx++;
    }

    zoneIdx = 0;
    bmp     = colorBitmap;
    while (bmp) {
        if (bmp & 1) {
            u8   count    = *src++;
            u16  zoneBase = zoneIdx * ZONE_HEIGHT_PIXELS * DISPLAY_WIDTH;
            u16 *zDst     = dst + zoneBase;
            u8   i;
            for (i = 0; i < count; i++) {
                u8   zi   = *src++;
                u8   ci   = *src++;
                u16 *bDst = zDst + gZoneBlockOffsets[zi];
                RenderColorBlock(&sRgb555Codebook[ci], bDst);
            }
        }
        bmp >>= 1;
        zoneIdx++;
    }
}

// ---------------------------------------------------------------------------
// Public decode entry point
// ---------------------------------------------------------------------------
void VideoDecoder_decode_frame(const u8 *frameData, u16 *dst) {
    u8 type = *frameData++;
    if (type == FRAME_TYPE_I)
        DecodeIFrame(frameData, dst);
    else if (type == FRAME_TYPE_P)
        DecodePFrame(frameData, dst);
}
