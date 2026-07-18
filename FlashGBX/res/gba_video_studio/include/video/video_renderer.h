#ifndef GUARD_VIDEO_RENDERER_H
#define GUARD_VIDEO_RENDERER_H

#include "gba/gba.h"
#include "gba_video.h"

// EWRAM single-buffer: 240x160 pixels, 16-bit RGB555
extern u16 gVideoFrameBuffer[DISPLAY_WIDTH * DISPLAY_HEIGHT];

void  VideoRenderer_init(void);
s32   VideoRenderer_render_frame(const u8 *frameData);
void  VideoRenderer_clear_buffer(void);

static inline u16 *VideoRenderer_get_buffer(void) {
    return gVideoFrameBuffer;
}

#endif // GUARD_VIDEO_RENDERER_H
