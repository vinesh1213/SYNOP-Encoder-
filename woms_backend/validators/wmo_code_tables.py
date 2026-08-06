# =============================================================================
# SYNOP Validation Engine — WMO FM-12 Code Tables
# =============================================================================
# Reference data for every coded value used in a SYNOP message.
# Sources: WMO Manual on Codes No. 306 — FM-12 XIII Ext. SYNOP
#
# Each table is exposed as a frozenset (for membership checks) or a dict
# (when the validator also needs descriptive labels).
# =============================================================================

from __future__ import annotations

# ---------------------------------------------------------------------------
# Code Table 0975  —  iw  (Wind speed indicator)
# ---------------------------------------------------------------------------
# 0 = m/s (estimated)
# 1 = m/s (from anemometer)
# 3 = knots (estimated)
# 4 = knots (from anemometer)
VALID_IW_CODES = frozenset({"0", "1", "3", "4"})

IW_DESCRIPTIONS = {
    "0": "Wind speed in m/s (estimated)",
    "1": "Wind speed in m/s (from anemometer)",
    "3": "Wind speed in knots (estimated)",
    "4": "Wind speed in knots (from anemometer)",
}


# ---------------------------------------------------------------------------
# Code Table 1860  —  iR  (Precipitation data indicator)
# ---------------------------------------------------------------------------
VALID_IR_CODES = frozenset({"0", "1", "2", "3", "4"})

IR_DESCRIPTIONS = {
    "0": "Precipitation in Section 1 and Section 3",
    "1": "Precipitation in Section 1 only",
    "2": "Precipitation in Section 3 only",
    "3": "No precipitation data",
    "4": "Station not staffed (automatic)",
}


# ---------------------------------------------------------------------------
# Code Table 1855  —  iX  (Station type / weather indicator)
# ---------------------------------------------------------------------------
VALID_IX_CODES = frozenset({"1", "2", "3", "4", "5", "6", "7"})

IX_DESCRIPTIONS = {
    "1": "Manned station, weather group included",
    "2": "Manned station, weather group omitted (no significant weather)",
    "3": "Manned station, weather group omitted (data not available)",
    "4": "Automatic station, weather group included (using code table 4680)",
    "5": "Automatic station, weather group omitted (no significant weather)",
    "6": "Automatic station, weather group omitted (data not available)",
    "7": "Automatic station, weather group included (using code table 4677)",
}


# ---------------------------------------------------------------------------
# Code Table 1600  —  h  (Height of base of lowest cloud)
# ---------------------------------------------------------------------------
VALID_H_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

H_DESCRIPTIONS = {
    "0": "0–50 m",
    "1": "50–100 m",
    "2": "100–200 m",
    "3": "200–300 m",
    "4": "300–600 m",
    "5": "600–1000 m",
    "6": "1000–1500 m",
    "7": "1500–2000 m",
    "8": "2000–2500 m",
    "9": "≥ 2500 m or no clouds",
    "/": "Height not observable / unknown",
}


# ---------------------------------------------------------------------------
# Code Table 4377  —  VV  (Horizontal visibility)
# ---------------------------------------------------------------------------
# 00       : < 0.1 km
# 01–50    : visibility = VV / 10  (in km)
# 51–55    : reserved / not used
# 56–80    : visibility = VV − 50  (in km)
# 81–88    : visibility = 35 + (VV − 80) * 5  (in km)  [i.e. 35, 40, …, 70 km]
# 89       : > 70 km
# 90–99    : special codes (table below)
VALID_VV_RANGE = set(range(0, 100))  # 00–99 are all potentially valid
VALID_VV_RANGE.add("/")              # '//' means not available

VV_SPECIAL = {
    90: "< 0.05 km (dense fog)",
    91: "0.05 km",
    92: "0.2 km",
    93: "0.5 km",
    94: "1 km",
    95: "2 km",
    96: "4 km",
    97: "10 km",
    98: "20 km",
    99: "≥ 50 km",
}

# Reserved VV codes that should trigger a WARNING
VV_RESERVED = frozenset({51, 52, 53, 54, 55})


# ---------------------------------------------------------------------------
# Code Table 2700  —  N  (Total cloud amount in oktas)
# ---------------------------------------------------------------------------
VALID_N_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

N_DESCRIPTIONS = {
    "0": "Clear sky (0 oktas)",
    "1": "1 okta or less but not zero",
    "2": "2 oktas",
    "3": "3 oktas",
    "4": "4 oktas",
    "5": "5 oktas",
    "6": "6 oktas",
    "7": "7 oktas",
    "8": "8 oktas (overcast)",
    "9": "Sky obscured",
    "/": "Cloud cover not observable",
}


# ---------------------------------------------------------------------------
# Code Table 0877  —  dd  (True wind direction, tens of degrees)
# ---------------------------------------------------------------------------
# Valid: 00 (calm), 01–36 (10°–360°), 99 (variable)
VALID_DD_CODES = frozenset({0, 99} | set(range(1, 37)))


# ---------------------------------------------------------------------------
# Code Table 0200  —  a  (Characteristic of pressure tendency)
# ---------------------------------------------------------------------------
VALID_A_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8"})

A_DESCRIPTIONS = {
    "0": "Increasing then decreasing; same or higher than 3h ago",
    "1": "Increasing then steady; or increasing then increasing more slowly",
    "2": "Increasing steadily or unsteadily",
    "3": "Decreasing or steady, then increasing; or increasing then increasing more rapidly",
    "4": "Steady; same as 3h ago",
    "5": "Decreasing then increasing; same or lower than 3h ago",
    "6": "Decreasing then steady; or decreasing then decreasing more slowly",
    "7": "Decreasing steadily or unsteadily",
    "8": "Steady or increasing, then decreasing; or decreasing then decreasing more rapidly",
}

# Tendency codes that indicate pressure rise
A_RISING = frozenset({"0", "1", "2", "3"})
# Tendency codes that indicate pressure steady
A_STEADY = frozenset({"4"})
# Tendency codes that indicate pressure fall
A_FALLING = frozenset({"5", "6", "7", "8"})


# ---------------------------------------------------------------------------
# Code Table 4677  —  ww  (Present weather, manned stations)
# ---------------------------------------------------------------------------
VALID_WW_CODES = frozenset(range(0, 100))  # 00–99

# Grouped categories for cross-validation
WW_NO_PRECIPITATION = frozenset(range(0, 4))     # 00–03: no significant weather
WW_HAZE_DUST = frozenset(range(4, 10))            # 04–09: haze, dust, visibility
WW_VISIBILITY = frozenset(range(10, 20))           # 10–19: mist, fog patches
WW_RECENT = frozenset(range(20, 30))               # 20–29: weather in preceding hour
WW_DUST_STORM = frozenset(range(30, 40))           # 30–39: dust/sandstorm
WW_FOG = frozenset(range(40, 50))                  # 40–49: fog, ice fog
WW_DRIZZLE = frozenset(range(50, 60))              # 50–59: drizzle
WW_RAIN = frozenset(range(60, 70))                 # 60–69: rain
WW_SNOW = frozenset(range(70, 80))                 # 70–79: snow
WW_SHOWERS = frozenset(range(80, 91))              # 80–90: showers
WW_THUNDERSTORM = frozenset(range(91, 100))        # 91–99: thunderstorm

# Any ww code that implies precipitation is occurring
WW_PRECIPITATION = (
    WW_DRIZZLE | WW_RAIN | WW_SNOW | WW_SHOWERS | WW_THUNDERSTORM
)


# ---------------------------------------------------------------------------
# Code Table 4561  —  W1, W2  (Past weather)
# ---------------------------------------------------------------------------
VALID_W_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

W_DESCRIPTIONS = {
    "0": "Cloud covering ½ or less of the sky",
    "1": "Cloud covering more than ½ of the sky during part of the period and ½ or less during part",
    "2": "Cloud covering more than ½ of the sky throughout",
    "3": "Sandstorm, duststorm, or blowing snow",
    "4": "Fog or ice fog, or thick haze",
    "5": "Drizzle",
    "6": "Rain",
    "7": "Snow, or rain and snow mixed",
    "8": "Shower(s)",
    "9": "Thunderstorm(s) with or without precipitation",
}


# ---------------------------------------------------------------------------
# Code Table 0500  —  CL  (Clouds of the genera Stratocumulus,
#                           Stratus, Cumulus, Cumulonimbus)
# ---------------------------------------------------------------------------
VALID_CL_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

CL_DESCRIPTIONS = {
    "0": "No CL clouds",
    "1": "Cumulus humilis or fractus (fair weather)",
    "2": "Cumulus mediocris or congestus (no anvil)",
    "3": "Cumulonimbus calvus (no anvil, no fibrous top)",
    "4": "Stratocumulus cumulogenitus",
    "5": "Stratocumulus (not cumulogenitus)",
    "6": "Stratus nebulosus or fractus (continuous layer)",
    "7": "Stratus fractus or Cumulus fractus (bad weather)",
    "8": "Cumulus and Stratocumulus (not cumulogenitus)",
    "9": "Cumulonimbus capillatus (with anvil)",
    "/": "CL clouds not visible or observation not made",
}


# ---------------------------------------------------------------------------
# Code Table 0515  —  CM  (Clouds of the genera Altocumulus,
#                           Altostratus, Nimbostratus)
# ---------------------------------------------------------------------------
VALID_CM_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

CM_DESCRIPTIONS = {
    "0": "No CM clouds",
    "1": "Altostratus translucidus",
    "2": "Altostratus opacus or Nimbostratus",
    "3": "Altocumulus translucidus (single level)",
    "4": "Altocumulus translucidus (patches, changing)",
    "5": "Altocumulus translucidus in bands",
    "6": "Altocumulus cumulogenitus",
    "7": "Altocumulus (multiple layers) or with Altostratus",
    "8": "Altocumulus castellanus or floccus",
    "9": "Altocumulus of chaotic sky",
    "/": "CM clouds not visible or observation not made",
}


# ---------------------------------------------------------------------------
# Code Table 0509  —  CH  (Clouds of the genera Cirrus,
#                           Cirrocumulus, Cirrostratus)
# ---------------------------------------------------------------------------
VALID_CH_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

CH_DESCRIPTIONS = {
    "0": "No CH clouds",
    "1": "Cirrus fibratus (not progressively invading sky)",
    "2": "Cirrus spissatus (dense, in patches)",
    "3": "Cirrus spissatus cumulonimbogenitus",
    "4": "Cirrus uncinus or fibratus (progressively invading sky)",
    "5": "Cirrus / Cirrostratus below 45° elevation",
    "6": "Cirrus / Cirrostratus above 45° elevation",
    "7": "Cirrostratus covering whole sky",
    "8": "Cirrostratus not covering whole sky, not progressively invading",
    "9": "Cirrocumulus predominant",
    "/": "CH clouds not visible or observation not made",
}


# ---------------------------------------------------------------------------
# Code Table 3590  —  tR  (Duration of precipitation)
# ---------------------------------------------------------------------------
VALID_TR_CODES = frozenset({"1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

TR_DESCRIPTIONS = {
    "1": "6 hours",
    "2": "12 hours",
    "3": "18 hours",
    "4": "24 hours",
    "5": "1 hour",
    "6": "2 hours",
    "7": "3 hours",
    "8": "9 hours",
    "9": "15 hours",
    "/": "Duration not known",
}


# ---------------------------------------------------------------------------
# Code Table 0901  —  E  (State of the ground without snow)
# ---------------------------------------------------------------------------
VALID_E_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})

E_DESCRIPTIONS = {
    "0": "Surface of ground dry (without cracks, no appreciable dust or sand)",
    "1": "Surface of ground moist",
    "2": "Surface of ground wet (standing water in pools)",
    "3": "Flooded",
    "4": "Surface of ground frozen",
    "5": "Glaze on ground",
    "6": "Loose dry dust or sand not covering ground completely",
    "7": "Thin cover of loose dry dust or sand covering ground completely",
    "8": "Moderate or thick cover of loose dry dust or sand",
    "9": "Extremely dry with cracks",
    "/": "State of ground not observable",
}


# ---------------------------------------------------------------------------
# Code Table 0833  —  Nh  (Amount of low/middle cloud)
# ---------------------------------------------------------------------------
VALID_NH_CODES = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/"})


# ---------------------------------------------------------------------------
# Wind speed physical limits (used by wind_validator.py)
# ---------------------------------------------------------------------------
MAX_WIND_SPEED_MS = 113.0    # ~220 knots — strongest recorded gust margin
MAX_WIND_SPEED_KT = 220.0


# ---------------------------------------------------------------------------
# Pressure physical limits
# ---------------------------------------------------------------------------
STATION_PRESSURE_MIN = 500.0   # hPa — high altitude stations
STATION_PRESSURE_MAX = 1100.0  # hPa
MSL_PRESSURE_MIN = 870.0       # hPa — strongest typhoons
MSL_PRESSURE_MAX = 1084.0      # hPa — record Siberian high + margin


# ---------------------------------------------------------------------------
# Temperature physical limits
# ---------------------------------------------------------------------------
TEMPERATURE_MIN = -80.0   # °C — per WMO/IMD manual observatory standard
TEMPERATURE_MAX = 60.0    # °C — beyond Death Valley record


# ---------------------------------------------------------------------------
# Rainfall physical limits
# ---------------------------------------------------------------------------
MAX_RAINFALL_SINGLE_PERIOD = 500.0   # mm — extreme warning threshold
MAX_RAINFALL_24H = 1200.0            # mm — record events (Réunion)
