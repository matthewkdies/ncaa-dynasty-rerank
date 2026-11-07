import pytest

from ncaa_dynasty_rerank.bitview import BitView


def test_bitview_unsigned_integers_across_byte_boundaries():
    buf = bytearray(16)
    bv = BitView(buf, big_endian=True)

    # 1. 8-bit at offset 0
    bv.set_bits(0, 255, 8)
    assert bv.get_bits(0, 8) == 255

    # 2. 1-bit flags
    bv.set_bits(8, 1, 1)
    bv.set_bits(9, 0, 1)
    assert bv.get_bits(8, 1) == 1
    assert bv.get_bits(9, 1) == 0

    # 3. 10-bit integer starting at bit 10 (spans byte 1 and byte 2)
    # 1023 is max for 10 bits
    bv.set_bits(10, 1023, 10)
    assert bv.get_bits(10, 10) == 1023

    # 4. 24-bit integer starting at bit 20 (spans byte 2, 3, 4, 5)
    test_val_24 = 0xA1B2C3
    bv.set_bits(20, test_val_24, 24)
    assert bv.get_bits(20, 24) == test_val_24

    # 5. Verify earlier bits were not clobbered
    assert bv.get_bits(0, 8) == 255
    assert bv.get_bits(8, 1) == 1
    assert bv.get_bits(9, 1) == 0
    assert bv.get_bits(10, 10) == 1023


def test_bitview_signed_integers():
    buf = bytearray(8)
    bv = BitView(buf, big_endian=True)
    # -1 in 8-bit two's complement is 255
    bv.set_bits(0, 255, 8)
    assert bv.get_bits(0, 8, signed=True) == -1

    # -12 in 6-bit two's complement: 64 - 12 = 52
    bv.set_bits(8, 52, 6)
    assert bv.get_bits(8, 6, signed=True) == -12


def test_bitview_overflow_bounds_validation():
    buf = bytearray(4)
    bv = BitView(buf, big_endian=True)

    # 8-bit field cannot hold 256
    with pytest.raises(ValueError, match="out of range for 8-bit"):
        bv.set_bits(0, 256, 8)

    # Cannot hold negative value in unsigned set_bits
    with pytest.raises(ValueError, match="out of range for 8-bit"):
        bv.set_bits(0, -1, 8)

    # 10-bit field cannot hold 1024
    with pytest.raises(ValueError, match="out of range for 10-bit"):
        bv.set_bits(0, 1024, 10)


def test_bitview_buffer_bounds_validation():
    buf = bytearray(2)
    bv = BitView(buf, big_endian=True)

    with pytest.raises(ValueError, match="available"):
        bv.get_bits(12, 8)

    with pytest.raises(ValueError, match="available"):
        bv.set_bits(12, 1, 8)

    with pytest.raises(ValueError, match="Bits must be positive"):
        bv.get_bits(0, 0)

    with pytest.raises(ValueError, match="Bits must be positive"):
        bv.set_bits(0, 1, 0)


def test_bitview_string_read_write():
    buf = bytearray(32)
    bv = BitView(buf, big_endian=True)

    bv.set_string(0, "Clemson Tigers", 176)
    assert bv.get_string(0, 176) == "Clemson Tigers"

    # Overwrite with shorter string
    bv.set_string(0, "Utah", 176)
    assert bv.get_string(0, 176) == "Utah"
