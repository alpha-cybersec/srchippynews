import calendar
import html
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import feedparser
import requests


# ============================================================
# CONFIGURACIÓN
# ============================================================

LOCAL_TIMEZONE = "America/Guayaquil"

WP_API_URL = "https://gbhackers.com/wp-json/wp/v2/posts"

RSS_FEEDS = [
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
        "CTI-RSS-Collector/2.0"
    ),
    "Accept": (
        "application/json,"
        "application/rss+xml,"
        "application/xml;q=0.9,"
        "text/xml;q=0.8,"
        "*/*;q=0.5"
    )
}


LOCAL_TZ = ZoneInfo(LOCAL_TIMEZONE)


# ============================================================
# FECHA DE HOY
# ============================================================

def get_today_local():

    now_local = datetime.now(LOCAL_TZ)

    return now_local.date()


# ============================================================
# CONVERTIR FECHA WORDPRESS
# ============================================================

def parse_wp_gmt_date(value):

    if not value:
        return None, None

    try:

        dt_utc = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        # WordPress date_gmt puede venir sin timezone explícito.
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(
                tzinfo=timezone.utc
            )

        dt_utc = dt_utc.astimezone(
            timezone.utc
        )

        dt_local = dt_utc.astimezone(
            LOCAL_TZ
        )

        return dt_utc, dt_local

    except Exception as exc:

        print(
            f"[WARNING] No se pudo interpretar "
            f"la fecha WordPress: {value}"
        )

        print(
            f"[WARNING] Error: {exc}"
        )

        return None, None


# ============================================================
# OBTENER WORDPRESS REST API
# ============================================================

def get_wordpress_posts_today():

    print("")
    print("=" * 70)
    print("[+] FUENTE 1: WordPress REST API")
    print(f"[+] URL: {WP_API_URL}")

    today_local = get_today_local()

    print(
        f"[+] Fecha objetivo: {today_local}"
    )

    print(
        f"[+] Zona horaria: {LOCAL_TIMEZONE}"
    )

    params = {

        # WordPress permite máximo 100 normalmente.
        "per_page": 100,

        "page": 1,

        "orderby": "date",

        "order": "desc",

        # Solicitamos solo campos útiles.
        "_fields": (
            "id,"
            "date,"
            "date_gmt,"
            "modified,"
            "modified_gmt,"
            "slug,"
            "status,"
            "link,"
            "title,"
            "excerpt,"
            "content,"
            "author,"
            "featured_media,"
            "categories,"
            "tags,"
            "yoast_head_json"
        )
    }

    try:

        response = requests.get(
            WP_API_URL,
            headers=HEADERS,
            params=params,
            timeout=30
        )

    except Exception as exc:

        print(
            f"[ERROR] Falló conexión con WordPress API: {exc}"
        )

        return {
            "success": False,
            "articles": []
        }

    print(
        f"[+] HTTP Status: "
        f"{response.status_code}"
    )

    print(
        f"[+] URL final: "
        f"{response.url}"
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
            "[ERROR] WordPress API no respondió HTTP 200."
        )

        return {
            "success": False,
            "articles": []
        }

    try:

        posts = response.json()

    except Exception as exc:

        print(
            f"[ERROR] La respuesta no es JSON válido: {exc}"
        )

        return {
            "success": False,
            "articles": []
        }

    if not isinstance(posts, list):

        print(
            "[ERROR] WordPress API no devolvió una lista."
        )

        return {
            "success": False,
            "articles": []
        }

    print(
        f"[+] Posts recibidos inicialmente: "
        f"{len(posts)}"
    )

    articles = []

    for post in posts:

        date_gmt = post.get(
            "date_gmt",
            ""
        )

        dt_utc, dt_local = parse_wp_gmt_date(
            date_gmt
        )

        if not dt_local:
            continue

        # ==========================================
        # FILTRO PRINCIPAL:
        # SOLO PUBLICACIONES DEL DÍA DE HOY
        # ==========================================

        if dt_local.date() != today_local:
            continue

        title_data = post.get(
            "title",
            {}
        ) or {}

        excerpt_data = post.get(
            "excerpt",
            {}
        ) or {}

        content_data = post.get(
            "content",
            {}
        ) or {}

        yoast = post.get(
            "yoast_head_json",
            {}
        ) or {}

        og_image = ""

        images = yoast.get(
            "og_image",
            []
        )

        if images and isinstance(images, list):

            first_image = images[0]

            if isinstance(first_image, dict):
                og_image = first_image.get(
                    "url",
                    ""
                )

        article = {

            # Fuente
            "source": "GBHackers",

            "source_method": (
                "wordpress_rest_api"
            ),

            # ID WordPress
            "id": post.get(
                "id"
            ),

            # Identificador textual
            "slug": post.get(
                "slug",
                ""
            ),

            # Título
            "title": html.unescape(
                title_data.get(
                    "rendered",
                    ""
                )
            ),

            # URL original
            "url": post.get(
                "link",
                ""
            ),

            # Fechas
            "published_utc": (
                dt_utc.isoformat()
            ),

            "published_local": (
                dt_local.isoformat()
            ),

            "published_date_local": (
                str(dt_local.date())
            ),

            # WordPress raw dates
            "wordpress_date": post.get(
                "date",
                ""
            ),

            "wordpress_date_gmt": (
                date_gmt
            ),

            # Resumen
            "excerpt_html": (
                excerpt_data.get(
                    "rendered",
                    ""
                )
            ),

            # CONTENIDO COMPLETO
            "content_html": (
                content_data.get(
                    "rendered",
                    ""
                )
            ),

            # SEO / descripción
            "seo_description": (
                yoast.get(
                    "description",
                    ""
                )
            ),

            # Imagen principal
            "featured_image": (
                og_image
            ),

            # Metadatos
            "author_id": post.get(
                "author"
            ),

            "featured_media_id": (
                post.get(
                    "featured_media"
                )
            ),

            "categories": post.get(
                "categories",
                []
            ),

            "tags": post.get(
                "tags",
                []
            )
        }

        articles.append(
            article
        )

    print("")
    print(
        f"[SUCCESS] WordPress API disponible."
    )

    print(
        f"[SUCCESS] Artículos publicados HOY: "
        f"{len(articles)}"
    )

    return {
        "success": True,
        "articles": articles,
        "endpoint": response.url
    }


# ============================================================
# CONVERTIR FECHA RSS
# ============================================================

def rss_date_to_local(entry):

    parsed_date = None

    if entry.get(
        "published_parsed"
    ):

        parsed_date = entry.get(
            "published_parsed"
        )

    elif entry.get(
        "updated_parsed"
    ):

        parsed_date = entry.get(
            "updated_parsed"
        )

    if not parsed_date:
        return None, None

    try:

        timestamp = calendar.timegm(
            parsed_date
        )

        dt_utc = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        )

        dt_local = dt_utc.astimezone(
            LOCAL_TZ
        )

        return dt_utc, dt_local

    except Exception:

        return None, None


# ============================================================
# RSS FALLBACK
# ============================================================

def get_rss_today(source):

    print("")
    print("=" * 70)

    print(
        f"[+] Probando RSS: "
        f"{source['name']}"
    )

    print(
        f"[+] URL: "
        f"{source['url']}"
    )

    today_local = get_today_local()

    try:

        response = requests.get(
            source["url"],
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

    except Exception as exc:

        print(
            f"[ERROR] Error RSS: {exc}"
        )

        return {
            "success": False,
            "articles": []
        }

    print(
        f"[+] HTTP Status: "
        f"{response.status_code}"
    )

    print(
        f"[+] Content-Type: "
        f"{response.headers.get('content-type', 'UNKNOWN')}"
    )

    if response.status_code != 200:

        return {
            "success": False,
            "articles": []
        }

    parsed = feedparser.parse(
        response.content
    )

    if not parsed.entries:

        print(
            "[ERROR] RSS válido pero sin entradas."
        )

        return {
            "success": False,
            "articles": []
        }

    articles = []

    for entry in parsed.entries:

        dt_utc, dt_local = (
            rss_date_to_local(
                entry
            )
        )

        if not dt_local:
            continue

        # SOLO HOY
        if dt_local.date() != today_local:
            continue

        articles.append({

            "source": "GBHackers",

            "source_method": (
                source["name"]
            ),

            "id": entry.get(
                "id",
                entry.get(
                    "link",
                    ""
                )
            ),

            "title": html.unescape(
                entry.get(
                    "title",
                    ""
                )
            ),

            "url": entry.get(
                "link",
                ""
            ),

            "published_utc": (
                dt_utc.isoformat()
            ),

            "published_local": (
                dt_local.isoformat()
            ),

            "published_date_local": (
                str(
                    dt_local.date()
                )
            ),

            "summary_html": entry.get(
                "summary",
                ""
            )
        })

    print(
        f"[SUCCESS] Artículos RSS de HOY: "
        f"{len(articles)}"
    )

    return {
        "success": True,
        "articles": articles,
        "endpoint": response.url
    }


# ============================================================
# GUARDAR RESULTADO
# ============================================================

def save_output(
    source_method,
    endpoint,
    articles
):

    now_local = datetime.now(
        LOCAL_TZ
    )

    output = {

        "collector": (
            "GitHub Actions CTI Collector"
        ),

        "collector_version": "2.0",

        "source": "GBHackers",

        "source_method": source_method,

        "endpoint": endpoint,

        "query_date": str(
            now_local.date()
        ),

        "timezone": (
            LOCAL_TIMEZONE
        ),

        "collected_at": (
            now_local.isoformat()
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


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("############################################")
    print("#      CTI GBHACKERS COLLECTOR V2          #")
    print("############################################")
    print("")

    today = get_today_local()

    print(
        f"[+] Día de consulta: {today}"
    )

    print(
        f"[+] Zona horaria: {LOCAL_TIMEZONE}"
    )

    # ========================================================
    # 1. WORDPRESS REST API
    # ========================================================

    wp_result = (
        get_wordpress_posts_today()
    )

    if wp_result["success"]:

        articles = wp_result[
            "articles"
        ]

        output_file = save_output(
            "wordpress_rest_api",
            wp_result.get(
                "endpoint",
                WP_API_URL
            ),
            articles
        )

        print("")
        print("############################################")
        print("[SUCCESS] WORDPRESS API UTILIZADA")
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
                f"  Fecha local: "
                f"{article['published_local']}"
            )

            print(
                f"  URL: "
                f"{article['url']}"
            )

            print(
                f"  Content HTML bytes: "
                f"{len(article['content_html'])}"
            )

            print("")

        return

    # ========================================================
    # 2. RSS DIRECTO
    # 3. FEEDBURNER
    # ========================================================

    print("")
    print(
        "[WARNING] WordPress API falló."
    )

    print(
        "[WARNING] Activando fallback RSS."
    )

    for source in RSS_FEEDS:

        rss_result = get_rss_today(
            source
        )

        if rss_result["success"]:

            articles = rss_result[
                "articles"
            ]

            output_file = save_output(
                source["name"],
                rss_result.get(
                    "endpoint",
                    source["url"]
                ),
                articles
            )

            print("")
            print("############################################")
            print("[SUCCESS] RSS FALLBACK UTILIZADO")
            print(
                f"[SUCCESS] Fuente: "
                f"{source['name']}"
            )
            print(
                f"[SUCCESS] Artículos de hoy: "
                f"{len(articles)}"
            )
            print(
                f"[SUCCESS] Archivo: "
                f"{output_file}"
            )
            print("############################################")

            return

    print("")
    print("############################################")
    print("[FAILED] Todas las fuentes fallaron.")
    print("############################################")

    sys.exit(1)


if __name__ == "__main__":
    main()
