#ifndef GUARD_GBA_DEFINES_H
#define GUARD_GBA_DEFINES_H

#include <stddef.h>

#define TRUE  1
#define FALSE 0

#define IWRAM_DATA __attribute__((section("iwram_data")))
#define EWRAM_DATA __attribute__((section("ewram_data")))
#define COMMON_DATA __attribute__((section("common_data")))
#define UNUSED __attribute__((unused))

#if MODERN
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

#define ALIGNED(n) __attribute__((aligned(n)))

// INCBIN macros (GCC-compatible)
// Provide binary inclusion helpers similar to pokeemerald's incbin.
#if defined(__GNUC__)
#define INCBIN(name, file)                         \
	ALIGNED(2) extern const unsigned char name[];  \
	__asm__(                                       \
		".section .rodata\n"                       \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")

#define INCBIN_U8(name, file) INCBIN(name, file)
#define INCBIN_U16(name, file)                     \
	ALIGNED(2) extern const unsigned short name[]; \
	__asm__(                                       \
		".section .rodata\n"                       \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")

#define INCBIN_U32(name, file)                     \
	ALIGNED(4) extern const unsigned int name[];   \
	__asm__(                                       \
		".section .rodata\n"                       \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")

#define INCBIN_S8(name, file) INCBIN(name, file)
#define INCBIN_S16(name, file) INCBIN_U16(name, file)
#define INCBIN_S32(name, file) INCBIN_U32(name, file)
#else
#error "INCBIN macros require GCC-compatible compiler"
#endif

// Aligned 4-byte variant that keeps the data as bytes but ensures 4-byte alignment
#if defined(__GNUC__)
#define INCBIN_ALIGN4(name, file)                   \
	ALIGNED(4) extern const unsigned char name[];  \
	__asm__(                                       \
		".section .rodata\n"                       \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")
#endif

// Definition-only variants: emit the assembler incbin without adding an "extern" declaration.
// Use these in a single .c to create the symbol; keep "extern" declarations in headers.
#if defined(__GNUC__)
#define INCBIN_DEFINE(name, file)                     \
	__asm__(                                         \
		".section .rodata\n"                         \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")

#define INCBIN_DEFINE_U16(name, file)                 \
	__asm__(                                         \
		".section .rodata\n"                         \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")

#define INCBIN_DEFINE_U32(name, file)                 \
	__asm__(                                         \
		".section .rodata\n"                         \
		".global " #name "\n"                      \
		".type " #name ", %object\n"               \
		#name ":\n"                                \
		".incbin \"" file "\"\n"                   \
		".size " #name ", . - " #name "\n")

#define INCBIN_DEFINE_ALIGN4(name, file)              INCBIN_DEFINE(name, file)
#endif

#define SOUND_INFO_PTR (*(struct SoundInfo **)0x3007FF0)
#define INTR_CHECK     (*(u16 *)0x3007FF8)
#define INTR_VECTOR    (*(void **)0x3007FFC)

#define EWRAM_START 0x02000000
#define EWRAM_END   (EWRAM_START + 0x40000)
#define IWRAM_START 0x03000000
#define IWRAM_END   (IWRAM_START + 0x8000)

#define PLTT          0x5000000
#define BG_PLTT       PLTT
#define BG_PLTT_SIZE  0x200
#define OBJ_PLTT      (PLTT + BG_PLTT_SIZE)
#define OBJ_PLTT_SIZE 0x200
#define PLTT_SIZE     (BG_PLTT_SIZE + OBJ_PLTT_SIZE)

#define VRAM      0x6000000
#define VRAM_SIZE 0x18000

#define BG_VRAM           VRAM
#define BG_VRAM_SIZE      0x10000
#define BG_CHAR_SIZE      0x4000
#define BG_SCREEN_SIZE    0x800
#define BG_CHAR_ADDR(n)   (BG_VRAM + (BG_CHAR_SIZE * (n)))
#define BG_SCREEN_ADDR(n) (BG_VRAM + (BG_SCREEN_SIZE * (n)))

#define BG_TILE_H_FLIP(n) (0x400 + (n))
#define BG_TILE_V_FLIP(n) (0x800 + (n))

#define NUM_BACKGROUNDS 4

// text-mode BG
#define OBJ_VRAM0      (VRAM + 0x10000)
#define OBJ_VRAM0_SIZE 0x8000

// bitmap-mode BG
#define OBJ_VRAM1      (VRAM + 0x14000)
#define OBJ_VRAM1_SIZE 0x4000

#define OAM      0x7000000
#define OAM_SIZE 0x400

#define ROM_HEADER_SIZE   0xC0

// Dimensions of a tile in pixels
#define TILE_WIDTH  8
#define TILE_HEIGHT 8

// Dimensions of the GBA screen in pixels
#define DISPLAY_WIDTH  240
#define DISPLAY_HEIGHT 160

// Dimensions of the GBA screen in tiles
#define DISPLAY_TILE_WIDTH  (DISPLAY_WIDTH / TILE_WIDTH)
#define DISPLAY_TILE_HEIGHT (DISPLAY_HEIGHT / TILE_HEIGHT)

// Size of different tile formats in bytes
#define TILE_SIZE(bpp) ((bpp) * TILE_WIDTH * TILE_HEIGHT / 8)
#define TILE_SIZE_1BPP TILE_SIZE(1) // 8
#define TILE_SIZE_4BPP TILE_SIZE(4) // 32
#define TILE_SIZE_8BPP TILE_SIZE(8) // 64

#define TILE_OFFSET_4BPP(n) ((n) * TILE_SIZE_4BPP)
#define TILE_OFFSET_8BPP(n) ((n) * TILE_SIZE_8BPP)

#define TOTAL_OBJ_TILE_COUNT 1024

#define PLTT_SIZEOF(n) ((n) * sizeof(u16))
#define PLTT_SIZE_4BPP PLTT_SIZEOF(16)
#define PLTT_SIZE_8BPP PLTT_SIZEOF(256)

#define PLTT_OFFSET_4BPP(n) ((n) * PLTT_SIZE_4BPP)

#endif // GUARD_GBA_DEFINES_H
