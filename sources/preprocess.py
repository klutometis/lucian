"""
Parse Lucian's Dialogues of the Dead from TEI XML into structured JSON.
Each dialogue becomes: { id, title, speakers, lines: [{speaker, text}] }
"""

from lxml import etree
import json
import re
from pathlib import Path

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def all_text(el) -> str:
    return clean("".join(el.itertext()))


def parse_dialogues(xml_path: Path) -> list[dict]:
    tree = etree.parse(xml_path)
    root = tree.getroot()

    dialogues = []

    # Each dialogue is a <div type="textpart" subtype="book">
    # Sections within it are subsections — flatten all <sp> across sections
    for div in root.findall(".//tei:div[@subtype='book']", NS):
        n = div.get("n", "?")

        # Title: direct <head> child (not inside a section)
        head = div.find("tei:head", NS)
        title = all_text(head) if head is not None else f"Dialogue {n}"

        lines = []
        speakers = set()

        for sp in div.findall(".//tei:sp", NS):
            speaker_el = sp.find("tei:speaker", NS)
            speaker = all_text(speaker_el) if speaker_el is not None else "?"

            # Collect all <p> text under this <sp>
            parts = []
            for p in sp.findall(".//tei:p", NS):
                parts.append(all_text(p))
            text = " ".join(parts).strip()

            if speaker and text:
                lines.append({"speaker": speaker, "text": text})
                speakers.add(speaker)

        if lines:
            dialogues.append(
                {
                    "id": int(n) if n.isdigit() else n,
                    "title": title,
                    "speakers": sorted(speakers),
                    "lines": lines,
                }
            )

    return dialogues


if __name__ == "__main__":
    src = Path(__file__).parent / "dialogi_mortuorum_grc.xml"
    out = Path(__file__).parent / "dialogues.json"

    dialogues = parse_dialogues(src)
    out.write_text(json.dumps(dialogues, ensure_ascii=False, indent=2))
    print(f"Parsed {len(dialogues)} dialogues → {out}")
    for d in dialogues:
        print(f"  [{d['id']:>2}] {d['title'][:60]}  ({len(d['lines'])} lines, speakers: {', '.join(d['speakers'])})")
