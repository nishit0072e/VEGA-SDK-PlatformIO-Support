FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# 1. Install system dependencies required by PlatformIO and Vega
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    python3 \
    python3-venv \
    python3-dev \
    git \
    make \
    curl \
    xz-utils \
    build-essential \
    libncurses5 \
    libusb-1.0-0-dev

# 2. Create the Vega directory and clone the official repositories
RUN mkdir -p /opt/vega
WORKDIR /opt/vega

# Clone the SDK and RV32 Toolchain
RUN git clone https://gitlab.com/riscv-vega/community/vega-sdk.git
RUN git clone https://gitlab.com/riscv-vega/community/vega-tools-rv32.git

# Ensure the downloaded toolchain binaries are executable
RUN chmod -R +x /opt/vega/vega-tools-rv32/bin/

# Transfer ownership to the default 'vscode' user so PlatformIO can read/write if needed
RUN chown -R vscode:vscode /opt/vega

# 3. Switch to the non-root user to install PlatformIO
USER vscode
WORKDIR /home/vscode

# Install PlatformIO Core via the official installer
RUN curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py -o get-platformio.py \
    && python3 get-platformio.py \
    && rm get-platformio.py

# 4. Add PlatformIO and the Vega RV32 Toolchain to the system PATH
ENV PATH="/home/vscode/.platformio/penv/bin:/opt/vega/vega-tools-rv32/bin:${PATH}"

# Reset working directory for when the container starts
WORKDIR /workspaces
