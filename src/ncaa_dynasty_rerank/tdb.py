"""Pure Python EA Sports TDB (Madden / NCAA) database reader and writer."""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ncaa_dynasty_rerank.bitview import BitView


@dataclass
class TDBFieldDef:
    name: str
    type_id: int
    offset: int  # Bit offset within record
    bits: int  # Bit width


@dataclass
class TDBTableHeader:
    prior_crc: int
    data_allocation_type: int
    length_bytes: int
    length_bits: int
    zero: int
    max_records: int
    current_records: int
    unknown2: int
    num_fields: int
    index_count: int
    zero2: int
    zero3: int
    header_crc: int


class TdbCrc:
    """Big-endian CRC-32 calculator matching EA Sports TDB database specification."""

    def __init__(self) -> None:
        self.poly = 79764919  # 0x04C11DB7
        e = 0x80000000
        table = [0]
        n = 1
        while n < 16:
            e = ((e << 1) & 0xFFFFFFFF) ^ (0 if (e & 0x80000000) == 0 else self.poly)
            for r in range(n):
                table.append(e ^ table[r])
            n <<= 1
        self.table = table

    def crc32_be(self, e: int, data: bytes | bytearray) -> int:
        e = (0xFFFFFFFF ^ e) & 0xFFFFFFFF
        table = self.table
        for b in data:
            e = (e ^ (b << 24)) & 0xFFFFFFFF
            e = (((e << 4) & 0xFFFFFFFF) ^ table[(e >> 28) & 0xF]) & 0xFFFFFFFF
            e = (((e << 4) & 0xFFFFFFFF) ^ table[(e >> 28) & 0xF]) & 0xFFFFFFFF
        return (0xFFFFFFFF ^ e) & 0xFFFFFFFF

    def checksum(self, data: bytes | bytearray) -> int:
        return (~self.crc32_be(0, data)) & 0xFFFFFFFF


class TDBTable:
    def __init__(
        self,
        name: str,
        table_offset: int,
        header: TDBTableHeader,
        fields: dict[str, TDBFieldDef],
        field_defs_raw: bytes,
        records_data: bytearray,
        file_records_offset: int,
    ):
        self.name = name
        self.table_offset = table_offset
        self.header = header
        self.fields = fields
        self.field_defs_raw = field_defs_raw
        self.records_data = records_data
        self.file_records_offset = file_records_offset
        self.is_changed = False

    def get_record_bitview(self, record_index: int) -> BitView:
        start = record_index * self.header.length_bytes
        end = start + self.header.length_bytes
        return BitView(self.records_data[start:end], big_endian=True)

    def write_record_bitview(self, record_index: int, bv: BitView) -> None:
        start = record_index * self.header.length_bytes
        end = start + self.header.length_bytes
        self.records_data[start:end] = bv.buf
        self.is_changed = True


class TDBFile:
    """Reads and updates NCAA 14 dynasty save files."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path).resolve()
        self.tables: dict[str, TDBTable] = {}
        self.num_tables: int = 0
        self.table_data_start: int = 0
        self.db_size: int = 0
        self.table_order: list[tuple[str, int]] = []
        self._load()

    def _load(self) -> None:
        with open(self.file_path, "rb") as f:
            hdr = f.read(24)
            if len(hdr) < 24:
                raise ValueError(f"File {self.file_path} is too small to be a valid save.")

            magic, _version, _endian, _u1, _u2, db_size, _zero, num_tables, _u3 = struct.unpack(">HHBBHIIII", hdr)
            if magic != 0x4442:  # "DB"
                raise ValueError(f"Invalid magic 0x{magic:04x}; expected 0x4442 (DB).")

            self.num_tables = num_tables
            self.db_size = db_size
            defs_raw = f.read(num_tables * 8)
            self.table_data_start = f.tell()

            table_defs: dict[str, int] = {}
            table_order_list: list[tuple[str, int]] = []
            for i in range(num_tables):
                name_raw = defs_raw[i * 8 : i * 8 + 4]
                # In big-endian files, table names are reversed 4-char ASCII strings
                name = name_raw.decode("latin1", errors="ignore")[::-1]
                offset = struct.unpack(">I", defs_raw[i * 8 + 4 : i * 8 + 8])[0]
                table_defs[name] = offset
                table_order_list.append((name, offset))

            # Maintain deterministic file offset order of all tables
            self.table_order = sorted(table_order_list, key=lambda t: t[1])

            # Load tables of interest (TEAM and SCHD)
            for target_name in ["TEAM", "SCHD"]:
                if target_name not in table_defs:
                    continue

                t_offset = table_defs[target_name]
                f.seek(self.table_data_start + t_offset)
                thdr_raw = f.read(40)
                if len(thdr_raw) < 40:
                    continue

                (
                    prior_crc,
                    alloc_type,
                    len_bytes,
                    len_bits,
                    zero_val,
                    max_records,
                    cur_records,
                    unk2,
                    num_fields,
                    idx_cnt,
                    zero2,
                    zero3,
                    hdr_crc,
                ) = struct.unpack(">IIIIIHHIBBHI", thdr_raw[:36]) + (struct.unpack(">I", thdr_raw[36:40])[0],)

                header = TDBTableHeader(
                    prior_crc,
                    alloc_type,
                    len_bytes,
                    len_bits,
                    zero_val,
                    max_records,
                    cur_records,
                    unk2,
                    num_fields,
                    idx_cnt,
                    zero2,
                    zero3,
                    hdr_crc,
                )

                fdefs_raw = f.read(16 * num_fields)
                fields: dict[str, TDBFieldDef] = {}
                for fi in range(num_fields):
                    fdef_chunk = fdefs_raw[fi * 16 : fi * 16 + 16]
                    ftype, foff, fname_raw, fbits = struct.unpack(">II4sI", fdef_chunk)
                    fname = fname_raw.decode("latin1", errors="ignore")[::-1]
                    fields[fname] = TDBFieldDef(fname, ftype, foff, fbits)

                records_offset = f.tell()
                records_data = bytearray(f.read(len_bytes * max_records))

                self.tables[target_name] = TDBTable(
                    name=target_name,
                    table_offset=t_offset,
                    header=header,
                    fields=fields,
                    field_defs_raw=fdefs_raw,
                    records_data=records_data,
                    file_records_offset=records_offset,
                )

    def get_teams(self) -> list[dict[str, Any]]:
        """Returns all populated FBS teams from the TEAM table."""
        if "TEAM" not in self.tables:
            return []

        team_table = self.tables["TEAM"]
        fields = team_table.fields
        teams: list[dict[str, Any]] = []

        tdna_def = fields.get("TDNA")
        tmna_def = fields.get("TMNA")

        def read_val(rec_bv: BitView, key: str, default: int = 0) -> int:
            if key in fields:
                return rec_bv.get_bits(fields[key].offset, fields[key].bits)
            return default

        seen_tgids: set[int] = set()
        # In NCAA Football 14, records 0..125 are the active 126 FBS teams.
        # Records 126+ are FCS teams (conf 17), duplicate transition slots, and high school teams (conf 24).
        max_fbs_records = min(126, team_table.header.max_records)

        for r_idx in range(max_fbs_records):
            bv = team_table.get_record_bitview(r_idx)
            tgid = bv.get_bits(fields["TGID"].offset, fields["TGID"].bits)
            toid = bv.get_bits(fields["TOID"].offset, fields["TOID"].bits)

            # Populated teams have non-zero TGID equal to TOID
            if tgid == 0 or tgid != toid:
                continue

            conf_id = read_val(bv, "CGID")
            # Filter out non-FBS conferences (FCS=17, High School=24) and duplicate entries
            if conf_id in (17, 24) or tgid in seen_tgids:
                continue

            seen_tgids.add(tgid)
            name = bv.get_string(tdna_def.offset, tdna_def.bits) if tdna_def else ""
            mascot = bv.get_string(tmna_def.offset, tmna_def.bits) if tmna_def else ""

            teams.append(
                {
                    "record_index": r_idx,
                    "tgid": tgid,
                    "name": name,
                    "mascot": mascot,
                    "full_name": f"{name} {mascot}".strip(),
                    "conf_id": conf_id,
                    "div_id": read_val(bv, "DGID"),
                    "wins": read_val(bv, "TSWI"),
                    "losses": read_val(bv, "TSLO"),
                    "conf_wins": read_val(bv, "TCWI"),
                    "conf_losses": read_val(bv, "TCLO"),
                    "cfp_rank": read_val(bv, "TBRK"),
                    "cfp_prev_rank": read_val(bv, "TBPR"),
                    "ap_rank": read_val(bv, "TMRK"),
                    "ap_points": read_val(bv, "tmpp"),
                    "ap_first_votes": read_val(bv, "TMPV"),
                    "ap_prev_rank": read_val(bv, "TMPP"),
                    "coaches_rank": read_val(bv, "TCRK"),
                    "coaches_points": read_val(bv, "TCPT"),
                    "coaches_first_votes": read_val(bv, "TCFP"),
                    "coaches_prev_rank": read_val(bv, "TCPR"),
                }
            )

        return teams

    def get_schedule(self) -> list[dict[str, Any]]:
        """Returns all populated games from the SCHD table."""
        if "SCHD" not in self.tables:
            return []

        schd_table = self.tables["SCHD"]
        fields = schd_table.fields
        games: list[dict[str, Any]] = []

        for r_idx in range(schd_table.header.max_records):
            bv = schd_table.get_record_bitview(r_idx)
            away_tgid = bv.get_bits(fields["GATG"].offset, fields["GATG"].bits)
            home_tgid = bv.get_bits(fields["GHTG"].offset, fields["GHTG"].bits)
            away_score = bv.get_bits(fields["GASC"].offset, fields["GASC"].bits)
            home_score = bv.get_bits(fields["GHSC"].offset, fields["GHSC"].bits)
            week = bv.get_bits(fields["SEWN"].offset, fields["SEWN"].bits) if "SEWN" in fields else 0
            status = bv.get_bits(fields["GSTA"].offset, fields["GSTA"].bits) if "GSTA" in fields else 0

            is_played = (away_score > 0 or home_score > 0) and (away_tgid > 0 and home_tgid > 0)
            if not is_played:
                continue

            games.append(
                {
                    "record_index": r_idx,
                    "week": week,
                    "status": status,
                    "away_tgid": away_tgid,
                    "home_tgid": home_tgid,
                    "away_score": away_score,
                    "home_score": home_score,
                    "winner_tgid": home_tgid if home_score > away_score else away_tgid,
                    "loser_tgid": away_tgid if home_score > away_score else home_tgid,
                    "margin": abs(home_score - away_score),
                }
            )

        return games

    def get_all_schedule_records(self) -> list[dict[str, Any]]:
        """Returns all schedule records (both played and unplayed) from the SCHD table."""
        if "SCHD" not in self.tables:
            return []

        schd_table = self.tables["SCHD"]
        fields = schd_table.fields
        records: list[dict[str, Any]] = []

        for r_idx in range(schd_table.header.max_records):
            bv = schd_table.get_record_bitview(r_idx)
            away_tgid = bv.get_bits(fields["GATG"].offset, fields["GATG"].bits) if "GATG" in fields else 0
            home_tgid = bv.get_bits(fields["GHTG"].offset, fields["GHTG"].bits) if "GHTG" in fields else 0
            away_score = bv.get_bits(fields["GASC"].offset, fields["GASC"].bits) if "GASC" in fields else 0
            home_score = bv.get_bits(fields["GHSC"].offset, fields["GHSC"].bits) if "GHSC" in fields else 0
            week = bv.get_bits(fields["SEWN"].offset, fields["SEWN"].bits) if "SEWN" in fields else 0
            sewt = bv.get_bits(fields["SEWT"].offset, fields["SEWT"].bits) if "SEWT" in fields else 0
            sgnm = bv.get_bits(fields["SGNM"].offset, fields["SGNM"].bits) if "SGNM" in fields else 0
            status = bv.get_bits(fields["GSTA"].offset, fields["GSTA"].bits) if "GSTA" in fields else 0

            records.append(
                {
                    "record_index": r_idx,
                    "sgnm": sgnm,
                    "sewn": week,
                    "sewt": sewt,
                    "gsta": status,
                    "gatg": away_tgid,
                    "ghtg": home_tgid,
                    "away_score": away_score,
                    "home_score": home_score,
                }
            )

        return records

    def update_team_polls(self, team_updates: list[dict[str, Any]]) -> None:
        """Updates poll fields for teams in the TEAM table."""
        if "TEAM" not in self.tables:
            raise KeyError("TEAM table not loaded.")

        team_table = self.tables["TEAM"]
        fields = team_table.fields

        field_map = {
            "cfp_rank": "TBRK",
            "cfp_prev_rank": "TBPR",
            "coaches_rank": "TCRK",
            "coaches_prev_rank": "TCPR",
            "coaches_points": "TCPT",
            "coaches_first_votes": "TCFP",
            "ap_rank": "TMRK",
            "ap_prev_rank": "TMPP",
            "ap_points": "tmpp",
            "ap_first_votes": "TMPV",
        }

        tgid_to_record_idx: dict[int, int] = {}
        # Restrict mapping strictly to FBS records (0..125) and filter non-FBS / duplicate slots
        max_fbs_records = min(126, team_table.header.max_records)
        for r_idx in range(max_fbs_records):
            bv = team_table.get_record_bitview(r_idx)
            tgid = bv.get_bits(fields["TGID"].offset, fields["TGID"].bits)
            toid = bv.get_bits(fields["TOID"].offset, fields["TOID"].bits)
            conf_id = bv.get_bits(fields["CGID"].offset, fields["CGID"].bits) if "CGID" in fields else 0
            if tgid > 0 and tgid == toid and conf_id not in (17, 24) and tgid not in tgid_to_record_idx:
                tgid_to_record_idx[tgid] = r_idx

        for update in team_updates:
            tgid = update["tgid"]
            if tgid not in tgid_to_record_idx:
                continue

            r_idx = tgid_to_record_idx[tgid]
            bv = team_table.get_record_bitview(r_idx)

            for key, db_field in field_map.items():
                if key in update and db_field in fields:
                    f_def = fields[db_field]
                    bv.set_bits(f_def.offset, int(update[key]), f_def.bits)

            team_table.write_record_bitview(r_idx, bv)

    def update_schedule_games(self, game_updates: list[dict[str, Any]]) -> None:
        """Updates team participants (GATG, GHTG) for specific records in the SCHD table."""
        if "SCHD" not in self.tables:
            raise KeyError("SCHD table not loaded.")

        schd_table = self.tables["SCHD"]
        fields = schd_table.fields
        if "GATG" not in fields or "GHTG" not in fields:
            raise KeyError("GATG or GHTG fields missing from SCHD table.")

        gatg_def = fields["GATG"]
        ghtg_def = fields["GHTG"]

        for update in game_updates:
            r_idx = update["record_index"]
            if r_idx < 0 or r_idx >= schd_table.header.max_records:
                continue

            bv = schd_table.get_record_bitview(r_idx)
            if "away_tgid" in update:
                bv.set_bits(gatg_def.offset, int(update["away_tgid"]), gatg_def.bits)
            if "home_tgid" in update:
                bv.set_bits(ghtg_def.offset, int(update["home_tgid"]), ghtg_def.bits)

            schd_table.write_record_bitview(r_idx, bv)

    def save(self, output_path: str | Path | None = None) -> None:
        """Writes modified table record buffers back to the file and updates successor table CRCs."""
        target_path = Path(output_path or self.file_path).resolve()

        if target_path != self.file_path:
            import shutil

            shutil.copyfile(self.file_path, target_path)

        crc_calc = TdbCrc()
        with open(target_path, "r+b") as f:
            for table in self.tables.values():
                if not table.is_changed:
                    continue

                # 1. Write modified records data
                f.seek(table.file_records_offset)
                f.write(table.records_data)
                table.is_changed = False

                # 2. Compute table checksum over field_defs + records_data
                payload = bytes(table.field_defs_raw) + bytes(table.records_data)
                calc_crc = crc_calc.checksum(payload)

                # 3. Locate the table succeeding this one in file offset order
                curr_idx = next(
                    (i for i, (t_name, _) in enumerate(self.table_order) if t_name == table.name),
                    None,
                )
                if curr_idx is None:
                    continue

                if curr_idx + 1 < len(self.table_order):
                    # Next table's header starts with prior_crc (uint32 big-endian at offset 0)
                    next_name, next_offset = self.table_order[curr_idx + 1]
                    f.seek(self.table_data_start + next_offset)
                    f.write(struct.pack(">I", calc_crc))
                    if next_name in self.tables:
                        self.tables[next_name].header.prior_crc = calc_crc
                elif self.db_size > 0:
                    # Last table in file: write to EOF CRC buffer at db_size - 4 if space exists
                    f.seek(0, 2)
                    file_len = f.tell()
                    eof_offset = self.db_size - 4
                    if eof_offset >= 0 and eof_offset + 4 <= file_len:
                        f.seek(eof_offset)
                        f.write(struct.pack(">I", calc_crc))
