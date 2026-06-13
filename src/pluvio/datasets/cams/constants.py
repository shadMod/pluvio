VARIABLE_MAP: dict[str, tuple[str, str]] = {
    "particulate_matter_10um": ("pm10_conc", "pm10_ugm3"),
    "particulate_matter_2.5um": ("pm2p5_conc", "pm2p5_ugm3"),
    "nitrogen_dioxide": ("no2_conc", "no2_ugm3"),
    "sulphur_dioxide": ("so2_conc", "so2_ugm3"),
    "ozone": ("o3_conc", "o3_ugm3"),
}

DEFAULT_VARIABLES = [
    "particulate_matter_10um",
    "particulate_matter_2.5um",
    "nitrogen_dioxide",
]
