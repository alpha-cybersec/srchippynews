from __future__ import annotations

import sys

import collector_cybersecuritynews
import collector_gbhackers
import collector_thehackernews
from dedup_store import cleanup_retention, process_source, write_allnews

COLLECTORS = [
    (collector_gbhackers.SOURCE_NAME, collector_gbhackers.SOURCE_SLUG, collector_gbhackers.collect),
    (collector_cybersecuritynews.SOURCE_NAME, collector_cybersecuritynews.SOURCE_SLUG, collector_cybersecuritynews.collect),
    (collector_thehackernews.SOURCE_NAME, collector_thehackernews.SOURCE_SLUG, collector_thehackernews.collect),
]


def main() -> int:
    print("\n" + "#" * 88)
    print("# CTI CHIPPY NEWS - FULL RUN")
    print("#" * 88)

    all_new_articles = []
    successful_sources = 0

    for source_name, source_slug, collector in COLLECTORS:
        print("\n" + "-" * 88)
        print(f"[SOURCE] {source_name}")
        print("-" * 88)

        try:
            snapshot = collector()
            results = snapshot.get("results", {})

            endpoint_success = any(
                endpoint.get("status") == "SUCCESS"
                for endpoint in results.values()
            )

            if endpoint_success:
                successful_sources += 1
            else:
                print(f"[WARNING] {source_name}: ningún endpoint válido.")

            new_articles = process_source(
                source_name=source_name,
                source_slug=source_slug,
                results=results,
            )
            all_new_articles.extend(new_articles)

        except Exception as exc:
            print(f"[ERROR] Falló {source_name}: {exc}")

    # allnews siempre representa ESTA corrida.
    write_allnews(all_new_articles)

    print("\n" + "#" * 88)
    print("# RESUMEN DE LA CORRIDA")
    print("#" * 88)
    print(f"[+] Fuentes con al menos un endpoint válido: {successful_sources}")
    print(f"[+] Noticias nuevas totales: {len(all_new_articles)}")
    print("[+] Salida: data/allnews.json")

    cleanup_retention()

    if successful_sources == 0:
        print("[FAILED] Ninguna fuente pudo ser consultada.")
        return 1

    print("[SUCCESS] Corrida completada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
