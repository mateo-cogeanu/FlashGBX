# -*- coding: utf-8 -*-
"""Modern, play-first shell for FlashGBX.

This file intentionally contains no Epilogue artwork or proprietary assets.  It
implements the same kind of calm, cartridge-first information hierarchy while
leaving FlashGBX's device and transfer widgets untouched on the Data page.
"""

import hashlib
import os
import threading

import requests

from .pyside import QtCore, QtWidgets, QtGui
from .app import AppContext
from .CartridgePresentation import authenticity_assessment, box_art_url


class _ArtworkSignals(QtCore.QObject):
	loaded = QtCore.Signal(str, bytes)


class PlaybackShell(QtWidgets.QWidget):
	"""A navigation shell with a welcoming Play page and the original Data UI."""

	def __init__(self, host, data_page):
		super().__init__()
		self.host = host
		self._cover_key = None
		self._art_signals = _ArtworkSignals()
		self._art_signals.loaded.connect(self._apply_cover_art)
		self.setObjectName("playbackShell")
		self.setMinimumSize(940, 620)

		root = QtWidgets.QHBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._build_sidebar())

		self.pages = QtWidgets.QStackedWidget()
		self.pages.setObjectName("pages")
		self.play_page = self._build_play_page()
		self.pages.addWidget(self.play_page)
		self.pages.addWidget(data_page)
		root.addWidget(self.pages, 1)

		self._select_page(0)
		self.setStyleSheet(STYLESHEET)
		self.update_cartridge()

	def _build_sidebar(self):
		bar = QtWidgets.QFrame()
		bar.setObjectName("sidebar")
		bar.setFixedWidth(184)
		layout = QtWidgets.QVBoxLayout(bar)
		layout.setContentsMargins(22, 28, 22, 24)
		layout.setSpacing(10)

		brand = QtWidgets.QLabel("CARTRIDGE")
		brand.setObjectName("brand")
		brand_accent = QtWidgets.QLabel("PLAY")
		brand_accent.setObjectName("brandAccent")
		layout.addWidget(brand)
		layout.addWidget(brand_accent)
		layout.addSpacing(34)

		self.play_nav = self._nav_button("▶   Play", 0)
		self.data_nav = self._nav_button("▤   Data", 1)
		layout.addWidget(self.play_nav)
		layout.addWidget(self.data_nav)
		layout.addStretch()

		caption = QtWidgets.QLabel("Powered by\nFlashGBX")
		caption.setObjectName("sidebarCaption")
		layout.addWidget(caption)
		return bar

	def _nav_button(self, text, index):
		button = QtWidgets.QPushButton(text)
		button.setObjectName("navButton")
		button.setCheckable(True)
		button.setCursor(QtCore.Qt.PointingHandCursor)
		button.clicked.connect(lambda _checked=False, i=index: self._select_page(i))
		return button

	def _build_play_page(self):
		page = QtWidgets.QWidget()
		page.setObjectName("playPage")
		outer = QtWidgets.QVBoxLayout(page)
		outer.setContentsMargins(48, 40, 48, 38)
		outer.setSpacing(20)

		eyebrow = QtWidgets.QLabel("YOUR CARTRIDGE, READY TO PLAY")
		eyebrow.setObjectName("eyebrow")
		outer.addWidget(eyebrow)

		card = QtWidgets.QFrame()
		card.setObjectName("gameCard")
		card_layout = QtWidgets.QHBoxLayout(card)
		card_layout.setContentsMargins(40, 36, 40, 36)
		card_layout.setSpacing(46)

		art = QtWidgets.QFrame()
		art.setObjectName("cartridgeArt")
		art.setFixedSize(236, 292)
		art_layout = QtWidgets.QVBoxLayout(art)
		art_layout.setContentsMargins(24, 32, 24, 24)
		self.cartridge_label = QtWidgets.QLabel("GB")
		self.cartridge_label.setAlignment(QtCore.Qt.AlignCenter)
		self.cartridge_label.setObjectName("cartridgeLabel")
		art_layout.addWidget(self.cartridge_label, 1)
		groove = QtWidgets.QFrame()
		groove.setObjectName("cartridgeGroove")
		groove.setFixedHeight(8)
		art_layout.addWidget(groove)
		card_layout.addWidget(art, 0, QtCore.Qt.AlignVCenter)

		copy = QtWidgets.QVBoxLayout()
		copy.setSpacing(12)
		self.state_label = QtWidgets.QLabel("WAITING FOR CARTRIDGE")
		self.state_label.setObjectName("stateLabel")
		self.title_label = QtWidgets.QLabel("Insert a Game Boy cartridge")
		self.title_label.setWordWrap(True)
		self.title_label.setObjectName("gameTitle")
		self.subtitle_label = QtWidgets.QLabel("Connect a supported reader and your game will appear here.")
		self.subtitle_label.setWordWrap(True)
		self.subtitle_label.setObjectName("subtitle")
		copy.addStretch()
		copy.addWidget(self.state_label)
		copy.addWidget(self.title_label)
		copy.addWidget(self.subtitle_label)
		copy.addSpacing(8)

		meta = QtWidgets.QHBoxLayout()
		meta.setSpacing(8)
		self.platform_chip = QtWidgets.QLabel("GAME BOY")
		self.platform_chip.setObjectName("chip")
		self.device_chip = QtWidgets.QLabel("NO READER")
		self.device_chip.setObjectName("chipMuted")
		meta.addWidget(self.platform_chip)
		meta.addWidget(self.device_chip)
		meta.addStretch()
		copy.addLayout(meta)
		copy.addSpacing(4)

		auth = QtWidgets.QFrame()
		auth.setObjectName("authCard")
		auth_layout = QtWidgets.QVBoxLayout(auth)
		auth_layout.setContentsMargins(14, 11, 14, 11)
		auth_layout.setSpacing(4)
		auth_top = QtWidgets.QHBoxLayout()
		self.auth_label = QtWidgets.QLabel("Not checked")
		self.auth_label.setObjectName("authUnknown")
		self.auth_button = QtWidgets.QPushButton("Run full check")
		self.auth_button.setObjectName("authButton")
		self.auth_button.clicked.connect(lambda _checked=False: self.host.CheckAuthenticity())
		auth_top.addWidget(self.auth_label)
		auth_top.addStretch()
		auth_top.addWidget(self.auth_button)
		self.auth_detail = QtWidgets.QLabel("Identify the cartridge to check its data.")
		self.auth_detail.setObjectName("authDetail")
		self.auth_detail.setWordWrap(True)
		auth_layout.addLayout(auth_top)
		auth_layout.addWidget(self.auth_detail)
		copy.addWidget(auth)
		copy.addSpacing(8)

		self.play_button = QtWidgets.QPushButton("Play cartridge  →")
		self.play_button.setObjectName("playButton")
		self.play_button.setMinimumHeight(56)
		self.play_button.setCursor(QtCore.Qt.PointingHandCursor)
		self.play_button.clicked.connect(self._primary_action)
		self.play_button.setEnabled(False)
		copy.addWidget(self.play_button)

		self.refresh_button = QtWidgets.QPushButton("Refresh cartridge")
		self.refresh_button.setObjectName("quietButton")
		self.refresh_button.setCursor(QtCore.Qt.PointingHandCursor)
		# clicked(bool) must not feed False into ReadCartridge(resetStatus=True).
		self.refresh_button.clicked.connect(lambda _checked=False: self._refresh_action())
		copy.addWidget(self.refresh_button)
		copy.addStretch()
		card_layout.addLayout(copy, 1)
		outer.addWidget(card, 1)

		self.hint_label = QtWidgets.QLabel("ROM and save tools live in Data. Nothing is written to a cartridge while playing.")
		self.hint_label.setObjectName("hint")
		self.hint_label.setAlignment(QtCore.Qt.AlignCenter)
		outer.addWidget(self.hint_label)
		return page

	def _select_page(self, index):
		self.pages.setCurrentIndex(index)
		self.play_nav.setChecked(index == 0)
		self.data_nav.setChecked(index == 1)

	def _primary_action(self):
		if getattr(self.host, "CONN", None) is None:
			self.host.STATUS["autoplay_after_connect"] = True
			self.host.ConnectDevice()
			if getattr(self.host, "CONN", None) is not None and self.host.CONN.GetMode() not in ("DMG", "AGB"):
				self.host.SelectPlatformForPlay(auto_play=True)
		elif self.host.CONN.GetMode() not in ("DMG", "AGB"):
			self.host.SelectPlatformForPlay(auto_play=True)
		elif not self.host.CONN.INFO or self.host.CONN.INFO.get("empty", True):
			self.host.STATUS["autoplay_after_refresh"] = True
			self.host.ReadCartridge()
		else:
			self.host.PlayCartridge()

	def _refresh_action(self):
		if getattr(self.host, "CONN", None) is None:
			self.host.ConnectDevice()
		elif self.host.CONN.GetMode() not in ("DMG", "AGB"):
			self.host.SelectPlatformForPlay(auto_play=False)
		else:
			self.host.ReadCartridge()

	def show_data(self):
		self._select_page(1)

	def update_cartridge(self, info=None, mode=None, device_name=None):
		info = info or {}
		empty = bool(info.get("empty", True))
		connected = bool(device_name)
		if mode == "AGB":
			self.platform_chip.setText("GAME BOY ADVANCE")
		else:
			self.platform_chip.setText("GAME BOY / COLOR")
		self.device_chip.setText(device_name.upper() if connected else "NO READER")

		if not connected:
			self._reset_cover_art()
			self._update_authenticity({})
			self.state_label.setText("READER DISCONNECTED")
			self.title_label.setText("Connect your cartridge reader")
			self.subtitle_label.setText("FlashGBX supports GBxCart RW, GBFlash, Joey Jr and Game Bub.")
			self.play_button.setText("Connect reader and play  →")
			self.play_button.setEnabled(True)
			return
		if mode not in ("DMG", "AGB"):
			self._reset_cover_art()
			self._update_authenticity({})
			self.state_label.setText("READER CONNECTED")
			self.title_label.setText("Choose your cartridge platform")
			self.subtitle_label.setText("Select Game Boy / Color or Game Boy Advance so the reader uses the correct voltage.")
			self.platform_chip.setText("PLATFORM REQUIRED")
			self.play_button.setText("Choose platform and play  →")
			self.play_button.setEnabled(True)
			return
		if empty:
			self._reset_cover_art()
			self._update_authenticity({})
			self.state_label.setText("WAITING FOR CARTRIDGE")
			self.title_label.setText("Insert a Game Boy cartridge")
			self.subtitle_label.setText("Then refresh once if your reader does not detect hot-swaps automatically.")
			self.play_button.setText("Detect cartridge  →")
			self.play_button.setEnabled(True)
			return

		db = info.get("db") if isinstance(info.get("db"), dict) else {}
		title = db.get("gn") or info.get("game_title") or "Unknown cartridge"
		code = db.get("gc") or info.get("game_code") or ""
		self.state_label.setText("CARTRIDGE READY")
		self.title_label.setText(str(title).strip())
		self.subtitle_label.setText(("Game code " + str(code)) if code else "Header read successfully. Ready for a temporary verified dump.")
		self.play_button.setText("Play cartridge  →")
		self.play_button.setEnabled(True)
		self._update_authenticity(info)
		self._load_cover_art(info, mode)

	def set_busy(self, busy, text=None):
		self.play_button.setEnabled(not busy)
		self.play_button.setText(text or ("Preparing game…" if busy else "Play cartridge  →"))

	def set_auth_busy(self, busy):
		self.auth_button.setEnabled(not busy)
		self.auth_button.setText("Checking full ROM…" if busy else "Run full check")

	def _update_authenticity(self, info):
		assessment = authenticity_assessment(info)
		self.auth_label.setText(assessment["label"])
		self.auth_label.setObjectName("auth{:s}".format(assessment["level"].title()))
		self.auth_label.style().unpolish(self.auth_label)
		self.auth_label.style().polish(self.auth_label)
		self.auth_detail.setText(assessment["detail"])
		ready = bool(info) and not info.get("empty", True)
		self.auth_button.setEnabled(ready)
		self.auth_button.setText("Re-check full ROM" if "file_crc32" in (info or {}) else "Run full check")

	def _reset_cover_art(self):
		self._cover_key = None
		self.cartridge_label.setPixmap(QtGui.QPixmap())
		self.cartridge_label.setText("GB")
		self.cartridge_label.setStyleSheet("")

	def _load_cover_art(self, info, mode):
		url = box_art_url(info, mode)
		if not url:
			self._reset_cover_art()
			return
		key = hashlib.sha1(url.encode("utf-8")).hexdigest()
		if key == self._cover_key:
			return
		self._cover_key = key
		cache_dir = os.path.join(AppContext.CONFIG_PATH, "cover-cache")
		cache_path = os.path.join(cache_dir, key + ".png")

		def load():
			try:
				if os.path.isfile(cache_path):
					with open(cache_path, "rb") as cover_file:
						data = cover_file.read()
				else:
					response = requests.get(url, timeout=12, headers={"User-Agent":"CartridgePlay/1.0"})
					if response.status_code != 200 or "image" not in response.headers.get("Content-Type", ""):
						return
					data = response.content
					os.makedirs(cache_dir, exist_ok=True)
					with open(cache_path, "wb") as cover_file:
						cover_file.write(data)
				self._art_signals.loaded.emit(key, data)
			except (OSError, requests.RequestException):
				return

		threading.Thread(target=load, daemon=True).start()

	def _apply_cover_art(self, key, data):
		if key != self._cover_key:
			return
		pixmap = QtGui.QPixmap()
		if not pixmap.loadFromData(data):
			return
		pixmap = pixmap.scaled(188, 232, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
		self.cartridge_label.setText("")
		self.cartridge_label.setStyleSheet("background:#0f1116; border:0; border-radius:9px;")
		self.cartridge_label.setPixmap(pixmap)


STYLESHEET = """
#playbackShell { background: #0d0f13; color: #f4f2ed; }
#sidebar { background: #11141a; border-right: 1px solid #242932; }
#brand, #brandAccent { color: #f4f2ed; font-size: 18px; font-weight: 800; letter-spacing: 2px; }
#brandAccent { color: #ff6b47; }
#sidebarCaption { color: #68707d; font-size: 11px; line-height: 1.4; }
QPushButton#navButton { color: #858d99; text-align: left; border: 0; border-radius: 10px; padding: 13px 14px; font-size: 14px; font-weight: 600; }
QPushButton#navButton:hover { background: #191d25; color: #f4f2ed; }
QPushButton#navButton:checked { background: #232832; color: #ffffff; }
#pages, #playPage { background: #0d0f13; }
#eyebrow, #stateLabel { color: #ff7656; font-size: 11px; font-weight: 800; letter-spacing: 2px; }
#gameCard { background: #15181e; border: 1px solid #292e37; border-radius: 22px; }
#cartridgeArt { background: #d8d6cf; border: 1px solid #efeee9; border-radius: 16px 16px 28px 16px; }
#cartridgeLabel { color: #242830; background: #f3f0e8; border: 1px solid #c3c1bb; border-radius: 9px; font-size: 38px; font-weight: 900; letter-spacing: -2px; }
#cartridgeGroove { background: #b5b3ac; border-radius: 4px; }
#gameTitle { color: #ffffff; font-size: 34px; font-weight: 750; }
#subtitle { color: #9ca3ae; font-size: 14px; line-height: 1.4; }
#chip, #chipMuted { background: #262b33; color: #d9dde3; border-radius: 10px; padding: 7px 10px; font-size: 10px; font-weight: 700; }
#chipMuted { color: #858d99; }
#authCard { background: #1c2027; border: 1px solid #303640; border-radius: 10px; }
#authUnknown, #authKnown, #authWarning, #authDanger, #authVerified { font-size: 11px; font-weight: 800; }
#authUnknown { color: #8d95a1; }
#authKnown { color: #73a8ff; }
#authWarning { color: #f1b85b; }
#authDanger { color: #ff6b62; }
#authVerified { color: #69d49a; }
#authDetail { color: #89919c; font-size: 10px; }
QPushButton#authButton { color: #d5d9df; background: transparent; border: 0; min-height: 18px; font-size: 10px; font-weight: 700; }
QPushButton#authButton:hover { color: #ffffff; }
QPushButton#playButton { background: #ff6b47; color: #15120f; border: 0; border-radius: 12px; padding: 0 20px; font-size: 15px; font-weight: 800; text-align: left; }
QPushButton#playButton:hover { background: #ff805f; }
QPushButton#playButton:disabled { background: #333740; color: #747b86; }
QPushButton#quietButton { background: transparent; color: #8e96a2; border: 0; padding: 8px; }
QPushButton#quietButton:hover { color: #ffffff; }
#hint { color: #6e7580; font-size: 11px; }
QGroupBox { border: 1px solid #343943; border-radius: 8px; margin-top: 12px; padding-top: 8px; font-weight: 600; }
QGroupBox::title { color: #c9cdd3; subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton { min-height: 26px; }
"""
