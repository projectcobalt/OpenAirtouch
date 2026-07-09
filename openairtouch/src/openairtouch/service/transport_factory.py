"""Transport factory helpers for the OpenAirTouch service runtime."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from ..runtime import TransportLike
from ..transport import SerialConfig, SerialRs485Transport, TcpSerialConfig, TcpSerialTransport

TransportFactory = Callable[[], AbstractContextManager[TransportLike]]


def build_transport_factory(
    *,
    transport: str,
    port: str,
    baudrate: int,
    tcp_host: str,
    tcp_port: int,
) -> AbstractContextManager[TransportLike]:
    if transport == "local_serial":
        return SerialRs485Transport(SerialConfig(port=port, baudrate=baudrate))
    if transport == "tcp_serial":
        return TcpSerialTransport(TcpSerialConfig(host=tcp_host, port=tcp_port))
    raise ValueError(f"unsupported transport: {transport}")
