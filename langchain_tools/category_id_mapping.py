#!/usr/bin/env python3
"""
Functions to map between ticker symbols and UUIDs for category IDs.
"""

# Ticker to UUID mapping (ticker → uuid)
TICKER_TO_UUID = {
    "AMZN": "AMZN",
    "AAPL": "AAPL",
    "INTC": "INTC",
    "MU": "MU",
    "GOOGL": "989b35ce-b8fd-44dc-b53f-2d3233a85706",
    "MSFT": "5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18",
    "AMD": "1598ce28-8bb0-4787-ad40-f5227d3a72a6",
    "ASML": "077deca3-7e7e-4c48-b848-6f8cfcf84b5c",
    "NVDA": "5602d908-a5c5-43c1-b888-975dff32a2c4",
    "CSCO": "f39dc51b-689e-424d-af9b-0ba2d2c0bb86"
}

# UUID to ticker mapping (uuid → ticker)
UUID_TO_TICKER = {
    "AMZN": "AMZN",
    "AAPL": "AAPL",
    "INTC": "INTC",
    "MU": "MU",
    "989b35ce-b8fd-44dc-b53f-2d3233a85706": "GOOGL",
    "5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18": "MSFT",
    "1598ce28-8bb0-4787-ad40-f5227d3a72a6": "AMD",
    "077deca3-7e7e-4c48-b848-6f8cfcf84b5c": "ASML",
    "5602d908-a5c5-43c1-b888-975dff32a2c4": "NVDA",
    "f39dc51b-689e-424d-af9b-0ba2d2c0bb86": "CSCO"
}

def get_uuid_for_ticker(ticker):
    """Get the UUID for a given ticker symbol."""
    if not ticker:
        return None
    return TICKER_TO_UUID.get(ticker)

def get_ticker_for_uuid(uuid_str):
    """Get the ticker symbol for a given UUID."""
    if not uuid_str:
        return None
    return UUID_TO_TICKER.get(uuid_str)

def normalize_category_id(category_id):
    """
    Normalize a category ID to ensure we return the ticker if available, otherwise the UUID.
    This helps resolve inconsistencies between ticker and UUID formats.
    """
    if not category_id:
        return None
        
    # If it's a ticker already, return it
    if category_id in TICKER_TO_UUID:
        return category_id
        
    # If it's a UUID, convert to ticker if possible
    ticker = UUID_TO_TICKER.get(category_id)
    if ticker:
        return ticker
        
    # Otherwise just return what we got
    return category_id
    
# Example usage
if __name__ == "__main__":
    # Test with known values
    for ticker in TICKER_TO_UUID.keys():
        uuid_str = get_uuid_for_ticker(ticker)
        print(f"Ticker {ticker} → UUID {uuid_str}")
        
        # Convert back
        ticker_back = get_ticker_for_uuid(uuid_str)
        print(f"UUID {uuid_str} → Ticker {ticker_back}")
        print() 