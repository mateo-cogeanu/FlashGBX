#ifndef GUARD_VIDEO_DECODER_H
#define GUARD_VIDEO_DECODER_H

#include "gba/gba.h"
#include "gba_video.h"
#include "video_data.h"
#include "bit_reader.h"

// Zone and codebook constants
#define ZONE_HEIGHT_PIXELS       16
#define ZONE_HEIGHT_BIG_BLOCKS   (ZONE_HEIGHT_PIXELS / (BLOCK_HEIGHT * 2))
#define MINI_CODEBOOK_SIZE       16
#define MEDIUM_CODEBOOK_SIZE     64

// Motion compensation constants
#define MOTION_BLOCK_8X8_SIZE             8
#define MOTION_BLOCKS_8X8_WIDTH           (DISPLAY_WIDTH  / MOTION_BLOCK_8X8_SIZE)  // 30
#define MOTION_BLOCKS_8X8_HEIGHT          (DISPLAY_HEIGHT / MOTION_BLOCK_8X8_SIZE)  // 20
#define MOTION_BLOCKS_8X8_PER_ZONE_ROW    MOTION_BLOCKS_8X8_WIDTH
#define MOTION_BLOCKS_8X8_PER_ZONE_HEIGHT 8
#define MOTION_TOTAL_ZONES \
    ((MOTION_BLOCKS_8X8_HEIGHT + MOTION_BLOCKS_8X8_PER_ZONE_HEIGHT - 1) / MOTION_BLOCKS_8X8_PER_ZONE_HEIGHT)
#define MOTION_RANGE 7

// YUV 2x2 block structure (packed, 6 bytes)
typedef struct {
    u8 y[2][2];
    s8 cb;
    s8 cr;
} __attribute__((packed)) YuvBlock;

// Pre-decoded RGB555 2x2 block (direct pixel values, no runtime conversion)
typedef struct {
    union {
        u16 rgb[2][2];
        struct {
            union { u16 u16_vals[2]; u32 u32_val; } row[2];
        };
    };
} __attribute__((packed)) Rgb555Block;

// Public API — all decoder state is in video_decoder.c globals

void  VideoDecoder_init(void);
void  VideoDecoder_reset_codebook(void);
void  VideoDecoder_decode_frame(const u8 *frameData, u16 *dst);
void  VideoDecoder_preload_codebook(const u8 *src);
void  VideoDecoder_preload_codebook_blocking(const u8 *src);
void  VideoDecoder_load_codebook_and_convert(const u8 *src);
void  VideoDecoder_find_next_i_frame(const u8 *videoData, s32 startFrame);

bool8 VideoDecoder_is_codebook_preloaded(void);
bool8 VideoDecoder_is_rgb555_codebook_preloaded(void);
s32   VideoDecoder_get_next_i_frame(void);

// Inline: check if a frame pointer points to an I-frame
static inline bool8 VideoDecoder_is_i_frame(const u8 *frameData) {
    return (*frameData) == FRAME_TYPE_I;
}

#endif // GUARD_VIDEO_DECODER_H
