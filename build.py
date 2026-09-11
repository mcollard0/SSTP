#!/usr/bin/env python3
"""Cross-platform packaging and compilation script for Stuart Saves the Pomodoro (SSTP).

Supports Linux, Apple macOS, and Microsoft Windows using PyInstaller.
Produces compressed release packages (.tar.gz or .zip) inside dist/.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

# Add project root to sys.path so we can import sstp
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from sstp.const import VERSION


def ensure_icons():
    """Ensure Windows .ico exists, generating it from assets/icon.png if needed."""
    png_icon = ROOT_DIR / "assets" / "icon.png"
    ico_icon = ROOT_DIR / "assets" / "icon.ico"
    if png_icon.exists() and not ico_icon.exists():
        try:
            from PIL import Image

            img = Image.open(png_icon)
            img.save(
                ico_icon,
                format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            )
            print(f"[Build] Generated Windows icon at {ico_icon}")
        except Exception as e:
            print(f"[Build] Note: Could not generate .ico file ({e})")


def get_platform_info():
    system = sys.platform
    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64", "x64"):
        arch_tag = "x86_64" if system != "win32" else "x64"
    elif arch in ("arm64", "aarch64"):
        arch_tag = "arm64"
    else:
        arch_tag = arch

    if system == "linux":
        plat_tag = f"linux-{arch_tag}"
    elif system == "win32":
        plat_tag = f"windows-{arch_tag}"
    elif system == "darwin":
        plat_tag = f"macos-{arch_tag}"
    else:
        plat_tag = f"{system}-{arch_tag}"

    return system, plat_tag


def run_pyinstaller(onefile=False):
    """Executes PyInstaller with appropriate flags for the current platform."""
    ensure_icons()
    system, _ = get_platform_info()
    sep = os.pathsep  # ';' on Windows, ':' on POSIX

    app_name = "sstp"
    entry_point = str(ROOT_DIR / "sstp" / "__main__.py")
    assets_data = f"{ROOT_DIR / 'assets'}{sep}assets"
    outputs_data = f"{ROOT_DIR / 'outputs'}{sep}outputs"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        app_name,
        "--add-data",
        assets_data,
        "--add-data",
        outputs_data,
        "--hidden-import",
        "sstp",
        "--hidden-import",
        "sstp.app",
        "--hidden-import",
        "sstp.qt_app",
        "--hidden-import",
        "sstp.const",
        "--hidden-import",
        "sstp.config",
        "--hidden-import",
        "sstp.timer",
        "--hidden-import",
        "sstp.audio",
        "--hidden-import",
        "sstp.led_renderer",
        "--hidden-import",
        "sstp.settings_dialog",
        "--hidden-import",
        "sstp.qt_settings_dialog",
        "--hidden-import",
        "sstp.tray",
    ]

    # Mode
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Platform specific icon & imports
    if system == "win32":
        ico = ROOT_DIR / "assets" / "icon.ico"
        if ico.exists():
            cmd.extend(["--icon", str(ico)])
        cmd.extend(["--hidden-import", "winsound"])
    elif system == "darwin":
        png = ROOT_DIR / "assets" / "icon.png"
        if png.exists():
            cmd.extend(["--icon", str(png)])
        cmd.extend(["--osx-bundle-identifier", "com.sstp.pomodoro"])
    else:
        png = ROOT_DIR / "assets" / "icon.png"
        if png.exists():
            cmd.extend(["--icon", str(png)])
        cmd.extend(["--hidden-import", "cairo"])

    cmd.append(entry_point)

    print(f"[Build] Executing PyInstaller command:\n{' '.join(cmd)}\n")
    subprocess.run(cmd, check=True)


def create_release_archive(onefile=False):
    """Packages the compiled output in dist/ into a release archive."""
    system, plat_tag = get_platform_info()
    dist_dir = ROOT_DIR / "dist"
    archive_base_name = f"sstp-v{VERSION}-{plat_tag}"

    if system == "linux":
        archive_name = f"{archive_base_name}.tar.gz"
        archive_path = dist_dir / archive_name
        print(f"[Build] Creating Linux release archive: {archive_path}")

        with tarfile.open(archive_path, "w:gz") as tar:
            if onefile:
                bin_file = dist_dir / "sstp"
                if bin_file.exists():
                    tar.add(bin_file, arcname=f"sstp-v{VERSION}/sstp")
            else:
                bundle_dir = dist_dir / "sstp"
                if bundle_dir.exists():
                    tar.add(bundle_dir, arcname=f"sstp-v{VERSION}")

        # Also package README and LICENSE if desired
        print(f"[Build] Successfully created {archive_path} ({archive_path.stat().st_size} bytes)")
        return archive_path

    else:
        archive_name = f"{archive_base_name}.zip"
        archive_path = dist_dir / archive_name
        print(f"[Build] Creating release archive: {archive_path}")

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if system == "darwin" and (dist_dir / "sstp.app").exists():
                app_dir = dist_dir / "sstp.app"
                for root, _, files in os.walk(app_dir):
                    for file in files:
                        p = Path(root) / file
                        zf.write(p, p.relative_to(dist_dir))
            else:
                bundle_dir = dist_dir / "sstp"
                if bundle_dir.exists():
                    for root, _, files in os.walk(bundle_dir):
                        for file in files:
                            p = Path(root) / file
                            zf.write(p, p.relative_to(dist_dir))
                elif (dist_dir / "sstp.exe").exists():
                    zf.write(dist_dir / "sstp.exe", arcname="sstp.exe")

        print(f"[Build] Successfully created {archive_path} ({archive_path.stat().st_size} bytes)")
        return archive_path


def main():
    parser = argparse.ArgumentParser(description="Build and package SSTP desktop application.")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build a single standalone binary instead of directory bundle.",
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Skip compressing into .tar.gz / .zip after build.",
    )
    args = parser.parse_args()

    print(f"=== Stuart Saves the Pomodoro (SSTP) Builder v{VERSION} ===")
    run_pyinstaller(onefile=args.onefile)
    if not args.skip_archive:
        create_release_archive(onefile=args.onefile)
    print("=== Build and packaging completed successfully ===")


if __name__ == "__main__":
    main()
