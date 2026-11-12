"""Geographic helpers: distances and catchment areas."""

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Works on numbers or numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def add_nearest_hub(stores: pd.DataFrame, hubs: pd.DataFrame) -> pd.DataFrame:
    """Add km_to_nearest_hub and nearest_hub. Road distance ≈ 1.25 x straight line (common rule of thumb)."""
    distances = np.column_stack([
        haversine_km(stores["lat"].values, stores["lon"].values, h.lat, h.lon) for h in hubs.itertuples()
    ])
    out = stores.copy()
    out["km_to_nearest_hub"] = (distances.min(axis=1) * 1.25).round(1)
    out["nearest_hub"] = hubs["hub"].values[distances.argmin(axis=1)]
    return out


def catchment_density(stores: pd.DataFrame, cities: pd.DataFrame, radius_km: float = 10.0) -> pd.DataFrame:
    """For each main city: selective beauty stores within `radius_km` of the centre, per 100k inhabitants."""
    rows = []
    selective = stores[stores["segment"] == "selective"]
    for city in cities.itertuples():
        s = selective[selective["country_code"] == city.country_code]
        d = haversine_km(s["lat"].values, s["lon"].values, city.lat, city.lon)
        n = int((d <= radius_km).sum())
        rows.append({
            "country_code": city.country_code, "city": city.city, "population": city.population,
            "selective_stores_10km": n, "stores_per_100k": n / city.population * 1e5,
        })
    return pd.DataFrame(rows)
