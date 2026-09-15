from config import FEEDS_DIR

from rss_common import (
    collect_source,
)


SOURCE_NAME = "GBHackers"
SOURCE_SLUG = "gbhackers"


FEEDS = [

    {

        "key": "ORIGINAL",

        "label": (
            "GBHackers-ORIGINAL"
        ),

        "url": (
            "https://gbhackers.com/feed/"
        ),
    },

    {

        "key": "FEEDBURNER",

        "label": (
            "GBHackers-FEEDBURNER"
        ),

        "url": (
            "https://feeds.feedburner.com/"
            "gbhackers"
        ),
    },
]


SNAPSHOT_FILE = (
    FEEDS_DIR
    / "gbhackers.json"
)


def collect():

    return collect_source(

        source_name=(
            SOURCE_NAME
        ),

        source_slug=(
            SOURCE_SLUG
        ),

        feeds=FEEDS,

        snapshot_file=(
            SNAPSHOT_FILE
        ),
    )


if __name__ == "__main__":

    collect()
