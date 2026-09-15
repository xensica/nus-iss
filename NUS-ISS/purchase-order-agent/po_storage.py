import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).with_name("purchase_orders.db")


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS po_batches (
            batch_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            records TEXT NOT NULL
        )
    """)
    connection.commit()
    return connection


def save_new_batch(drafts):
    if not drafts or any(po["status"] != "DRAFT" for po in drafts):
        raise ValueError("Only a new draft batch can be saved.")

    batch_id = drafts[0]["po_id"].rsplit("-", 1)[0]

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO po_batches
                (batch_id, created_at, status, records)
            VALUES (?, ?, ?, ?)
            """,
            (
                batch_id,
                datetime.now(timezone.utc).isoformat(),
                "DRAFT",
                json.dumps(drafts),
            ),
        )

    return batch_id


def load_batch(batch_id):
    with connect() as connection:
        row = connection.execute(
            "SELECT records FROM po_batches WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()

    return json.loads(row[0]) if row else None


def update_review(batch_id, reviewed):
    with connect() as connection:
        row = connection.execute(
            "SELECT status, records FROM po_batches WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()

        if row is None or row[0] != "DRAFT":
            raise ValueError("Only an existing draft batch can be reviewed.")

        original = json.loads(row[1])

        # Approval must apply to the exact saved order details.
        def order_details(records):
            return [
                {
                    key: value
                    for key, value in po.items()
                    if key not in {"status", "approved_at"}
                }
                for po in records
            ]

        if order_details(original) != order_details(reviewed):
            raise ValueError("Order details changed. Create a new draft.")

        statuses = {po["status"] for po in reviewed}

        if len(statuses) != 1:
            raise ValueError("All orders in a batch must have the same status.")

        status = statuses.pop()

        if status not in {"DRAFT", "REJECTED", "APPROVED_SIMULATION"}:
            raise ValueError("Invalid review status.")

        cursor = connection.execute(
            """
            UPDATE po_batches
            SET status = ?, records = ?
            WHERE batch_id = ? AND status = 'DRAFT'
            """,
            (status, json.dumps(reviewed), batch_id),
        )

        if cursor.rowcount != 1:
            raise ValueError("Batch status changed. Reload before reviewing.")


def list_batches():
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT batch_id, created_at, status
            FROM po_batches
            ORDER BY created_at DESC
            """
        ).fetchall()

    return rows