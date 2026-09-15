import json
import os
import sys
from datetime import datetime, timezone

import feedparser
import requests


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
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/140.0 Safari/537.36 "
        "CTI-RSS-Collector/1.0"
    ),
    "Accept": (
        "application/rss+xml,"
        "application/xml;q=0.9,"
        "text/xml;q=0.8,"
        "*/*;q=0.5"
    )
}


def get_feed(source):
    print("=" * 70)
    print(f"[+] Probando: {source['name']}")
    print(f"[+] URL: {source['url']}")

    try:
        response = requests.get(
            source["url"],
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

    except Exception as exc:
        print(f"[ERROR] Error de conexión: {exc}")
        return None

    print(f"[+] HTTP Status: {response.status_code}")
    print(f"[+] URL final: {response.url}")
    print(
        f"[+] Content-Type: "
        f"{response.headers.get('content-type', 'UNKNOWN')}"
    )
    print(f"[+] Bytes recibidos: {len(response.content)}")

    text_lower = response.text[:10000].lower()

    captcha_indicators = [
        "captcha",
        "verify you are human",
        "checking your browser",
        "challenge-platform",
        "cf-chl",
        "cloudflare"
    ]

    detected = [
        word
        for word in captcha_indicators
        if word in text_lower
    ]

    if detected:
        print(f"[WARNING] Posible protección/CAPTCHA detectado: {detected}")
        return None

    if response.status_code != 200:
        print(
            f"[ERROR] El servidor respondió "
            f"HTTP {response.status_code}"
        )
        return None

    parsed = feedparser.parse(response.content)

    print(f"[+] Feed title: {parsed.feed.get('title', 'UNKNOWN')}")
    print(f"[+] Entradas detectadas: {len(parsed.entries)}")

    if len(parsed.entries) == 0:
        print("[ERROR] No se encontraron entradas RSS.")

        if getattr(parsed, "bozo", False):
            print(
                f"[ERROR] FeedParser error: "
                f"{parsed.bozo_exception}"
            )

        print("[DEBUG] Primeros 500 caracteres recibidos:")
        print(response.text[:500])

        return None

    return {
        "source_name": source["name"],
        "source_url": source["url"],
        "final_url": response.url,
        "content_type": response.headers.get(
            "content-type",
            ""
        ),
        "parsed": parsed
    }


def convert_entries(result):
    parsed = result["parsed"]

    articles = []

    for entry in parsed.entries[:20]:

        article = {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "id": entry.get(
                "id",
                entry.get("link", "")
            )
        }

        articles.append(article)

    output = {
        "collector": "GitHub Actions RSS Collector",
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": "GBHackers",
        "working_endpoint": result["source_url"],
        "final_url": result["final_url"],
        "content_type": result["content_type"],
        "article_count": len(articles),
        "articles": articles
    }

    return output


def main():

    print("")
    print("############################################")
    print("#      CTI RSS COLLECTOR - TEST            #")
    print("############################################")
    print("")

    working_feed = None

    for source in FEEDS:

        result = get_feed(source)

        if result:
            working_feed = result
            print("")
            print(
                f"[SUCCESS] Feed funcionando: "
                f"{source['name']}"
            )
            break

        print("")
        print(
            f"[FAILED] No funcionó: "
            f"{source['name']}"
        )
        print("")

    if not working_feed:
        print("")
        print("############################################")
        print("[FAILED] Ningún endpoint RSS funcionó.")
        print("############################################")
        sys.exit(1)

    output = convert_entries(working_feed)

    os.makedirs("data", exist_ok=True)

    output_file = "data/gbhackers.json"

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

    print("")
    print("############################################")
    print("[SUCCESS] JSON generado correctamente")
    print(f"[SUCCESS] Archivo: {output_file}")
    print(
        f"[SUCCESS] Artículos: "
        f"{output['article_count']}"
    )
    print("############################################")

    print("")
    print("Primeros artículos:")

    for article in output["articles"][:5]:
        print("")
        print(f" - {article['title']}")
        print(f"   {article['url']}")


if __name__ == "__main__":
    main()
