import csv
import time
from typing import Dict, Iterator, Optional, Tuple

import requests


API_STUDIES = "https://clinicaltrials.gov/api/v2/studies"


# Helper to safely access nested dicts
def _safe_get(d: Dict, path: Tuple[str, ...], default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def iter_study_index_rows(
    keyword: str,
    query_mode: str = "cond",
    page_size: int = 100,
    sleep_seconds: float = 0.0, # small delay between requests to avoid rate limiting
    session: Optional[requests.Session] = None,
) -> Iterator[Tuple[str, str]]:
    """
    Yields (nct_id, last_update_posted_date) for all studies matching keyword.
    last_update_posted_date is ISO 8601 date like "2025-01-14" when present.

    Can be treated as a generator to stream results.

    args:
        keyword: search keyword
        query_mode: one of "cond" (condition), "term" (all terms), "titles" (study titles)
        page_size: number of results per API request (max 1000)
        sleep_seconds: delay between requests to avoid rate limiting
        session: optional requests.Session for connection reuse
    
    yields:
        Tuple of (nct_id, last_update_posted_date), where last_update_posted_date may be empty string if not available.
    """
    if query_mode not in {"cond", "term", "titles"}:
        raise ValueError("query_mode must be one of: cond, term, titles")

    s = session or requests.Session()
    page_token: Optional[str] = None

    # Limit payload to the exact fields you need
    fields = ",".join(
        [
            "protocolSection.identificationModule.nctId",
            "protocolSection.statusModule.lastUpdatePostDateStruct",
        ]
    )

    while True:
        params = {
            f"query.{query_mode}": keyword,
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
    keyword: str,
    out_csv_path: str,
    query_mode: str = "cond",
    page_size: int = 100,
    sleep_seconds: float = 0.0,
) -> None:
    with requests.Session() as s, open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nct_id", "last_update_posted_date"])

        count = 0
        for nct_id, last_update in iter_study_index_rows(
            keyword=keyword,
            query_mode=query_mode,
            page_size=page_size,
            sleep_seconds=sleep_seconds,
            session=s,
        ):
            w.writerow([nct_id, last_update])
            count += 1

    print(f"Wrote {count} rows to {out_csv_path}")


if __name__ == "__main__":
    export_index_csv(keyword="osteosarcoma", out_csv_path="osteosarcoma_index.csv")
