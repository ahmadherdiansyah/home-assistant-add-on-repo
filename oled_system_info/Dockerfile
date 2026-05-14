ARG BUILD_FROM
FROM ${BUILD_FROM}

WORKDIR /

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    python3-smbus \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    smbus2 \
    adafruit-circuitpython-ssd1306 \
    pillow \
    psutil \
    requests

COPY run.sh /
COPY system_info.py /
RUN chmod a+x /run.sh

CMD ["/run.sh"]