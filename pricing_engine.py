import csv
import re
import os
import subprocess
from datetime import datetime
from collections import defaultdict
from duckduckgo_search import DDGS


# ---------------------------------------------------------------------------
# OEM PRICE LOOKUP (web search for current India MRP)
# ---------------------------------------------------------------------------

_BRAND_DOMAINS = {
    "Canon": "site:canon.co.in",
    "Sony": "site:sony.co.in",
    "Nikon": "site:nikon.co.in",
    "Fujifilm": "site:fujifilm-x.com OR site:fujifilm-x.com/in",
    "Panasonic": "site:panasonic.co.in",
    "Sigma": "site:sigmaphoto.com",
    "Tamron": "site:tamron.co.in",
    "Zeiss": "site:zeiss.co.in OR site:zeiss.com/consumer-products",
    "Nothing": "site:nothing.tech",
    "Blackmagic": "site:blackmagicdesign.com",
}

_PRICE_RE = [
    re.compile(r"₹\s*([0-9,]+)"),
    re.compile(r"Rs\.?\s*([0-9,]+)"),
    re.compile(r"INR\s*([0-9,]+)"),
    re.compile(r"MRP[:\s]*₹?\s*([0-9,]+)"),
    re.compile(r"price[:\s]*₹?\s*([0-9,]+)"),
]


def search_oem_price(item_name, brand=None, max_results=5):
    """
    Search DuckDuckGo for current India MRP of the item.
    Returns (price_int | None, source_url | None).
    """
    try:
        site_filter = _BRAND_DOMAINS.get(brand, "") if brand else ""
        query = f"{item_name} price India MRP {site_filter}".strip()

        ddgs = DDGS()
        results = ddgs.text(keywords=query, max_results=max_results)

        prices = []
        best_url = None
        for r in results:
            text = f"{r.get('title', '')} {r.get('snippet', '')}"
            for pat in _PRICE_RE:
                for m in pat.finditer(text):
                    try:
                        price = int(m.group(1).replace(",", ""))
                        if 500 < price < 5_000_000:
                            prices.append(price)
                            if not best_url:
                                best_url = r.get("href", "")
                    except ValueError:
                        pass

        if prices:
            prices.sort()
            return prices[len(prices) // 2], best_url  # median
        return None, None

    except Exception as e:
        print(f"  [OEM search error: {e}]")
        return None, None


# ---------------------------------------------------------------------------
# 1. PRICELIST LOADING (handles 3-blank-line header + QUOTE_ALL)
# ---------------------------------------------------------------------------


def _load_raw(csv_path):
    """Load CSV skipping blank header lines, returns list of dicts."""
    with open(csv_path, "r") as f:
        lines = f.readlines()

    # Find header row (starts with "Sr No")
    header_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('"Sr No"'):
            header_idx = i
            break

    reader = csv.DictReader(lines[header_idx:], quoting=csv.QUOTE_ALL)
    rows = []
    for row in reader:
        try:
            d1 = float(row.get("1 Day", "0").strip() or "0")
            d24 = float(row.get("2-4 Days", "0").strip() or "0")
            d58 = float(row.get("5-8 Days", "0").strip() or "0")
            d9 = float(row.get("9+ Days", "0").strip() or "0")
            mrp = float(row.get("MRP", "0").strip() or "0")
            rows.append(
                {
                    "type": row.get("Type", ""),
                    "res_type": row.get("Res Type", ""),
                    "grp": row.get("Res Grp", ""),
                    "sku": row.get("SKU", ""),
                    "name": row.get("Item Name", ""),
                    "d1": d1,
                    "d24": d24,
                    "d58": d58,
                    "d9": d9,
                    "mrp": mrp,
                    "status": row.get("Status", ""),
                }
            )
        except Exception:
            pass
    return rows


# ---------------------------------------------------------------------------
# 2. DEEP PATTERN ANALYSIS (used by both generation and review)
# ---------------------------------------------------------------------------


def analyze_patterns(csv_path):
    """Build per-category benchmarks from pricelist. Returns (by_type, by_key)."""
    rows = _load_raw(csv_path)

    by_type = defaultdict(list)  # Type -> [items]
    by_key = defaultdict(list)  # Type|Res_Grp -> [items]

    for r in rows:
        if r["d1"] > 0 and r["mrp"] > 0:
            entry = {
                "mrp": r["mrp"],
                "d1": r["d1"],
                "d24": r["d24"],
                "d58": r["d58"],
                "d9": r["d9"],
                "ratio": r["d1"] / r["mrp"],
                "disc_2d": r["d24"] / r["d1"],
                "disc_5d": r["d58"] / r["d1"],
                "disc_9d": r["d9"] / r["d1"],
                "type": r["type"],
                "grp": r["grp"],
            }
            by_type[r["type"]].append(entry)
            key = f"{r['type']}|{r['grp']}"
            by_key[key].append(entry)

    return rows, by_type, by_key


def _benchmarks(items):
    """Compute avg, p25, p75 for a list of item dicts."""
    if not items:
        return None
    ratios = sorted([i["ratio"] for i in items])
    d2 = sorted([i["disc_2d"] for i in items])
    d5 = sorted([i["disc_5d"] for i in items])
    d9 = sorted([i["disc_9d"] for i in items])
    mrps = [i["mrp"] for i in items]
    n = len(ratios)
    return {
        "count": n,
        "mrp_min": min(mrps),
        "mrp_max": max(mrps),
        "mrp_avg": sum(mrps) / n,
        "ratio_avg": sum(ratios) / n,
        "ratio_p25": ratios[n // 4],
        "ratio_p75": ratios[3 * n // 4],
        "disc2_avg": sum(d2) / n,
        "disc5_avg": sum(d5) / n,
        "disc9_avg": sum(d9) / n,
    }


# ---------------------------------------------------------------------------
# 3. BAND CALCULATION
# ---------------------------------------------------------------------------


def _round50(x):
    return round(x / 50) * 50


def calculate_bands(mrp, ratio, disc2, disc5, disc9):
    return {
        "1d": _round50(mrp * ratio),
        "2d": _round50(mrp * ratio * disc2),
        "5d": _round50(mrp * ratio * disc5),
        "9d": _round50(mrp * ratio * disc9),
    }


def format_bands(bands):
    return f"1d-{bands['1d']},2d-{bands['2d']},5d-{bands['5d']},9d-{bands['9d']}"


# ---------------------------------------------------------------------------
# 4. REVIEW LAYER — validates pricing against pricelist benchmarks
# ---------------------------------------------------------------------------


def review_pricing(item_type, res_grp, mrp, bands, by_type, by_key):
    """
    Compare proposed pricing against pricelist patterns.
    Returns (verdict, remarks_list, flags).
    verdict: 'OK' | 'CAUTION' | 'ADJUSTED'
    flags: list of str (e.g. 'HIGH_1D', 'LOW_DISCOUNT')
    """
    remarks = []
    flags = []
    key = f"{item_type}|{res_grp}"

    # --- A. Category benchmark ---
    bench = _benchmarks(by_key.get(key, []))
    if not bench:
        bench = _benchmarks(by_type.get(item_type, []))
    if not bench:
        return (
            "CAUTION",
            ["No pricelist data for this category; pricing is best-effort"],
            ["NO_DATA"],
        )

    ratio = bands["1d"] / mrp if mrp else 0

    # Check 1-day rate vs category average
    if ratio > bench["ratio_avg"] * 1.25:
        flags.append("HIGH_1D")
        remarks.append(
            f"1d rate ₹{bands['1d']} is >25% above category avg "
            f"(avg ratio {bench['ratio_avg']:.4f} → ₹{mrp * bench['ratio_avg']:,.0f})"
        )
    elif ratio < bench["ratio_avg"] * 0.75:
        flags.append("LOW_1D")
        remarks.append(
            f"1d rate ₹{bands['1d']} is >25% below category avg "
            f"(avg ratio {bench['ratio_avg']:.4f} → ₹{mrp * bench['ratio_avg']:,.0f})"
        )
    else:
        remarks.append(
            f"1d rate aligns with category avg (ratio {ratio:.4f} vs avg {bench['ratio_avg']:.4f})"
        )

    # --- B. MRP range check ---
    if mrp > bench["mrp_max"] * 1.5:
        flags.append("MRP_OUTLIER_HIGH")
        remarks.append(
            f"MRP ₹{mrp:,.0f} is above category range "
            f"(₹{bench['mrp_min']:,.0f}–₹{bench['mrp_max']:,.0f}); "
            f"consider if high-value items need premium pricing"
        )
    elif mrp < bench["mrp_min"] * 0.5:
        flags.append("MRP_OUTLIER_LOW")
        remarks.append(
            f"MRP ₹{mrp:,.0f} is below category range "
            f"(₹{bench['mrp_min']:,.0f}–₹{bench['mrp_max']:,.0f})"
        )

    # --- C. Discount curve sanity ---
    disc_deviation = (
        abs(bands["2d"] / bands["1d"] - bench["disc2_avg"]) if bands["1d"] else 0
    )
    if disc_deviation > 0.15:
        flags.append("DISCOUNT_CURVE_OFF")
        remarks.append(
            f"2d/1d discount ratio {bands['2d'] / bands['1d']:.3f} deviates from "
            f"category avg {bench['disc2_avg']:.3f}"
        )

    # --- D. Edge cases: very low MRP items ---
    if mrp < 10000:
        flags.append("LOW_MRP")
        remarks.append(
            "Low-MRP item; 1d rate may floor at ₹50–100 minimum "
            "regardless of ratio calculation"
        )

    # --- E. Video/specialty equipment premium hint ---
    if item_type in ("Body",) and "Video" in (res_grp or ""):
        flags.append("VIDEO_GEAR")
        remarks.append(
            "Video camera category; verify if cinema-grade pricing premium applies"
        )

    # --- F. Final verdict ---
    if "HIGH_1D" in flags or "MRP_OUTLIER_HIGH" in flags:
        verdict = "CAUTION"
    elif "DISCOUNT_CURVE_OFF" in flags:
        verdict = "CAUTION"
    else:
        verdict = "OK"

    return verdict, remarks, flags


# ---------------------------------------------------------------------------
# 5. GENERATE PRICING (orchestrates pattern + calculation + review)
# ---------------------------------------------------------------------------


def generate_pricing_band(
    csv_path,
    item_name,
    sku,
    mrp,
    brand=None,
    item_type="Lens",
    res_grp="Mid Range",
    skip_oem=False,
):
    """
    Generate pricing band with review + OEM market price.
    Returns (result_dict, error_str).
    """
    all_rows, by_type, by_key = analyze_patterns(csv_path)

    if not mrp or mrp == 0:
        return None, "MRP must be provided (auto-lookup disabled for speed)"

    # --- OEM market price lookup ---
    oem_price = None
    oem_source = None
    if not skip_oem:
        oem_price, oem_source = search_oem_price(item_name, brand)

    # --- Band calculation ---
    key = f"{item_type}|{res_grp}"
    bench_items = by_key.get(key, by_type.get(item_type, []))
    bench = _benchmarks(bench_items) if bench_items else None

    if bench:
        ratio = bench["ratio_avg"]
        disc2 = bench["disc2_avg"]
        disc5 = bench["disc5_avg"]
        disc9 = bench["disc9_avg"]
        source = f"learned from {bench['count']} items in {key}"
    else:
        ratio = 0.01
        disc2, disc5, disc9 = 0.85, 0.75, 0.65
        source = "default fallback (no category data)"

    bands = calculate_bands(mrp, ratio, disc2, disc5, disc9)

    # --- Review ---
    verdict, remarks, flags = review_pricing(
        item_type, res_grp, mrp, bands, by_type, by_key
    )

    remarks.insert(0, f"Pattern source: {source}")

    # --- OEM price comparison ---
    oem_note = "No OEM data found"
    if oem_price:
        diff = oem_price - mrp
        pct = (diff / mrp * 100) if mrp else 0
        if abs(pct) < 5:
            oem_note = f"OEM {oem_price:,} matches your MRP (Δ{pct:+.1f}%)"
        elif pct > 0:
            oem_note = f"OEM {oem_price:,} — your MRP is {abs(pct):.1f}% below market"
        else:
            oem_note = f"OEM {oem_price:,} — your MRP is {abs(pct):.1f}% above market"
        remarks.append(oem_note)
        if oem_source:
            remarks.append(f"OEM source: {oem_source}")
    else:
        remarks.append(oem_note)

    if verdict == "OK":
        remarks.insert(1, "Verdict: Pricing is within expected range for this category")
    else:
        remarks.insert(1, f"Verdict: {verdict} — review flagged: {', '.join(flags)}")

    return {
        "sku": sku,
        "item_name": item_name,
        "mrp": mrp,
        "brand": brand,
        "item_type": item_type,
        "res_grp": res_grp,
        "bands": bands,
        "bands_str": format_bands(bands),
        "oem_price": oem_price,
        "oem_source": oem_source or "",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "review_verdict": verdict,
        "review_remarks": "; ".join(remarks),
        "review_flags": ",".join(flags) if flags else "NONE",
    }, None


# ---------------------------------------------------------------------------
# 6. SAVE / PUSH
# ---------------------------------------------------------------------------


def save_to_csv(results, csv_path="pricing_bands.csv"):
    full_path = os.path.join(os.path.dirname(__file__), csv_path)

    existing = []
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            reader = csv.DictReader(f)
            existing = list(reader)

    for r in results:
        entry = {
            "Sr No": str(len(existing) + 1),
            "SKU": r["sku"],
            "Item Name": r["item_name"],
            "Date": r["date"],
            "Pricing Band": r["bands_str"],
            "OEM Price": f"₹{r['oem_price']:,}" if r.get("oem_price") else "N/A",
            "Remarks": r.get("review_remarks", ""),
        }
        existing.append(entry)

    fieldnames = [
        "Sr No",
        "SKU",
        "Item Name",
        "Date",
        "Pricing Band",
        "OEM Price",
        "Remarks",
    ]
    with open(full_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing)

    return full_path


def push_to_github(csv_path="pricing_bands.csv"):
    full_path = os.path.join(os.path.dirname(__file__), csv_path)
    try:
        subprocess.run(["git", "add", full_path], check=True, capture_output=True)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"Update pricing bands - {date_str}"],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "push", "origin", "main"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, "Pushed to GitHub successfully"
        subprocess.run(
            ["git", "push", "-u", "origin", "main"], capture_output=True, text=True
        )
        return True, "Pushed to GitHub (set upstream)"
    except subprocess.CalledProcessError as e:
        return False, f"Git error: {e}"
    except Exception as e:
        return False, f"Error: {e}"
