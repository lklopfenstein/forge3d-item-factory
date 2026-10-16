"""Small no-dependency integrity check for the static interface."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            if values["id"] in self.ids:
                raise AssertionError(f"Duplicate id: {values['id']}")
            self.ids.add(values["id"])
        for key in ("src", "href"):
            value = values.get(key, "")
            if value and not value.startswith(("#", "http://", "https://", "mailto:")):
                self.references.append(value)


def main():
    html = (DIST / "index.html").read_text(encoding="utf-8")
    parser = AssetParser()
    parser.feed(html)
    missing = []
    for reference in parser.references:
        target = DIST / urlparse(reference).path
        if not target.exists():
            missing.append(reference)
    assert not missing, f"Missing static assets: {', '.join(missing)}"
    required = {"factory", "helmetCanvas", "downloadScript", "localBuildButton", "qaList"}
    assert required.issubset(parser.ids), f"Missing UI ids: {required - parser.ids}"
    print(f"Static integrity passed: {len(parser.ids)} ids, {len(parser.references)} local assets.")


if __name__ == "__main__":
    main()
