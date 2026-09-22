import os
import re

STATEMENT_TIMEOUT_RE = re.compile(r"^\d+(ms|s|min|h|d)?$")


class Settings:
    db_host: str = os.environ["DB_HOST"]
    db_port: str = os.environ.get("DB_PORT", "5432")
    db_user: str = os.environ["DB_USER"]
    db_password: str = os.environ["DB_PASSWORD"]
    db_name: str = os.environ["DB_NAME"]
    cron_schedule: str = os.environ.get("CRON_SCHEDULE", "0 2 * * *")
    query_statement_timeout: str = os.environ.get("QUERY_STATEMENT_TIMEOUT", "10min")

    if not STATEMENT_TIMEOUT_RE.match(query_statement_timeout):
        raise ValueError(f"Invalid QUERY_STATEMENT_TIMEOUT: {query_statement_timeout!r}")


settings = Settings()
