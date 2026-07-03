
import pandas as pd

def load_inventory(file_path):
    """Loads the CSV inventory file into a pandas DataFrame."""
    try:
        df = pd.read_csv(file_path, skiprows=3, quoting=1)  # skip 3 blank lines, handle quoted fields
        # Clean column names by stripping whitespace and replacing spaces with underscores
        df.columns = df.columns.str.strip().str.replace(' ', '_')
        # Drop fully empty rows
        df = df.dropna(how='all')
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

def get_item_details(df, item_id=None, sku=None, item_name=None):
    """Retrieves details for a specific item based on ID, SKU, or name."""
    if df is None:
        return None
    if item_id:
        return df[df['Item_ID'] == item_id].to_dict(orient='records')
    elif sku:
        return df[df['SKU'] == sku].to_dict(orient='records')
    elif item_name:
        return df[df['Item_Name'].str.contains(item_name, case=False, na=False)].to_dict(orient='records')
    return None

def search_items(df, query):
    """Searches for items in the inventory based on a query string across relevant columns."""
    if df is None:
        return []

    # Extract meaningful keywords from query, removing common stopwords
    stopwords = {'what', 'is', 'the', 'rent', 'for', 'a', 'an', 'of', 'and', 'or', 'how',
                 'much', 'does', 'cost', 'price', 'rate', 'per', 'day', 'days', 'available',
                 'do', 'you', 'have', 'can', 'i', 'get', 'need', 'want', 'looking', 'tell',
                 'about', 'me', 'show', 'list', 'all', 'some', 'any', 'my', 'your', 'our',
                 'their', 'this', 'that', 'it', 'to', 'in', 'on', 'at', 'with', 'from'}
    words = query.lower().replace('?', '').replace(',', '').split()
    keywords = [w for w in words if w not in stopwords and len(w) > 1]

    if not keywords:
        return []

    # Try searching with the most specific keyword组合 first (2+ words), then fallback
    # Build search patterns: try multi-word brand+model combos first
    search_terms = []
    # Try bigrams first (more specific)
    for i in range(len(keywords) - 1):
        search_terms.append(f"{keywords[i]} {keywords[i+1]}")
    # Then individual keywords
    search_terms.extend(keywords)

    matched_indices = set()
    for term in search_terms:
        results = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(term, na=False).any(), axis=1)]
        matched_indices.update(results.index)
        if matched_indices:
            break  # Found matches, stop searching

    if not matched_indices:
        return []

    return df.loc[list(matched_indices)].to_dict(orient='records')
