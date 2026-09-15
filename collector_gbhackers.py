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

FEEDS = [
    {
        "name": "GBHackers-direct",
        "url": "https://gbhackers.com/feed/"
    },
    {
        "name": "GBHackers-feedburner",
        "url": "https://feeds.feedburner.com/gbhackers"
    }
]


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


def get_feed(source):

    print("")
    print("=" * 70)

    print(
        f"[+] Probando: {source['name']}"
    )

    print(
        f"[+] URL: {source['url']}"
    )

    try:

        response = requests.get(
            source["url"],
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
        "name": source["name"],
        "url": source["url"],
        "final_url": response.url,
        "parsed": parsed
    }


def filter_today(result):

    today = get_today()

    print("")
    print(
        f"[+] Fecha de hoy: {today}"
    )

    articles = []

    for entry in result["parsed"].entries:

        published_dt = get_entry_date(
            entry
        )

        if not published_dt:
            continue

        # SOLO FECHA DE HOY
        if published_dt.date() != today:
            continue

        articles.append({

            "source": "GBHackers",

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

        "source": "GBHackers",

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
        "data/gbhackers.json"
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
    print("#      CTI GBHACKERS RSS COLLECTOR         #")
    print("############################################")

    working_feed = None

    for source in FEEDS:

        result = get_feed(
            source
        )

        if result:

            working_feed = result

            print("")
            print(
                f"[SUCCESS] Feed funcionando: "
                f"{source['name']}"
            )

            break

    if not working_feed:

        print("")
        print(
            "[FAILED] Ningún feed funcionó."
        )

        sys.exit(1)

    articles = filter_today(
        working_feed
    )

    output_file = save_json(
        working_feed,
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
