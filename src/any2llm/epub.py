"""Extract EPUB chapters in reading order."""

import posixpath
from typing import BinaryIO
from urllib.parse import unquote
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring

from .cleaner import clean_text
from .markup import html_to_text

# Font obfuscation leaves the text readable, unlike DRM.
_FONT_OBFUSCATION = {"http://www.idpf.org/2008/embedding", "http://ns.adobe.com/pdf/enc#RC"}
_HTML_TYPES = {"application/xhtml+xml", "text/html"}
_MAX_CHAPTER_BYTES = 16 * 1024**2


class EncryptedEpub(Exception):
    """The book is protected with DRM."""


def _local(tag: str) -> str:
    return tag.rpartition("}")[2]


def _drm(archive: ZipFile) -> bool:
    try:
        root = fromstring(archive.read("META-INF/encryption.xml"))
    except KeyError:
        return False
    algorithms = {
        element.get("Algorithm") for element in root.iter() if _local(element.tag) == "EncryptionMethod"
    }
    return bool(algorithms - _FONT_OBFUSCATION)


def epub_text(stream: BinaryIO) -> str:
    """Return the book text with one section per spine document."""
    with ZipFile(stream) as archive:
        if _drm(archive):
            raise EncryptedEpub
        container = fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(e.get("full-path") for e in container.iter() if _local(e.tag) == "rootfile")
        package = fromstring(archive.read(rootfile))
        base = posixpath.dirname(rootfile)
        manifest = {
            item.get("id"): (item.get("href", ""), item.get("media-type", ""))
            for item in package.iter() if _local(item.tag) == "item"
        }
        title = next((e.text for e in package.iter() if _local(e.tag) == "title" and e.text), "")
        sections = [f"# {title.strip()}"] if title.strip() else []
        for itemref in (e for e in package.iter() if _local(e.tag) == "itemref"):
            href, media_type = manifest.get(itemref.get("idref"), ("", ""))
            if media_type not in _HTML_TYPES or not href:
                continue
            name = posixpath.normpath(posixpath.join(base, unquote(href.partition("#")[0])))
            try:
                info = archive.getinfo(name)
            except KeyError:
                continue
            if info.file_size > _MAX_CHAPTER_BYTES:
                continue
            text = html_to_text(archive.read(info).decode("utf-8", errors="replace"))
            if text:
                sections.append(text)
        return clean_text("\n\n".join(sections))
