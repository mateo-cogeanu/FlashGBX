#---------------------------------------------------------------------------------
.SUFFIXES:
#---------------------------------------------------------------------------------

ifeq ($(strip $(DEVKITARM)),)
$(error "Please set DEVKITARM in your environment. export DEVKITARM=<path to>devkitARM")
endif

include $(DEVKITARM)/gba_rules

#---------------------------------------------------------------------------------
# TARGET is the name of the output
# BUILD is the directory where object files & intermediate files will be placed
# SOURCES is a list of directories containing source code
# INCLUDES is a list of directories containing extra header files
# DATA is a list of directories containing binary data
# GRAPHICS is a list of directories containing files to be processed by grit
#
# All directories are specified relative to the project directory where
# the makefile is found
#
#---------------------------------------------------------------------------------
TARGET		:= GBA_Video
BUILD		:= build
INCLUDES	:= include include/video
DATA		:= video
MUSIC		:=

# ---------------------------------------------------------------------------
# Detect AUDIO_FORMAT from the generated header so we only compile the
# source files that are actually needed for the selected audio codec.
#
#   AUDIO_FORMAT 0 → PCM   : sound.c only
#   AUDIO_FORMAT 1 → ADPCM : sound.c + adpcm_decoder.c + adpcm_decoder.iwram.c
# ---------------------------------------------------------------------------
# Only detect from the header in the top-level invocation; the sub-make
# inherits the exported value and skips re-detection.
ifndef AUDIO_FORMAT
  AUDIO_DATA_H := $(CURDIR)/include/video/audio_data.h
  AUDIO_FORMAT := $(shell grep -m1 'define AUDIO_FORMAT' $(AUDIO_DATA_H) 2>/dev/null | awk '{print $$3}')
  ifeq ($(AUDIO_FORMAT),)
    AUDIO_FORMAT := 0
  endif
endif

# Export so the recursive sub-make inherits the value
export AUDIO_FORMAT

# Base sources (always compiled)
SOURCES_BASE := src

# Per-format extra sources
ifeq ($(AUDIO_FORMAT),1)
  $(info Audio format: ADPCM (1))
else
  $(info Audio format: PCM (0))
endif

SOURCES := $(SOURCES_BASE)

#---------------------------------------------------------------------------------
# options for code generation
#---------------------------------------------------------------------------------
ARCH	:=

# Note: LTO (-flto) is disabled because it causes the linker to misplace
# the ewram section into IWRAM when using devkitARM's gba_cart.ld.
CFLAGS	:=	-g -Wall -O2 \
		-mcpu=arm7tdmi -mtune=arm7tdmi \
		$(ARCH)

CFLAGS	+=	$(INCLUDE)

CXXFLAGS	:=	$(CFLAGS)

ASFLAGS	:=	-g $(ARCH)
LDFLAGS	=	-g $(ARCH) -Wl,-Map,$(notdir $*.map)

#---------------------------------------------------------------------------------
# Libraries
# libagbsyscall: pokeemerald-compatible BIOS syscall stubs (VBlankIntrWait etc.)
# libgba: devkitARM startup/crt0 and linker script support
#---------------------------------------------------------------------------------
LIBS	:= -lagbsyscall -lgba
LIBDIRS	:=	$(LIBGBA)

#---------------------------------------------------------------------------------
# Extra library search path for libagbsyscall
#---------------------------------------------------------------------------------
LIBPATHS_EXTRA := -L$(CURDIR)/libagbsyscall

#---------------------------------------------------------------------------------
# no real need to edit anything past this point unless you need to add additional
# rules for different file extensions
#---------------------------------------------------------------------------------


ifneq ($(BUILD),$(notdir $(CURDIR)))
#---------------------------------------------------------------------------------

export OUTPUT	:=	$(CURDIR)/$(TARGET)

export VPATH	:=	$(foreach dir,$(SOURCES),$(CURDIR)/$(dir)) \
			$(foreach dir,$(DATA),$(CURDIR)/$(dir)) \
			$(foreach dir,$(GRAPHICS),$(CURDIR)/$(dir))

export DEPSDIR	:=	$(CURDIR)/$(BUILD)

CFILES		:=	$(foreach dir,$(SOURCES),$(notdir $(wildcard $(dir)/*.c)))
CPPFILES	:=	$(foreach dir,$(SOURCES),$(notdir $(wildcard $(dir)/*.cpp)))
SFILES		:=	$(foreach dir,$(SOURCES),$(notdir $(wildcard $(dir)/*.s)))
BINFILES	:=	$(foreach dir,$(DATA),$(notdir $(wildcard $(dir)/*.*)))

# ---------------------------------------------------------------------------
# Filter audio-specific source files based on AUDIO_FORMAT.
# adpcm_decoder files live in src/ so the wildcard picks them up always;
# remove them when not needed.
# ---------------------------------------------------------------------------
ADPCM_CFILES := adpcm_decoder.c adpcm_decoder.iwram.c

ifeq ($(AUDIO_FORMAT),1)
  # ADPCM: keep adpcm files
else
  # PCM: remove adpcm files
  CFILES := $(filter-out $(ADPCM_CFILES),$(CFILES))
endif

ifneq ($(strip $(MUSIC)),)
	export AUDIOFILES	:=	$(foreach dir,$(notdir $(wildcard $(MUSIC)/*.*)),$(CURDIR)/$(MUSIC)/$(dir))
	BINFILES += soundbank.bin
endif

#---------------------------------------------------------------------------------
# use CXX for linking C++ projects, CC for standard C
#---------------------------------------------------------------------------------
ifeq ($(strip $(CPPFILES)),)
#---------------------------------------------------------------------------------
	export LD	:=	$(CC)
#---------------------------------------------------------------------------------
else
#---------------------------------------------------------------------------------
	export LD	:=	$(CXX)
#---------------------------------------------------------------------------------
endif
#---------------------------------------------------------------------------------

export OFILES_BIN := $(addsuffix .o,$(BINFILES))

export OFILES_SOURCES := $(CPPFILES:.cpp=.o) $(CFILES:.c=.o) $(SFILES:.s=.o)

export OFILES := $(OFILES_BIN) $(OFILES_SOURCES)

export HFILES := $(addsuffix .h,$(subst .,_,$(BINFILES)))

export INCLUDE	:=	$(foreach dir,$(INCLUDES),-iquote $(CURDIR)/$(dir)) \
					$(foreach dir,$(LIBDIRS),-I$(dir)/include) \
					-I$(CURDIR)/$(BUILD)

export LIBPATHS	:=	$(foreach dir,$(LIBDIRS),-L$(dir)/lib) $(LIBPATHS_EXTRA)

.PHONY: $(BUILD) clean

#---------------------------------------------------------------------------------
$(BUILD):
	@[ -d $@ ] || mkdir -p $@
	@$(MAKE) --no-print-directory -C $(BUILD) -f $(CURDIR)/Makefile

#---------------------------------------------------------------------------------
clean:
	@echo clean ...
	@rm -fr $(BUILD) $(TARGET).elf $(TARGET).gba
	@rm -f video/*.*
	@rm -f temp/*.*
	@rm -f include/video/audio_data.h \
	       include/video/video_data.h
	@rm -fr output/
	@echo output/ cleaned


#---------------------------------------------------------------------------------
else

#---------------------------------------------------------------------------------
# main targets
#---------------------------------------------------------------------------------

$(OUTPUT).gba	:	$(OUTPUT).elf

# Override the default %.elf rule from gba_rules to add --print-memory-usage
# and display a formatted memory usage report after linking.
$(OUTPUT).elf	:	$(OFILES)
	@echo linking cartridge
	@$(LD) $(LDFLAGS) -specs=gba.specs $(OFILES) $(LIBPATHS) $(LIBS) -o $@ \
		-Wl,--print-memory-usage > $(DEPSDIR)/memuse.txt 2>&1 \
		&& awk ' \
		/^Memory region/ { \
			printf "\n  %-8s  %14s  %12s  %s\n", "Region", "Used", "Total", "Used%"; \
			printf "  %-8s  %14s  %12s  %s\n",   "--------","-------------- ","------------","------"; \
			next \
		} \
		/rom:|ewram:|iwram:/ { \
			region=$$1; used=$$2; uunit=$$3; size=$$4; sunit=$$5; pct=$$6; \
			gsub(/%/,"",pct); gsub(/:/,"",region); \
			if (uunit == "KB") used = used * 1024; \
			else if (uunit == "MB") used = used * 1024 * 1024; \
			uunit = "B"; \
			if (region == "rom")        { color="\033[0;36m"; REGION="ROM";   } \
			else if (region == "ewram") { color="\033[0;33m"; REGION="EWRAM"; } \
			else                        { color="\033[0;32m"; REGION="IWRAM"; } \
			printf "  " color "%-8s  %10s %-3s  %8s %-3s  %5s%%\033[0m\n", \
				REGION, used, uunit, size, sunit, pct \
		} \
		END { printf "\n" } \
		' $(DEPSDIR)/memuse.txt \
		|| { cat $(DEPSDIR)/memuse.txt; exit 1; }

$(OFILES_SOURCES) : $(HFILES)

#---------------------------------------------------------------------------------
# The bin2o rule should be copied and modified
# for each extension used in the data directories
#---------------------------------------------------------------------------------

#---------------------------------------------------------------------------------
# rule to build soundbank from music files
#---------------------------------------------------------------------------------
soundbank.bin soundbank.h : $(AUDIOFILES)
#---------------------------------------------------------------------------------
	@mmutil $^ -osoundbank.bin -hsoundbank.h

#---------------------------------------------------------------------------------
# This rule links in binary data with the .bin extension
#---------------------------------------------------------------------------------
%.bin.o	%_bin.h :	%.bin
#---------------------------------------------------------------------------------
	@echo $(notdir $<)
	@$(bin2o)


-include $(DEPSDIR)/*.d
#---------------------------------------------------------------------------------------
endif
#---------------------------------------------------------------------------------------
