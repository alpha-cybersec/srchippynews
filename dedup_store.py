from __future__ import annotations

import hashlib
import html
import re
import shutil

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

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

from rss_common import (
    atomic_write_json,
    load_json,
)


LOCAL_TZ = ZoneInfo(
    TIMEZONE_NAME
)


HTML_TAG_RE = re.compile(
    r"<[^>]+>"
)

ZERO_WIDTH_RE = re.compile(
    r"[\u200b\u200c\u200d\ufeff]"
)


def now_utc():

    return datetime.now(
        timezone.utc
    )


def now_local():

    return datetime.now(
        LOCAL_TZ
    )


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_url(
    url: str,
) -> str:

    if not url:
        return ""

    value = url.strip()

    if not value:
        return ""

    if "://" not in value:

        value = (
            "https://"
            + value
        )

    try:

        parts = urlsplit(
            value
        )

        host = (
            parts.netloc
            .lower()
            .strip()
        )

        if host.startswith(
            "www."
        ):

            host = host[4:]

        if host.endswith(
            ":80"
        ):

            host = host[:-3]

        elif host.endswith(
            ":443"
        ):

            host = host[:-4]

        path = (
            parts.path
            or ""
        )

        path = (
            "/"
            + "/".join(

                segment

                for segment
                in path.split("/")

                if segment
            )
        )

        if path == "/":

            path = ""

        return (
            f"{host}{path}"
        ).lower()

    except Exception:

        return (
            url
            .lower()
            .rstrip("/")
        )


def normalize_text(
    value: str,
) -> str:

    if not value:
        return ""

    value = html.unescape(
        str(value)
    )

    value = HTML_TAG_RE.sub(
        " ",
        value,
    )

    value = ZERO_WIDTH_RE.sub(
        "",
        value,
    )

    value = " ".join(
        value.split()
    )

    return (
        value
        .strip()
        .lower()
    )


# ============================================================
# IDENTIDAD
# ============================================================

def build_article_key(
    article: dict[str, Any],
) -> str:

    normalized_url = (
        normalize_url(
            article.get(
                "url",
                "",
            )
        )
    )

    if normalized_url:

        return normalized_url

    title = normalize_text(
        article.get(
            "title",
            "",
        )
    )

    if not title:

        return ""

    return (
        "title-sha256:"
        + hashlib.sha256(
            title.encode(
                "utf-8"
            )
        ).hexdigest()
    )


# ============================================================
# VERSIONADO DE CONTENIDO
# ============================================================

def build_content_hash(
    article: dict[str, Any],
) -> str:

    title = normalize_text(
        article.get(
            "title",
            "",
        )
    )

    summary = normalize_text(
        article.get(
            "summary",
            "",
        )
    )

    content = (
        title
        + "|"
        + summary
    )

    return hashlib.sha256(
        content.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# HISTÓRICOS
# ============================================================

def month_id(
    value: date,
):

    return value.strftime(
        "%Y-%m"
    )


def previous_month(
    value: date,
):

    first = value.replace(
        day=1
    )

    return first - timedelta(
        days=1
    )


def history_file(
    source_slug,
    month,
):

    return (
        HISTORY_DIR
        / month
        / f"{source_slug}.json"
    )


def daily_file(
    value,
):

    return (
        DAILY_DIR
        / f"{value.isoformat()}.json"
    )


def empty_history(
    source_name,
    source_slug,
    month,
):

    return {

        "month": month,

        "source": source_name,

        "source_slug": (
            source_slug
        ),

        "article_count": 0,

        "articles": [],
    }


def empty_daily(
    value,
):

    return {

        "date": (
            value.isoformat()
        ),

        "article_count": 0,

        "sources": {},

        "articles": [],
    }


def prepare_stored_article(
    article,
):

    prepared = dict(
        article
    )

    # Compatibilidad con nuestra
    # versión anterior.
    article_key = (

        prepared.get(
            "article_key"
        )

        or prepared.get(
            "dedup_key"
        )

        or build_article_key(
            prepared
        )
    )

    prepared[
        "article_key"
    ] = article_key

    if not prepared.get(
        "content_hash"
    ):

        prepared[
            "content_hash"
        ] = build_content_hash(
            prepared
        )

    if not prepared.get(
        "version"
    ):

        prepared[
            "version"
        ] = 1

    prepared.pop(
        "dedup_key",
        None,
    )

    return prepared


def build_history_index(
    previous_history,
    current_history,
):

    index = {}

    # Primero mes anterior.
    # Después actual para que
    # tenga prioridad.

    for history in (
        previous_history,
        current_history,
    ):

        for raw in history.get(
            "articles",
            [],
        ):

            article = (
                prepare_stored_article(
                    raw
                )
            )

            key = article.get(
                "article_key"
            )

            if key:

                index[key] = (
                    article
                )

    return index


# ============================================================
# ORIGINAL + FEEDBURNER
# ============================================================

def prepare_candidate(
    raw_article,
    source_name,
    source_slug,
    endpoint_type,
):

    article = dict(
        raw_article
    )

    article[
        "source"
    ] = source_name

    article[
        "source_slug"
    ] = source_slug

    article[
        "article_key"
    ] = build_article_key(
        article
    )

    article[
        "content_hash"
    ] = build_content_hash(
        article
    )

    article[
        "detected_via"
    ] = [
        endpoint_type
    ]

    article[
        "endpoint_content_hashes"
    ] = {

        endpoint_type:
            article[
                "content_hash"
            ]
    }

    return article


def merge_current_endpoints(
    source_name,
    source_slug,
    results,
):

    merged = {}

    # IMPORTANTE:
    # ORIGINAL siempre se procesa
    # antes que FeedBurner.

    for endpoint_type in (
        "ORIGINAL",
        "FEEDBURNER",
    ):

        endpoint = results.get(
            endpoint_type,
            {},
        )

        if endpoint.get(
            "status"
        ) != "SUCCESS":

            continue

        for raw_article in endpoint.get(
            "articles",
            [],
        ):

            candidate = (
                prepare_candidate(

                    raw_article,

                    source_name,

                    source_slug,

                    endpoint_type,
                )
            )

            key = candidate.get(
                "article_key"
            )

            if not key:

                continue

            if key not in merged:

                merged[key] = (
                    candidate
                )

                continue

            current = merged[key]

            if endpoint_type not in (
                current[
                    "detected_via"
                ]
            ):

                current[
                    "detected_via"
                ].append(
                    endpoint_type
                )

            current[
                "endpoint_content_hashes"
            ][
                endpoint_type
            ] = candidate[
                "content_hash"
            ]

            # NO sustituimos ORIGINAL
            # con FeedBurner.
            #
            # El contenido canónico
            # sigue siendo ORIGINAL.

    for article in (
        merged.values()
    ):

        detected = set(
            article.get(
                "detected_via",
                [],
            )
        )

        hashes = set(

            article.get(
                "endpoint_content_hashes",
                {},
            ).values()
        )

        if len(detected) == 1:

            article[
                "feed_comparison"
            ] = "SINGLE_ENDPOINT"

        elif len(hashes) == 1:

            article[
                "feed_comparison"
            ] = "MATCH"

        else:

            article[
                "feed_comparison"
            ] = (
                "CONTENT_DIFFERENT"
            )

        if "ORIGINAL" in detected:

            article[
                "canonical_endpoint"
            ] = "ORIGINAL"

        else:

            article[
                "canonical_endpoint"
            ] = "FEEDBURNER"

    return list(
        merged.values()
    )


# ============================================================
# UTILIDADES DE ACTUALIZACIÓN
# ============================================================

def sort_articles(
    articles,
):

    articles.sort(

        key=lambda item: (

            item.get(
                "published_utc",
                "",
            ),

            item.get(
                "title",
                "",
            ),
        ),

        reverse=True,
    )


def replace_or_append_history(
    articles,
    article,
):

    target_key = article.get(
        "article_key"
    )

    for index, current in enumerate(
        articles
    ):

        current = (
            prepare_stored_article(
                current
            )
        )

        if current.get(
            "article_key"
        ) == target_key:

            articles[index] = (
                article
            )

            return

    articles.append(
        article
    )


def replace_or_append_daily(
    articles,
    article,
):

    target = (

        article.get(
            "source_slug"
        ),

        article.get(
            "article_key"
        ),
    )

    for index, current in enumerate(
        articles
    ):

        current = (
            prepare_stored_article(
                current
            )
        )

        current_target = (

            current.get(
                "source_slug"
            ),

            current.get(
                "article_key"
            ),
        )

        if current_target == target:

            articles[index] = (
                article
            )

            return

    articles.append(
        article
    )


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def process_source(
    source_name,
    source_slug,
    results,
):

    local_now = now_local()
    utc_now = now_utc()

    today = local_now.date()

    current_month = month_id(
        today
    )

    previous_month_id = month_id(
        previous_month(
            today
        )
    )

    current_history_path = (
        history_file(
            source_slug,
            current_month,
        )
    )

    previous_history_path = (
        history_file(
            source_slug,
            previous_month_id,
        )
    )

    today_path = daily_file(
        today
    )

    current_history = load_json(

        current_history_path,

        empty_history(
            source_name,
            source_slug,
            current_month,
        ),
    )

    previous_history = load_json(

        previous_history_path,

        empty_history(
            source_name,
            source_slug,
            previous_month_id,
        ),
    )

    daily = load_json(

        today_path,

        empty_daily(
            today
        ),
    )

    known = build_history_index(

        previous_history,

        current_history,
    )

    # Daily como segunda barrera.

    for raw in daily.get(
        "articles",
        [],
    ):

        article = (
            prepare_stored_article(
                raw
            )
        )

        if article.get(
            "source_slug"
        ) != source_slug:

            continue

        key = article.get(
            "article_key"
        )

        if key:

            known.setdefault(
                key,
                article,
            )

    candidates = (
        merge_current_endpoints(

            source_name,

            source_slug,

            results,
        )
    )

    events = []

    current_articles = [

        prepare_stored_article(
            article
        )

        for article
        in current_history.get(
            "articles",
            [],
        )
    ]

    daily_articles = [

        prepare_stored_article(
            article
        )

        for article
        in daily.get(
            "articles",
            [],
        )
    ]

    for candidate in candidates:

        key = candidate[
            "article_key"
        ]

        current_hash = candidate[
            "content_hash"
        ]

        previous = known.get(
            key
        )

        # ====================================================
        # NEW
        # ====================================================

        if previous is None:

            event = dict(
                candidate
            )

            event[
                "event_type"
            ] = "NEW"

            event[
                "version"
            ] = 1

            event[
                "first_seen_utc"
            ] = utc_now.isoformat()

            event[
                "first_seen_local"
            ] = local_now.isoformat()

            event[
                "last_updated_utc"
            ] = utc_now.isoformat()

            event[
                "last_updated_local"
            ] = local_now.isoformat()

            events.append(
                event
            )

            replace_or_append_history(
                current_articles,
                event,
            )

            replace_or_append_daily(
                daily_articles,
                event,
            )

            known[key] = event

            continue

        previous = (
            prepare_stored_article(
                previous
            )
        )

        previous_hash = (
            previous.get(
                "content_hash",
                "",
            )
        )

        # ====================================================
        # DUPLICATE
        # ====================================================

        if (
            previous_hash
            == current_hash
        ):

            continue

        # ====================================================
        # UPDATED
        # ====================================================

        event = dict(
            candidate
        )

        event[
            "event_type"
        ] = "UPDATED"

        event[
            "previous_content_hash"
        ] = previous_hash

        event[
            "version"
        ] = (

            int(
                previous.get(
                    "version",
                    1,
                )
            )

            + 1
        )

        event[
            "first_seen_utc"
        ] = previous.get(

            "first_seen_utc",

            utc_now.isoformat(),
        )

        event[
            "first_seen_local"
        ] = previous.get(

            "first_seen_local",

            local_now.isoformat(),
        )

        event[
            "last_updated_utc"
        ] = utc_now.isoformat()

        event[
            "last_updated_local"
        ] = local_now.isoformat()

        events.append(
            event
        )

        replace_or_append_history(
            current_articles,
            event,
        )

        replace_or_append_daily(
            daily_articles,
            event,
        )

        known[key] = event

    # ========================================================
    # Nada nuevo
    # ========================================================

    if not events:

        print(
            f"[DEDUP] "
            f"{source_name}: "
            "0 NEW / 0 UPDATED"
        )

        return []

    # ========================================================
    # Guardar HISTÓRICO
    # ========================================================

    sort_articles(
        current_articles
    )

    current_history[
        "month"
    ] = current_month

    current_history[
        "source"
    ] = source_name

    current_history[
        "source_slug"
    ] = source_slug

    current_history[
        "article_count"
    ] = len(
        current_articles
    )

    current_history[
        "articles"
    ] = current_articles

    atomic_write_json(
        current_history_path,
        current_history,
    )

    # ========================================================
    # Guardar DAILY
    # ========================================================

    sort_articles(
        daily_articles
    )

    source_counts = {}

    for article in daily_articles:

        slug = article.get(
            "source_slug",
            "unknown",
        )

        source_counts[
            slug
        ] = (

            source_counts.get(
                slug,
                0,
            )

            + 1
        )

    daily[
        "date"
    ] = today.isoformat()

    daily[
        "article_count"
    ] = len(
        daily_articles
    )

    daily[
        "sources"
    ] = source_counts

    daily[
        "articles"
    ] = daily_articles

    atomic_write_json(
        today_path,
        daily,
    )

    new_count = sum(

        1

        for event in events

        if event.get(
            "event_type"
        ) == "NEW"
    )

    updated_count = sum(

        1

        for event in events

        if event.get(
            "event_type"
        ) == "UPDATED"
    )

    print(
        f"[DEDUP] "
        f"{source_name}: "
        f"NEW={new_count} "
        f"UPDATED={updated_count}"
    )

    return events


# ============================================================
# ALLNEWS
# ============================================================

def write_allnews(
    events,
):

    sort_articles(
        events
    )

    source_counts = {}

    new_count = 0
    updated_count = 0

    for article in events:

        slug = article.get(
            "source_slug",
            "unknown",
        )

        source_counts[
            slug
        ] = (

            source_counts.get(
                slug,
                0,
            )

            + 1
        )

        if article.get(
            "event_type"
        ) == "UPDATED":

            updated_count += 1

        else:

            new_count += 1

    if events:

        output = {

            "generated_at_utc":
                now_utc().isoformat(),

            "generated_at_local":
                now_local().isoformat(),

            "article_count":
                len(events),

            "new_count":
                new_count,

            "updated_count":
                updated_count,

            "sources":
                source_counts,

            "articles":
                events,
        }

    else:

        output = {

            "article_count": 0,

            "new_count": 0,

            "updated_count": 0,

            "sources": {},

            "articles": [],
        }

    atomic_write_json(
        ALLNEWS_FILE,
        output,
    )


# ============================================================
# RETENCIÓN
# ============================================================

def cleanup_daily_files():

    reference = now_local().date()

    DAILY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in DAILY_DIR.glob(
        "*.json"
    ):

        try:

            file_date = (
                datetime.strptime(

                    path.stem,

                    "%Y-%m-%d",

                ).date()
            )

        except ValueError:

            continue

        age = (
            reference
            - file_date
        ).days

        if (
            age
            >= DAILY_RETENTION_DAYS
        ):

            path.unlink(
                missing_ok=True
            )

            print(
                "[CLEANUP DAILY] "
                f"{path}"
            )


def cleanup_history_months():

    reference = now_local().date()

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in HISTORY_DIR.iterdir():

        if not path.is_dir():
            continue

        try:

            folder_date = (
                datetime.strptime(

                    path.name,

                    "%Y-%m",

                ).date()
            )

        except ValueError:

            continue

        age_months = (

            (
                reference.year
                - folder_date.year
            )
            * 12

            +

            (
                reference.month
                - folder_date.month
            )
        )

        if (
            age_months
            >= HISTORY_RETENTION_MONTHS
        ):

            shutil.rmtree(
                path
            )

            print(
                "[CLEANUP HISTORY] "
                f"{path}"
            )


def cleanup_retention():

    cleanup_daily_files()

    cleanup_history_months()
