"""AirTouch 5 DataPack framing from the tablet APK.

The AT5 main-board protocol keeps the same raw sync marker and CRC family as
AT4, but expanded commands are first-class 16-bit values with a structured
base-data plus repeated-record payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ...packet import RAW_PREFIX, PacketParseError, crc16_modbus, hex_bytes, unstuff_raw_body

ADDR_MAIN_BOARD = 0x80
ADDR_EXTENSION = 0x81
ADDR_CONSOLE_BASE = 0x90

COMMAND_NAMES = {
    0x001B: "response_update_gateway",
    0x001F: "expanded_app",
    0x0040: "set_datetime",
    0x0055: "airtouch4_preference_check",
    0x0061: "response_extension_info",
    0x0091: "response_rsa_key",
    0xC021: "response_zone_control",
    0xC023: "response_ac_control",
    0xC027: "response_itc_sensor",
    0xC02B: "response_ac_timer",
    0xC02F: "response_sensor",
    0xC033: "response_notice",
    0xC043: "response_zone_name",
    0xC045: "response_preference",
    0xC047: "response_password",
    0xC051: "response_parameters",
    0xC055: "response_balance",
    0xC057: "response_zoning",
    0xC059: "response_spill",
    0xC05B: "response_service",
    0xC05D: "response_ac_setting",
    0xC05F: "response_io_setting",
    0xC071: "response_bridge",
    0xC073: "response_update_bridge",
}


def command_name(command: int) -> str:
    return COMMAND_NAMES.get(command, f"cmd_0x{command:04X}" if command > 0xFF else f"cmd_0x{command:02X}")


def address_name(address: int) -> str:
    if address == ADDR_MAIN_BOARD:
        return "main_board"
    if address == ADDR_EXTENSION:
        return "extension"
    if (address & 0xF0) == ADDR_CONSOLE_BASE:
        return f"console_{address & 0x0F}"
    if address == 0xFF:
        return "broadcast"
    return f"addr_0x{address:02X}"


def _append_u16(buffer: bytearray, value: int) -> None:
    buffer.extend(((value >> 8) & 0xFF, value & 0xFF))


@dataclass(frozen=True)
class AT5DataPack:
    dest: int
    src: int
    packet_id: int
    command: int
    payload: bytes = b""
    repeat_records: tuple[bytes, ...] = field(default_factory=tuple)
    raw_mode: bool = True
    crc_received: int | None = None
    crc_calculated: int | None = None
    stream_offset: int = 0

    @property
    def crc_ok(self) -> bool:
        return self.crc_received is not None and self.crc_received == self.crc_calculated

    @property
    def command_name(self) -> str:
        return command_name(self.command)

    @property
    def dest_name(self) -> str:
        return address_name(self.dest)

    @property
    def src_name(self) -> str:
        return address_name(self.src)

    @property
    def expanded(self) -> bool:
        return self.command >= 0xC0

    def encode(self, *, raw_mode: bool | None = None, stuff_raw: bool = False) -> bytes:
        use_raw = self.raw_mode if raw_mode is None else raw_mode
        prefix = RAW_PREFIX if use_raw else b"\x55\x55"
        body = bytearray((self.dest & 0xFF, self.src & 0xFF, self.packet_id & 0xFF))
        if self.expanded:
            record_len = len(self.repeat_records[0]) if self.repeat_records else 0
            if any(len(record) != record_len for record in self.repeat_records):
                raise ValueError("AT5 repeat records must have a fixed length")
            body.append((self.command >> 8) & 0xFF)
            _append_u16(body, len(self.payload) + 8 + (record_len * len(self.repeat_records)))
            body.append(self.command & 0xFF)
            body.append(0)
            _append_u16(body, len(self.payload))
            _append_u16(body, record_len)
            _append_u16(body, len(self.repeat_records))
            body.extend(self.payload)
            for record in self.repeat_records:
                body.extend(record)
        else:
            body.append(self.command & 0xFF)
            _append_u16(body, len(self.payload))
            body.extend(self.payload)
        crc = crc16_modbus(body)
        _append_u16(body, crc)
        frame = prefix + bytes(body)
        return _stuff_body(frame) if stuff_raw and use_raw else frame

    def to_record(self) -> dict:
        return {
            "stream_offset": self.stream_offset,
            "raw_mode": self.raw_mode,
            "raw": hex_bytes(self.encode(raw_mode=self.raw_mode)),
            "dest": f"0x{self.dest:02X}",
            "dest_name": self.dest_name,
            "src": f"0x{self.src:02X}",
            "src_name": self.src_name,
            "packet_id": self.packet_id,
            "cmd": f"0x{self.command:04X}" if self.command > 0xFF else f"0x{self.command:02X}",
            "cmd_name": self.command_name,
            "len": len(self.payload),
            "payload": hex_bytes(self.payload),
            "repeat_count": len(self.repeat_records),
            "repeat_records": [hex_bytes(record) for record in self.repeat_records],
            "crc_received": None if self.crc_received is None else f"0x{self.crc_received:04X}",
            "crc_calc": None if self.crc_calculated is None else f"0x{self.crc_calculated:04X}",
            "crc_ok": self.crc_ok,
        }


def build_datapack(
    *,
    dest: int,
    src: int,
    packet_id: int,
    command: int,
    payload: bytes | bytearray = b"",
    repeat_records: Iterable[bytes | bytearray] = (),
    stuff_raw: bool = True,
) -> bytes:
    packet = AT5DataPack(
        dest=dest,
        src=src,
        packet_id=packet_id,
        command=command,
        payload=bytes(payload),
        repeat_records=tuple(bytes(record) for record in repeat_records),
    )
    return packet.encode(stuff_raw=stuff_raw)


def parse_datapack(frame: bytes, *, stream_offset: int = 0) -> AT5DataPack:
    raw_mode = frame.startswith(RAW_PREFIX)
    prefix_len = len(RAW_PREFIX) if raw_mode else 2
    if raw_mode:
        clean = unstuff_raw_body(frame)
    elif frame.startswith(b"\x55\x55"):
        clean = frame
    else:
        raise PacketParseError("missing AirTouch 5 prefix")
    if len(clean) < prefix_len + 8:
        raise PacketParseError("packet is too short")

    body_start = prefix_len
    length = (clean[body_start + 4] << 8) | clean[body_start + 5]
    frame_len = prefix_len + 8 + length
    if len(clean) < frame_len:
        raise PacketParseError("packet is incomplete")
    if len(clean) > frame_len:
        clean = clean[:frame_len]

    payload_start = body_start + 6
    payload_end = payload_start + length
    crc_received = (clean[payload_end] << 8) | clean[payload_end + 1]
    crc_calculated = crc16_modbus(clean[body_start:payload_end])
    if crc_received != crc_calculated:
        raise PacketParseError("packet CRC mismatch")

    command = clean[body_start + 3]
    payload = clean[payload_start:payload_end]
    repeat_records: tuple[bytes, ...] = ()
    if command >= 0xC0:
        if len(payload) < 8:
            raise PacketParseError("expanded packet header is incomplete")
        command = (command << 8) | payload[0]
        base_len = (payload[2] << 8) | payload[3]
        repeat_len = (payload[4] << 8) | payload[5]
        repeat_count = (payload[6] << 8) | payload[7]
        records_start = 8 + base_len
        records_end = records_start + (repeat_len * repeat_count)
        if records_end > len(payload):
            raise PacketParseError("expanded packet repeat records are incomplete")
        if repeat_count and repeat_len <= 0:
            raise PacketParseError("expanded packet repeat length is zero")
        repeat_records = tuple(
            payload[index:index + repeat_len]
            for index in range(records_start, records_end, repeat_len)
        ) if repeat_count else ()
        payload = payload[8:records_start]

    return AT5DataPack(
        dest=clean[body_start],
        src=clean[body_start + 1],
        packet_id=clean[body_start + 2],
        command=command,
        payload=payload,
        repeat_records=repeat_records,
        raw_mode=raw_mode,
        crc_received=crc_received,
        crc_calculated=crc_calculated,
        stream_offset=stream_offset,
    )


def extract_datapacks(data: bytes, *, max_payload_len: int = 8192) -> list[AT5DataPack]:
    packets: list[AT5DataPack] = []
    index = 0
    while index <= len(data) - 10:
        if data[index:index + 4] == RAW_PREFIX:
            prefix_len = len(RAW_PREFIX)
        elif data[index:index + 2] == b"\x55\x55":
            prefix_len = 2
        else:
            index += 1
            continue
        candidate = unstuff_raw_body(data[index:]) if prefix_len == len(RAW_PREFIX) else data[index:]
        if len(candidate) < prefix_len + 8:
            break
        shell = prefix_len
        payload_len = (candidate[shell + 4] << 8) | candidate[shell + 5]
        frame_len = prefix_len + 8 + payload_len
        if payload_len > max_payload_len:
            index += 1
            continue
        if len(candidate) < frame_len:
            index += 1
            continue
        try:
            source = data[index:] if prefix_len == len(RAW_PREFIX) else candidate[:frame_len]
            packet = parse_datapack(source, stream_offset=index)
            packets.append(packet)
        except PacketParseError:
            index += 1
            continue
        index += len(packet.encode(raw_mode=packet.raw_mode, stuff_raw=packet.raw_mode))
    return packets


def _stuff_body(frame: bytes) -> bytes:
    if not frame.startswith(RAW_PREFIX):
        return frame
    out = bytearray(frame[:4])
    count_55 = 0
    for byte in frame[4:]:
        out.append(byte)
        if byte == 0x55:
            count_55 += 1
            if count_55 >= 3:
                out.append(0x00)
                count_55 = 0
        else:
            count_55 = 0
    return bytes(out)
