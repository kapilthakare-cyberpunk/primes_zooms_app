#!/usr/bin/env python3
"""
CLI tool for generating pricing bands for new inventory items.

Usage:
    # Single item
    python cli.py --sku "C2470F28RF" --name "Canon RF 24-70mm f/2.8L IS USM" --mrp 165000 --brand Canon

    # Bulk from CSV file
    python cli.py --bulk items.csv

    # Interactive mode
    python cli.py --interactive

    # Dry run (preview without saving)
    python cli.py --sku "..." --name "..." --mrp 165000 --dry-run

    # Skip GitHub push
    python cli.py --sku "..." --name "..." --mrp 165000 --no-push

    # Skip slow OEM web search
    python cli.py --sku "..." --name "..." --mrp 165000 --skip-oem
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pricing_engine import (
    generate_pricing_band,
    save_to_csv,
    push_to_github,
    analyze_patterns,
)

PRICELIST = os.path.join(os.path.dirname(__file__), "Pricelist_20260703.csv")


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         Primes & Zooms - Pricing Band Generator              ║
║         with Review Layer + OEM Market Price                 ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_result(result):
    """Pretty print a pricing band result with review + OEM."""
    oem_str = f"₹{result['oem_price']:,}" if result.get("oem_price") else "N/A"
    print(f"\n{'─' * 70}")
    print(f"  SKU:          {result['sku']}")
    print(f"  Item:         {result['item_name']}")
    print(f"  Brand:        {result['brand'] or 'N/A'}")
    print(f"  MRP:          ₹{result['mrp']:,}")
    print(f"  Category:     {result['item_type']} / {result['res_grp']}")
    print(f"  Date:         {result['date']}")
    print(f"{'─' * 70}")
    print(f"  ✓ Pricing Band:  {result['bands_str']}")
    print(f"  ◆ OEM Market:    {oem_str}")
    print(f"  ● Verdict:       {result['review_verdict']}")
    print(f"{'─' * 70}")
    print(f"  Remarks:")
    for line in result["review_remarks"].split("; "):
        print(f"    • {line.strip()}")
    print(f"{'─' * 70}")


def interactive_mode(no_push=False, skip_oem=False):
    """Interactive mode for adding items one by one."""
    print("\n  Interactive Mode - Enter item details (type 'quit' to exit)\n")

    results = []

    while True:
        print(f"\n{'━' * 70}")
        sku = input("  SKU (or 'quit'): ").strip()
        if sku.lower() in ("quit", "q", "exit"):
            break

        name = input("  Item Name: ").strip()
        if not name:
            print("  ✗ Item name is required")
            continue

        brand = input("  Brand (Canon/Sony/Nikon/Fujifilm/etc): ").strip() or None

        mrp_str = input("  Purchase Cost / MRP (₹): ").strip()
        mrp = int(mrp_str) if mrp_str.isdigit() else None

        item_type = input("  Type (Lens/Body/Accessory) [Lens]: ").strip() or "Lens"
        res_grp = (
            input("  Category (Mid Range/Tele/Wide Angle/etc) [Mid Range]: ").strip()
            or "Mid Range"
        )

        print("  Generating pricing band with review...")
        result, error = generate_pricing_band(
            csv_path=PRICELIST,
            item_name=name,
            sku=sku,
            mrp=mrp,
            brand=brand,
            item_type=item_type,
            res_grp=res_grp,
            skip_oem=skip_oem,
        )

        if error:
            print(f"\n  ✗ Error: {error}")
            continue

        print_result(result)
        results.append(result)

        save = input("\n  Save this result? (y/n) [y]: ").strip().lower()
        if save != "n":
            print("  ✓ Saved to memory")

    if results:
        confirm = (
            input(f"\n  Save {len(results)} items to CSV? (y/n) [y]: ").strip().lower()
        )
        if confirm != "n":
            csv_path = save_to_csv(results)
            print(f"  ✓ Saved to {csv_path}")

            if not no_push:
                push = input("  Push to GitHub? (y/n) [y]: ").strip().lower()
                if push != "n":
                    success, msg = push_to_github()
                    print(f"  {'✓' if success else '✗'} {msg}")


def bulk_mode(csv_file, no_push=False, skip_oem=False):
    """Process multiple items from a CSV file."""
    if not os.path.exists(csv_file):
        print(f"  ✗ File not found: {csv_file}")
        sys.exit(1)

    results = []

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku = row.get("sku", row.get("SKU", ""))
            name = row.get("name", row.get("Item Name", row.get("item_name", "")))
            brand = row.get("brand", row.get("Brand", None))
            mrp_str = row.get("mrp", row.get("MRP", row.get("cost", "")))
            mrp = int(mrp_str) if mrp_str and mrp_str.isdigit() else None
            item_type = row.get("type", row.get("Type", "Lens"))
            res_grp = row.get(
                "category", row.get("Category", row.get("Res_Grp", "Mid Range"))
            )

            if not name:
                print(f"  ⚠ Skipping row without name: {row}")
                continue

            print(f"\n  Processing: {name}...")

            result, error = generate_pricing_band(
                csv_path=PRICELIST,
                item_name=name,
                sku=sku,
                mrp=mrp,
                brand=brand,
                item_type=item_type,
                res_grp=res_grp,
                skip_oem=skip_oem,
            )

            if error:
                print(f"  ✗ {error}")
                continue

            print_result(result)
            results.append(result)

    if results:
        csv_path = save_to_csv(results)
        print(f"\n  ✓ Saved {len(results)} items to {csv_path}")

        if not no_push:
            success, msg = push_to_github()
            print(f"  {'✓' if success else '✗'} {msg}")
    else:
        print("\n  ✗ No results to save")


def single_item_mode(args):
    """Process a single item from CLI arguments."""
    result, error = generate_pricing_band(
        csv_path=PRICELIST,
        item_name=args.name,
        sku=args.sku,
        mrp=args.mrp,
        brand=args.brand,
        item_type=args.type,
        res_grp=args.category,
        skip_oem=args.skip_oem,
    )

    if error:
        print(f"\n  ✗ Error: {error}")
        sys.exit(1)

    print_result(result)

    if not args.dry_run:
        csv_path = save_to_csv([result])
        print(f"\n  ✓ Saved to {csv_path}")

        if not args.no_push:
            success, msg = push_to_github()
            print(f"  {'✓' if success else '✗'} {msg}")
    else:
        print("\n  ℹ Dry run - not saved")


def main():
    parser = argparse.ArgumentParser(
        description="Primes & Zooms - Pricing Band Generator with Review + OEM Price",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --sku "CR6V" --name "Canon EOS R6 V" --mrp 208000 --brand Canon --type Body --category "Full Frame"
  %(prog)s --bulk items.csv
  %(prog)s --interactive
  %(prog)s --sku "CR6V" --name "Canon EOS R6 V" --mrp 208000 --dry-run --skip-oem
        """,
    )

    parser.add_argument("--sku", help="Item SKU")
    parser.add_argument("--name", help="Item name")
    parser.add_argument("--mrp", type=int, help="Purchase cost / MRP in ₹")
    parser.add_argument("--brand", help="Brand name (Canon, Sony, Nikon, etc.)")
    parser.add_argument(
        "--type", default="Lens", help="Item type (Lens/Body/Accessory) [default: Lens]"
    )
    parser.add_argument(
        "--category",
        default="Mid Range",
        help="Category (Mid Range/Tele/Wide Angle/etc) [default: Mid Range]",
    )

    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    parser.add_argument(
        "--bulk", metavar="CSV_FILE", help="Process items from CSV file"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--no-push", action="store_true", help="Skip GitHub push")
    parser.add_argument(
        "--skip-oem", action="store_true", help="Skip OEM web search (faster)"
    )

    args = parser.parse_args()

    print_banner()

    if args.interactive:
        interactive_mode(args.no_push, args.skip_oem)
    elif args.bulk:
        bulk_mode(args.bulk, args.no_push, args.skip_oem)
    elif args.name:
        single_item_mode(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
