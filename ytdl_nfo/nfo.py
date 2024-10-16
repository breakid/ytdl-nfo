from __future__ import annotations

# Standard Libraries
import ast
import xml.etree.ElementTree as ET
from datetime import datetime
from logging import Logger
from logging import getLogger
from typing import Any
from typing import TypedDict
from typing import cast

# Third-party Libraries
from defusedxml.minidom import parseString

logger: Logger = getLogger()


# ============================================================================ #
#                                 Type Classes                                 #
# ============================================================================ #


class Converter(TypedDict):
    data_type: str
    input_f: str
    output_f: str


class NFOFieldType(TypedDict, total=False):
    attrs: dict[str, str]
    converter: Converter
    value: str


# ============================================================================ #
#                                  Dataclasses                                 #
# ============================================================================ #


class NFOField:
    attrs: dict[str, str]
    tag_path: str
    value: list[str]

    def __init__(self, tag_path: str, field_info: NFOFieldType, metadata: dict[str, Any]) -> None:
        self.tag_path = tag_path.rstrip("!")
        self.attrs = field_info.get("attrs", {})

        value: str = field_info.get("value", "").format_map(metadata)

        # If tag_path ends with a '!', the value should be deserialized to a Python list
        self.value = ast.literal_eval(value) if tag_path[-1] == "!" else [value]

        # If a converter is specified, apply it to each element in the value list
        if field_info.get("converter"):
            self.value = [
                self._convert(item=item, **cast(Converter, field_info.get("converter"))) for item in self.value
            ]

    def _convert(self, item: str, data_type: str, input_f: str, output_f: str, *_: str) -> str:
        if data_type == "date":
            item = datetime.strptime(item, input_f).strftime(output_f)  # noqa: DTZ007

        return item


class NFOConfig:
    filename: str = ""
    root_tag: str
    fields: list[NFOField]
    metadata: dict[str, Any]

    def __init__(self, config: dict[str, list[dict[str, str | NFOFieldType]]], metadata: dict[str, Any]) -> None:
        if "_filename" in config:
            self.filename = str(config["_filename"])

        # Treat the first top-level key that doesn't begin with "_" as the root tag element
        # This allows meta-fields such as "_filename" to be used
        # Note: To reduce confusion, there should only be one key that satisfies this criteria
        self.root_tag = next(key for key in config if not key.startswith("_"))

        self.fields = [
            NFOField(
                tag_path=tag,
                field_info=field_info if isinstance(field_info, dict) else NFOFieldType(value=field_info),
                metadata=metadata,
            )
            for elem in config[self.root_tag]
            for tag, field_info in elem.items()
        ]

        self.metadata = metadata

    @property
    def xml_str(self) -> str:
        self.top = ET.Element(self.root_tag)

        # Recursively generate the rest of the NFO XML
        try:
            self._create_child_element(self.top, self.fields, self.metadata)
        except ValueError as e:
            logger.exception(e)

        return parseString(ET.tostring(self.top, encoding="utf-8")).toprettyxml(indent=" " * 4)

    def _create_child_element(
        self,
        parent_element: ET.Element,
        subtree_data: NFOField | list[NFOField],
        metadata: dict[str, Any],
    ) -> None:
        # If the subtree_data is a list, recursively process each field
        if isinstance(subtree_data, list):
            for field in subtree_data:
                self._create_child_element(parent_element, field, metadata)
            return

        field: NFOField = subtree_data

        for item in field.value:
            element: ET.Element = parent_element

            # Create any intermediary elements
            for tag in field.tag_path.split(">"):
                element = ET.SubElement(parent=element, tag=tag)

            # Create the final ("leaf") element
            element.text = item

            # Add attributes
            for attribute, attr_value in field.attrs.items():
                element.set(attribute, attr_value.format_map(metadata))
