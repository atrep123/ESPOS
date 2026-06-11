from __future__ import annotations

import ctypes
import random
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DLL = HERE / "protocol_abi.dll"
KEY = bytes(
    [
        0x00,
        0x11,
        0x22,
        0x33,
        0x44,
        0x55,
        0x66,
        0x77,
        0x88,
        0x99,
        0xAA,
        0xBB,
        0xCC,
        0xDD,
        0xEE,
        0xFF,
    ]
)
KEY_ID = 1
FIELD_PACK = struct.Struct(">BBBBIQ")


def _import_protocol():
    sys.path.insert(0, str(ROOT / "shared" / "protocol"))
    import protocol as py_protocol

    return py_protocol


def _load_dll() -> ctypes.CDLL:
    if not DLL.exists():
        sys.path.insert(0, str(HERE))
        import build

        rc = build.main()
        if rc != 0:
            raise SystemExit(rc)

    lib = ctypes.CDLL(str(DLL))
    lib.proto_encode.argtypes = [
        ctypes.c_ubyte,
        ctypes.c_ubyte,
        ctypes.c_ubyte,
        ctypes.c_ubyte,
        ctypes.c_uint,
        ctypes.c_ulonglong,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
    ]
    lib.proto_encode.restype = ctypes.c_int
    lib.proto_decode.argtypes = [
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte),
    ]
    lib.proto_decode.restype = ctypes.c_int
    return lib


def _buf(data: bytes) -> ctypes.Array[ctypes.c_ubyte]:
    if data:
        return (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    return (ctypes.c_ubyte * 1)()


def _cpp_encode(lib: ctypes.CDLL, frame, payload: bytes) -> bytes:
    payload_buf = _buf(payload)
    key_buf = _buf(KEY)
    out = (ctypes.c_ubyte * 256)()
    n = lib.proto_encode(
        int(frame.frame_type),
        frame.key_id,
        frame.source,
        frame.destination,
        frame.sequence,
        frame.nonce,
        payload_buf,
        len(payload),
        key_buf,
        len(KEY),
        out,
        len(out),
    )
    if n < 0:
        raise AssertionError("C++ proto_encode returned -1")
    return bytes(out[:n])


def _cpp_decode(lib: ctypes.CDLL, encoded: bytes) -> tuple[bytes, bytes]:
    data_buf = _buf(encoded)
    key_buf = _buf(KEY)
    out_payload = (ctypes.c_ubyte * 128)()
    out_fields = (ctypes.c_ubyte * FIELD_PACK.size)()
    n = lib.proto_decode(
        data_buf,
        len(encoded),
        key_buf,
        len(KEY),
        out_payload,
        len(out_payload),
        out_fields,
    )
    if n < 0:
        raise AssertionError("C++ proto_decode returned -1")
    return bytes(out_payload[:n]), bytes(out_fields)


def _cpp_decode_rc(lib: ctypes.CDLL, encoded: bytes) -> int:
    data_buf = _buf(encoded)
    key_buf = _buf(KEY)
    out_payload = (ctypes.c_ubyte * 128)()
    out_fields = (ctypes.c_ubyte * FIELD_PACK.size)()
    return lib.proto_decode(
        data_buf,
        len(encoded),
        key_buf,
        len(KEY),
        out_payload,
        len(out_payload),
        out_fields,
    )


def _frames(py_protocol, count: int = 500):
    rng = random.Random(0xC0DEC0DE)
    frame_types = list(py_protocol.FrameType)
    for i in range(count):
        payload_len = rng.randrange(65)
        payload = bytes(rng.getrandbits(8) for _ in range(payload_len))
        frame_type = frame_types[i % len(frame_types)]
        yield py_protocol.PropFrame(
            frame_type=frame_type,
            key_id=KEY_ID,
            source=rng.randrange(256),
            destination=rng.randrange(256),
            sequence=rng.getrandbits(32),
            nonce=rng.getrandbits(64),
            payload=payload,
        )


def _fail(group: str, index: int, message: str, **items: object) -> int:
    print(f"FAIL {group}: frame {index}: {message}")
    for name, value in items.items():
        if isinstance(value, bytes):
            print(f"{name}={value.hex()}")
        else:
            print(f"{name}={value}")
    return 1


def main() -> int:
    py_protocol = _import_protocol()
    lib = _load_dll()
    keys = {KEY_ID: KEY}
    frames = list(_frames(py_protocol))

    for i, frame in enumerate(frames):
        try:
            cpp = _cpp_encode(lib, frame, frame.payload)
            py = py_protocol.encode_frame(frame, keys)
        except Exception as exc:
            return _fail("encode", i, repr(exc), frame=frame)
        if cpp != py:
            return _fail("encode", i, "byte mismatch", cpp=cpp, python=py, frame=frame)
    print(f"PASS encode parity ({len(frames)} frames)")

    for i, frame in enumerate(frames):
        encoded = py_protocol.encode_frame(frame, keys)
        try:
            payload, fields = _cpp_decode(lib, encoded)
        except Exception as exc:
            return _fail("decode", i, repr(exc), encoded=encoded, frame=frame)
        expected_fields = FIELD_PACK.pack(
            int(frame.frame_type),
            frame.key_id,
            frame.source,
            frame.destination,
            frame.sequence,
            frame.nonce,
        )
        if payload != frame.payload or fields != expected_fields:
            return _fail(
                "decode",
                i,
                "round-trip mismatch",
                encoded=encoded,
                payload=payload,
                expected_payload=frame.payload,
                fields=fields,
                expected_fields=expected_fields,
                frame=frame,
            )
    print(f"PASS decode round-trip ({len(frames)} frames)")

    for i, frame in enumerate(frames):
        tampered = bytearray(py_protocol.encode_frame(frame, keys))
        tampered[-1] ^= 0x01
        rc = _cpp_decode_rc(lib, bytes(tampered))
        if rc != -1:
            return _fail("tamper", i, "MAC-tampered frame accepted", rc=rc, encoded=bytes(tampered), frame=frame)
    print(f"PASS tamper rejection ({len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
