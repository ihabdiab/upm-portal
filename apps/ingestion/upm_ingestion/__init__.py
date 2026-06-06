"""UPM ingestion — extracts from the source to a Parquet landing zone (§9).

Workers NEVER open DuckDB. They write Parquet then hand a LoadCommand to the Gateway
(in prod via Redis; in dev the orchestrator loads inline through a passed-in Gateway).
"""
