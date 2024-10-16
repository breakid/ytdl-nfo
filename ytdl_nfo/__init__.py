from __future__ import annotations

# Standard Libraries
import re
from argparse import ArgumentParser
from argparse import Namespace
from pathlib import Path

from .nfo_generator import NFOGenerator


def main() -> None:
    parser: ArgumentParser = ArgumentParser(
        prog="ytdl-nfo",
        description="A utility for converting metadata, saved using the youtube-dl '--write-info-json' flag, to an "
        "NFO file compatible with Kodi, Plex, Emby, Jellyfin, etc.",
    )
    parser.add_argument(
        "--config",
        action="version",
        version=str(Path(__file__) / "configs"),
        help="Show the path to the config directory",
    )
    parser.add_argument("-e", "--extractor", default="file specific", help="Specify specific extractor")
    parser.add_argument(
        "-r", "--regex", type=str, default=r".json$", help="A regular expression used to search for JSON source files"
    )
    parser.add_argument("-w", "--overwrite", action="store_true", help="Overwrite existing NFO files")
    parser.add_argument(
        "input", metavar="JSON_FILE", type=Path, help="JSON file to convert or directory to process recursively"
    )
    args: Namespace = parser.parse_args()

    if args.input.isfile():
        NFOGenerator(args.input, extractor_name=args.extractor, overwrite=args.overwrite)
    else:
        for file in args.input.rglob("*"):
            if file.name.endswith(".live_chat.json"):
                continue

            if re.search(args.regex, file.name):
                NFOGenerator(file, extractor_name=args.extractor, overwrite=args.overwrite)


__all__: list[str] = ["main", "NFOGenerator"]
