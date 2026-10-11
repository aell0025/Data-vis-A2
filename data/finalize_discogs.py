"""
Clean and finalize the Discogs pull for charting.

Run from the folder containing discogs_releases.csv:
  python finalize_discogs.py

Output: discogs_final.json and discogs_final.csv
"""
import csv
import json

SRC = "discogs_releases.csv"

# Tiers reflect genuine collector value, not lumped together.
# "reissue" alone is common and only mildly collectible; the others
# indicate a release made to be scarce/special on purpose.
TIER_HIGH = {"numbered", "limited edition", "picture disc", "box set",
             "test pressing", "promo"}
TIER_MID = {"deluxe", "coloured", "colored"}
TIER_LOW = {"reissue", "repress"}


def tier_for(descriptions):
    descs = set(d.strip().lower() for d in descriptions)
    if descs & TIER_HIGH:
        return "high"
    if descs & TIER_MID:
        return "mid"
    if descs & TIER_LOW:
        return "low"
    return "none"


def decade_for(year):
    if not year or year == 0:
        return None
    return (year // 10) * 10


def main():
    with open(SRC, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows")

    cleaned = []
    dropped_year = 0
    dropped_digital = 0
    for r in rows:
        # Physical copies only: skip digital-only releases (Discogs format "File")
        if [f.strip() for f in r["formats"].split(";")] == ["File"]:
            dropped_digital += 1
            continue
        year = int(r["year"]) if r["year"].isdigit() else 0
        if year == 0:
            dropped_year += 1
            continue
        descs = [d.strip() for d in r["format_descriptions"].split(";") if d.strip()]
        cleaned.append({
            "id": r["id"],
            "title": r["title"],
            "artist": r["searched_artist"],
            "year": year,
            "decade": decade_for(year),
            "country": r["country"] or "Unknown",
            "genre": r["genres"],
            "styles": [s.strip() for s in r["styles"].split(";") if s.strip()],
            "formats": [f.strip() for f in r["formats"].split(";") if f.strip()],
            "format_descriptions": descs,
            "collectible_tier": tier_for(descs),
            "have": int(r["have"]) if r["have"].isdigit() else None,
            "want": int(r["want"]) if r["want"].isdigit() else None,
        })

    print(f"Dropped {dropped_digital} digital-only (File) rows")
    print(f"Dropped {dropped_year} rows with year=0")
    print(f"Final rows: {len(cleaned)}")

    from collections import Counter
    tier_counts = Counter(r["collectible_tier"] for r in cleaned)
    print("\nCollectible tier breakdown:")
    for t, n in tier_counts.most_common():
        print(f"  {t}: {n}")

    with open("discogs_final.json", "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    with open("discogs_final.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "artist", "year", "decade", "country",
                    "genre", "styles", "formats", "format_descriptions",
                    "collectible_tier", "have", "want"])
        for r in cleaned:
            w.writerow([
                r["id"], r["title"], r["artist"], r["year"], r["decade"],
                r["country"], r["genre"], "; ".join(r["styles"]),
                "; ".join(r["formats"]), "; ".join(r["format_descriptions"]),
                r["collectible_tier"], r["have"], r["want"],
            ])
    print("\nSaved discogs_final.json and discogs_final.csv")


if __name__ == "__main__":
    main()