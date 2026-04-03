"""
upload_vega.py — PlatformIO extra_script (post)
================================================
The native platform hardcodes its 'upload' target to run the ELF
locally as a Windows process. This post: script replaces that alias
with a call to flasher.bat <COM_PORT> <ELF> instead.
"""

Import("env")

import subprocess
from pathlib import Path

# -----------------------------------------------------------------------
# Paths (Read from platformio.ini)
# -----------------------------------------------------------------------
flasher_dir_str = env.GetProjectOption("vega_flasher_dir", "").strip()
if not flasher_dir_str:
    raise SystemExit("ERROR: 'vega_flasher_dir' is not set in platformio.ini.")

FLASHER_DIR = Path(flasher_dir_str).resolve()
FLASHER_BAT = FLASHER_DIR / "flasher.bat"

if not FLASHER_BAT.exists():
    raise SystemExit(f"ERROR: flasher.bat not found in '{FLASHER_DIR}'. Check 'vega_flasher_dir' in platformio.ini.")

FLASHER_BAT_STR = str(FLASHER_BAT)

import sys
import subprocess
import os

def do_upload(source, target, env):
    port = env.GetProjectOption("upload_port", "")
    if not port:
        port = env.get("UPLOAD_PORT", "")
    if not port:
        print("[VEGA] ERROR: No upload port specified.")
        print("[VEGA] Run: pio run --target upload --upload-port COM3")
        os._exit(1)

    build_dir = Path(env.subst("$BUILD_DIR")).resolve()
    
    elf_files = list(build_dir.glob("*.elf"))
    if not elf_files:
        print(f"[VEGA] ERROR: No .elf file found in {build_dir}")
        os._exit(1)
    elf = str(elf_files[0])

    print(f"[VEGA] Uploading to {port}: {elf}")
    r = subprocess.run(["cmd", "/c", FLASHER_BAT_STR, port, elf])
    
    # We forcefully exit the build process immediately.
    # Why? PlatformIO's "native" environment hardcodes the `upload` action 
    # to natively EXECUTE the .elf file on your Windows machine, which causes 
    # Node.js to crash when it tries to parse raw ELF bytes!
    # By exiting here, we get a clean upload and skip the crash.
    if r.returncode == 0:
        print("========================= [SUCCESS] =========================")
        os._exit(0)
    else:
        print("========================= [FAILED] =========================")
        os._exit(1)

# Hook our flashing script as a Pre-Action to the upload target
env.AddPreAction("upload", do_upload)

print("[VEGA] Upload target intercepted: will call flasher.bat and skip native execution")
