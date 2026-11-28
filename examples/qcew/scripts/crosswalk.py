"""Read the BLS QCEW County-MSA-CSA crosswalk spreadsheet, as BLS serves it.

    python3 examples/qcew/scripts/crosswalk.py            (prints the 2024 to current sheet as CSV)

The file is sources/codelists/qcew-county-msa-csa-crosswalk.xlsx, saved unchanged from
https://www.bls.gov/cew/classifications/areas/qcew-county-msa-csa-crosswalk.xlsx (D-016;
www.bls.gov refuses command-line requests, so a person saves it from a browser). An .xlsx is
a zip of XML files; this reads it with the standard library only. The sheet read is the one
for data from 2024 on (the July 2023 delineations): the first sheet whose name holds "2023",
or the first sheet of the workbook.
"""

import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parents[1]
FILE = HERE / "sources" / "codelists" / "qcew-county-msa-csa-crosswalk.xlsx"
COLUMNS = ("county_code", "county_title", "msa_code", "msa_title", "csa_code", "csa_title")
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _column(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    assert letters
    index = 0
    for letter in letters.group(0):
        index = index * 26 + ord(letter) - 64
    return index - 1


def _sheet_rows(book: zipfile.ZipFile, path: str, strings: list[str]) -> list[list[str]]:
    out = []
    root = ElementTree.fromstring(book.read(path))
    for row in root.iterfind(".//m:sheetData/m:row", NS):
        cells: dict[int, str] = {}
        for cell in row.iterfind("m:c", NS):
            value = cell.find("m:v", NS)
            if cell.get("t") == "inlineStr":
                text = "".join(t.text or "" for t in cell.iterfind(".//m:t", NS))
            elif value is None or value.text is None:
                continue
            elif cell.get("t") == "s":
                text = strings[int(value.text)]
            else:
                text = value.text
            cells[_column(cell.get("r", "A1"))] = text.strip()
        if cells:
            out.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return out


def sheet_name_and_rows(path: Path = FILE) -> tuple[str, list[tuple[str, ...]]]:
    """The name of the sheet read and its rows as COLUMNS; county codes are five characters."""
    with zipfile.ZipFile(path) as book:
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            shared = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            for item in shared.iterfind("m:si", NS):
                strings.append("".join(t.text or "" for t in item.iterfind(".//m:t", NS)))
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        links = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target", "") for r in links.iterfind("p:Relationship", NS)}
        sheets = [
            (s.get("name", ""), targets[s.get(f"{{{NS['r']}}}id")])
            for s in workbook.iterfind("m:sheets/m:sheet", NS)
        ]
        name, target = next((s for s in sheets if "2023" in s[0]), sheets[0])
        target = target.lstrip("/")
        rows = _sheet_rows(book, target if target.startswith("xl/") else f"xl/{target}", strings)
    start = next(i for i, r in enumerate(rows) if r and r[0].lower().startswith("county code"))
    out = []
    for row in rows[start + 1 :]:
        cells = (row + [""] * 6)[:6]
        if not cells[0]:
            continue
        cells[0] = cells[0].split(".")[0].zfill(5)
        out.append(tuple(cells))
    return name, out


def main() -> int:
    if not FILE.is_file():
        print(f"crosswalk: {FILE.relative_to(HERE)} is not there; see this script's header")
        return 1
    _, rows = sheet_name_and_rows()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
