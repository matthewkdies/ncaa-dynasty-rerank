"""Pure Python bit-level reader and writer for EA Sports big-endian data buffers."""


class BitView:
    """Provides bit-level read and write access to a bytearray buffer."""

    def __init__(self, buf: bytearray, big_endian: bool = True):
        self.buf = buf
        self.big_endian = big_endian

    def get_bits(self, offset: int, bits: int, signed: bool = False) -> int:
        """Extracts `bits` number of bits starting at bit `offset`."""
        if bits <= 0:
            raise ValueError(f"Bits must be positive, got {bits}")

        available = len(self.buf) * 8 - offset
        if bits > available or offset < 0:
            raise ValueError(f"Cannot read {bits} bit(s) from offset {offset}; {available} available.")

        value = 0
        i = 0
        while i < bits:
            remaining = bits - i
            bit_offset = offset & 7
            byte_idx = offset >> 3
            current_byte = self.buf[byte_idx]
            read = min(remaining, 8 - bit_offset)

            if self.big_endian:
                mask = ~(0xFF << read) & 0xFF
                read_bits = (current_byte >> (8 - read - bit_offset)) & mask
                value = (value << read) | read_bits
            else:
                mask = ~(0xFF << read) & 0xFF
                read_bits = (current_byte >> bit_offset) & mask
                value |= read_bits << i

            offset += read
            i += read

        if signed and bits != 32 and (value & (1 << (bits - 1))):
            value |= -1 ^ ((1 << bits) - 1)

        return value

    def set_bits(self, offset: int, value: int, bits: int) -> None:
        """Writes `bits` number of bits for `value` starting at bit `offset`."""
        if bits <= 0:
            raise ValueError(f"Bits must be positive, got {bits}")

        available = len(self.buf) * 8 - offset
        if bits > available or offset < 0:
            raise ValueError(f"Cannot set {bits} bit(s) at offset {offset}; {available} available.")

        # Range validation: value must fit in unsigned `bits` bits
        max_val = (1 << bits) - 1
        if value < 0 or value > max_val:
            raise ValueError(f"Value {value} out of range for {bits}-bit unsigned field (0 to {max_val}).")

        i = 0
        while i < bits:
            remaining = bits - i
            bit_offset = offset & 7
            byte_idx = offset >> 3
            wrote = min(remaining, 8 - bit_offset)

            if self.big_endian:
                mask = (~(0xFF << wrote)) & 0xFF
                write_bits = (value >> (bits - i - wrote)) & mask
                dest_shift = 8 - bit_offset - wrote
                dest_mask = (~(mask << dest_shift)) & 0xFF
                self.buf[byte_idx] = (self.buf[byte_idx] & dest_mask) | (write_bits << dest_shift)
            else:
                mask = ~(0xFF << wrote) & 0xFF
                write_bits = value & mask
                value >>= wrote
                dest_mask = (~(mask << bit_offset)) & 0xFF
                self.buf[byte_idx] = (self.buf[byte_idx] & dest_mask) | (write_bits << bit_offset)

            offset += wrote
            i += wrote

    def get_string(self, offset_bits: int, bits: int, encoding: str = "latin1") -> str:
        """Reads a fixed-width null-padded string from byte boundary."""
        byte_start = offset_bits // 8
        byte_len = bits // 8
        raw_slice = self.buf[byte_start : byte_start + byte_len]
        return raw_slice.split(b"\x00")[0].decode(encoding, errors="ignore").strip()

    def set_string(self, offset_bits: int, text: str, bits: int, encoding: str = "latin1") -> None:
        """Writes a fixed-width null-padded string at byte boundary."""
        byte_start = offset_bits // 8
        byte_len = bits // 8
        encoded = text.encode(encoding)[:byte_len]
        padded = encoded.ljust(byte_len, b"\x00")
        self.buf[byte_start : byte_start + byte_len] = padded
