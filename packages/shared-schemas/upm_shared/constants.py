"""Cross-service names. Backend and worker must agree on these literally."""

# Redis list the worker LPUSHes LoadCommands onto; the Gateway-owning backend BRPOPs it.
LOAD_QUEUE = "upm:duckdb:load"

# Celery task the scheduler/API enqueue and the ingestion worker registers.
TASK_RUN_EXTRACTION = "upm.ingestion.run_extraction_job"

# Default Celery queue for extraction work.
EXTRACTION_QUEUE = "extraction"
