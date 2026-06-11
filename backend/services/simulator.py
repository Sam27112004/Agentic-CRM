from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from backend.database import SessionLocal
from backend.schemas import IngestEmailPayload
from backend.services.ingestion import IngestionError, ingest_email


DEFAULT_DATA_PATH = Path("data/email-data-advanced.json")


def load_messages(data_path: Path) -> list[dict[str, object]]:
    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {data_path}. Add email-data-advanced.json before running the simulator."
        )

    with data_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("emails", "messages", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    raise ValueError("Unsupported dataset format. Expected a list of email payloads.")


def build_payload(raw_message: dict[str, object]) -> IngestEmailPayload:
    timestamp = raw_message.get("timestamp")
    if isinstance(timestamp, str):
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    elif isinstance(timestamp, datetime):
        parsed_timestamp = timestamp
    else:
        raise ValueError("Each message must include a timestamp")

    return IngestEmailPayload(
        message_id=str(raw_message["message_id"]),
        thread_id=str(raw_message["thread_id"]),
        sender=str(raw_message["sender"]),
        subject=raw_message.get("subject") if raw_message.get("subject") is not None else None,
        body=raw_message.get("body") if raw_message.get("body") is not None else None,
        timestamp=parsed_timestamp,
    )


def run_simulation(data_path: Path, speed: float, message_id: str | None = None) -> None:
    messages = load_messages(data_path)
    if message_id is not None:
        messages = [message for message in messages if str(message.get("message_id")) == message_id]

    if not messages:
        raise ValueError("No matching email messages were found in the dataset.")

    delay = 1.0 / speed if speed > 0 else 0.0
    db = SessionLocal()
    try:
        for raw_message in messages:
            payload = build_payload(raw_message)
            try:
                result = ingest_email(db=db, payload=payload)
                print(json.dumps(result, default=str))
            except IngestionError as exc:
                print(
                    json.dumps(
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "details": exc.details,
                        },
                        default=str,
                    )
                )

            if delay:
                time.sleep(delay)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the email dataset through the ingestion pipeline.")
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="Path to email-data-advanced.json")
    parser.add_argument("--speed", type=float, default=float(os.getenv("SIMULATION_SPEED", "1")))
    parser.add_argument("--message-id", default=None, help="Replay a single message by message_id")
    args = parser.parse_args()

    run_simulation(Path(args.data), speed=args.speed, message_id=args.message_id)


if __name__ == "__main__":
    main()
