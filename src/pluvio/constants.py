DRY_TYPOLOGY: tuple[str] = ("dry", "very_dry")

CDS_DEFAULT_URL: str = "https://cds.climate.copernicus.eu/api"

AQI_THRESHOLDS: dict[str, tuple[float, float, float]] = {
    "pm10": (15.0, 45.0, 75.0),
    "pm2p5": (10.0, 25.0, 50.0),
    "no2": (40.0, 100.0, 200.0),
    "so2": (20.0, 80.0, 125.0),
    "o3": (60.0, 100.0, 180.0),
}
