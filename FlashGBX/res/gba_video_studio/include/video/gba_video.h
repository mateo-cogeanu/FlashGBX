#ifndef GUARD_GBA_VIDEO_H
#define GUARD_GBA_VIDEO_H

// Project-level GBA definitions not present in pokeemerald's include/gba/
// but needed for bare-metal video player code.

// ---------------------------------------------------------------------------
// IWRAM_CODE: place function in fast IWRAM for performance-critical code
// ---------------------------------------------------------------------------
#define IWRAM_CODE __attribute__((section("iwram"), long_call))

// EWRAM_DATA: place large buffers in external WRAM (256 KB, slower but big)
// devkitARM linker script uses section ".ewram" (with dot prefix).
#undef  EWRAM_DATA
#define EWRAM_DATA __attribute__((section(".ewram")))

// ---------------------------------------------------------------------------
// Key input bitmasks (REG_KEYINPUT — bits are ACTIVE LOW, so we invert)
// Usage: u16 keys = ~REG_KEYINPUT & KEY_MASK_ALL;
// ---------------------------------------------------------------------------
#define KEY_A        (1 << 0)
#define KEY_B        (1 << 1)
#define KEY_SELECT   (1 << 2)
#define KEY_START    (1 << 3)
#define KEY_RIGHT    (1 << 4)
#define KEY_LEFT     (1 << 5)
#define KEY_UP       (1 << 6)
#define KEY_DOWN     (1 << 7)
#define KEY_R        (1 << 8)
#define KEY_L        (1 << 9)
#define KEY_MASK_ALL 0x03FF

// ---------------------------------------------------------------------------
// Timer control
// ---------------------------------------------------------------------------
#define TIMER_START   TIMER_ENABLE   // alias for clarity
#define TIMER_CASCADE 0x04           // increment on previous timer overflow

// ---------------------------------------------------------------------------
// Interrupt vector (GBA BIOS uses 0x3007FFC)
// ---------------------------------------------------------------------------
#define INTR_VECTOR (*(void **)0x3007FFC)

#endif // GUARD_GBA_VIDEO_H
