import json
import os
from datetime import datetime, timezone

import feedparser
import requests


SOURCE_NAME = "Cyber Security News"
OUTPUT_FILE = "data/cybersecuritynews.json"

FEEDS = [
    {
        "key": "ORIGINAL",
        "name": "CyberSecurityNews-ORIGINAL",
        "url": "https://cybersecuritynews.com/feed/"
    },
    {
        "key": "FEEDBURNER",
        "name": "CyberSecurityNews-FEEDBURNER",
        "url": "https://feeds.feedburner.com/cyber-security-news"
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
        "application/atom+xml;q=0.9,"
        "application/xml;q=0.9,"
        "text/xml;q=0.8,"
        "*/*;q=0.5"
    )
}


def get_feed(source):
    print("")
    print("=" * 80)
    print(f"[+] FUENTE: {source['key']}")
    print(f"[+] Nombre: {source['name']}")
    print(f"[+] URL: {source['url']}")

    result = {
        "label": source["name"],
        "endpoint": source["url"],
        "status": "FAILED",
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "article_count": 0,
        "articles": [],
        "error": ""
    }

    try:
        response = requests.get(
            source["url"],
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        result["http_status"] = response.status_code
        result["final_url"] = response.url
        result["content_type"] = response.headers.get(
            "content-type",
            ""
        )

        print(f"[+] HTTP Status: {response.status_code}")
        print(f"[+] URL final: {response.url}")
        print(f"[+] Content-Type: {result['content_type']}")
        print(f"[+] Bytes recibidos: {len(response.content)}")

        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            print(f"[ERROR] {result['error']}")
            return result

        text_lower = response.text[:10000].lower()

        captcha_indicators = [
            "captcha",
            "verify you are human",
            "checking your browser",
            "challenge-platform",
            "cf-chl"
        ]

        detected = [
            word
            for word in captcha_indicators
            if word in text_lower
        ]

        if detected:
            result["error"] = (
                f"Posible protección/CAPTCHA: {detected}"
            )
            print(f"[WARNING] {result['error']}")
            return result

        parsed = feedparser.parse(response.content)

        print(
            f"[+] Feed title: "
            f"{parsed.feed.get('title', 'UNKNOWN')}"
        )
        print(f"[+] Entradas detectadas: {len(parsed.entries)}")

        if len(parsed.entries) == 0:
            result["error"] = "No se encontraron entradas RSS."

            if getattr(parsed, "bozo", False):
                result["error"] += (
                    f" FeedParser: {parsed.bozo_exception}"
                )

            print(f"[ERROR] {result['error']}")
            return result

        articles = []

        for entry in parsed.entries[:20]:
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published": entry.get(
                    "published",
                    entry.get("updated", "")
                ),
                "summary": entry.get("summary", ""),
                "id": entry.get(
                    "id",
                    entry.get("link", "")
                )
            })

        result["status"] = "SUCCESS"
        result["article_count"] = len(articles)
        result["articles"] = articles

        return result

    except Exception as exc:
        result["error"] = str(exc)
        print(f"[ERROR] {exc}")
        return result


def show_articles(key, result):
    print("")
    print("#" * 80)
    print(f"# RESULTADOS {key}")
    print("#" * 80)
    print(f"Estado: {result['status']}")
    print(f"Artículos: {result['article_count']}")
    print("")

    for number, article in enumerate(
        result["articles"],
        start=1
    ):
        print(f"{number}. {article['title']}")
        print(f"   {article['url']}")
        print(f"   {article['published']}")
        print("")


def main():
    print("")
    print("############################################")
    print("#   CTI CYBER SECURITY NEWS - COMPARADOR   #")
    print("############################################")

    results = {}

    for source in FEEDS:
        result = get_feed(source)
        results[source["key"]] = result
        show_articles(source["key"], result)

    output = {
        "collector": "GitHub Actions RSS Comparator",
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": SOURCE_NAME,
        "results": {
            "ORIGINAL": results.get("ORIGINAL", {}),
            "FEEDBURNER": results.get("FEEDBURNER", {})
        }
    }

    os.makedirs("data", exist_ok=True)

    with open(
        OUTPUT_FILE,
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
    print("[SUCCESS] Comparación terminada")
    print(f"[SUCCESS] JSON: {OUTPUT_FILE}")
    print(
        f"[ORIGINAL] "
        f"{results['ORIGINAL']['article_count']} artículos"
    )
    print(
        f"[FEEDBURNER] "
        f"{results['FEEDBURNER']['article_count']} artículos"
    )
    print("############################################")


if __name__ == "__main__":
    main()
