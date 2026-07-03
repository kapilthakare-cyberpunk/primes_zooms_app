# Primes & Zooms AI Assistant

This is a local web application designed for Primes & Zooms, a photo and cine gear rental service. It provides two main AI-powered modes: **Rental Consultant** and **Pricing Assistant**, to help manage inventory and assist with customer inquiries and pricing strategies.

## Features

- **CSV Inventory Loading**: Easily upload your gear inventory via a CSV file.
- **Groq API Integration**: Utilizes the Groq API for fast and efficient LLM responses.
- **DuckDuckGo Search Integration**: Provides real-time web search capabilities for product information.
- **Rental Consultant Mode**: Assists users with product information, alternative suggestions, and related item recommendations based on inventory and web data.
- **Pricing Assistant Mode**: Helps analyze current pricing structures and suggests optimal rental pricing for new or existing products.
- **Pricing Band Generator**: CLI and Streamlit tool to generate rental pricing bands for new inventory additions with review layer and OEM market price comparison.
- **Clean User Interface**: Built with Streamlit for an intuitive and professional local web experience.

## Pricing Band Generator

### Overview

The pricing band generator creates rental pricing bands for new inventory items. It uses a **3-layer approach**:

1. **Pattern Learning** — Analyzes the existing pricelist (1300+ items) to learn:
   - Per-day rate as a percentage of MRP by category (Type + Res_Grp)
   - Discount curves across rental slabs (2d, 5d, 9d relative to 1d)

2. **OEM Market Research** — Searches DuckDuckGo for current India MRP from manufacturer websites (canon.co.in, sony.co.in, etc.) and compares with your purchase cost.

3. **Review Layer** — Validates the generated bands against pricelist benchmarks:
   - Checks if 1-day rate is within ±25% of category average
   - Flags MRP outliers above/below category range
   - Detects discount curve deviations
   - Identifies low-MRP items where rate floors may apply
   - Outputs verdict: `OK` or `CAUTION` with specific flags

### Output Format

```csv
Sr No,SKU,Item Name,Date,Pricing Band,OEM Price,Remarks
1,CR6V,Canon EOS R6 V,2026-07-03,1d-1950,2d-1750,5d-1600,9d-1500,N/A,"Pattern source: learned from 40 items in Body|Full Frame; Verdict: OK"
```

**Pricing Band format:** `1d-{total},2d-{total},5d-{total},9d-{total}` where each value is the **total rental cost** for that duration (not per-day).

### CLI Usage

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Single item
python3 cli.py --sku "CR6V" --name "Canon EOS R6 V" --mrp 208000 --brand Canon --type Body --category "Full Frame"

# Bulk from CSV
python3 cli.py --bulk new_items.csv

# Interactive mode
python3 cli.py --interactive

# Dry run (preview only)
python3 cli.py --sku "CR6V" --name "Canon EOS R6 V" --mrp 208000 --dry-run

# Skip OEM web search (faster)
python3 cli.py --sku "CR6V" --name "Canon EOS R6 V" --mrp 208000 --skip-oem

# Skip GitHub push
python3 cli.py --sku "CR6V" --name "Canon EOS R6 V" --mrp 208000 --no-push
```

**Bulk CSV input format:**
```csv
sku,name,brand,mrp,type,category
CR6V,Canon EOS R6 V,Canon,208000,Body,Full Frame
SA7M5,Sony A7 Mark V,Sony,240000,Body,Full Frame
```

### Review Layer Flags

| Flag | Meaning |
|------|---------|
| `OK` | Pricing is within expected range |
| `CAUTION` | Review flagged issues — see remarks |
| `HIGH_1D` | 1-day rate >25% above category average |
| `LOW_1D` | 1-day rate >25% below category average |
| `MRP_OUTLIER_HIGH` | MRP above category range (needs premium pricing consideration) |
| `MRP_OUTLIER_LOW` | MRP below category range |
| `DISCOUNT_CURVE_OFF` | 2d/1d discount ratio deviates from category norm |
| `LOW_MRP` | Low-MRP item; rate may floor at ₹50-100 minimum |
| `VIDEO_GEAR` | Video camera category; verify cinema-grade pricing |
| `NO_DATA` | No pricelist data for this category |

### Category Benchmarks (from pricelist analysis)

| Type | Items | MRP Range | Avg 1d/MRP Ratio |
|------|-------|-----------|-----------------|
| Body | 137 | ₹16,500–₹600,000 | 0.99% |
| Lens | 437 | ₹5,000–₹1,500,000 | 1.20% |
| Lights | 87 | ₹300–₹250,000 | 3.03% |
| Binoculars | 6 | ₹3,500–₹50,000 | 3.15% |
| Books | 19 | ₹400–₹9,500 | 5.85% |
| Mobile Phone | 8 | ₹52,000–₹178,100 | 0.88% |
| Battery Charger | 5 | ₹1,800–₹4,500 | 4.98% |

## Requirements

- Python 3.7+
- `pip` (Python package installer)

## Setup and Installation

1.  **Clone the repository (or download the files):**

    ```bash
    git clone https://github.com/kapilthakare-cyberpunk/primes_zooms_app.git
    cd primes_zooms_app
    ```

2.  **Install dependencies:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Usage

1.  **Start the Streamlit application:**

    ```bash
    ./start.sh
    ```

2.  **Enter Groq API Key:**

    In the sidebar of the application, enter your Groq API Key.

3.  **Use the Pricing Band Calculator:**

    The Streamlit app has a "New Item Pricing Band Calculator" section where you can enter item details and generate bands interactively.

4.  **AI Modes:**

    -   **Rental Consultant**: Ask questions about specific items, their uses, or seek recommendations.
    -   **Pricing Assistant**: Provide an item name (and optionally category or current MRP) to get pricing suggestions.

## Project Structure

```
primes_zooms_app/
├── app.py                  # Main Streamlit application with pricing band UI
├── csv_processor.py        # Handles CSV inventory loading and searching
├── ai_agents.py            # AI agent logic for Rental Consultant and Pricing Assistant
├── pricing_engine.py       # Pricing band generation, pattern analysis, review layer, OEM search
├── cli.py                  # CLI tool for batch pricing band generation
├── telegram_bot.py         # Telegram bot for inventory queries
├── push_to_github.sh       # Auto-commit and push pricing bands to GitHub
├── requirements.txt        # Python dependencies
├── start.sh                # Start Streamlit app
├── start_telegram.sh       # Start Telegram bot
├── Pricelist_20260703.csv  # Current inventory pricelist
├── pricing_bands.csv       # Generated pricing bands output
└── README.md               # This file
```

## Troubleshooting

-   If the application doesn't start, ensure all dependencies are installed (`pip install -r requirements.txt`).
-   Check your Groq API key if AI responses are not working.
-   Verify your CSV file format if inventory loading fails.
-   For CLI, if OEM search is slow, use `--skip-oem` flag.

---

**Primes & Zooms**
*Your trusted partner for photo and cine gear rentals in Pune.*
