# CDAC Aries V3 (THEJAS32) - PlatformIO Baremetal Project

This project provides a clean, baremetal development environment for the **C-DAC Aries V3 (VEGA ET1031 / THEJAS32)** RISC-V development board using **PlatformIO**. It allows you to build and upload code to the Aries V3 board without relying on Eclipse or complex Makefiles, integrating seamlessly with VS Code.

This project includes a working example of the `ssd1306` I2C OLED display driver, ported correctly to compile with PlatformIO.

---

## 🚀 Prerequisites

Before you begin, ensure you have the following installed on your Windows system:

1.  **[VS Code](https://code.visualstudio.com/)**
2.  **[PlatformIO IDE Extension](https://platformio.org/install/ide?install=vscode)** (Install within VS Code)
3.  **[VEGA SDK](https://gitlab.com/cdac-vega/vega-sdk), [Toolchain for Windows](https://gitlab.com/riscv-vega) and [Upload Tools](https://gitlab.com/riscv-vega)** 

---

## 🛠️ Environment Setup

Unlike standard PlatformIO boards, the Aries V3 requires the official VEGA SDK and Toolchain to compile its baremetal drivers. You must tell PlatformIO where these tools are located.

### 1. Configure Paths

Open the `platformio.ini` file located in the root of this project and update the paths to match where you extracted the VEGA SDK and Toolchain on your PC:

```ini
[env:aries_v3]
; ... other settings ...

; ==========================================================
; ⚠️ CRITICAL: UPDATE THESE PATHS TO MATCH YOUR SYSTEM! ⚠️
; ==========================================================
; Use forward slashes (/) or double backslashes (\\)
vega_sdk_path   = /path/where/Vega-sdk/is/located
vega_tools_path  = /path/where/vega-tools-windows/is/located/bin
vega_flasher_dir = /path/where/vega-flasher-windows/is/located
```

### 2. Connect Your Board

1.  Connect the **UART/Debug USB port** of the Aries V3 board to your PC.
2.  Identify the COM port it connected to (e.g., `COM3`, `COM9`). You can check this in Windows Device Manager under "Ports (COM & LPT)".

---

## 🏃‍♂️ How to Build and Upload

### Building the Firmware

To compile the project, use the PlatformIO build button (checkmark icon ✓) in the bottom toolbar of VS Code, or run the following command in the PlatformIO ide CLI:

```bash
pio run
```
*(or the build button in platformIO ide)*

### Uploading to the Board

To flash the compiled binary to the Aries V3 board, you must specify the COM port you identified earlier. 

1. **Ensure no other program (like TeraTerm or PuTTY) is currently using the COM port.**
2. Run the following command in the terminal, replacing `<YOUR_COM_PORT>` with your actual port (e.g., `COM3`):

```bash
pio run --target upload --upload-port <YOUR_COM_PORT>
```
*(or the upload button in platformIO ide after selecting the correct COM port)*

*Note: The upload script uses XMODEM protocols internally via a custom flasher script (`flasher.bat`).*

---

## 📁 Project Structure

This project uses a custom build script to seamlessly compile the VEGA SDK source files alongside your project files.

```text
aries_pio_project/
├── .vscode/               # VS Code workspace settings
├── boards/                
│   └── aries_v3.json      # Custom highly-tailored board definition
├── extra_scripts/         
│   ├── build_vega.py      # PlatformIO extra_script (pre): handles SDK compilation & flags
│   └── upload_vega.py     # PlatformIO extra_script (post): handles XMODEM upload
├── src/                   # Your application source code goes here!
│   ├── fonts.h            # OLED font data
│   ├── ssd1306.c          # I2C OLED Driver
│   ├── ssd1306.h          
│   └── main.c             # Main application entry point
├── platformio.ini         # PlatformIO configuration & Path settings
└── README.md              # This file
```

---

## ⚠️ Important Notes & Troubleshooting

*   **Compiler Optimization Bug**: The official Linux VEGA SDK builds without optimization (`-O0`). PlatformIO defaults to `-O2`. Aggressive `-O2` optimization breaks the SDK's `udelay()` timing functions and pointer-based data arrays (like OLED image buffers). This project's custom `build_vega.py` script **explicitly enforces `-O0`** along with the necessary RISC-V memory models (`-mcmodel=medany`, `-fno-pic`) to ensure identical behavior to the official SDK.
*   **Missing standard libraries**: The SDK requires its own `stdlib.c` and does not use the standard `libc`. The custom build script automatically includes these.
*   **I2C Initialization**: Check `main.c` for proper I2C initialization (`i2c_configure()`) which is strictly required for peripherals like displays.

---
