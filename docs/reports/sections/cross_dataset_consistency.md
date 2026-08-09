# Cross-dataset entity/sector consistency

One row per (entity_id, entity_name, sector) triple found in each dataset. All three should agree exactly per entity_id.

Distinct `entity_id` values across all 3 datasets combined: 20

**MATCH** — every `entity_id` maps to the identical `(entity_name, sector)` pair in all 3 internal datasets. Safe to join on `entity_id` alone across all 3.