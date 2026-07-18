# -*- coding: utf-8 -*-
"""Launch the bundled GBA Video Studio tool from FlashGBX."""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .pyside import QtCore, QtWidgets
from .app import AppContext, AppInfo


_REQUIRED_MODULES = (
	("cv2", "opencv-python>=4.5.0"),
	("numpy", "numpy>=1.20.0"),
	("numba", "numba>=0.55.0"),
	("scipy", "scipy>=1.7.0"),
	("sklearn", "scikit-learn>=1.0.0"),
	("pydub", "pydub>=0.25.0"),
	("imageio_ffmpeg", "imageio-ffmpeg>=0.4.9"),
)


def _missing_packages():
	packages = []
	for module, package in _REQUIRED_MODULES:
		if importlib.util.find_spec(module) is None:
			packages.append(package)
	if sys.version_info >= (3, 13) and importlib.util.find_spec("audioop") is None:
		packages.append("audioop-lts")
	return packages


def _source_path():
	candidates = (
		Path(AppContext.APP_PATH) / "res" / "gba_video_studio",
		Path(__file__).resolve().parent / "res" / "gba_video_studio",
	)
	for candidate in candidates:
		if (candidate / "main.py").is_file():
			return candidate
	raise FileNotFoundError("The bundled GBA Video Studio files could not be found.")


def _prepare_runtime():
	"""Copy the read-only bundled project to a user-writable build directory."""
	source = _source_path()
	runtime = Path(AppContext.CONFIG_PATH) / "gba_video_studio"
	runtime.mkdir(parents=True, exist_ok=True)
	for item in source.iterdir():
		destination = runtime / item.name
		if item.is_dir():
			shutil.copytree(str(item), str(destination), dirs_exist_ok=True)
		else:
			shutil.copy2(str(item), str(destination))
	return runtime


def _start(host):
	try:
		runtime = _prepare_runtime()
		env = os.environ.copy()
		env["FLASHGBX_VIDEO_STUDIO"] = "1"
		creation_flags = 0x08000000 if sys.platform == "win32" else 0
		host.VIDEOSTUDIOPROC = subprocess.Popen(
			[sys.executable, str(runtime / "main.py"), "--gui"],
			cwd=str(runtime),
			env=env,
			creationflags=creation_flags,
		)
	except Exception as error:
		QtWidgets.QMessageBox.critical(
			host,
			"{:s} {:s}".format(AppInfo.NAME, AppInfo.VERSION),
			"GBA Video Maker could not be started.\n\n{:s}".format(str(error)),
			QtWidgets.QMessageBox.Ok,
		)


def _install_dependencies(host, packages):
	dialog = QtWidgets.QProgressDialog(
		"Installing the GBA video encoder…", "Cancel", 0, 0, host
	)
	dialog.setWindowTitle("GBA Video Maker")
	dialog.setWindowModality(QtCore.Qt.WindowModal)
	dialog.setMinimumDuration(0)
	dialog.setAutoClose(False)
	dialog.setAutoReset(False)

	process = QtCore.QProcess(host)
	process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
	host._videoStudioInstaller = process
	host._videoStudioInstallDialog = dialog

	def finished(exit_code, _exit_status):
		dialog.close()
		output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
		if exit_code == 0:
			QtWidgets.QMessageBox.information(
				host, "GBA Video Maker", "Video encoder components are installed.",
				QtWidgets.QMessageBox.Ok,
			)
			_start(host)
		else:
			QtWidgets.QMessageBox.critical(
				host, "GBA Video Maker",
				"The video components could not be installed.\n\n{:s}".format(output[-3000:]),
				QtWidgets.QMessageBox.Ok,
			)

	dialog.canceled.connect(process.kill)
	process.finished.connect(finished)
	process.start(sys.executable, ["-m", "pip", "install"] + list(packages))
	dialog.show()


def launch_video_studio(host):
	"""Open GBA Video Maker, offering to install its optional dependencies."""
	process = getattr(host, "VIDEOSTUDIOPROC", None)
	if process is not None and process.poll() is None:
		QtWidgets.QMessageBox.information(
			host, "GBA Video Maker", "GBA Video Maker is already open.",
			QtWidgets.QMessageBox.Ok,
		)
		return

	packages = _missing_packages()
	if packages:
		message = (
			"GBA Video Maker needs additional video-encoding components. "
			"They are only used by this tool.\n\nInstall them now?"
		)
		answer = QtWidgets.QMessageBox.question(
			host, "GBA Video Maker", message,
			QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
			QtWidgets.QMessageBox.Yes,
		)
		if answer == QtWidgets.QMessageBox.Yes:
			_install_dependencies(host, packages)
		return

	_start(host)
