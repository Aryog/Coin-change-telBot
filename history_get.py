import requests
import time

def get_current_price():
    # Define the base URL
    url = "https://focus.xyz/api/v0/tokens/candlesticks/history"

    # Get the current Unix timestamp in milliseconds
    current_time = int(time.time() * 1000)

    # Define query parameters
    params = {
        "symbol": "BC1YLbnP7rndL92x7DbLp6bkUpCgKmgoHgz7xEbwhgHTps3ZrXA6LtQ",
        "to": current_time,
        "resolution": "15M",
        "countback": 1,
        "quoteSymbol": "BC1YLiwTN3DbkU8VmD7F7wXcRR1tFX6jDEkLyruHD2WsH3URomimxLX"
    }

    # Make the GET request
    response = requests.get(url, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        # Assuming the data is a list of dictionaries
        print(data)
        return data
    else:
        return None

# Output is like this below for (data)
# {'timestamp': '2025-02-12 15:00:00', 'time': '1739372400000', 'open': 11.757702800623075, 'close': 11.757702800623075, 'high': 11.757702800623075, 'low': 11.757702800623075, 'volume': 0}