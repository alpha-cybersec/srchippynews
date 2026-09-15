import sys

import collector_gbhackers
import collector_cybersecuritynews
import collector_thehackernews

from dedup_store import (
    cleanup_retention,
    process_source,
    write_allnews,
)


COLLECTORS = [

    (
        collector_gbhackers.SOURCE_NAME,

        collector_gbhackers.SOURCE_SLUG,

        collector_gbhackers.collect,
    ),

    (
        collector_cybersecuritynews.SOURCE_NAME,

        collector_cybersecuritynews.SOURCE_SLUG,

        collector_cybersecuritynews.collect,
    ),

    (
        collector_thehackernews.SOURCE_NAME,

        collector_thehackernews.SOURCE_SLUG,

        collector_thehackernews.collect,
    ),
]


def main():

    print("")
    print("#" * 88)
    print(
        "# CTI CHIPPY NEWS V3"
    )
    print("#" * 88)

    all_events = []

    successful_sources = 0

    for (

        source_name,

        source_slug,

        collector,

    ) in COLLECTORS:

        print("")
        print("-" * 88)

        print(
            f"[SOURCE] "
            f"{source_name}"
        )

        print("-" * 88)

        try:

            snapshot = collector()

            results = snapshot.get(
                "results",
                {},
            )

            endpoint_success = any(

                endpoint.get(
                    "status"
                ) == "SUCCESS"

                for endpoint
                in results.values()
            )

            if endpoint_success:

                successful_sources += 1

            events = process_source(

                source_name=(
                    source_name
                ),

                source_slug=(
                    source_slug
                ),

                results=results,
            )

            all_events.extend(
                events
            )

        except Exception as exc:

            print(
                f"[ERROR] "
                f"{source_name}: "
                f"{exc}"
            )

    write_allnews(
        all_events
    )

    new_count = sum(

        1

        for article
        in all_events

        if article.get(
            "event_type"
        ) == "NEW"
    )

    updated_count = sum(

        1

        for article
        in all_events

        if article.get(
            "event_type"
        ) == "UPDATED"
    )

    print("")
    print("#" * 88)
    print("# RESUMEN")
    print("#" * 88)

    print(
        f"[+] Fuentes OK: "
        f"{successful_sources}"
    )

    print(
        f"[+] NEW: "
        f"{new_count}"
    )

    print(
        f"[+] UPDATED: "
        f"{updated_count}"
    )

    print(
        f"[+] ALLNEWS: "
        f"{len(all_events)}"
    )

    cleanup_retention()

    if successful_sources == 0:

        print(
            "[FAILED] "
            "Todas las fuentes fallaron."
        )

        return 1

    print(
        "[SUCCESS] "
        "Corrida terminada."
    )

    return 0


if __name__ == "__main__":

    sys.exit(
        main()
    )
