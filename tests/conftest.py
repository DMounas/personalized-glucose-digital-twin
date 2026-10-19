"""Pytest fixtures and programmatic data generators.

All test datasets are generated in tmp_path with planted secret sentinels.
No external network downloads or real patient data are ever used in tests.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

PLANTED_SENTINEL_STRING = "PLANTED_SECRET_SENTINEL_PATIENT_Z9"
PLANTED_SENTINEL_PATH = "PLANTED_SECRET_PATH_X7Q/patient_photo_01.jpg"
PLANTED_SENTINEL_NAME = "PLANTED_SECRET_NAME_ALICE_SMITH"
PLANTED_SENTINEL_FLOAT = 8888.7777


@pytest.fixture
def sample_config() -> dict[str, Any]:
    return {
        "small_cell_threshold": 5,
        "min_rows_for_stats": 5,
        "chunk_size": 20,
        "chunk_size_bytes_threshold": 1000,
        "datetime_column_hints": ["time", "date", "timestamp"],
        "datetime_parse_threshold": 0.8,
        "gap_multiplier": 3.0,
        "suspicious_sentinels": [-999, -1, 400, 800, 9999],
        "quantiles": [0.05, 0.25, 0.5, 0.75, 0.95],
    }


@pytest.fixture
def synthetic_data_dir(tmp_path: Path) -> Path:
    """Creates a realistic synthetic dataset tree in tmp_path."""
    data_dir = tmp_path / "synthetic_cgmacros"
    data_dir.mkdir(parents=True)

    # Participant 1: 5-min intervals, 25 rows
    p1_dir = data_dir / "CGMacros-001"
    p1_dir.mkdir()
    dates_p1 = pd.date_range("2024-01-01 08:00:00", periods=25, freq="5min")
    df1 = pd.DataFrame(
        {
            "Timestamp": dates_p1.astype(str),
            "Glucose": [100.0 + i * 2 for i in range(25)],
            "Meal_Type": ["Breakfast"] * 10 + ["Lunch"] * 10 + ["Dinner"] * 5,
            "Image_Path": [f"photos/meal_{i}_{PLANTED_SENTINEL_PATH}.jpg" for i in range(25)],
            "Participant_Name": [PLANTED_SENTINEL_NAME] * 25,
            "Category_Rare": ["Common"] * 21 + ["Rare_A", "Rare_B", "Rare_C", "Rare_D"],
            "Sentinel_Col": [-999] * 2 + [0] * 3 + [400] * 1 + [120] * 19,
        }
    )
    df1.to_csv(p1_dir / "CGMacros-001.csv", index=False)

    # Participant 1 photos subfolder with dummy image
    p1_photos = p1_dir / "photos"
    p1_photos.mkdir()
    (p1_photos / "meal_before.jpg").write_bytes(b"\xff\xd8\xff\xe0dummy_jpg_bytes")
    (p1_photos / "meal_after.png").write_bytes(b"\x89PNG\r\n\x1a\ndummy_png_bytes")

    # Participant 2: 5-min intervals, 20 rows
    p2_dir = data_dir / "CGMacros-002"
    p2_dir.mkdir()
    dates_p2 = pd.date_range("2024-01-01 08:00:00", periods=20, freq="5min")
    df2 = pd.DataFrame(
        {
            "Timestamp": dates_p2.astype(str),
            "Glucose": [110.0 + i for i in range(20)],
            "Meal_Type": ["Breakfast"] * 8 + ["Lunch"] * 8 + ["Dinner"] * 4,
            "Image_Path": [f"photos/p2_meal_{i}.jpg" for i in range(20)],
            "Participant_Name": [PLANTED_SENTINEL_NAME] * 20,
            "Category_Rare": ["Common"] * 18 + ["Rare_E", "Rare_F"],
            "Sentinel_Col": [800] * 2 + [0] * 2 + [110] * 16,
        }
    )
    df2.to_csv(p2_dir / "CGMacros-002.csv", index=False)

    # Participant 4: numeric gap! (003 is missing)
    p4_dir = data_dir / "CGMacros-004"
    p4_dir.mkdir()
    dates_p4 = pd.date_range("2024-01-01 08:00:00", periods=15, freq="5min")
    df4 = pd.DataFrame(
        {
            "Timestamp": dates_p4.astype(str),
            "Glucose": [120.0 + i for i in range(15)],
            "Meal_Type": ["Breakfast"] * 5 + ["Lunch"] * 5 + ["Dinner"] * 5,
            "Image_Path": [f"photos/p4_meal_{i}.jpg" for i in range(15)],
            "Participant_Name": [PLANTED_SENTINEL_NAME] * 15,
            "Category_Rare": ["Common"] * 15,
            "Sentinel_Col": [120] * 15,
        }
    )
    df4.to_csv(p4_dir / "CGMacros-004.csv", index=False)

    # Secondary Schema Family: bio.csv (different column signature)
    df_bio = pd.DataFrame(
        {
            "Participant_ID": ["001", "002", "004"],
            "Age": [45, 52, 61],
            "BMI": [24.5, 29.1, 31.2],
            "Secret_Token": [PLANTED_SENTINEL_STRING, "token_b", "token_c"],
        }
    )
    df_bio.to_csv(data_dir / "bio.csv", index=False)

    # Dummy archive
    zip_path = data_dir / "CGMacros_archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("read_me.txt", "Sample archive content")
        zf.writestr("subfolder/data.csv", "a,b\n1,2\n")

    # Data dictionary
    df_dict = pd.DataFrame(
        {
            "Field Name": ["Glucose", "BMI", "Age", "Undocumented_Field"],
            "Range": ["Numeric: 40-400 mg/dL", "15-50", "18-90", "0-100"],
            "Description": [
                "Sensor glucose level",
                "Body mass index",
                "Age in years",
                "Some extra info",
            ],
        }
    )
    df_dict.to_csv(data_dir / "DataDictionary_Bio.csv", index=False)

    # Checksum manifest for all files
    manifest_lines = []
    for f in sorted(data_dir.rglob("*")):
        if f.is_file() and f.name != "SHA256SUMS.txt":
            rel = f.relative_to(data_dir).as_posix()
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            manifest_lines.append(f"{h}  {rel}")
    (data_dir / "SHA256SUMS.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    return data_dir
