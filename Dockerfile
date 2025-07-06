# Standalone Mininet Docker Container for SDN Development
FROM ubuntu:20.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages
RUN apt-get update && apt-get install -y \
    mininet \
    net-tools \
    iputils-ping \
    iperf \
    python3 \
    python3-pip \
    curl \
    wget \
    nano \
    vim \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Ryu controller
RUN pip3 install ryu==4.34 eventlet==0.30.2

# Create working directory
WORKDIR /app

# Set up environment for mininet
ENV PYTHONPATH=/app:$PYTHONPATH

# Create a user for running mininet (optional, for security)
RUN useradd -m -s /bin/bash mininet && \
    echo "mininet ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Expose common ports
EXPOSE 6653 8080 8000

# Default command starts bash for interactive use
CMD ["/bin/bash"]