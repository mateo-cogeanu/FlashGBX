#include "gba/gba.h"
#include <string.h>
#include "gba_video.h"
#include "video_renderer.h"
#include "video_decoder.h"

// EWRAM single-buffer: decoded frame pixels before copy to VRAM
__attribute__((aligned(4))) EWRAM_DATA u16 gVideoFrameBuffer[DISPLAY_WIDTH * DISPLAY_HEIGHT];

void VideoRenderer_init(void) {
    VideoDecoder_init();
    VideoRenderer_clear_buffer();
    DmaCopy32(3, gVideoFrameBuffer, (void *)VRAM,
              DISPLAY_WIDTH * DISPLAY_HEIGHT * sizeof(u16));
}

s32 VideoRenderer_render_frame(const u8 *frameData) {
    bool8 isIFrame = VideoDecoder_is_i_frame(frameData);
    VideoDecoder_decode_frame(frameData, gVideoFrameBuffer);
    return isIFrame ? 1 : -1;
}

void VideoRenderer_clear_buffer(void) {
    CpuFastFill(0, gVideoFrameBuffer, DISPLAY_WIDTH * DISPLAY_HEIGHT * sizeof(u16));
}
