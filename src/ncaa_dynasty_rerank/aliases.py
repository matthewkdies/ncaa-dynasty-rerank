"""Canonical mappings and alias resolution for NCAA Football 14 conferences and teams."""

import re

# Canonical Conference ID mapping and aliases
CONFERENCE_MAP: dict[int, str] = {
    0: "ACC",
    1: "Big Ten",
    2: "Big 12",
    3: "American",
    4: "C-USA",
    5: "Independents",
    7: "MAC",
    9: "Mountain West",
    10: "Pac-12",
    11: "SEC",
    13: "Sun Belt",
    17: "FCS",
    24: "Generic / High School",
}

CONFERENCE_ALIASES: dict[str, int] = {
    # SEC (11)
    "sec": 11,
    "southeastern": 11,
    "southeastern_conference": 11,
    # Big Ten (1)
    "big10": 1,
    "big_10": 1,
    "bigten": 1,
    "big_ten": 1,
    "b1g": 1,
    "b10": 1,
    # ACC (0)
    "acc": 0,
    "atlantic_coast": 0,
    "atlantic_coast_conference": 0,
    # Big 12 (2)
    "big12": 2,
    "big_12": 2,
    "b12": 2,
    "bigxii": 2,
    # Pac-12 (10)
    "pac12": 10,
    "pac_12": 10,
    "pac": 10,
    "pac10": 10,
    "pac_10": 10,
    # Independents (5)
    "independents": 5,
    "independent": 5,
    "ind": 5,
    "indy": 5,
    # American (3)
    "american": 3,
    "aac": 3,
    "american_athletic": 3,
    # Mountain West (9)
    "mountain_west": 9,
    "mountainwest": 9,
    "mwc": 9,
    # Sun Belt (13)
    "sun_belt": 13,
    "sunbelt": 13,
    "sbc": 13,
    # MAC (7)
    "mac": 7,
    "mid_american": 7,
    "midamerican": 7,
    # C-USA (4)
    "cusa": 4,
    "c_usa": 4,
    "conference_usa": 4,
    # FCS (17)
    "fcs": 17,
    "fcs_east": 17,
    "fcs_west": 17,
    "fcs_midwest": 17,
    "fcs_northwest": 17,
    # Generic / High School (24)
    "generic": 24,
    "high_school": 24,
    "hs": 24,
}

# Canonical Team ID mapping and aliases for NCAA Football 14 FBS programs
TEAM_MAP: dict[int, str] = {
    1: "Air Force",
    2: "Akron",
    3: "Alabama",
    4: "Arizona",
    5: "Arizona State",
    6: "Arkansas",
    7: "Arkansas State",
    8: "Army",
    9: "Auburn",
    10: "Ball State",
    11: "Baylor",
    12: "Boise State",
    13: "Boston College",
    14: "Bowling Green",
    15: "Buffalo",
    16: "BYU",
    17: "California",
    18: "Central Michigan",
    19: "Cincinnati",
    20: "Colorado",
    21: "Clemson",
    22: "Colorado State",
    23: "Connecticut",
    24: "Duke",
    25: "East Carolina",
    26: "Eastern Michigan",
    27: "Florida",
    28: "Florida Atlantic",
    29: "FIU",
    30: "Georgia",
    31: "Florida State",
    32: "Fresno State",
    33: "Georgia Tech",
    34: "Hawaii",
    35: "Houston",
    36: "Idaho",
    37: "Illinois",
    38: "Indiana",
    39: "Iowa",
    40: "Iowa State",
    41: "Kansas",
    42: "Kansas State",
    43: "Kent State",
    44: "Kentucky",
    45: "LSU",
    46: "Louisiana Tech",
    47: "Louisville",
    48: "Marshall",
    49: "Maryland",
    50: "Memphis",
    51: "Michigan",
    52: "Miami (FL)",
    53: "Miami (OH)",
    54: "Michigan State",
    55: "Middle Tennessee",
    56: "Minnesota",
    57: "Mississippi State",
    58: "Missouri",
    59: "Navy",
    60: "Nebraska",
    61: "Nevada",
    62: "UNLV",
    63: "New Mexico",
    64: "New Mexico State",
    65: "North Carolina",
    66: "NC State",
    67: "North Texas",
    68: "Notre Dame",
    69: "Northern Illinois",
    70: "Ohio State",
    71: "Oklahoma",
    72: "Oklahoma State",
    73: "Ole Miss",
    74: "Oregon",
    75: "Oregon State",
    76: "Penn State",
    77: "Pittsburgh",
    78: "Purdue",
    79: "Rice",
    80: "Rutgers",
    81: "SMU",
    82: "South Carolina",
    83: "South Florida",
    84: "USC",
    85: "Southern Miss",
    86: "Stanford",
    87: "Syracuse",
    88: "Tennessee",
    89: "Texas A&M",
    90: "TCU",
    91: "Temple",
    92: "Texas Tech",
    93: "Toledo",
    94: "Tulane",
    95: "Tulsa",
    96: "UAB",
    97: "Texas",
    98: "UCF",
    99: "UL Lafayette",
    100: "UL Monroe",
    101: "Utah",
    102: "Utah State",
    103: "UTEP",
    104: "Vanderbilt",
    105: "Virginia",
    106: "Virginia Tech",
    107: "Wake Forest",
    108: "Washington",
    109: "Washington State",
    110: "Western Michigan",
    111: "Western Kentucky",
    112: "Wisconsin",
    113: "Wyoming",
    118: "UTSA",
    119: "Texas State",
    120: "South Alabama",
    121: "Georgia State",
    122: "Old Dominion",
    123: "Charlotte",
    124: "Georgia Southern",
    125: "Appalachian State",
    126: "West Virginia",
}

TEAM_ALIASES: dict[str, int] = {
    # Alabama (3)
    "alabama": 3,
    "bama": 3,
    "crimson_tide": 3,
    "crimsontide": 3,
    # Ohio State (70)
    "ohio_state": 70,
    "ohiostate": 70,
    "osu": 70,
    "buckeyes": 70,
    # Florida (27)
    "florida": 27,
    "uf": 27,
    "gators": 27,
    # Michigan (51)
    "michigan": 51,
    "um": 51,
    "u_of_m": 51,
    "wolverines": 51,
    # Oklahoma (71)
    "oklahoma": 71,
    "ou": 71,
    "sooners": 71,
    # Oklahoma State (72)
    "oklahoma_state": 72,
    "oklahomastate": 72,
    "okstate": 72,
    "ok_state": 72,
    "cowboys": 72,
    # Texas (97)
    "texas": 97,
    "ut": 97,
    "longhorns": 97,
    # Notre Dame (68)
    "notre_dame": 68,
    "notredame": 68,
    "nd": 68,
    "fighting_irish": 68,
    "irish": 68,
    # LSU (45)
    "lsu": 45,
    "louisiana_state": 45,
    "tigers_lsu": 45,
    # Georgia (30)
    "georgia": 30,
    "uga": 30,
    "bulldogs": 30,
    # Clemson (21)
    "clemson": 21,
    # USC (84)
    "usc": 84,
    "southern_cal": 84,
    "southern_california": 84,
    "trojans": 84,
    # Penn State (76)
    "penn_state": 76,
    "pennstate": 76,
    "psu": 76,
    "nittany_lions": 76,
    # Florida State (31)
    "florida_state": 31,
    "floridastate": 31,
    "fsu": 31,
    "seminoles": 31,
    # Miami (52)
    "miami": 52,
    "miami_fl": 52,
    "the_u": 52,
    "canes": 52,
    "hurricanes": 52,
    # Tennessee (88)
    "tennessee": 88,
    "tenn": 88,
    "vols": 88,
    "volunteers": 88,
    # Nebraska (60)
    "nebraska": 60,
    "neb": 60,
    "huskers": 60,
    "cornhuskers": 60,
    # Texas A&M (89)
    "texas_am": 89,
    "tamu": 89,
    "aggies": 89,
    # Auburn (9)
    "auburn": 9,
    "aub": 9,
    "war_eagle": 9,
    # Oregon (74)
    "oregon": 74,
    "ducks": 74,
    # Washington (108)
    "washington": 108,
    "uw": 108,
    "huskies": 108,
    # Wisconsin (112)
    "wisconsin": 112,
    "badgers": 112,
    # Boise State (12)
    "boise_state": 12,
    "boise": 12,
    "bsu": 12,
    "broncos": 12,
    # West Virginia (126)
    "west_virginia": 126,
    "wvu": 126,
    "mountaineers": 126,
}

# Populate automatic aliases from TEAM_MAP
for _tgid, _name in TEAM_MAP.items():
    _normalized = re.sub(r"[^a-z0-9]+", "_", _name.lower()).strip("_")
    TEAM_ALIASES.setdefault(_normalized, _tgid)
    TEAM_ALIASES.setdefault(_normalized.replace("_", ""), _tgid)


def normalize_identifier(value: str) -> str:
    """Normalizes string name by stripping non-alphanumeric chars and lowercasing."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def resolve_conference_id(val: str | int) -> int:
    """Resolves conference string alias or int ID to canonical conference integer ID."""
    if isinstance(val, int):
        return val

    s = str(val).strip()
    if s.isdigit():
        return int(s)

    normalized = normalize_identifier(s)
    # Check directly or without underscores
    if normalized in CONFERENCE_ALIASES:
        return CONFERENCE_ALIASES[normalized]
    no_under = normalized.replace("_", "")
    if no_under in CONFERENCE_ALIASES:
        return CONFERENCE_ALIASES[no_under]

    raise ValueError(
        f"Unknown conference alias or ID: '{val}'. "
        f"Valid examples: 'sec', 'big10', 'acc', 'big12', 'pac12', 'mwc', 'aac', or numeric ID."
    )


def resolve_team_id(val: str | int) -> int:
    """Resolves team string alias or TGID to canonical team integer ID."""
    if isinstance(val, int):
        return val

    s = str(val).strip()
    if s.isdigit():
        return int(s)

    normalized = normalize_identifier(s)
    if normalized in TEAM_ALIASES:
        return TEAM_ALIASES[normalized]
    no_under = normalized.replace("_", "")
    if no_under in TEAM_ALIASES:
        return TEAM_ALIASES[no_under]

    raise ValueError(
        f"Unknown team alias or TGID: '{val}'. "
        f"Valid examples: 'alabama', 'osu', 'michigan', 'texas', 'notre_dame', 'wvu', or numeric TGID."
    )
