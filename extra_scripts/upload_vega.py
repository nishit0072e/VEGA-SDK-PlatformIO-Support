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

def do_upload(source, target, env):
    port = env.GetProjectOption("upload_port", "")
    if not port:
        port = env.get("UPLOAD_PORT", "")
    if not port:
        print("[VEGA] ERROR: No upload port specified.")
        print("[VEGA] Run: pio run --target upload --upload-port COM3")
        return -1

    build_dir = Path(env.subst("$BUILD_DIR")).resolve()
    elf = str(build_dir / "firmware.elf")  # backslashes from resolve()

    print(f"[VEGA] Uploading to {port}: {elf}")
    # Use list form to avoid shell-quoting issues with spaces in paths
    r = subprocess.run(["cmd", "/c", FLASHER_BAT_STR, port, elf])
    return r.returncode

# Replace the native platform's 'upload' Alias (which runs the ELF locally)
# with our flasher action.
env.Replace(
    UPLOADCMD=do_upload
)

# Also redefine the 'upload' alias to call our function
upload_target = env.get("PIOMAINPROG") or env.subst("$BUILD_DIR/firmware.elf")
env.AlwaysBuild(
    env.Alias("upload", upload_target, do_upload)
)

print("[VEGA] Upload target overridden: will call flasher.bat <PORT> <ELF>")
