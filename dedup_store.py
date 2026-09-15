from __future__ import annotations

import hashlib
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from config import (
    ALLNEWS_FILE,
    DAILY_DIR,
    DAILY_RETENTION_DAYS,
    HISTORY_DIR,
    HISTORY_RETENTION_MONTHS,
    TIMEZONE_NAME,
)
from rss_common import atomic_write_json, load_json

LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def normalize_url(url: str) -> str:
    if not url:
        return ""

    value = url.strip()
    if not value:
        return ""

    parse_value = value if "://" in value else f"https://{value}"

    try:
        parts = urlsplit(parse_value)
        host = parts.netloc.lower().strip()

        if host.startswith("www."):
            host = host[4:]

        if host.endswith(":80"):
            host = host[:-3]
        elif host.endswith(":443"):
            host = host[:-4]

        path = parts.path or ""
        path = "/" + "/".join(segment for segment in path.split("/") if segment)
        if path == "/":
            path = ""

        return f"{host}{path}".lower()
    except Exception:
        return value.lower().rstrip("/")


def normalize_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def build_dedup_key(article: dict[str, Any]) -> str:
    normalized_url = normalize_url(article.get("url", ""))
    if normalized_url:
        return normalized_url

    fallback = (
        normalize_title(article.get("title", ""))
        + "|"
        + (article.get("published_utc") or article.get("published", ""))
    )

    return "sha256:" + hashlib.sha256(fallback.encode("utf-8")).hexdigest()


def month_id(value: date) -> str:
    return value.strftime("%Y-%m")


def previous_month(value: date) -> date:
    return value.replace(day=1) - timedelta(days=1)


def history_file(source_slug: str, month: str) -> Path:
    return HISTORY_DIR / month / f"{source_slug}.json"


def daily_file(value: date) -> Path:
    return DAILY_DIR / f"{value.isoformat()}.json"


def empty_history(source_name: str, source_slug: str, month: str) -> dict[str, Any]:
    return {
        "month": month,
        "source": source_name,
        "source_slug": source_slug,
        "article_count": 0,
        "articles": [],
    }


def empty_daily(value: date) -> dict[str, Any]:
    return {
        "date": value.isoformat(),
        "article_count": 0,
        "sources": {},
        "articles": [],
    }


def merge_current_endpoints(source_name: str, source_slug: str, results: dict[str, Any]) -> list[dict[str, Any]]:
    """Une ORIGINAL + FEEDBURNER dentro de la misma fuente."""
    merged: dict[str, dict[str, Any]] = {}

    # ORIGINAL primero para conservarlo como versión canónica si existe en ambos.
    for endpoint_type in ("ORIGINAL", "FEEDBURNER"):
        endpoint = results.get(endpoint_type, {})
        if endpoint.get("status") != "SUCCESS":
            continue

        for raw_article in endpoint.get("articles", []):
            article = dict(raw_article)
            key = build_dedup_key(article)
            if not key:
                continue

            if key not in merged:
                article["source"] = source_name
                article["source_slug"] = source_slug
                article["dedup_key"] = key
                article["detected_via"] = [endpoint_type]
                merged[key] = article
            elif endpoint_type not in merged[key]["detected_via"]:
                merged[key]["detected_via"].append(endpoint_type)

    return list(merged.values())


def _article_keys(articles: list[dict[str, Any]]) -> set[str]:
    keys = set()
    for article in articles:
        key = article.get("dedup_key") or build_dedup_key(article)
        if key:
            keys.add(key)
    return keys


def _sort_articles(articles: list[dict[str, Any]]) -> None:
    articles.sort(
        key=lambda item: (item.get("published_utc", ""), item.get("title", "")),
        reverse=True,
    )


def process_source(source_name: str, source_slug: str, results: dict[str, Any]) -> list[dict[str, Any]]:
    """
    1) Dedup ORIGINAL + FEEDBURNER.
    2) Compara mes actual + mes anterior.
    3) Compara daily actual como segunda barrera.
    4) Solo lo no visto se considera nuevo.
    5) Guarda nuevo en histórico mensual actual y daily.
    6) Devuelve solo lo nuevo para allnews.
    """
    local_now = now_local()
    today = local_now.date()

    current_month = month_id(today)
    prev_month = month_id(previous_month(today))

    current_history_path = history_file(source_slug, current_month)
    previous_history_path = history_file(source_slug, prev_month)
    today_path = daily_file(today)

    current_history = load_json(
        current_history_path,
        empty_history(source_name, source_slug, current_month),
    )
    previous_history = load_json(
        previous_history_path,
        empty_history(source_name, source_slug, prev_month),
    )
    daily = load_json(today_path, empty_daily(today))

    known_keys = set()
    known_keys.update(_article_keys(current_history.get("articles", [])))
    known_keys.update(_article_keys(previous_history.get("articles", [])))

    # Segunda barrera de seguridad: el daily del día actual.
    for article in daily.get("articles", []):
        if article.get("source_slug") != source_slug:
            continue
        key = article.get("dedup_key") or build_dedup_key(article)
        if key:
            known_keys.add(key)

    candidates = merge_current_endpoints(source_name, source_slug, results)

    first_seen_utc = now_utc().isoformat()
    first_seen_local = local_now.isoformat()
    new_articles = []

    for article in candidates:
        key = article["dedup_key"]
        if key in known_keys:
            continue

        article["first_seen_utc"] = first_seen_utc
        article["first_seen_local"] = first_seen_local
        new_articles.append(article)
        known_keys.add(key)

    if not new_articles:
        print(f"[DEDUP] {source_name}: 0 noticias nuevas.")
        return []

    history_articles = current_history.setdefault("articles", [])
    history_articles.extend(new_articles)
    _sort_articles(history_articles)

    current_history["month"] = current_month
    current_history["source"] = source_name
    current_history["source_slug"] = source_slug
    current_history["article_count"] = len(history_articles)
    atomic_write_json(current_history_path, current_history)

    daily_articles = daily.setdefault("articles", [])
    existing_daily_pairs = {
        (
            article.get("source_slug", ""),
            article.get("dedup_key") or build_dedup_key(article),
        )
        for article in daily_articles
    }

    for article in new_articles:
        pair = (source_slug, article["dedup_key"])
        if pair not in existing_daily_pairs:
            daily_articles.append(article)
            existing_daily_pairs.add(pair)

    _sort_articles(daily_articles)

    source_counts = {}
    for article in daily_articles:
        slug = article.get("source_slug", "unknown")
        source_counts[slug] = source_counts.get(slug, 0) + 1

    daily["date"] = today.isoformat()
    daily["article_count"] = len(daily_articles)
    daily["sources"] = source_counts
    atomic_write_json(today_path, daily)

    print(f"[DEDUP] {source_name}: {len(new_articles)} noticias nuevas.")
    print(f"[HISTORY] {current_history_path}: {current_history['article_count']} artículos.")
    print(f"[DAILY] {today_path}: {daily['article_count']} artículos.")

    return new_articles


def write_allnews(new_articles: list[dict[str, Any]]) -> None:
    """allnews.json contiene SOLO noticias nuevas de la corrida actual."""
    _sort_articles(new_articles)

    source_counts = {}
    for article in new_articles:
        slug = article.get("source_slug", "unknown")
        source_counts[slug] = source_counts.get(slug, 0) + 1

    if new_articles:
        output = {
            "generated_at_utc": now_utc().isoformat(),
            "generated_at_local": now_local().isoformat(),
            "article_count": len(new_articles),
            "sources": source_counts,
            "articles": new_articles,
        }
    else:
        # Archivo estable cuando varias corridas seguidas no traen novedades.
        output = {
            "article_count": 0,
            "sources": {},
            "articles": [],
        }

    atomic_write_json(ALLNEWS_FILE, output)


def cleanup_daily_files(reference_date: date | None = None) -> list[Path]:
    reference_date = reference_date or now_local().date()
    deleted = []
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    for path in DAILY_DIR.glob("*.json"):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue

        if (reference_date - file_date).days >= DAILY_RETENTION_DAYS:
            path.unlink(missing_ok=True)
            deleted.append(path)

    return deleted


def cleanup_history_months(reference_date: date | None = None) -> list[Path]:
    reference_date = reference_date or now_local().date()
    deleted = []
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    for path in HISTORY_DIR.iterdir():
        if not path.is_dir():
            continue

        try:
            folder_date = datetime.strptime(path.name, "%Y-%m").date()
        except ValueError:
            continue

        age_months = (
            (reference_date.year - folder_date.year) * 12
            + (reference_date.month - folder_date.month)
        )

        if age_months >= HISTORY_RETENTION_MONTHS:
            shutil.rmtree(path)
            deleted.append(path)

    return deleted


def cleanup_retention() -> None:
    daily_deleted = cleanup_daily_files()
    history_deleted = cleanup_history_months()

    for path in daily_deleted:
        print(f"[CLEANUP DAILY] Eliminado: {path}")
    for path in history_deleted:
        print(f"[CLEANUP HISTORY] Eliminado: {path}")

    if not daily_deleted:
        print("[CLEANUP DAILY] Sin archivos para eliminar.")
    if not history_deleted:
        print("[CLEANUP HISTORY] Sin meses para eliminar.")
