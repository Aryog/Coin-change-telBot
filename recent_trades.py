import requests

# Define the GraphQL endpoint
url = "https://graphql.focus.xyz/graphql"

# GraphQL query
query = """
query TradingRecentTrades($first: Int, $orderBy: [TradingRecentTradesOrderBy!], $filter: TradingRecentTradeFilter, $offset: Int) {
  tradingRecentTrades(first: $first, orderBy: $orderBy, filter: $filter, offset: $offset) {
    nodes {
      denominatedCoinPublicKey
      tradeTimestamp
      tradeType
      traderPublicKey
      traderUsername
      traderDisplayName
      traderProfilePicUrl
      tokenPublicKey
      tokenUsername
      tokenProfilePicUrl
      tokenCategory
      tradeValueUsd
      tradeValueFocus
      tradeValueDeso
      tradePriceUsd
      tradePriceFocus
      tradePriceDeso
      tokenMarketCapUsd
      tokenMarketCapFocus
      txnHashHex
      tradeBuyCoinPublicKey
      tradeSellCoinPublicKey
      tradeBuyQuantity
      tradeSellQuantity
      __typename
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
      __typename
    }
    totalCount
    __typename
  }
}
"""

# GraphQL variables
variables = {
  "first": 5,
  "orderBy": ["TRADE_TIMESTAMP_DESC"],
  "filter": {
    "isMatchedOrder": { "equalTo": False },
    "tradeValueUsd": {"greaterThanOrEqualTo": 10000},
    "tokenPublicKey": { "equalTo": "BC1YLbnP7rndL92x7DbLp6bkUpCgKmgoHgz7xEbwhgHTps3ZrXA6LtQ" }
  },
  "offset": 0
}

# Request payload
payload = {
    "query": query,
    "variables": variables
}

# Headers
headers = {
    "Content-Type": "application/json"
}

# Make the POST request
response = requests.post(url, json=payload, headers=headers)

# Check if request was successful
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {response.status_code}, {response.text}")

# Data is like below so give upto 5 data like this as response
# {'data': {'tradingRecentTrades': {'nodes': [{'denominatedCoinPublicKey': 'BC1YLiwTN3DbkU8VmD7F7wXcRR1tFX6jDEkLyruHD2WsH3URomimxLX', 'tradeTimestamp': '2025-02-12T03:21:40.610084', 'tradeType': 'BUY', 'traderPublicKey': 'BC1YLg5xgL7PAToY7dNrxqRmtAarJvBBZKJTkreuv2eLvCppf58Pwn9', 'traderUsername': 'Doodles', 'traderDisplayName': 'Doodles', 'traderProfilePicUrl': '', 'tokenPublicKey': 'BC1YLbnP7rndL92x7DbLp6bkUpCgKmgoHgz7xEbwhgHTps3ZrXA6LtQ', 'tokenUsername': 'DESO', 'tokenProfilePicUrl': 'https://node.deso.org/assets/deso/coin-deso.png', 'tokenCategory': '', 'tradeValueUsd': 26247.97656737173, 'tradeValueFocus': 36304807.63520846, 'tradeValueDeso': 2235.7731318033843, 'tradePriceUsd': 11.649012820480072, 'tradePriceFocus': 16112.296066026, 'tradePriceDeso': 0.9922498143509431, 'tokenMarketCapUsd': 131350325.08959344, 'tokenMarketCapFocus': 181676796036.44513, 'txnHashHex': '0391e212f692cd8ba12898ddded56d36db9f689fc822bbca9526cd97c6bc99d9', 'tradeBuyCoinPublicKey': 'BC1YLbnP7rndL92x7DbLp6bkUpCgKmgoHgz7xEbwhgHTps3ZrXA6LtQ', 'tradeSellCoinPublicKey': 'BC1YLiwTN3DbkU8VmD7F7wXcRR1tFX6jDEkLyruHD2WsH3URomimxLX', 'tradeBuyQuantity': 2253.236130123, 'tradeSellQuantity': 26254.407383374553, '__typename': 'TradingRecentTrade'}], 'pageInfo': {'hasNextPage': True, 'hasPreviousPage': False, 'startCursor': 'WyJ0cmFkZV90aW1lc3RhbXBfZGVzYyIsMV0=', 'endCursor': 'WyJ0cmFkZV90aW1lc3RhbXBfZGVzYyIsMV0=', '__typename': 'PageInfo'}, 'totalCount': 335, '__typename': 'TradingRecentTradesConnection'}}}
