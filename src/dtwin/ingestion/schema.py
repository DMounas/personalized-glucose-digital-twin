"""Canonical schema mapping and validation for CGMacros tables.

Enforces name-based column resolution (never positional).
Normalizes whitespace, handles known variants, preserves unknown columns in permissive mode,
and fails loudly in strict mode unless columns are explicitly approved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


class SchemaValidationError(Exception):
    """Raised when DataFrame columns violate canonical schema constraints in strict mode."""


class CanonicalSchemaMapper:
    """Maps raw CGMacros column names to canonical snake_case names via YAML configuration."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        if config_path is None:
            # Default to configs/schema_aliases.yaml relative to repository root
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            config_path = base_dir / "configs" / "schema_aliases.yaml"
        self.config_path = Path(config_path)
        self.config = self._load_config()

        self.strict_default = self.config.get("settings", {}).get("strict_mode_default", True)
        self.normalize_whitespace = self.config.get("settings", {}).get(
            "normalize_whitespace", True
        )
        self.case_insensitive = self.config.get("settings", {}).get(
            "case_insensitive_matching", True
        )

        self._build_lookup_tables()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Schema aliases configuration not found at {self.config_path}")
        with open(self.config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _build_lookup_tables(self) -> None:
        """Construct fast lookup dictionaries for exact and normalized alias matching."""
        self.lookup_tables: dict[str, dict[str, str]] = {}
        self.required_columns: dict[str, list[str]] = {}
        self.ignorable_columns: dict[str, set[str]] = {}
        self.canonical_dtypes: dict[str, dict[str, str]] = {}

        for table_key in ["participant_timeseries", "bio_baseline", "gut_health", "microbes"]:
            table_cfg = self.config.get(table_key, {})
            alias_map: dict[str, str] = {}
            req_cols: list[str] = []
            dtypes: dict[str, str] = {}

            # Approved ignorable
            ignorable = set(table_cfg.get("approved_ignorable_columns", []))
            for ign in list(ignorable):
                ignorable.add(ign.strip())
                if self.case_insensitive:
                    ignorable.add(ign.strip().lower())
            self.ignorable_columns[table_key] = ignorable

            canonical_cols = table_cfg.get("canonical_columns", {})
            for can_name, col_info in canonical_cols.items():
                if col_info.get("required", False):
                    req_cols.append(can_name)
                if "dtype" in col_info:
                    dtypes[can_name] = col_info["dtype"]

                # Register canonical name itself
                alias_map[can_name] = can_name
                alias_map[can_name.lower()] = can_name

                # Register all aliases
                for alias in col_info.get("aliases", []):
                    alias_map[alias] = can_name
                    clean_alias = alias.strip()
                    alias_map[clean_alias] = can_name
                    if self.case_insensitive:
                        alias_map[clean_alias.lower()] = can_name

            self.lookup_tables[table_key] = alias_map
            self.required_columns[table_key] = req_cols
            self.canonical_dtypes[table_key] = dtypes

    def resolve_column(self, col: str, table_type: str) -> tuple[str | None, bool]:
        """Resolve a raw column name to its canonical name or ignorable flag.

        Returns:
            (canonical_name, is_ignorable)
        """
        table_aliases = self.lookup_tables.get(table_type, {})
        ignorable = self.ignorable_columns.get(table_type, set())

        clean_col = col.strip() if self.normalize_whitespace else col

        # Check exact match in aliases
        if col in table_aliases:
            return table_aliases[col], False
        if clean_col in table_aliases:
            return table_aliases[clean_col], False
        if self.case_insensitive and clean_col.lower() in table_aliases:
            return table_aliases[clean_col.lower()], False

        # Check ignorable
        if col in ignorable or clean_col in ignorable:
            return None, True
        if self.case_insensitive and clean_col.lower() in ignorable:
            return None, True

        # Special handling for microbes indicator columns
        if table_type == "microbes":
            # Any column other than subject is a bacterial species indicator
            return clean_col, False

        return None, False

    def map_dataframe(
        self,
        df: pd.DataFrame,
        table_type: str,
        strict: bool | None = None,
        drop_ignorable: bool = True,
    ) -> pd.DataFrame:
        """Map DataFrame columns to canonical schema.

        Args:
            df: Raw DataFrame read from CSV.
            table_type: One of 'participant_timeseries', 'bio_baseline', 'gut_health', 'microbes'.
            strict: If True, raises SchemaValidationError on unmapped columns.
                    If None, uses strict_mode_default from config.
            drop_ignorable: If True, drops approved ignorable columns like Unnamed: 0.

        Returns:
            Normalized DataFrame with canonical column names.
        """
        if table_type not in self.lookup_tables:
            expected = list(self.lookup_tables.keys())
            raise ValueError(f"Unknown table_type: {table_type}. Expected one of {expected}")

        is_strict = self.strict_default if strict is None else strict

        rename_map: dict[str, str] = {}
        cols_to_drop: list[str] = []
        unmapped_cols: list[str] = []

        for col in df.columns:
            can_name, is_ign = self.resolve_column(str(col), table_type)
            if is_ign:
                if drop_ignorable:
                    cols_to_drop.append(col)
                else:
                    rename_map[col] = f"_ignorable_{col.strip()}"
            elif can_name is not None:
                rename_map[col] = can_name
            else:
                unmapped_cols.append(str(col))

        if is_strict and unmapped_cols:
            raise SchemaValidationError(
                f"Strict schema validation failed for table '{table_type}'. "
                f"Found {len(unmapped_cols)} unexpected unapproved column(s): {unmapped_cols}. "
                f"Add these columns to configs/schema_aliases.yaml or run in permissive mode."
            )

        # Apply transformations
        result_df = df.copy()
        if cols_to_drop:
            result_df = result_df.drop(columns=cols_to_drop)

        result_df = result_df.rename(columns=rename_map)

        # Verify required columns
        missing_req = [
            req for req in self.required_columns.get(table_type, []) if req not in result_df.columns
        ]
        if missing_req:
            raise SchemaValidationError(
                f"Table '{table_type}' is missing required canonical column(s): {missing_req}"
            )

        return result_df
