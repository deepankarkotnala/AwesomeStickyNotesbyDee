#!/usr/bin/env python3
"""Build "Awesome Sticky Notes.app" from this folder, zipped up to copy to a Mac.

Run it after updating the code here (stickynotes/, AwesomeStickyNotes.py, requirements.txt), with any Python 3
and no extra libraries, on Windows or on a Mac:

    python build-app.py

It writes "Awesome Sticky Notes.zip". Copy that zip to the Mac and double-click it to get the app: the zip
keeps the app's launcher marked as a program, which copying the app folder from Windows would lose.
On a Mac it also leaves "Awesome Sticky Notes.app" next to this file, ready to open.
"""
from __future__ import annotations

import os
import plistlib
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "Awesome Sticky Notes"
EXECUTABLE = "AwesomeStickyNotes"                 # Contents/MacOS/<this>, from packaging/launcher.sh
BUNDLE_ID = "com.dee.awesomestickynotes"         # also in stickynotes/macutil.py
CODE = ("AwesomeStickyNotes.py", "requirements.txt", "stickynotes")
RUNNABLE = {f"Contents/MacOS/{EXECUTABLE}", "Contents/Resources/app/AwesomeStickyNotes.py"}


def version() -> str:
    text = (HERE / "stickynotes" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def build_app(target: Path) -> Path:
    """Lay out the app bundle inside `target`."""
    app = target / f"{NAME}.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    code = contents / "Resources" / "app"
    code.mkdir(parents=True)

    launcher = contents / "MacOS" / EXECUTABLE
    launcher.write_bytes((HERE / "packaging" / "launcher.sh").read_bytes().replace(b"\r\n", b"\n"))
    shutil.copy2(HERE / "packaging" / "AppIcon.icns", contents / "Resources" / "AppIcon.icns")
    skip = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    for name in CODE:
        source = HERE / name
        if source.is_dir():
            shutil.copytree(source, code / name, ignore=skip)
        else:
            shutil.copy2(source, code / name)
    for relative in RUNNABLE:
        os.chmod(app / relative, 0o755)

    v = version()
    with open(contents / "Info.plist", "wb") as fh:
        plistlib.dump({
            "CFBundleDevelopmentRegion": "en",
            "CFBundleDisplayName": NAME,
            "CFBundleName": NAME,
            "CFBundleExecutable": EXECUTABLE,
            "CFBundleIconFile": "AppIcon",
            "CFBundleIdentifier": BUNDLE_ID,
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": v,
            "CFBundleVersion": v,
            "LSApplicationCategoryType": "public.app-category.productivity",
            "LSMinimumSystemVersion": "13.0",
            "LSUIElement": True,                    # a menu-bar app: no Dock icon
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "Developed by Deepankar Kotnala",
        }, fh)
    (contents / "PkgInfo").write_text("APPL????", encoding="ascii")
    return app


def write_zip(app: Path, zip_path: Path) -> None:
    """Zip the app with Unix permissions, so the Mac's Archive Utility keeps the launcher runnable."""
    def entry(path: Path, arcname: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(arcname, time.localtime(path.stat().st_mtime)[:6])
        info.create_system = 3                     # Unix: the permission bits below are honoured
        if path.is_dir():
            info.external_attr = (0o040755 << 16) | 0x10
        else:
            runnable = path.relative_to(app).as_posix() in RUNNABLE
            info.external_attr = (0o100755 if runnable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
        return info

    tmp = zip_path.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w") as z:
        for path in [app, *sorted(app.rglob("*"))]:
            arcname = path.relative_to(app.parent).as_posix() + ("/" if path.is_dir() else "")
            z.writestr(entry(path, arcname), b"" if path.is_dir() else path.read_bytes())
    tmp.replace(zip_path)


def main() -> int:
    zip_path = HERE / f"{NAME}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        app = build_app(Path(tmp))
        write_zip(app, zip_path)
        if sys.platform == "darwin":               # on a Mac, also leave the app itself here
            final = HERE / app.name
            if final.exists():
                shutil.rmtree(final)
            shutil.copytree(app, final, symlinks=True)
            print(f"Built {final}")
    print(f"Built {zip_path} (version {version()}, {zip_path.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
