
import json
import re
from dataclasses import dataclass
from typing import Any

import asyncpg

from app.core.config import settings

pool: asyncpg.Pool | None = None
database: "DatabaseFacade | None" = None

CANDIDATE_COLUMNS = [
    "id",
    "email",
    "name",
    "eligible_phase",
    "intake_year",
    "college",
    "graduation_year",
    "tech_stack",
    "percentage",
    "batch_id",
    "uid",
    "employee_email",
    "offer_accepted",
    "source",
    "status",
    "pre_onboarding_score",
    "post_onboarding_score",
    "knowledge_check_python_score",
    "knowledge_check_java_score",
    "marks",
    "alternate_emails",
    "baseline_data",
    "baseline_email_map",
    "created_at",
    "updated_at",
]


@dataclass
class InsertOneResult:
    inserted_id: str | None = None


class CursorFacade:
    def __init__(self, collection: "CollectionFacade", query: dict[str, Any]):
        self.collection = collection
        self.query = query
        self._sort_field: str | None = None
        self._sort_direction: int = 1

    def sort(self, field: str, direction: int = 1) -> "CursorFacade":
        self._sort_field = field
        self._sort_direction = direction
        return self

    async def to_list(self, length: int = 1000) -> list[dict[str, Any]]:
        return await self.collection._fetch_many(self.query, limit=length, sort_field=self._sort_field, sort_direction=self._sort_direction)


class CollectionFacade:
    def __init__(self, table: str, columns: list[str]):
        self.table = table
        self.columns = columns

    async def create_index(self, *args, **kwargs) -> None:
        return None

    async def insert_one(self, document: dict[str, Any]) -> InsertOneResult:
        payload = self._normalize_document(document)
        keys = list(payload.keys())
        placeholders = ", ".join(f"${idx}" for idx in range(1, len(keys) + 1))
        sql = f'INSERT INTO {self.table} ({", ".join(keys)}) VALUES ({placeholders})'
        values = [payload[key] for key in keys]
        await _execute_with_schema_retry(sql, *values)
        return InsertOneResult(inserted_id=payload.get("id"))

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        rows = await self._fetch_many(query, limit=1)
        return rows[0] if rows else None

    def find(self, query: dict[str, Any]) -> "CursorFacade":
        return CursorFacade(self, query)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        set_data = update.get("$set", {})
        if not set_data:
            return
        payload = self._normalize_document(set_data)
        set_clause = ", ".join(f"{key} = ${idx}" for idx, key in enumerate(payload.keys(), start=1))
        where_clause, values = self._build_where(query, start_index=len(payload) + 1)
        sql = f'UPDATE {self.table} SET {set_clause} WHERE {where_clause}'
        await _execute_with_schema_retry(sql, *payload.values(), *values)

    async def update_many(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        await self.update_one(query, update)

    async def distinct(self, field: str) -> list[Any]:
        rows = await _fetch_with_schema_retry(f'SELECT DISTINCT {field} FROM {self.table}')
        return [row[field] for row in rows if row[field] is not None]

    async def count_documents(self, query: dict[str, Any]) -> int:
        where_clause, values = self._build_where(query)
        sql = f'SELECT COUNT(*) AS count FROM {self.table} WHERE {where_clause}'
        row = await _fetchrow_with_schema_retry(sql, *values)
        return int(row["count"] if row else 0)

    async def _fetch_many(self, query: dict[str, Any], *, limit: int, sort_field: str | None = None, sort_direction: int = 1) -> list[dict[str, Any]]:
        where_clause, values = self._build_where(query)
        order_clause = ""
        if sort_field:
            order_clause = f' ORDER BY {sort_field} {"DESC" if sort_direction < 0 else "ASC"}'
        sql = f'SELECT * FROM {self.table} WHERE {where_clause}{order_clause} LIMIT {limit}'
        rows = await _fetch_with_schema_retry(sql, *values)
        return [self._row_to_dict(row) for row in rows]

    def _build_where(self, query: dict[str, Any], start_index: int = 1) -> tuple[str, list[Any]]:
        if not query:
            return "TRUE", []
        clauses: list[str] = []
        values: list[Any] = []
        index = start_index
        for key, value in query.items():
            if key == "$or":
                or_clauses = []
                for subquery in value:
                    sub_clause, sub_values = self._build_where(subquery, index)
                    or_clauses.append(f'({sub_clause})')
                    values.extend(sub_values)
                    index += len(sub_values)
                clauses.append("(" + " OR ".join(or_clauses) + ")")
                continue
            if isinstance(value, dict) and "$regex" in value:
                pattern = str(value["$regex"])
                clauses.append(f'{key} ILIKE ${index}')
                values.append(f'%{pattern}%')
                index += 1
                continue
            if key == "alternate_emails":
                clauses.append(f'{key}::jsonb @> ${index}::jsonb')
                values.append(json.dumps([value]))
                index += 1
                continue
            clauses.append(f'{key} = ${index}')
            values.append(self._normalize_value(value))
            index += 1
        return " AND ".join(clauses) if clauses else "TRUE", values

    def _normalize_document(self, document: dict[str, Any]) -> dict[str, Any]:
        return {key: self._normalize_value(value) for key, value in document.items() if key in self.columns}

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    def _row_to_dict(self, row: asyncpg.Record) -> dict[str, Any]:
        result = dict(row)
        for field in ("marks", "metadata", "tech_stack", "alternate_emails", "baseline_data", "baseline_email_map"):
            value = result.get(field)
            if isinstance(value, str):
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return result


class DatabaseFacade:
    def __init__(self) -> None:
        self.users = CollectionFacade("users", ["id", "email", "name", "employee_id", "role", "hashed_password", "must_change_password", "is_active", "created_at", "updated_at"])
        self.year_phases = CollectionFacade("year_phases", ["id", "year", "phase", "created_at", "updated_at"])
        self.batches = CollectionFacade("batches", ["id", "year", "name", "owner_id", "phase", "start_date", "end_date", "tech_stack", "created_at", "updated_at"])
        self.candidates = CollectionFacade("candidates", CANDIDATE_COLUMNS)
        self.exam_results = CollectionFacade("exam_results", ["id", "candidate_id", "batch_id", "phase", "exam_type", "exam_name", "attempt", "score", "max_score", "pass_percentage", "passed", "candidate_status_after", "timeline_badge", "created_by", "created_at"])
        self.timeline_events = CollectionFacade("timeline_events", ["id", "candidate_id", "actor_id", "event_type", "description", "metadata", "created_at"])
        self.change_requests = CollectionFacade("change_requests", ["id", "candidate_id", "candidate_email", "batch_id", "requested_by", "request_type", "exam_type", "custom_exam_name", "reason", "current_pass_percentage", "requested_pass_percentage", "status", "reviewer_id", "reviewer_comment", "created_at", "reviewed_at"])

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        return await _fetch_with_schema_retry(query, *args)

    async def fetchval(self, query: str, *args: Any, column: int = 0) -> Any:
        return await _fetchval_with_schema_retry(query, *args, column=column)

    async def execute(self, query: str, *args: Any) -> str:
        return await _execute_with_schema_retry(query, *args)

    async def ensure_candidate_columns(self, column_types: dict[str, str]) -> None:
        async with pool.acquire() as conn:
            await _ensure_candidate_columns(conn, column_types)

    async def insert_candidate_row(self, document: dict[str, Any]) -> None:
        keys = list(document.keys())
        placeholders = ", ".join(f"${idx}" for idx in range(1, len(keys) + 1))
        sql = f'INSERT INTO candidates ({", ".join(keys)}) VALUES ({placeholders})'
        await _execute_with_schema_retry(
            sql,
            *[CollectionFacade._normalize_value(self.candidates, document[key]) for key in keys],
        )

    async def update_candidate_row(self, query: dict[str, Any], updates: dict[str, Any]) -> None:
        if not updates:
            return
        set_clause = ", ".join(f"{key} = ${idx}" for idx, key in enumerate(updates.keys(), start=1))
        where_clause = " AND ".join(
            f"{key} = ${len(updates) + idx}" for idx, key in enumerate(query.keys(), start=1)
        )
        values = [CollectionFacade._normalize_value(self.candidates, value) for value in updates.values()] + list(query.values())
        await _execute_with_schema_retry(f"UPDATE candidates SET {set_clause} WHERE {where_clause}", *values)


async def _execute_with_schema_retry(query: str, *args: Any) -> str:
    try:
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
    except asyncpg.UndefinedTableError:
        await create_tables()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)


async def _fetch_with_schema_retry(query: str, *args: Any) -> list[asyncpg.Record]:
    try:
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
    except asyncpg.UndefinedTableError:
        await create_tables()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)


async def _fetchrow_with_schema_retry(query: str, *args: Any) -> asyncpg.Record | None:
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    except asyncpg.UndefinedTableError:
        await create_tables()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)


async def _fetchval_with_schema_retry(query: str, *args: Any, column: int = 0) -> Any:
    try:
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)
    except asyncpg.UndefinedTableError:
        await create_tables()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _compact_key(value: str) -> str:
    return "".join(char for char in value.strip().lower() if char.isalnum())


def _knowledge_check_column_name(exam_name: str) -> str | None:
    normalized = exam_name.strip().lower()
    compact = _compact_key(exam_name)
    if "python" in normalized or "python" in compact:
        return "knowledge_check_python_score"
    if ("java" in normalized or compact.startswith("java")) and "javascript" not in normalized and not compact.startswith("javascript"):
        return "knowledge_check_java_score"
    return None


def sanitize_dynamic_column_name(header: str, prefix: str | None = None) -> str:
    name = _normalize_key(header)
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if prefix:
        prefix_name = sanitize_dynamic_column_name(prefix)
        if name:
            name = f"{prefix_name}_{name}"
        else:
            name = prefix_name
    if not name:
        name = "uploaded_value"
    if name[0].isdigit():
        name = f"field_{name}"
    return name


def _first_value(data: dict[str, Any], *keys: str) -> Any:
    normalized_data = {_normalize_key(key): value for key, value in data.items()}
    compact_data = {_compact_key(key): value for key, value in data.items()}
    for key in keys:
        value = normalized_data.get(_normalize_key(key))
        if value is None:
            value = compact_data.get(_compact_key(key))
        if value not in (None, ""):
            return value
    return None


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    return None


def _coerce_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip()


def infer_sql_type(values: list[Any]) -> str:
    non_empty = [value for value in values if value not in (None, "")]
    if not non_empty:
        return "TEXT"

    bool_like = True
    int_like = True
    float_like = True

    for value in non_empty:
        if _coerce_bool(value) is None:
            bool_like = False
        try:
            number = float(value)
            if int(number) != number:
                int_like = False
        except (TypeError, ValueError):
            int_like = False
            float_like = False

    if bool_like:
        return "BOOLEAN"
    if int_like:
        return "INTEGER"
    if float_like:
        return "DOUBLE PRECISION"
    return "TEXT"


def coerce_dynamic_value(value: Any, sql_type: str) -> Any:
    if value in (None, ""):
        return None
    if sql_type == "BOOLEAN":
        return _coerce_bool(value)
    if sql_type == "INTEGER":
        return _coerce_int(value)
    if sql_type == "DOUBLE PRECISION":
        return _coerce_float(value)
    return _coerce_text(value)


async def _column_exists(conn: asyncpg.Connection, table: str, column: str) -> bool:
    return bool(
        await conn.fetchval(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2
            """,
            table,
            column,
        )
    )


async def _table_columns(conn: asyncpg.Connection, table: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        """,
        table,
    )
    return {row["column_name"] for row in rows}


async def _ensure_candidate_columns(conn: asyncpg.Connection, column_types: dict[str, str]) -> None:
    if not column_types:
        return
    existing_columns = await _table_columns(conn, "candidates")
    for column_name, sql_type in column_types.items():
        if column_name not in CANDIDATE_COLUMNS:
            continue
        if column_name in existing_columns:
            continue
        await conn.execute(f"ALTER TABLE candidates ADD COLUMN IF NOT EXISTS {column_name} {sql_type}")
        existing_columns.add(column_name)


async def _drop_unexpected_candidate_columns(conn: asyncpg.Connection) -> None:
    existing_columns = await _table_columns(conn, "candidates")
    unexpected_columns = sorted(existing_columns - set(CANDIDATE_COLUMNS))
    for column_name in unexpected_columns:
        await conn.execute(f"ALTER TABLE candidates DROP COLUMN IF EXISTS {column_name}")


async def _normalize_candidates_table(conn: asyncpg.Connection) -> None:
    has_master_data = await _column_exists(conn, "candidates", "master_data")
    has_timeline = await _column_exists(conn, "candidates", "timeline")
    has_marks = await _column_exists(conn, "candidates", "marks")
    has_baseline_data = await _column_exists(conn, "candidates", "baseline_data")

    if has_master_data or has_timeline:
        select_fields = ["id", "email", "name", "eligible_phase", "intake_year", "college", "graduation_year", "tech_stack", "percentage", "offer_accepted", "source", "updated_at"]
        if has_master_data:
            select_fields.append("master_data")
        if has_timeline:
            select_fields.append("timeline")

        rows = await conn.fetch(f"SELECT {', '.join(select_fields)} FROM candidates")

        for raw_row in rows:
            row = dict(raw_row)
            master_data = _json_object(row.get("master_data")) if has_master_data else {}
            updates: dict[str, Any] = {}

            if not row.get("name"):
                name = _coerce_text(_first_value(master_data, "name", "candidate_name", "candidate name", "student_name", "student name"))
                if name:
                    updates["name"] = name

            if not row.get("college"):
                college = _coerce_text(_first_value(master_data, "college", "college_name", "college name", "institution", "institution_name"))
                if college:
                    updates["college"] = college

            if not row.get("eligible_phase"):
                eligible_phase = _coerce_text(_first_value(master_data, "eligible_phase", "eligible phase"))
                if eligible_phase:
                    updates["eligible_phase"] = eligible_phase.upper()

            if row.get("intake_year") is None:
                intake_year = _coerce_int(_first_value(master_data, "intake_year", "intake year"))
                if intake_year is not None:
                    updates["intake_year"] = intake_year

            if row.get("graduation_year") is None:
                graduation_year = _coerce_int(_first_value(master_data, "graduation_year", "graduation year"))
                if graduation_year is not None:
                    updates["graduation_year"] = graduation_year

            if row.get("tech_stack") in (None, ""):
                tech_stack = _coerce_text(_first_value(master_data, "tech_stack", "tech stack", "technology", "technology_stack", "technology stack"))
                if tech_stack:
                    updates["tech_stack"] = tech_stack

            if row.get("percentage") is None:
                percentage = _coerce_float(_first_value(master_data, "percentage", "marks", "score"))
                if percentage is not None:
                    updates["percentage"] = percentage

            if row.get("offer_accepted") is None:
                offer_accepted = _coerce_bool(_first_value(master_data, "offer_accepted", "offer accepted"))
                if offer_accepted is not None:
                    updates["offer_accepted"] = offer_accepted

            if not row.get("source"):
                source = _coerce_text(_first_value(master_data, "source"))
                if source:
                    updates["source"] = source

            if updates:
                updates["updated_at"] = updates.get("updated_at") or row.get("updated_at")
                set_clause = ", ".join(f"{column} = ${index}" for index, column in enumerate(updates.keys(), start=1))
                values = list(updates.values()) + [row["id"]]
                await conn.execute(f"UPDATE candidates SET {set_clause} WHERE id = ${len(values)}", *values)

    if has_marks:
        rows = await conn.fetch(
            """
            SELECT id, marks, knowledge_check_python_score, knowledge_check_java_score
            FROM candidates
            """
        )

        marks_updates: list[tuple[str, dict[str, Any]]] = []

        for raw_row in rows:
            row = dict(raw_row)
            original_marks = _json_object(row.get("marks"))
            marks = dict(original_marks)
            updates: dict[str, Any] = {}
            extracted_scores: dict[str, float] = {}

            for key in list(marks.keys()):
                column_name = _knowledge_check_column_name(key)
                if not column_name:
                    continue
                score = _coerce_float(marks.pop(key, None))
                if score is not None:
                    extracted_scores[column_name] = score

            for column_name, score in extracted_scores.items():
                if row.get(column_name) != score:
                    updates[column_name] = score

            if marks != original_marks:
                updates["marks"] = json.dumps(marks)

            if updates:
                marks_updates.append((row["id"], updates))

        for candidate_id, updates in marks_updates:
            set_clause = ", ".join(f"{column} = ${index}" for index, column in enumerate(updates.keys(), start=1))
            values = list(updates.values()) + [candidate_id]
            await conn.execute(f"UPDATE candidates SET {set_clause} WHERE id = ${len(values)}", *values)

    if has_baseline_data:
        rows = await conn.fetch("SELECT id, baseline_data FROM candidates")
        baseline_updates: list[tuple[str, dict[str, Any]]] = []

        for raw_row in rows:
            row = dict(raw_row)
            baseline_data = _json_object(row.get("baseline_data"))
            baseline_exam = _json_object(baseline_data.get("baseline_exam"))
            updates: dict[str, Any] = {}

            if baseline_exam:
                updates["baseline_data"] = json.dumps({})

            if updates:
                baseline_updates.append((row["id"], updates))

        for candidate_id, updates in baseline_updates:
            set_clause = ", ".join(f"{column} = ${index}" for index, column in enumerate(updates.keys(), start=1))
            values = list(updates.values()) + [candidate_id]
            await conn.execute(f"UPDATE candidates SET {set_clause} WHERE id = ${len(values)}", *values)

    await conn.execute(
        """
        UPDATE candidates
        SET
            name = COALESCE(NULLIF(name, ''), split_part(email, '@', 1)),
            eligible_phase = COALESCE(NULLIF(eligible_phase, ''), 'PRE_ONBOARDING'),
            offer_accepted = COALESCE(offer_accepted, FALSE),
            status = COALESCE(NULLIF(status, ''), 'ELIGIBLE'),
            marks = COALESCE(NULLIF(marks, ''), '{}'),
            alternate_emails = COALESCE(NULLIF(alternate_emails, ''), '[]'),
            baseline_data = COALESCE(NULLIF(baseline_data, ''), '{}'),
            baseline_email_map = COALESCE(NULLIF(baseline_email_map, ''), '{}')
        """
    )

    await conn.execute("ALTER TABLE candidates DROP COLUMN IF EXISTS master_data")
    await conn.execute("ALTER TABLE candidates DROP COLUMN IF EXISTS timeline")
    await _drop_unexpected_candidate_columns(conn)


async def connect_to_postgresql() -> None:
    global pool, database
    pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=10)
    await create_tables()
    database = DatabaseFacade()


async def close_postgresql_connection() -> None:
    global pool, database
    if pool is not None:
        await pool.close()
    pool = None
    database = None


def get_database() -> DatabaseFacade:
    if database is None:
        raise RuntimeError("PostgreSQL is not connected")
    return database


async def create_tables() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        employee_id TEXT,
        role TEXT NOT NULL,
        hashed_password TEXT NOT NULL,
        must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );
    CREATE TABLE IF NOT EXISTS batches (
        id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        name TEXT NOT NULL,
        owner_id TEXT,
        phase TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        tech_stack TEXT NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );
    CREATE TABLE IF NOT EXISTS year_phases (
        id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        phase TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(year, phase)
    );
    CREATE TABLE IF NOT EXISTS candidates (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        eligible_phase TEXT NOT NULL,
        intake_year INTEGER,
        college TEXT,
        graduation_year INTEGER,
        tech_stack TEXT,
        percentage DOUBLE PRECISION,
        batch_id TEXT,
        uid TEXT,
        employee_email TEXT,
        offer_accepted BOOLEAN NOT NULL DEFAULT FALSE,
        source TEXT,
        status TEXT NOT NULL,
        pre_onboarding_score DOUBLE PRECISION,
        post_onboarding_score DOUBLE PRECISION,
        knowledge_check_python_score DOUBLE PRECISION,
        knowledge_check_java_score DOUBLE PRECISION,
        marks TEXT NOT NULL DEFAULT '{}',
        alternate_emails TEXT NOT NULL DEFAULT '[]',
        baseline_data TEXT NOT NULL DEFAULT '{}',
        baseline_email_map TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS eligible_phase TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS intake_year INTEGER;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS college TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS graduation_year INTEGER;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS tech_stack TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS percentage DOUBLE PRECISION;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS batch_id TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS uid TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS employee_email TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS offer_accepted BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS source TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS status TEXT;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS pre_onboarding_score DOUBLE PRECISION;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS post_onboarding_score DOUBLE PRECISION;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS knowledge_check_python_score DOUBLE PRECISION;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS knowledge_check_java_score DOUBLE PRECISION;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS marks TEXT NOT NULL DEFAULT '{}';
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS alternate_emails TEXT NOT NULL DEFAULT '[]';
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS baseline_data TEXT NOT NULL DEFAULT '{}';
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS baseline_email_map TEXT NOT NULL DEFAULT '{}';
    ALTER TABLE candidates ALTER COLUMN eligible_phase SET DEFAULT 'PRE_ONBOARDING';
    ALTER TABLE candidates ALTER COLUMN status SET DEFAULT 'ELIGIBLE';
    CREATE TABLE IF NOT EXISTS exam_results (
        id TEXT PRIMARY KEY,
        candidate_id TEXT NOT NULL,
        batch_id TEXT,
        phase TEXT NOT NULL,
        exam_type TEXT NOT NULL,
        exam_name TEXT NOT NULL,
        attempt INTEGER NOT NULL,
        score DOUBLE PRECISION NOT NULL,
        max_score DOUBLE PRECISION NOT NULL,
        pass_percentage DOUBLE PRECISION,
        passed BOOLEAN NOT NULL,
        candidate_status_after TEXT NOT NULL,
        timeline_badge TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        UNIQUE(candidate_id, phase, exam_name, attempt)
    );
    CREATE TABLE IF NOT EXISTS timeline_events (
        id TEXT PRIMARY KEY,
        candidate_id TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL
    );
    CREATE TABLE IF NOT EXISTS change_requests (
        id TEXT PRIMARY KEY,
        candidate_id TEXT,
        candidate_email TEXT,
        batch_id TEXT,
        requested_by TEXT NOT NULL,
        request_type TEXT NOT NULL,
        exam_type TEXT,
        custom_exam_name TEXT,
        reason TEXT NOT NULL,
        current_pass_percentage DOUBLE PRECISION,
        requested_pass_percentage DOUBLE PRECISION,
        status TEXT NOT NULL,
        reviewer_id TEXT,
        reviewer_comment TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        reviewed_at TIMESTAMPTZ
    );
    ALTER TABLE change_requests ADD COLUMN IF NOT EXISTS exam_type TEXT;
    ALTER TABLE change_requests ADD COLUMN IF NOT EXISTS custom_exam_name TEXT;
    ALTER TABLE change_requests ADD COLUMN IF NOT EXISTS current_pass_percentage DOUBLE PRECISION;
    ALTER TABLE change_requests ADD COLUMN IF NOT EXISTS requested_pass_percentage DOUBLE PRECISION;
    ALTER TABLE change_requests DROP COLUMN IF EXISTS requested_changes;
    ALTER TABLE change_requests DROP COLUMN IF EXISTS details;
    ALTER TABLE change_requests DROP COLUMN IF EXISTS rule_type;
    ALTER TABLE change_requests DROP COLUMN IF EXISTS current_configuration;
    ALTER TABLE change_requests DROP COLUMN IF EXISTS requested_configuration;
    CREATE INDEX IF NOT EXISTS idx_users_employee_id ON users(employee_id);
    CREATE INDEX IF NOT EXISTS idx_batches_owner_id ON batches(owner_id);
    CREATE INDEX IF NOT EXISTS idx_batches_year ON batches(year);
    CREATE INDEX IF NOT EXISTS idx_year_phases_year ON year_phases(year);
    CREATE INDEX IF NOT EXISTS idx_candidates_batch_id ON candidates(batch_id);
    CREATE INDEX IF NOT EXISTS idx_candidates_intake_year ON candidates(intake_year);
    CREATE INDEX IF NOT EXISTS idx_timeline_events_candidate_id ON timeline_events(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_change_requests_candidate_status ON change_requests(candidate_id, status);
    """
    async with pool.acquire() as conn:
        await conn.execute(ddl)
        await _normalize_candidates_table(conn)
