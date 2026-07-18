#include "gba/gba.h"
#include "sound.h"
#include "audio_data.h"

void SoundInit(void) {
    REG_SOUNDCNT_X = SOUND_MASTER_ENABLE;
    REG_SOUNDCNT_H = SOUND_A_MIX_FULL | SOUND_A_RIGHT_OUTPUT |
                     SOUND_A_LEFT_OUTPUT | SOUND_A_FIFO_RESET;

#if AUDIO_FORMAT == 1
    // Configure SOUNDBIAS for the sample rate to avoid distortion.
    // GBA DAC uses PWM; amplitude resolution must match the sample rate
    // so PWM can update in time.
    //
    // Rule: resolution_bits + log2(sample_rate) <= 21 (hardware limit).
    //   SAMPLE_RATE <= 10923 Hz → 9-bit (bit15:14 = 00)  PWM at 32768 Hz
    //   SAMPLE_RATE <= 21845 Hz → 8-bit (bit15:14 = 01)  PWM at 65536 Hz
    //   SAMPLE_RATE <= 43690 Hz → 7-bit (bit15:14 = 10)  PWM at 131072 Hz
    //   SAMPLE_RATE <= 65536 Hz → 6-bit (bit15:14 = 11)  PWM at 262144 Hz
    //
    // Bias 0x200 centers the waveform at DAC midpoint.
    #if SAMPLE_RATE <= 10923
        REG_SOUNDBIAS = 0x200 | (0 << 14);  // 9-bit
    #elif SAMPLE_RATE <= 21845
        REG_SOUNDBIAS = 0x200 | (1 << 14);  // 8-bit (covers up to ~21845 Hz)
    #elif SAMPLE_RATE <= 43690
        REG_SOUNDBIAS = 0x200 | (2 << 14);  // 7-bit (covers 22050, 32768 Hz)
    #else
        REG_SOUNDBIAS = 0x200 | (3 << 14);  // 6-bit (cubre 44100 Hz)
    #endif
#endif
}
