from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lxml import etree

MAX_ARCHIVE_SIZE = 1_000_000_000
MAX_EXPANDED_SIZE = 2_000_000_000
MAX_MEMBER_SIZE = 750_000_000
MAX_MEMBERS = 100_000
MAX_COMPRESSION_RATIO = 2_500


class UnsafePackageError(RuntimeError):
    """Raised when an OOXML package fails defensive validation."""


def xml_parser() -> etree.XMLParser:
    """Return a fresh parser that never loads DTDs, networks, or entities."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        recover=False,
    )


def parse_xml(data: bytes) -> etree._Element:
    return etree.fromstring(data, parser=xml_parser())


def validate_ooxml_archive(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > MAX_ARCHIVE_SIZE:
        raise UnsafePackageError("The document exceeds the 1 GB safety limit.")
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_MEMBERS:
                raise UnsafePackageError("The document contains too many package entries.")
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                raise UnsafePackageError("The document contains duplicate ZIP entry names.")
            required = {"word/document.xml", "[Content_Types].xml"}
            if not required.issubset(names):
                raise UnsafePackageError("The file is not a valid Word OOXML package.")
            expanded = 0
            for item in infos:
                if item.flag_bits & 0x1:
                    raise UnsafePackageError("Encrypted OOXML package entries are not supported.")
                if item.file_size > MAX_MEMBER_SIZE:
                    raise UnsafePackageError(f"Package entry is too large: {item.filename}")
                expanded += item.file_size
                if expanded > MAX_EXPANDED_SIZE:
                    raise UnsafePackageError("The expanded document exceeds the 2 GB safety limit.")
                if item.compress_size and item.file_size / item.compress_size > MAX_COMPRESSION_RATIO:
                    raise UnsafePackageError(f"Suspicious compression ratio in {item.filename}.")
    except BadZipFile as exc:
        raise UnsafePackageError("The document is damaged or encrypted.") from exc
