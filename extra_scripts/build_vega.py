"""
build_vega.py — PlatformIO extra_script (pre)
==============================================
Compiles the VEGA SDK (BSP) and user source files, then links
everything into a named ELF + BIN. The output binary is named
after whichever source file in src/ contains main(), e.g.:
  main.c       -> main.elf / main.bin
  bluetooth.c  -> bluetooth.elf / bluetooth.bin
Falls back to 'firmware' if no main() is detected.
"""

Import("env")

import re
import subprocess
from pathlib import Path

# -----------------------------------------------------------------------
# Helper: read a required path from platformio.ini
# -----------------------------------------------------------------------
def get_required_path(option_name):
    path_str = env.GetProjectOption(option_name, "").strip()
    if not path_str:
        raise SystemExit(f"ERROR: '{option_name}' is not set in platformio.ini.")
    path = Path(path_str).resolve()
    if not path.exists():
        raise SystemExit(
            f"ERROR: Path '{path}' for '{option_name}' does not exist. "
            f"Check your platformio.ini."
        )
    return path

# -----------------------------------------------------------------------
# Paths — read from platformio.ini
# -----------------------------------------------------------------------
SDK_PATH  = get_required_path("vega_sdk_path")
TOOLS_BIN = get_required_path("vega_tools_path")

# Toolchain binaries
GCC     = str(TOOLS_BIN / "riscv64-vega-elf-gcc.exe").replace("\\", "/")
AR      = str(TOOLS_BIN / "riscv64-vega-elf-ar.exe").replace("\\", "/")
OBJCOPY = str(TOOLS_BIN / "riscv64-vega-elf-objcopy.exe").replace("\\", "/")

# SDK layout
BSP_DIR    = SDK_PATH / "bsp"
INC_DIR    = BSP_DIR / "include"
LD_SCRIPT  = str(BSP_DIR / "common" / "mbl.lds").replace("\\", "/")
CRT_S      = str(BSP_DIR / "common" / "crt.S")
STDLIB_C   = str(BSP_DIR / "common" / "stdlib.c")
RAWFLOAT_C = str(BSP_DIR / "common" / "rawfloat.c")
DRIVER_SRCS = list((BSP_DIR / "drivers").rglob("*.c"))

# Path strings (forward-slash safe for GCC on Windows)
INC = str(INC_DIR).replace("\\", "/")
BSP = str(BSP_DIR).replace("\\", "/")

SRC_DIR = Path(env.subst("$PROJECT_SRC_DIR")).resolve()
SRC     = str(SRC_DIR).replace("\\", "/")

# -----------------------------------------------------------------------
# Compilation flags
# -----------------------------------------------------------------------
ARCH = "-march=rv32im -mabi=ilp32 -mcmodel=medany"
INCS = f"-I{INC} -I{BSP} -I{SRC}"
DEFS = "-DTHEJAS32"
OPT  = (
    "-O0 -g "
    "-fno-builtin-printf -fno-builtin-puts -fno-builtin-memcmp "
    "-fno-common -fno-pic "
    "-ffunction-sections -fdata-sections"
)
SDK_STDLIB = f"-include {INC}/stdlib.h"

C_FLAGS = f"{ARCH} {INCS} {DEFS} {OPT} {SDK_STDLIB}"
LDFLAGS = (
    f"-nostartfiles -T{LD_SCRIPT} "
    "--specs=nano.specs -specs=nosys.specs "
    "-Wl,--gc-sections"
)
LIBS = f"-L{BSP} -Wl,--start-group -lvega -lc -lgcc -lm -Wl,--end-group"

# Build / object output directories
build_dir = Path(env.subst("$BUILD_DIR")).resolve()
obj_dir   = build_dir / "vega_objs"
obj_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------
# Helper: compile a single source file → object file (incremental)
# -----------------------------------------------------------------------
def build_obj(src, obj):
    src_path = Path(src)
    obj_path = Path(obj)
    if not obj_path.exists() or src_path.stat().st_mtime > obj_path.stat().st_mtime:
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = f'"{GCC}" {C_FLAGS} -c "{src}" -o "{obj}"'
        print(f"[VEGA] Compiling {src_path.name}...")
        subprocess.run(cmd, shell=True, check=True)
    return env.File(str(obj_path))

# -----------------------------------------------------------------------
# Helper: detect which source file owns main() → names the binary
# -----------------------------------------------------------------------
MAIN_PATTERN = re.compile(r'\b(?:void|int)\s+main\s*\(')

def find_main_file(src_files):
    """
    Scan each .c file for a main() definition.
    Returns the stem (name without extension) of the first match,
    or 'firmware' as a safe fallback.
    """
    for f in src_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if MAIN_PATTERN.search(content):
                print(f"[VEGA] main() found in '{f.name}' — output will be '{f.stem}'")
                return f.stem
        except Exception as exc:
            print(f"[VEGA] Warning: could not read '{f}': {exc}")
    print("[VEGA] Warning: main() not found in any source file — using 'firmware' as output name.")
    return "firmware"

# -----------------------------------------------------------------------
# Stage 1 — BSP objects (SDK drivers + stdlib + rawfloat + crt.S)
# -----------------------------------------------------------------------
bsp_srcs = DRIVER_SRCS + [Path(STDLIB_C), Path(RAWFLOAT_C)]
bsp_objs = []

for s in bsp_srcs:
    o = obj_dir / "bsp" / f"{s.stem}.o"
    bsp_objs.append(build_obj(s, o))

# crt.S — assembled separately (no C flags needed beyond arch + includes)
crt_o = obj_dir / "bsp" / "crt.o"
if not crt_o.exists() or Path(CRT_S).stat().st_mtime > crt_o.stat().st_mtime:
    print("[VEGA] Assembling crt.S...")
    subprocess.run(
        f'"{GCC}" {ARCH} {INCS} -c "{CRT_S}" -o "{crt_o}"',
        shell=True, check=True
    )
bsp_objs.insert(0, env.File(str(crt_o)))  # crt.o must be first in link order

# -----------------------------------------------------------------------
# Stage 2 — User objects (everything in src/)
# -----------------------------------------------------------------------
user_srcs = sorted(SRC_DIR.glob("*.c"))  # sorted for deterministic order
if not user_srcs:
    raise SystemExit(
        f"ERROR: No .c files found in '{SRC_DIR}'. "
        "Add your source files to the src/ directory."
    )

user_objs = []
for s in user_srcs:
    o = obj_dir / "user" / f"{s.stem}.o"
    user_objs.append(build_obj(s, o))

# -----------------------------------------------------------------------
# Stage 3 — Determine output name from the file containing main()
# -----------------------------------------------------------------------
prog_name = find_main_file(user_srcs)

# -----------------------------------------------------------------------
# Stage 4 — Configure the PlatformIO environment for linking
# -----------------------------------------------------------------------
env.Replace(PROGNAME=prog_name, PROGSUFFIX=".elf")

# Prevent the native platform's host compiler from touching src/
env["SRC_FILTER"] = "-<*>"
env.Append(PIOBUILDFILES=user_objs + bsp_objs)

env.Replace(
    LINKCOM=f'"{GCC}" {ARCH} {LDFLAGS} -o $TARGET $SOURCES {LIBS}'
)

# -----------------------------------------------------------------------
# Stage 5 — Post-link: convert ELF → BIN via objcopy
# -----------------------------------------------------------------------
def objcopy_to_bin(source, target, env):
    elf     = str(target[0])
    bin_out = elf.replace(".elf", ".bin")
    print(f"[VEGA] Running objcopy: {Path(elf).name} -> {Path(bin_out).name}")
    subprocess.run(
        f'"{OBJCOPY}" -O binary "{elf}" "{bin_out}"',
        shell=True, check=True
    )
    print(f"[VEGA] Binary ready : {bin_out}")

env.AddPostAction(f"$BUILD_DIR/{prog_name}.elf", objcopy_to_bin)