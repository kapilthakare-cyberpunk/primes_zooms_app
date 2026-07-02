
import pandas as pd

def load_inventory(file_path):
    """Loads the CSV inventory file into a pandas DataFrame."""
    try:
        df = pd.read_csv(file_path)
        # Clean column names by stripping whitespace and replacing spaces with underscores
        df.columns = df.columns.str.strip().str.replace(' ', '_')
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
        return pd.DataFrame()
    query_lower = query.lower()
    # Search in Item_Name, Type, Res_Type, Res_Grp, SKU
    results = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(query_lower, na=False).any(), axis=1)]
    return results.to_dict(orient='records')
