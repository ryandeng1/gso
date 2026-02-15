DOCKERFILE = r"""
FROM --platform={platform} ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y \
wget \
git \
build-essential \
libffi-dev \
libtiff-dev \
python3 \
python3-pip \
python-is-python3 \
jq \
curl \
locales \
locales-all \
tzdata \
# Add packages BLAS/LAPACK support
gcc \
gcc-11 \
g++-11 \
gfortran \
libopenblas-dev \
liblapack-dev \
pkg-config \
libssl-dev \
clang \
# Add image processing libs
libtiff5-dev \
libjpeg8-dev \
libopenjp2-7-dev \
zlib1g-dev \
libfreetype6-dev \
liblcms2-dev \
libwebp-dev \
tcl8.6-dev \
tk8.6-dev \
python3-tk \
libharfbuzz-dev \
libfribidi-dev \
libxcb1-dev \
libx11-dev
# && rm -rf /var/lib/apt/lists/*

# Use g++-11 as default to maintain compatibility with older C++ code (e.g. pybind11 in scipy)
RUN update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 100 \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100

# my-swe-agent stuff installs py-spy and copies over some profiling scripts
RUN apt install -y autoconf libtool
RUN git clone https://github.com/libunwind/libunwind.git \
    && cd libunwind && git checkout v1.8.1 \
    && autoreconf -i \
    && ./configure \
    && make && make install \
    && ldconfig
ENV LIBRARY_PATH="/usr/local/lib"
# RUN apt install -y libunwind-dev
RUN git config --global --add safe.directory '*'
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"
RUN . "$HOME/.cargo/env"
RUN cargo install py-spy --features unwind
RUN git config --global --add safe.directory '*'

# get images used for a few GSO instances
RUN mkdir -p /images && \
    wget -O /images/Fronalpstock_big.jpg "https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg" && \
    wget -O /images/Lenna.png "https://upload.wikimedia.org/wikipedia/en/7/7d/Lenna_%28test_image%29.png"

# Download and install conda
# RUN wget 'https://repo.anaconda.com/miniconda/Miniconda3-py311_23.11.0-2-Linux-{conda_arch}.sh' -O miniconda.sh \
#     && bash miniconda.sh -b -p /opt/miniconda3
# # Add conda to PATH
# ENV PATH=/opt/miniconda3/bin:$PATH
# # Add conda to shell startup scripts like .bashrc (DO NOT REMOVE THIS)
# RUN conda init --all
# RUN conda config --append channels conda-forge

# Download and instal uv
# RUN curl -LsSf https://astral.sh/uv/0.5.4/install.sh | sh
# Use newer version of uv so we don't need setup commands
RUN curl -LsSf https://astral.sh/uv/0.8.24/install.sh | sh
RUN . $HOME/.local/bin/env
# Add uv to PATH
ENV PATH=/root/.local/bin:$PATH

RUN adduser --disabled-password --gecos 'dog' nonroot

WORKDIR /testbed/

# Copy and setup the repo
COPY ./setup_repo.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_repo.sh
RUN /bin/bash /root/setup_repo.sh

# Copy the test and eval scripts to parent of testbed
# Comment this out
# COPY ./eval.sh /
# COPY ./gso_test*.py /

WORKDIR /testbed/

# Run setup for all test and check if cache is full
# RUN find / -maxdepth 1 -name 'gso_test_*.py' -exec bash -c "source .venv/bin/activate && export HF_TOKEN={hf_token} && cd / && python {{}} prep.txt --reference --file_prefix prep" \;
# RUN find / -maxdepth 1 -name 'gso_test_*.py' -exec bash -c "source .venv/bin/activate && export DEBUG_GSO="true" && export HF_TOKEN={hf_token} && cd / && python {{}} prep.txt --reference --file_prefix prep" \;
# HF_HUB_DISABLE_XET=1 avoids Xet storage backend issues during pre-caching
RUN find / -maxdepth 1 -name 'gso_test_*.py' -exec bash -c "source .venv/bin/activate && export HF_TOKEN={hf_token} && export HF_HUB_DISABLE_XET=1 && cd / && python {{}} prep.txt --reference --file_prefix prep" \;
RUN find / -maxdepth 1 -name 'gso_test_*.py' -exec bash -c "source .venv/bin/activate && export DEBUG_GSO="true" && export HF_TOKEN={hf_token} && export HF_HUB_DISABLE_XET=1 && cd / && python {{}} prep.txt --reference --file_prefix prep" \;

# Automatically activate the env within the testbed directory
RUN echo "source .venv/bin/activate" >> /root/.bashrc
"""


def get_dockerfile_instance(platform: str, arch: str) -> str:
    import os

    if arch == "arm64":
        conda_arch = "aarch64"
    else:
        conda_arch = arch

    # look for HF_READ_TOKEN in the environment
    if not os.getenv("HF_READ_TOKEN"):
        raise ValueError(
            "A huggingface token w/ read access is needed for GSO dockers. Please set HF_READ_TOKEN."
        )
    else:
        hf_token = os.getenv("HF_READ_TOKEN")

    return DOCKERFILE.format(
        platform=platform, conda_arch=conda_arch, hf_token=hf_token
    )
