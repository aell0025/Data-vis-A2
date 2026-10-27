"""
Clean and finalize the Museums Victoria pull for charting.

Run from the folder containing mv_music_items.json:
  python finalize_mv.py

Output: mv_final.json and mv_final.csv
"""
import csv
import json
import re

SRC = "mv_music_items.json"


def object_type(title):
    if title and " - " in title: return title.split(" - ")[0].strip()
    return (title or "").split(",")[0].strip()


YEAR_RE = re.compile(r"\b(1[6-9]\d{2}|20[0-2]\d)\b")

# Association types that describe the ITEM's own date. Types like
# "Manufacturer", "Maker" or "Performer" often carry a date range for
# that person/company's whole career or operating years, not the date
# of this specific object - using those caused a real bug (a 1928
# catalogue got dated 1910, from its manufacturer's 1910-1930 operating
# span). Only trust these more specific types for a confident year.
RELIABLE_DATE_TYPES = {
    "date made", "date inscribed", "date written", "place made",
    "place & date of event", "place & date used", "date purchased",
}


def years_in(text):
    return [int(y) for y in YEAR_RE.findall(text or "")]


def extract_year(associations, title):
    """Three-tier approach, each returned with a confidence label:
      high   - a reliable, item-specific dating association exists
      medium - no reliable association, but the title itself has a year
      low    - fall back to any association date at all (least trustworthy,
               may belong to a related person/company rather than the item)
    Within a tier, the earliest year found is used.
    """
    reliable_years = []
    for a in associations:
        if (a.get("type") or "").lower() in RELIABLE_DATE_TYPES:
            reliable_years += years_in(a.get("date"))
    if reliable_years:
        return min(reliable_years), "high"

    title_years = years_in(title)
    if title_years:
        return min(title_years), "medium"

    all_years = []
    for a in associations:
        all_years += years_in(a.get("date"))
    if all_years:
        return min(all_years), "low"

    return None, None


def primary_place(associations):
    """Prefer the most specific place available: locality > state > country.
    Returns the first association that has any place info."""
    for a in associations:
        if a.get("locality"):
            return {"locality": a["locality"], "state": a.get("state"),
                    "country": a.get("country")}
    for a in associations:
        if a.get("state"):
            return {"locality": None, "state": a["state"],
                    "country": a.get("country")}
    for a in associations:
        if a.get("country"):
            return {"locality": None, "state": None, "country": a["country"]}
    return {"locality": None, "state": None, "country": None}


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    memo = [r for r in data if r.get("memorabilia_flag")]
    print(f"Loaded {len(data)} total records, {len(memo)} flagged as memorabilia")

    cleaned = []
    for r in memo:
        year, confidence = extract_year(r["associations"], r["title"])
        place = primary_place(r["associations"])
        cleaned.append({
            "id": r["id"],
            "registrationNumber": r["registrationNumber"],
            "title": r["title"],
            "object_type": object_type(r["title"]),
            "classifications": r["classifications"],
            "year": year,
            "year_confidence": confidence,
            "decade": (year // 10) * 10 if year else None,
            "locality": place["locality"],
            "state": place["state"],
            "country": place["country"],
            "thumbnail": r["thumbnail"],
            "thumbnail_licence": r["thumbnail_licence"],
        })

    from collections import Counter
    conf_counts = Counter(r["year_confidence"] for r in cleaned if r["year_confidence"])
    has_year = sum(1 for r in cleaned if r["year"])
    has_place = sum(1 for r in cleaned if r["country"])
    has_state = sum(1 for r in cleaned if r["state"])
    print(f"Have a usable year: {has_year}")
    print(f"  of which high confidence:   {conf_counts.get('high', 0)}")
    print(f"  of which medium confidence: {conf_counts.get('medium', 0)}")
    print(f"  of which low confidence:    {conf_counts.get('low', 0)}")
    print(f"Have a country: {has_place}")
    print(f"Have a state: {has_state}")

    type_counts = Counter(r["object_type"] for r in cleaned)
    print("\nTop object types:")
    for t, n in type_counts.most_common(10):
        print(f"  {n:3d}  {t}")

    with open("mv_final.json", "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    with open("mv_final.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "registrationNumber", "title", "object_type",
                    "classifications", "year", "year_confidence", "decade",
                    "locality", "state", "country", "thumbnail",
                    "thumbnail_licence"])
        for r in cleaned:
            w.writerow([
                r["id"], r["registrationNumber"], r["title"],
                r["object_type"], r["classifications"], r["year"],
                r["year_confidence"], r["decade"], r["locality"],
                r["state"], r["country"],
                r["thumbnail"], r["thumbnail_licence"],
            ])
    print("\nSaved mv_final.json and mv_final.csv")


if __name__ == "__main__":
    main()