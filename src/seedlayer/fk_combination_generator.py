from __future__ import annotations

import logging
import random
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .seeded_model import SeededModel


class FKCombinationGenerator:
    """Generates FK combinations for link tables.

    When seeded, sampling is position-based deterministic:
      - The RNG is seeded from the *order* of `_fk_targets` and `_value_lists`.
      - If the same inputs arrive in the same order and same seed, the same sample is produced.
      - If the order changes, results change (even if values are the same).

    When no seed is provided, sampling is random.

    Performance:
      - Uses indexed sampling with mixed-radix decoding to avoid streaming the
        entire Cartesian product when only a subset is requested.
    """

    def __init__(
        self,
        seeded_model: SeededModel,
        models: Mapping[str, SeededModel],
        seed: int,
    ) -> None:
        """Initialize the FKCombinationGenerator.

        Collects FK metadata for composite FK-PK columns, validates their structure,
        gathers candidate ID values from target tables, and initializes an RNG.

        Args:
            seeded_model: The seeded model containing FK-PK columns to generate combinations for.
            models: Dictionary of all seeded models, keyed by name.
            seed: Optional seed for the RNG. If None, the RNG is not seeded (non-deterministic).
        """
        # Collect FK metadata in deterministic (as given) order
        self._fk_targets: list[str] = []  # FK column names
        self._value_lists: list[list[Any]] = []  # candidate values per FK column

        # Identify PK columns that are also FKs
        primary_fk_columns = [
            col for col in seeded_model.columns.values() if col.primary_key and col.foreign_keys
        ]
        if len(primary_fk_columns) <= 1:
            # Not a composite FK-PK; nothing to combine
            return

        # Validate and gather candidate IDs for each FK column
        for col in primary_fk_columns:
            if len(col.foreign_keys) != 1:
                msg = (
                    f"Column '{col.name}' in model '{seeded_model.name}' has "
                    f"{len(col.foreign_keys)} foreign keys; expected exactly one."
                )
                raise ValueError(msg)

            fk = next(iter(col.foreign_keys))
            target_table = fk.column.table
            target_model = seeded_model.table_to_model(col, target_table, models)

            target_field = fk.column.name
            pk_data = models[target_model.name].new_ids
            if not pk_data:
                raise ValueError(f"No new IDs for FK '{col.name}' -> '{target_table.name}'")

            ids = [pk[target_field] for pk in pk_data.dicts()]
            if not ids:
                raise ValueError(f"No '{target_field}' values found in '{target_table.name}'")

            self._fk_targets.append(col.name)
            self._value_lists.append(ids)

        # Initialize RNG
        self._rng = random.Random(seed)  # noqa: S311
        self._picked_indices: set[int] = set()

    def _total_combos(self) -> int:
        total = 1
        for values in self._value_lists:
            total *= len(values)
        return total

    def _decode_index(self, idx: int) -> list[int]:
        """Decode a flat index into per-dimension coordinates (mixed radix)."""
        coords: list[int] = []
        bases = [len(v) for v in self._value_lists]
        for base in reversed(bases):
            coords.append(idx % base)
            idx //= base
        coords.reverse()
        return coords

    def _decode_combo(self, idx: int) -> dict[str, Any]:
        """Convert a flat index into a FK combination dictionary."""
        coords = self._decode_index(idx)
        return {col: self._value_lists[i][coords[i]] for i, col in enumerate(self._fk_targets)}

    def get_next_batch(self, n: int) -> list[dict[str, Any]]:
        """Return n FK combinations using uniform sampling without duplicates."""
        if not self._fk_targets or n == 0:
            return []

        total_combos = self._total_combos()
        remaining_combos = total_combos - len(self._picked_indices)
        logger.debug(f"Sampling {n} combinations from {remaining_combos} available")

        if n > remaining_combos:
            raise ValueError(f"Requested {n} more combinations but only {remaining_combos} remain")

        # If requesting most/all remaining combinations, gather them directly
        if n >= remaining_combos:
            logger.debug("Returning all remaining combinations")
            remaining_indices = []
            for idx in range(total_combos):
                if idx not in self._picked_indices:
                    remaining_indices.append(idx)
            self._picked_indices.update(remaining_indices)
            return [self._decode_combo(idx) for idx in remaining_indices]

        # Use rejection sampling for partial sampling
        logger.debug("Using rejection sampling for partial batch")
        sampled_indices: list[int] = []
        while len(sampled_indices) < n:
            idx = self._rng.randrange(total_combos)
            if idx not in self._picked_indices:
                self._picked_indices.add(idx)
                sampled_indices.append(idx)

        return [self._decode_combo(idx) for idx in sampled_indices]
