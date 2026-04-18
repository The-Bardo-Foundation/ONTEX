import csv
import time
from typing import Dict, Iterator, Optional, Tuple

import requests

API_STUDIES = "https://clinicaltrials.gov/api/v2/studies"


def _safe_get(d: Dict, path: Tuple[str, ...], default=None):
    """
    Traverse a nested dict by a sequence of keys, returning *default* if any
    key is missing or the value at that level is not a dict.

    Args:
        d:       The dict to traverse.
        path:    A tuple of keys forming the access path (e.g. ("a", "b", "c")).
        default: Value returned when the path cannot be followed.
    """
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def iter_study_index_rows(
    search_term: str = "osteosarcoma",
    query_mode: str = "term",
    page_size: int = 100,
    sleep_seconds: float = 0.0,
    session: Optional[requests.Session] = None,
) -> Iterator[Tuple[str, str]]:
    """
    Yields (nct_id, last_update_posted_date) for all studies matching the search term.
    last_update_posted_date is ISO 8601 date like "2025-01-14" when present.

    Can be treated as a generator to stream results.

    Args:
        search_term: text to search for (passed to query.term / query.cond / query.titles).
            Defaults to "osteosarcoma".
        query_mode: one of "term" (all terms, default), "cond" (condition), "titles"
        page_size: number of results per API request (max 1000)
        sleep_seconds: delay between requests to avoid rate limiting
        session: optional requests.Session for connection reuse

    Yields:
        Tuple of (nct_id, last_update_posted_date), where
        last_update_posted_date may be empty string if not available.
    """
    if query_mode not in {"cond", "term", "titles"}:
        raise ValueError("query_mode must be one of: term, cond, titles")

    s = session or requests.Session()
    page_token: Optional[str] = None

    fields = ",".join(
        [
            "protocolSection.identificationModule.nctId",
            "protocolSection.statusModule.lastUpdatePostDateStruct",
        ]
    )

    while True:
        params = {
            f"query.{query_mode}": search_term,
            "pageSize": page_size,
            "countTotal": "true",
            "fields": fields,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = s.get(API_STUDIES, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        for study in data.get("studies", []):
            nct_id = _safe_get(
                study,
                ("protocolSection", "identificationModule", "nctId"),
                default="",
            )
            last_update = _safe_get(
                study,
                ("protocolSection", "statusModule", "lastUpdatePostDateStruct", "date"),
                default="",
            )

            if nct_id:
                yield (nct_id, last_update or "")

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)


def export_index_csv(
    out_csv_path: str,
    search_term: str = "osteosarcoma",
    query_mode: str = "term",
    page_size: int = 100,
    sleep_seconds: float = 0.0,
) -> None:
    """
    Write all matching study index rows to a CSV file.

    Iterates iter_study_index_rows with the provided parameters and writes
    one row per study to *out_csv_path* with columns [nct_id, last_update_posted_date].
    Intended as a CLI utility / one-off data export.

    Args:
        out_csv_path:  Path to the output CSV file (created or overwritten).
        search_term:   Search text forwarded to iter_study_index_rows.
        query_mode:    Query mode forwarded to iter_study_index_rows.
        page_size:     API page size forwarded to iter_study_index_rows.
        sleep_seconds: Delay between API pages forwarded to iter_study_index_rows.
    """
    with (
        requests.Session() as s,
        open(out_csv_path, "w", newline="", encoding="utf-8") as f,
    ):
        w = csv.writer(f)
        w.writerow(["nct_id", "last_update_posted_date"])

        count = 0
        for nct_id, last_update in iter_study_index_rows(
            search_term=search_term,
            query_mode=query_mode,
            page_size=page_size,
            sleep_seconds=sleep_seconds,
            session=s,
        ):
            w.writerow([nct_id, last_update])
            count += 1

    print(f"Wrote {count} rows to {out_csv_path}")


if __name__ == "__main__":
    export_index_csv(out_csv_path="osteosarcoma_index.csv")
