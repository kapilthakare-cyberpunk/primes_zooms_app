import csv
import os
import subprocess
from datetime import datetime
from collections import defaultdict


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
# 2. DEEP PATTERN ANALYSIS
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
# 4. GENERATE PRICING (orchestrates pattern + calculation)
# ---------------------------------------------------------------------------


def generate_pricing_band(
    csv_path,
    item_name,
    sku,
    mrp,
    brand=None,
    item_type="Lens",
    res_grp="Mid Range",
):
    """
    Generate pricing band from pricelist patterns.
    Returns (result_dict, error_str).
    """
    all_rows, by_type, by_key = analyze_patterns(csv_path)

    if not mrp or mrp == 0:
        return None, "MRP must be provided"

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

    return {
        "sku": sku,
        "item_name": item_name,
        "mrp": mrp,
        "brand": brand,
        "item_type": item_type,
        "res_grp": res_grp,
        "bands": bands,
        "bands_str": format_bands(bands),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": source,
    }, None


# ---------------------------------------------------------------------------
# 5. SAVE / PUSH
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
        }
        existing.append(entry)

    fieldnames = ["Sr No", "SKU", "Item Name", "Date", "Pricing Band"]
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
