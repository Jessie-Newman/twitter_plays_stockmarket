import yfinance as yf
import json
from yfinance.scrapers.quote import InfoDictWrapper
from collections import defaultdict
import tweepy

# Tweepy access
API_KEY = ''
API_KEY_SECRET = ''
BEARER_TOKEN = ''
ACCESS_TOKEN = ''
ACCESS_TOKEN_SECRET = ''

USER_ID = 1619900009813803009
# This is a very low usage bot, checking 10 results every 10 seconds is fine for now.
SECONDS = 10
MAX_RESULTS = 10
GENERIC_EXCEPTION_MESSAGE = "We only support the following messages: \nPORTFOLIO \nASSETS\nBUY <#> <symbol> (Buy 10 MSFT)\nSELL <#> <symbol> (Sell 20 MSFT)"
INVALID_SYMBOL_EXCEPTION_MESSAGE = "Sorry, this is not a valid stock symbol."
PRIVATE_SYM_EXCEPTION_MESSAGE = "Sorry, this stock symbol is not trading publicly."

### Butterfly Meme <Is this a database?>
def write_json(portfolio, handled_ids):
    portfolio_json = json.dumps(portfolio)
    with open("portfolio.json", "w") as f:
        f.write(portfolio_json)
        
    ids_json = json.dumps(list(handled_ids))
    with open("handled_ids.json", "w") as f:
        f.write(ids_json)
        
def read_json():
    portfolio_, handled_ids_ = None, None
    with open("portfolio.json", "r") as f:
        portfolio_ = json.load(f)
    with open("handled_ids.json", "r") as f:
        handled_ids_ = set(json.load(f))
    return portfolio_, handled_ids_
    
    def get_portfolio_strings(portfolio):
    strs = [f"We have {portfolio['cash']:.2f} in cash"]
    strs.extend([f"We own {num} shares of {sym}" for sym, num in portfolio['stocks'].items()])
    str_groupings = []
    for i in range(0, len(strs), 5):
        str_groupings.append("\n".join(strs[i:i+5]))
    return str_groupings

### Buying & Selling
def get_portfolio_value(portfolio):
    value = portfolio['cash']
    for sym, num in portfolio['stocks'].items():
        sym_info = yf.Ticker(sym).info
        ticker_value = (sym_info['bid'] + sym_info['ask']) / 2
        value += num * ticker_value
    return value

# TODO: Dig deeper into order book instead of buying all shares at bid/ask regardless of how many shares are at that level.
def buy(num, sym, portfolio):
    sym_info = yf.Ticker(sym).info
    price = sym_info['ask'] * num
    if price > portfolio['cash']:
        return portfolio, f"Buying {num} shares of {sym} would cost {price}. We only have ..."
    else:
        if sym not in portfolio['stocks']:
            portfolio['stocks'][sym] = 0
        portfolio['stocks'][sym] += num
        portfolio['cash'] -= price
        return portfolio, f"Bought {num} shares of {sym} for ${sym_info['ask']} each."
    
def sell(num, sym, portfolio):
    sym_info = yf.Ticker(sym).info
    shares_owned = portfolio['stocks'][sym] if sym in portfolio['stocks'] else 0
    price = sym_info['bid'] * num
    if shares_owned < num:
        return portfolio, f"Cannot sell {num} shares of {sym} as we only have {shares_owned} shares."
    else:
        portfolio['stocks'][sym] -= num
        portfolio['cash'] += price
        return portfolio, f"Selling {num} shares of {sym} for ${sym_info['bid']} each."
    
def is_private(sym):    
    sym_info = yf.Ticker(sym).info
    return sym_info['bid'] in (0, None) or sym_info['ask'] in (0, None)

### Read & write tweets
def parse_tweet(text):
    words = [word for word in text.split(" ") if "@" not in word]
    
    match words:
        case ["portfolio", *_]:
            return "portfolio", None, None
        case ["assets", *_]:
            return "assets", None, None
        case [action, num, sym, *_] if num.isnumeric() and action.lower() in ("buy", "sell"):
            return action, int(num), sym.upper()
        
    raise Exception()
    
def post_tweet(client, text, reply_to):
    print("tweeting!", text)
    client.create_tweet(
        in_reply_to_tweet_id=reply_to,
        text=text
    )
    
def post_tweets(client, texts, reply_to):
    for text in texts:
        print("tweeting!", text)
        response = client.create_tweet(
            in_reply_to_tweet_id=reply_to,
            text=text
        )
        print(response)        
        reply_to = response.data['id']
        
 def run(client):
    response = client.get_users_mentions(USER_ID, max_results=MAX_RESULTS)
    portfolio, handled_ids = read_json()

    for tweet in response.data:
        if tweet.id in handled_ids:
            # print("Already handled", tweet.id, tweet.text)
            continue

        print("Handling: ", tweet.id, tweet.text)
        handled_ids.add(tweet.id)

        try:
            action, num, sym = parse_tweet(tweet.text)
            if action.lower() == "portfolio":
                post_tweets(client, get_portfolio_strings(portfolio), tweet.id)
            elif action.lower() == "assets":
                text = f"The total value of the portfolio is ${get_portfolio_value(portfolio)}"
                post_tweet(client, text, tweet.id)
            elif action.lower() == "buy":
                if type(yf.Ticker(sym).info) == InfoDictWrapper:
                    if is_private(sym):
                        post_tweet(client, PRIVATE_SYM_EXCEPTION_MESSAGE, tweet.id)
                    else:
                        portfolio, reply_text = buy(num, sym, portfolio)
                        post_tweet(client, reply_text, tweet.id)
                else:
                    post_tweet(client, INVALID_SYMBOL_EXCEPTION_MESSAGE, tweet.id)
            elif action.lower() == "sell":
                if type(yf.Ticker(sym).info) == InfoDictWrapper:
                    if is_private(sym):
                        post_tweet(client, PRIVATE_SYM_EXCEPTION_MESSAGE, tweet.id)
                    else:
                        portfolio, reply_text = sell(num, sym, portfolio)
                        post_tweet(client, reply_text, tweet.id)
                else:
                    post_tweet(client, INVALID_SYMBOL_EXCEPTION_MESSAGE, tweet.id)

        except Exception as e:
            print(e)
    write_json(portfolio, handled_ids)


client = tweepy.Client(
    consumer_key=API_KEY, consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token=BEARER_TOKEN,
)

while True:
    run(client)
    time.sleep(SECONDS)
