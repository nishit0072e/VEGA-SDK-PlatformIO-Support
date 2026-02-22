"""
build_vega.py — Simplified PlatformIO extra_script (pre)
Restored to a stable state for GPIO work.
"""

Import("env")

import subprocess
from pathlib import Path

# -----------------------------------------------------------------------
# Paths (Read from platformio.ini)
# -----------------------------------------------------------------------
def get_required_path(option_name):
    path_str = env.GetProjectOption(option_name, "").strip()
    if not path_str:
        raise SystemExit(f"ERROR: '{option_name}' is not set in platformio.ini.")
    path = Path(path_str).resolve()
    if not path.exists():
        raise SystemExit(f"ERROR: Path '{path}' for '{option_name}' does not exist.")
    return path

SDK_PATH  = get_required_path("vega_sdk_path")
TOOLS_BIN = get_required_path("vega_tools_path")

GCC     = str(TOOLS_BIN / "riscv64-vega-elf-gcc.exe").replace("\\", "/")
AR      = str(TOOLS_BIN / "riscv64-vega-elf-ar.exe").replace("\\", "/")
OBJCOPY = str(TOOLS_BIN / "riscv64-vega-elf-objcopy.exe").replace("\\", "/")

BSP_DIR    = SDK_PATH / "bsp"
INC_DIR    = BSP_DIR / "include"
LD_SCRIPT  = str(BSP_DIR / "common" / "mbl.lds").replace("\\", "/")
CRT_S      = str(BSP_DIR / "common" / "crt.S")
STDLIB_C   = str(BSP_DIR / "common" / "stdlib.c")
RAWFLOAT_C = str(BSP_DIR / "common" / "rawfloat.c")
DRIVER_SRCS = list((BSP_DIR / "drivers").rglob("*.c"))

INC   = str(INC_DIR).replace("\\", "/")
BSP   = str(BSP_DIR).replace("\\", "/")
SRC_DIR = Path(env.subst("$PROJECT_SRC_DIR")).resolve()
SRC   = str(SRC_DIR).replace("\\", "/")

# -----------------------------------------------------------------------
# Compilation Flags
# -----------------------------------------------------------------------
ARCH    = "-march=rv32im -mabi=ilp32 -mcmodel=medany"
INCS    = f"-I{INC} -I{BSP} -I{SRC}"
DEFS    = "-DTHEJAS32"
OPT     = "-O0 -g -fno-builtin-printf -fno-builtin-puts -fno-builtin-memcmp -fno-common -fno-pic -ffunction-sections -fdata-sections"
SDK_STDLIB = f"-include {INC}/stdlib.h"

C_FLAGS   = f"{ARCH} {INCS} {DEFS} {OPT} {SDK_STDLIB}"
LDFLAGS   = f"-nostartfiles -T{LD_SCRIPT} --specs=nano.specs -specs=nosys.specs -Wl,--gc-sections"
LIBS      = f"-L{BSP} -Wl,--start-group -lvega -lc -lgcc -lm -Wl,--end-group"

build_dir = Path(env.subst("$BUILD_DIR")).resolve()
obj_dir   = build_dir / "vega_objs"
obj_dir.mkdir(parents=True, exist_ok=True)

def build_obj(src, obj):
    src_path = Path(src)
    obj_path = Path(obj)
    if not obj_path.exists() or src_path.stat().st_mtime > obj_path.stat().st_mtime:
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = f'"{GCC}" {C_FLAGS} -c "{str(src)}" -o "{obj}"'
        print(f"[VEGA] Compiling {src_path.name}...")
        subprocess.run(cmd, shell=True, check=True)
    return env.File(str(obj_path))

# -----------------------------------------------------------------------
# Steps
# -----------------------------------------------------------------------
# 1. BSP Objects
bsp_srcs = DRIVER_SRCS + [Path(STDLIB_C), Path(RAWFLOAT_C)]
bsp_objs = []
for s in bsp_srcs:
    o = obj_dir / "bsp" / f"{s.stem}.o"
    bsp_objs.append(build_obj(s, o))

crt_o = obj_dir / "bsp" / "crt.o"
if not Path(crt_o).exists() or Path(CRT_S).stat().st_mtime > Path(crt_o).stat().st_mtime:
    subprocess.run(f'"{GCC}" {ARCH} {INCS} -c "{CRT_S}" -o "{crt_o}"', shell=True, check=True)
bsp_objs.insert(0, env.File(str(crt_o)))

# 2. User Objects
user_srcs = list(SRC_DIR.glob("*.c"))
user_objs = []
for s in user_srcs:
    o = obj_dir / "user" / f"{s.stem}.o"
    user_objs.append(build_obj(s, o))

# 3. Configure Env
env.Replace(PROGNAME="firmware", PROGSUFFIX=".elf")
env.Append(PIOBUILDFILES=user_objs + bsp_objs)
env["SRC_FILTER"] = "-<*>"

env.Replace(
    LINKCOM = f'"{GCC}" {ARCH} {LDFLAGS} -o $TARGET $SOURCES {LIBS}'
)

def objcopy_to_bin(source, target, env):
    elf = str(target[0])
    bin_out = elf.replace(".elf", ".bin")
    subprocess.run(f'"{OBJCOPY}" -O binary "{elf}" "{bin_out}"', shell=True, check=True)
    print(f"[VEGA] Binary generated: {bin_out}")

env.AddPostAction("$BUILD_DIR/${PROGNAME}.elf", objcopy_to_bin)
