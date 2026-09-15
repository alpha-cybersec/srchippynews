import calendar
import html
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import feedparser
import requests


ECUADOR_TZ = ZoneInfo("America/Guayaquil")

FEED = {
    "name": "TheHackerNews-feedburner",
    "url": "https://feeds.feedburner.com/TheHackersNews"
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "CTI-RSS-Collector/1.0"
    ),
    "Accept": (
        "application/rss+xml,"
        "application/xml;q=0.9,"
        "text/xml;q=0.8,"
        "*/*;q=0.5"
    )
}


def get_today():
    return datetime.now(ECUADOR_TZ).date()


def get_entry_date(entry):

    if entry.get("published_parsed"):

        try:

            timestamp = calendar.timegm(
                entry.published_parsed
            )

            dt_utc = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc
            )

            return dt_utc.astimezone(
                ECUADOR_TZ
            )

        except Exception:
            return None

    if entry.get("updated_parsed"):

        try:

            timestamp = calendar.timegm(
                entry.updated_parsed
            )

            dt_utc = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc
            )

            return dt_utc.astimezone(
                ECUADOR_TZ
            )

        except Exception:
            return None

    return None


def get_feed():

    print("")
    print("=" * 70)

    print(
        f"[+] Probando: {FEED['name']}"
    )

    print(
        f"[+] URL: {FEED['url']}"
    )

    try:

        response = requests.get(
            FEED["url"],
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

    except Exception as exc:

        print(
            f"[ERROR] Error de conexión: {exc}"
        )

        return None

    print(
        f"[+] HTTP Status: "
        f"{response.status_code}"
    )

    print(
        f"[+] Content-Type: "
        f"{response.headers.get('content-type', 'UNKNOWN')}"
    )

    print(
        f"[+] Bytes recibidos: "
        f"{len(response.content)}"
    )

    if response.status_code != 200:

        print(
            f"[ERROR] HTTP "
            f"{response.status_code}"
        )

        return None

    parsed = feedparser.parse(
        response.content
    )

    print(
        f"[+] Feed title: "
        f"{parsed.feed.get('title', 'UNKNOWN')}"
    )

    print(
        f"[+] Entradas totales: "
        f"{len(parsed.entries)}"
    )

    if not parsed.entries:

        print(
            "[ERROR] No se encontraron entradas."
        )

        return None

    return {
        "name": FEED["name"],
        "url": FEED["url"],
        "final_url": response.url,
        "parsed": parsed
    }


def filter_today(result):

    today = get_today()

    print("")
    print(
        f"[+] Fecha de hoy en Ecuador: {today}"
    )

    articles = []

    for entry in result["parsed"].entries:

        published_dt = get_entry_date(
            entry
        )

        if not published_dt:
            continue

        if published_dt.date() != today:
            continue

        articles.append({

            "source": "The Hacker News",

            "id": entry.get(
                "id",
                entry.get("link", "")
            ),

            "title": html.unescape(
                entry.get("title", "")
            ),

            "url": entry.get(
                "link",
                ""
            ),

            "published": entry.get(
                "published",
                ""
            ),

            "published_date": str(
                published_dt.date()
            ),

            "summary": entry.get(
                "summary",
                ""
            )
        })

    return articles


def save_json(result, articles):

    output = {

        "source": "The Hacker News",

        "source_method": result["name"],

        "source_url": result["url"],

        "query_date": str(
            get_today()
        ),

        "article_count": len(
            articles
        ),

        "articles": articles
    }

    os.makedirs(
        "data",
        exist_ok=True
    )

    output_file = (
        "data/thehackernews.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    return output_file


def main():

    print("")
    print("############################################")
    print("#     CTI THE HACKER NEWS COLLECTOR        #")
    print("############################################")

    result = get_feed()

    if not result:

        print("")
        print(
            "[FAILED] El feed no funcionó."
        )

        sys.exit(1)

    print("")
    print(
        f"[SUCCESS] Feed funcionando: "
        f"{result['name']}"
    )

    articles = filter_today(
        result
    )

    output_file = save_json(
        result,
        articles
    )

    print("")
    print("############################################")

    print(
        f"[SUCCESS] Archivo: "
        f"{output_file}"
    )

    print(
        f"[SUCCESS] Artículos de hoy: "
        f"{len(articles)}"
    )

    print("############################################")

    print("")

    for article in articles:

        print(
            f"- {article['title']}"
        )

        print(
            f"  Fecha RSS: "
            f"{article['published']}"
        )

        print(
            f"  URL: "
            f"{article['url']}"
        )

        print("")


if __name__ == "__main__":
    main()
