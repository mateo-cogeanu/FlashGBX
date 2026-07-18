# -*- coding: utf-8 -*-
"""Cartridge identity, authenticity evidence, and box-art lookup helpers."""

from urllib.parse import quote


def authenticity_assessment(info):
	"""Return a conservative digital-authenticity assessment.

	This can verify cartridge data, not the physical PCB or shell. A sophisticated
	reproduction can contain a byte-perfect copy of an official ROM.
	"""
	info = info or {}
	if not info or info.get("empty", True):
		return {"level":"unknown", "label":"Not checked", "detail":"Insert and identify a cartridge first."}

	failed = []
	if info.get("logo_correct") is False:
		failed.append("Nintendo logo")
	if info.get("header_checksum_correct") is False:
		failed.append("header checksum")
	if failed:
		return {
			"level":"danger",
			"label":"Suspicious data",
			"detail":"Failed: {:s}. Clean the contacts and read again before judging the cartridge.".format(", ".join(failed)),
		}

	db = info.get("db") if isinstance(info.get("db"), dict) else None
	if db is None:
		return {
			"level":"warning",
			"label":"Inconclusive",
			"detail":"The header is internally valid but is not in FlashGBX’s known-release database.",
		}

	if "file_crc32" in info and "rc" in db:
		if int(info["file_crc32"]) == int(db["rc"]):
			return {
				"level":"verified",
				"label":"Likely authentic",
				"detail":"Full ROM data exactly matches a known release. Physical PCB inspection is still required for certainty.",
			}
		return {
			"level":"danger",
			"label":"ROM mismatch",
			"detail":"The full cartridge dump does not match the known release CRC. This may be a repro, modification, or bad read.",
		}

	return {
		"level":"known",
		"label":"Known release",
		"detail":"Logo, header checksum, and header fingerprint match the database. Run the full check for stronger evidence.",
	}


def box_art_url(info, mode):
	"""Build the Libretro Named_Boxarts URL for a FlashGBX database entry."""
	info = info or {}
	db = info.get("db") if isinstance(info.get("db"), dict) else None
	if db is None or not db.get("gn"):
		return None
	if mode == "AGB":
		system = "Nintendo - Game Boy Advance"
	elif info.get("cgb") in (0x80, 0xC0) or str(db.get("gc", "")).startswith("CGB-"):
		system = "Nintendo - Game Boy Color"
	else:
		system = "Nintendo - Game Boy"
	name = "{:s} {:s}.png".format(str(db["gn"]).strip(), str(db.get("ne", "")).strip()).replace("  ", " ")
	return "https://thumbnails.libretro.com/{:s}/Named_Boxarts/{:s}".format(quote(system, safe=""), quote(name, safe=""))
