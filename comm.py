# coding: utf-8
"""
Serial bridge: Jetson Nano / PC (Python) <-> Arduino Mega 2560 or STM32
(Mecanum motor driver via UART).

Default protocol: one ASCII byte per command. Implement matching reads on
the MCU (see README). For different framing, extend _send().
"""
import os
import sys
from typing import Optional

try:
    import serial
except ImportError as e:
    serial = None  # type: ignore
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None

# Commands — must match Arduino / STM32 UART handler in your sketch.
CMD_STOP = ord("S")
CMD_FORWARD = ord("F")
CMD_BACKWARD = ord("B")
CMD_LEFT = ord("L")
CMD_RIGHT = ord("R")

_ser: "serial.Serial | None" = None


def default_port() -> str:
    for key in ("ROBOT_SERIAL_PORT", "ARDUINO_SERIAL_PORT", "STM32_SERIAL_PORT"):
        p = os.environ.get(key)
        if p:
            return p
    if sys.platform == "win32":
        return "COM3"
    return "/dev/ttyUSB0"


def connect(port=None, baudrate=115200):
    # type: (Optional[str], int) -> None
    global _ser
    if serial is None:
        raise RuntimeError(
            "pyserial is not installed. Run: pip install pyserial"
        ) from _IMPORT_ERROR
    port = port or default_port()
    if _ser is not None and _ser.is_open:
        _ser.close()
    try:
        _ser = serial.Serial(port, baudrate, timeout=0.05)
    except (OSError, ValueError, serial.SerialException):
        _ser = None


def _ensure_open() -> None:
    global _ser
    if _ser is None or not _ser.is_open:
        connect()


def _send(cmd: int) -> None:
    _ensure_open()
    if _ser is None or not _ser.is_open:
        return
    try:
        _ser.write(bytes([cmd & 0xFF]))
    except OSError:
        pass


def stop() -> None:
    _send(CMD_STOP)


def forward() -> None:
    _send(CMD_FORWARD)


def backward() -> None:
    _send(CMD_BACKWARD)


def left() -> None:
    _send(CMD_LEFT)


def right() -> None:
    _send(CMD_RIGHT)


def close() -> None:
    global _ser
    if _ser is not None and _ser.is_open:
        _ser.close()
    _ser = None
