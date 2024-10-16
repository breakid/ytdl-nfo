"""TODO"""

from __future__ import annotations

# Standard Libraries
import json
import re
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from logging import Logger
from logging import getLogger
from typing import TYPE_CHECKING
from typing import Any

# Third-party Libraries
import pkg_resources
from yaml import safe_load

# Internal Libraries
from ytdl_nfo.nfo import NFOConfig

if TYPE_CHECKING:
    # Standard Libraries
    from pathlib import Path

logger: Logger = getLogger()


# YouTube timestamps appear to use Pacific Standard Time (PST)
# Reference: https://support.google.com/youtube/answer/1270709?hl=en#:~:text='Published%20on'%20date%20on%20watch%20page
PST = timezone(timedelta(hours=-8))


class NFOGenerator:
    def __init__(self, json_file: Path, *, extractor_name: str | None = None, overwrite: bool = False) -> None:
        nfo_config: NFOConfig
        self.json_file: Path = json_file

        # ---------------------------- Load JSON Metadata ---------------------------- #

        # Use a defaultdict to return an empty string rather than raising a KeyError, if an extractor config references
        # a metadata field that does not exist
        # Reference: https://stackoverflow.com/a/21754294
        metadata: dict[str, Any] = defaultdict(lambda: "")

        try:
            # Read metadata from the JSON file
            metadata.update(json.loads(json_file.read_text(encoding="utf-8")))

            # Some .info.json files may not include an upload_date
            metadata.setdefault("upload_date", datetime.fromtimestamp((metadata["epoch"]), tz=PST).strftime("%Y%m%d"))
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from: %s", str(json_file))
            return

        # ------------------------ Set / Update Extractor Name ----------------------- #

        # Reset extractor name, if applicable
        if not isinstance((extractor_name := extractor_name or metadata.get("extractor")), str):
            logger.error("Invalid extractor: %s", extractor_name)
            return

        # Normalize the extractor name
        extractor_name = re.sub(r"[:?*/\\]", "_", extractor_name.lower())

        logger.info("Processing %s with %s extractor", str(json_file), extractor_name)

        # --------------------------- Initialize NFO Config -------------------------- #

        try:
            # Read the extractor config from the package resources
            extractor_path: str = f"configs/{extractor_name}.yaml"

            with pkg_resources.resource_stream("ytdl_nfo", extractor_path) as f:
                nfo_config = NFOConfig(safe_load(f), metadata)
        except FileNotFoundError:
            logger.error("No NFO config found for extractor %s", extractor_name)
            return

        # Set the NFO file name based on the '_filename' metadata attribute or the JSON file name
        self.nfo_filename: str = nfo_config.filename or self.default_nfo_name

        # Abort if NFO file exists and overwrite was not specified
        if self.nfo_path.exists() and not overwrite:
            logger.warning("Skipping %s; NFO file already exists, and 'overwrite' is disabled", str(self.nfo_path))
            return

        # ---------------------- Generate and Write the NFO File --------------------- #

        self.nfo_path.write_text(nfo_config.xml_str, encoding="utf-8")

    @property
    def default_nfo_name(self) -> str:
        suffixes: str = "".join(self.json_file.suffixes)

        return self.json_file.name[: len(suffixes) * -1]

    @property
    def nfo_path(self) -> Path:
        return self.json_file.with_name(f"{self.nfo_filename}.nfo")
