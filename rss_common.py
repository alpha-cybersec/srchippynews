from __future__ import annotations

import copy
import json
import os
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import feedparser
import requests

from config import HEADERS, REQUEST_TIMEOUT_SECONDS

CAPTCHA_INDICATORS = (
    "captcha",
    "verify you are human",
    "checking your browser",
    "challenge-platform",
    "cf-chl",
)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")

    os.replace(temp_path, path)


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return copy.deepcopy(default)

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass

    return copy.deepcopy(default)


def published_to_utc_iso(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def fetch_feed(source: dict[str, str]) -> dict[str, Any]:
    label = source["label"]
    url = source["url"]

    print("=" * 88)
    print(f"[+] Endpoint: {label}")
    print(f"[+] URL: {url}")

    result: dict[str, Any] = {
        "label": label,
        "endpoint": url,
        "status": "FAILED",
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "feed_title": "",
        "article_count": 0,
        "articles": [],
        "error": "",
    }

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        result["http_status"] = response.status_code
        result["final_url"] = response.url
        result["content_type"] = response.headers.get("content-type", "")

        print(f"[+] HTTP Status: {response.status_code}")
        print(f"[+] URL final: {response.url}")
        print(f"[+] Content-Type: {result['content_type']}")
        print(f"[+] Bytes recibidos: {len(response.content)}")

        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            print(f"[ERROR] {result['error']}")
            return result

        text_lower = response.text[:10000].lower()
        detected = [x for x in CAPTCHA_INDICATORS if x in text_lower]
        if detected:
            result["error"] = "Posible protección/CAPTCHA: " + ", ".join(detected)
            print(f"[WARNING] {result['error']}")
            return result

        parsed = feedparser.parse(response.content)
        result["feed_title"] = parsed.feed.get("title", "")

        print(f"[+] Feed title: {result['feed_title'] or 'UNKNOWN'}")
        print(f"[+] Entradas detectadas: {len(parsed.entries)}")

        if not parsed.entries:
            result["error"] = "No se encontraron entradas RSS/Atom."
            if getattr(parsed, "bozo", False):
                result["error"] += f" FeedParser: {parsed.bozo_exception}"
            print(f"[ERROR] {result['error']}")
            return result

        articles = []
        for entry in parsed.entries:
            published = entry.get("published", entry.get("updated", ""))
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published": published,
                "published_utc": published_to_utc_iso(published),
                "summary": entry.get("summary", entry.get("description", "")),
                "id": entry.get("id", entry.get("guid", entry.get("link", ""))),
            })

        result["status"] = "SUCCESS"
        result["article_count"] = len(articles)
        result["articles"] = articles
        return result

    except requests.RequestException as exc:
        result["error"] = f"Error HTTP/conexión: {exc}"
        print(f"[ERROR] {result['error']}")
        return result
    except Exception as exc:
        result["error"] = f"Error inesperado: {exc}"
        print(f"[ERROR] {result['error']}")
        return result


def collect_source(source_name: str, source_slug: str, feeds: list[dict[str, str]], snapshot_file: Path) -> dict[str, Any]:
    print("\n" + "#" * 88)
    print(f"# CTI SOURCE: {source_name}")
    print("#" * 88)

    results = {}
    for feed in feeds:
        results[feed["key"]] = fetch_feed(feed)
        print("")

    snapshot = {
        "source": source_name,
        "source_slug": source_slug,
        "results": results,
    }

    # Sin fetched_at para evitar commits si el contenido no cambió.
    atomic_write_json(snapshot_file, snapshot)

    print(f"[+] {source_name} ORIGINAL: {results.get('ORIGINAL', {}).get('article_count', 0)}")
    print(f"[+] {source_name} FEEDBURNER: {results.get('FEEDBURNER', {}).get('article_count', 0)}")
    print(f"[+] Snapshot: {snapshot_file}")
    return snapshot
