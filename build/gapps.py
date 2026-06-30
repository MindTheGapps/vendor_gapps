#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ANDROIDV, SDKV = ("17.0.0", 37)
GARCH = sys.argv[1]
CPUARCH = sys.argv[2] if len(sys.argv) > 2 else GARCH

GAPPS_TOP = Path(__file__).resolve().parents[1]

GAPPS_BUILD = GAPPS_TOP / "build"
GAPPS_BUILD_APKTOOL = GAPPS_BUILD / "apktool" / "apktool_3.0.2.jar"
GAPPS_BUILD_META = GAPPS_BUILD / "meta"
GAPPS_BUILD_SIGN = GAPPS_BUILD / "sign"
GAPPS_BUILD_SIGN_APKSIGNER = GAPPS_BUILD_SIGN / "apksigner.jar"
GAPPS_BUILD_SIGN_SIGNAPK = GAPPS_BUILD_SIGN / "signapk.jar"
GAPPS_BUILD_SIGN_TESTKEY = GAPPS_BUILD_SIGN / "testkey"

GAPPS_OUT = GAPPS_TOP / "out"
GAPPS_OUT_GARCH = GAPPS_OUT / GARCH
GAPPS_OUT_GARCH_METAINF = GAPPS_OUT_GARCH / "META-INF"
GAPPS_OUT_GARCH_SYSTEM = GAPPS_OUT_GARCH / "system"
GAPPS_OUT_GARCH_SYSTEM_ADDOND = GAPPS_OUT_GARCH_SYSTEM / "addon.d"
GAPPS_OUT_ZIP_BASENAME = (
    GAPPS_OUT
    / f"MindTheGapps-{ANDROIDV}-{GARCH}-{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}"
)
GAPPS_OUT_ZIP_BASENAME_UNSIGNED = Path(f"{GAPPS_OUT_ZIP_BASENAME}-unsigned")
GAPPS_OUT_ZIP_FILENAME = Path(f"{GAPPS_OUT_ZIP_BASENAME}.zip")
GAPPS_OUT_ZIP_FILENAME_UNSIGNED = Path(f"{GAPPS_OUT_ZIP_BASENAME_UNSIGNED}.zip")

GAPPS_OVERLAY = GAPPS_TOP / "overlay"

PROPRIETARY_COMMON = GAPPS_TOP / "common" / "proprietary"
PROPRIETARY_GARCH = GAPPS_TOP / GARCH / "proprietary"


def run_command(*args, **kwargs) -> subprocess.CompletedProcess:
    ret = subprocess.run(*args, **kwargs)

    if ret.returncode != 0:
        cmd = " ".join([str(x) for x in ret.args])
        s = f'Failed to run command "{cmd}":\n'
        s += f"stdout:\n{ret.stdout}\n"
        s += f"stderr:\n{ret.stderr}\n"
        raise ValueError(s)

    return ret


def build() -> None:
    # Build overlays
    for overlay in GAPPS_OVERLAY.iterdir():
        if not overlay.is_dir():
            continue

        with open(overlay / "Android.bp") as f:
            for line in f.readlines():
                if line.endswith("_specific: true\n"):
                    partition, _ = line.strip().split("_specific: true")

        overlay_target_dir = GAPPS_OUT_GARCH_SYSTEM / partition / "overlay"
        overlay_target_dir.mkdir(parents=True, exist_ok=True)

        overlay_target = overlay_target_dir / f"{overlay.name}.apk"

        # Compile overlay resources
        run_command(
            [
                "java",
                "-Xmx2048m",
                "-jar",
                GAPPS_BUILD_APKTOOL,
                "b",
                overlay,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Create overlay apk manually to avoid funny issues
        with zipfile.ZipFile(overlay_target, "w") as z:
            for src, filename, compress_type in [
                (
                    overlay / "build/apk/resources.arsc",
                    "resources.arsc",
                    zipfile.ZIP_STORED,
                ),
                (
                    overlay / "build/apk/AndroidManifest.xml",
                    "AndroidManifest.xml",
                    zipfile.ZIP_DEFLATED,
                ),
            ]:
                info = zipfile.ZipInfo(filename, (2009, 1, 1, 0, 0, 0))
                info.compress_type = compress_type

                with open(src, "rb") as f:
                    z.writestr(info, f.read())

        # Sign overlay apk
        run_command(
            [
                "java",
                "-Xmx2048m",
                "-jar",
                GAPPS_BUILD_SIGN_APKSIGNER,
                "sign",
                "--key",
                f"{GAPPS_BUILD_SIGN_TESTKEY}.pk8",
                "--cert",
                f"{GAPPS_BUILD_SIGN_TESTKEY}.x509.pem",
                overlay_target,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        os.remove(f"{overlay_target}.idsig")

    # Copy addon.d scripts
    GAPPS_OUT_GARCH_SYSTEM_ADDOND.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GAPPS_TOP / "addond_head", GAPPS_OUT_GARCH_SYSTEM_ADDOND)
    shutil.copy2(GAPPS_TOP / "addond_tail", GAPPS_OUT_GARCH_SYSTEM_ADDOND)

    # Copy META-INF
    shutil.copytree(GAPPS_BUILD_META, GAPPS_OUT_GARCH_METAINF, dirs_exist_ok=True)

    # Copy prebuilts
    shutil.copytree(PROPRIETARY_COMMON, GAPPS_OUT_GARCH_SYSTEM, dirs_exist_ok=True)
    shutil.copytree(PROPRIETARY_GARCH, GAPPS_OUT_GARCH_SYSTEM, dirs_exist_ok=True)

    # Merge split prebuilts
    for first_chunk in glob.glob(
        "**/*.00", root_dir=GAPPS_OUT_GARCH_SYSTEM, recursive=True
    ):
        merged_path = Path(GAPPS_OUT_GARCH_SYSTEM / first_chunk).with_suffix("")

        with open(merged_path, "wb+") as f:
            for chunk in sorted(glob.glob(f"{merged_path}.*")):
                with open(chunk, "rb") as c:
                    shutil.copyfileobj(c, f)

                os.remove(chunk)

    # Copy toybox
    shutil.copy2(GAPPS_TOP / f"toybox-{GARCH}", GAPPS_OUT_GARCH / "toybox")

    # Create build.prop
    with open(GAPPS_OUT_GARCH / "build.prop", "wt+") as f:
        f.write(f"arch={CPUARCH}\n")
        f.write(f"version={SDKV}\n")
        f.write(f"version_nice={ANDROIDV}\n")

    # Package
    shutil.make_archive(GAPPS_OUT_ZIP_BASENAME_UNSIGNED, "zip", GAPPS_OUT_GARCH)

    # Sign
    run_command(
        [
            "java",
            "-Xmx2048m",
            "-jar",
            GAPPS_BUILD_SIGN_SIGNAPK,
            "-w",
            f"{GAPPS_BUILD_SIGN_TESTKEY}.x509.pem",
            f"{GAPPS_BUILD_SIGN_TESTKEY}.pk8",
            GAPPS_OUT_ZIP_FILENAME_UNSIGNED,
            GAPPS_OUT_ZIP_FILENAME,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"LD_LIBRARY_PATH": GAPPS_BUILD_SIGN},
        text=True,
    )
    os.remove(GAPPS_OUT_ZIP_FILENAME_UNSIGNED)

    # Generate sha256 file
    with open(GAPPS_OUT / f"{GAPPS_OUT_ZIP_FILENAME}.sha256sum", "wt+") as f:
        f.write(
            hashlib.file_digest(
                open(GAPPS_OUT_ZIP_FILENAME, "rb"), "sha256"
            ).hexdigest()
        )
        f.write(f"  {GAPPS_OUT_ZIP_FILENAME.name}\n")

    # Clean up
    shutil.rmtree(GAPPS_OUT_GARCH)


if __name__ == "__main__":
    build()
