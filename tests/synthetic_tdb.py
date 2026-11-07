"""Synthetic EA Sports TDB binary generator for self-contained deterministic testing."""

import struct
from pathlib import Path

from ncaa_dynasty_rerank.bitview import BitView


def create_synthetic_save(
    file_path: Path,
    teams_data: list[dict],
    games_data: list[dict],
) -> Path:
    """Creates a binary-valid EA Sports TDB database with TEAM and SCHD tables."""
    # Field definitions for TEAM table (record size: 64 bytes = 512 bits)
    team_fields = [
        {"name": "TGID", "type": 3, "offset": 0, "bits": 16},
        {"name": "TOID", "type": 3, "offset": 16, "bits": 16},
        {"name": "CGID", "type": 3, "offset": 32, "bits": 8},
        {"name": "DGID", "type": 3, "offset": 40, "bits": 8},
        {"name": "TSWI", "type": 3, "offset": 48, "bits": 8},
        {"name": "TSLO", "type": 3, "offset": 56, "bits": 8},
        {"name": "TCWI", "type": 3, "offset": 64, "bits": 8},
        {"name": "TCLO", "type": 3, "offset": 72, "bits": 8},
        {"name": "TBRK", "type": 3, "offset": 80, "bits": 8},
        {"name": "TBPR", "type": 3, "offset": 88, "bits": 8},
        {"name": "TCRK", "type": 3, "offset": 96, "bits": 8},
        {"name": "TCPR", "type": 3, "offset": 104, "bits": 8},
        {"name": "TCPT", "type": 3, "offset": 112, "bits": 16},
        {"name": "TCFP", "type": 3, "offset": 128, "bits": 8},
        {"name": "TMRK", "type": 3, "offset": 136, "bits": 8},
        {"name": "TMPP", "type": 3, "offset": 144, "bits": 8},
        {"name": "tmpp", "type": 3, "offset": 152, "bits": 16},
        {"name": "TMPV", "type": 3, "offset": 168, "bits": 8},
        {"name": "TDNA", "type": 0, "offset": 176, "bits": 128},  # 16 bytes string
        {"name": "TMNA", "type": 0, "offset": 304, "bits": 128},  # 16 bytes string
    ]
    team_len_bytes = 64
    team_max_records = len(teams_data)

    # Pack TEAM records
    team_records_buf = bytearray(team_len_bytes * team_max_records)
    for idx, t in enumerate(teams_data):
        rec_buf = bytearray(team_len_bytes)
        bv = BitView(rec_buf, big_endian=True)
        bv.set_bits(0, t["tgid"], 16)
        bv.set_bits(16, t["tgid"], 16)  # TOID = TGID
        bv.set_bits(32, t.get("conf_id", 0), 8)
        bv.set_bits(40, t.get("div_id", 0), 8)
        bv.set_bits(48, t.get("wins", 0), 8)
        bv.set_bits(56, t.get("losses", 0), 8)
        bv.set_bits(64, t.get("conf_wins", 0), 8)
        bv.set_bits(72, t.get("conf_losses", 0), 8)
        bv.set_bits(80, t.get("cfp_rank", 0), 8)
        bv.set_bits(88, t.get("cfp_prev_rank", 0), 8)
        bv.set_bits(96, t.get("coaches_rank", 0), 8)
        bv.set_bits(104, t.get("coaches_prev_rank", 0), 8)
        bv.set_bits(112, t.get("coaches_points", 0), 16)
        bv.set_bits(128, t.get("coaches_first_votes", 0), 8)
        bv.set_bits(136, t.get("ap_rank", 0), 8)
        bv.set_bits(144, t.get("ap_prev_rank", 0), 8)
        bv.set_bits(152, t.get("ap_points", 0), 16)
        bv.set_bits(168, t.get("ap_first_votes", 0), 8)
        bv.set_string(176, t.get("name", "Team"), 128)
        bv.set_string(304, t.get("mascot", "Mascot"), 128)
        team_records_buf[idx * team_len_bytes : (idx + 1) * team_len_bytes] = rec_buf

    # Field definitions for SCHD table (record size: 16 bytes = 128 bits)
    schd_fields = [
        {"name": "GATG", "type": 3, "offset": 0, "bits": 16},
        {"name": "GHTG", "type": 3, "offset": 16, "bits": 16},
        {"name": "GASC", "type": 3, "offset": 32, "bits": 8},
        {"name": "GHSC", "type": 3, "offset": 40, "bits": 8},
        {"name": "SEWN", "type": 3, "offset": 48, "bits": 8},
        {"name": "GSTA", "type": 3, "offset": 56, "bits": 8},
    ]
    schd_len_bytes = 16
    schd_max_records = len(games_data)

    schd_records_buf = bytearray(schd_len_bytes * schd_max_records)
    for idx, g in enumerate(games_data):
        rec_buf = bytearray(schd_len_bytes)
        bv = BitView(rec_buf, big_endian=True)
        bv.set_bits(0, g["away_tgid"], 16)
        bv.set_bits(16, g["home_tgid"], 16)
        bv.set_bits(32, g["away_score"], 8)
        bv.set_bits(40, g["home_score"], 8)
        bv.set_bits(48, g.get("week", 1), 8)
        bv.set_bits(56, g.get("status", 2), 8)
        schd_records_buf[idx * schd_len_bytes : (idx + 1) * schd_len_bytes] = rec_buf

    # Construct tables binary
    # Table 1: TEAM
    team_header = struct.pack(
        ">IIIIIHHIBBHI",
        0,
        6,
        team_len_bytes,
        team_len_bytes * 8,
        0,
        team_max_records,
        team_max_records,
        0,
        len(team_fields),
        0,
        0,
        0,
    ) + struct.pack(">I", 0)
    team_fdefs = b"".join(
        struct.pack(">II4sI", f["type"], f["offset"], f["name"].encode("latin1")[::-1], f["bits"]) for f in team_fields
    )
    team_body = team_header + team_fdefs + team_records_buf

    # Table 2: SCHD
    schd_header = struct.pack(
        ">IIIIIHHIBBHI",
        0,
        6,
        schd_len_bytes,
        schd_len_bytes * 8,
        0,
        schd_max_records,
        schd_max_records,
        0,
        len(schd_fields),
        0,
        0,
        0,
    ) + struct.pack(">I", 0)
    schd_fdefs = b"".join(
        struct.pack(">II4sI", f["type"], f["offset"], f["name"].encode("latin1")[::-1], f["bits"]) for f in schd_fields
    )
    schd_body = schd_header + schd_fdefs + schd_records_buf

    # Layout:
    # 0x00 - 0x18: file header (24 bytes)
    # 0x18 - 0x28: table directory (2 tables * 8 = 16 bytes)
    # table_data_start = 40
    team_offset = 0
    schd_offset = len(team_body)

    table_dir = b"MAET" + struct.pack(">I", team_offset) + b"DHCS" + struct.pack(">I", schd_offset)

    total_size = 24 + len(table_dir) + len(team_body) + len(schd_body)
    file_header = struct.pack(">HHBBHIIII", 0x4442, 8, 1, 0, 0, total_size, 0, 2, 0)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(file_header)
        f.write(table_dir)
        f.write(team_body)
        f.write(schd_body)

    return file_path
