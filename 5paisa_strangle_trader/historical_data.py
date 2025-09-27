import requests
import config
import json
from datetime import datetime

def fetch_historical_data(exch, exch_type, scrip_code, interval, from_date, to_date):
    """
    Fetches historical candle data from the 5paisa API.

    :param exch: Exchange (e.g., 'N' for NSE).
    :param exch_type: Exchange type (e.g., 'C' for Cash).
    :param scrip_code: Scrip code of the instrument.
    :param interval: Candle interval (e.g., '1m', '5m', '1d').
    :param from_date: Start date in 'YYYY-MM-DD' format.
    :param to_date: End date in 'YYYY-MM-DD' format.
    :return: A list of candles or None if an error occurs.
    """
    base_url = "https://openapi.5paisa.com/V2/historical"
    url = f"{base_url}/{exch}/{exch_type}/{scrip_code}/{interval}?from={from_date}&end={to_date}"

    headers = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = response.json()

        if data.get("status") == "success" and "data" in data and "candles" in data["data"]:
            return data["data"]["candles"]
        else:
            # Correctly parse the error message from the API's failure response structure
            if "head" in data and "Status_description" in data.get("head", {}):
                error_message = data["head"]["Status_description"]
            else:
                error_message = data.get("message", "Unknown API error.")
            print(f"Error fetching data: {error_message}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the request: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON from response.")
        return None

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch historical candle data from 5paisa API.")
    parser.add_argument("--exch", type=str, required=True, help="Exchange (e.g., N, B, M).")
    parser.add_argument("--exch_type", type=str, required=True, help="Exchange type (e.g., C, D, U).")
    parser.add_argument("--scrip_code", type=str, required=True, help="Scrip code of the instrument.")
    parser.add_argument("--interval", type=str, required=True, help="Candle interval (e.g., 1m, 5m, 1d).")
    parser.add_argument("--from_date", type=str, required=True, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to_date", type=str, required=True, help="End date in YYYY-MM-DD format.")

    args = parser.parse_args()

    if config.ACCESS_TOKEN == "YOUR_ACCESS_TOKEN" or not config.ACCESS_TOKEN:
        print("Error: Access token not found in config.py.")
        print("Please run authenticate.py or authenticate_browser.py to generate an access token.")
    else:
        print(f"Fetching historical data for scrip {args.scrip_code} from {args.from_date} to {args.to_date} with {args.interval} interval...")
        candles = fetch_historical_data(
            args.exch,
            args.exch_type,
            args.scrip_code,
            args.interval,
            args.from_date,
            args.to_date
        )

        if candles:
            print("Successfully fetched data. Displaying first 5 and last 5 candles:")
            # To avoid flooding the console, print only a subset of the data
            display_candles = candles[:5] + candles[-5:] if len(candles) > 10 else candles

            # Print header
            print("-" * 80)
            print(f"{'Timestamp':<22} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'Volume':>12}")
            print("-" * 80)

            for candle in display_candles:
                # Assuming candle format is [Timestamp, Open, High, Low, Close, Volume]
                ts, o, h, l, c, v = candle
                print(f"{ts:<22} {o:>10.2f} {h:>10.2f} {l:>10.2f} {c:>10.2f} {v:>12}")

            if len(candles) > 10:
                print("...")
                print(f"(Total {len(candles)} candles fetched)")

        else:
            print("Failed to fetch historical data.")