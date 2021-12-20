import requests
import os
import json
import csv

############################### Twitter API stuff ##############################
# To set your environment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = os.environ.get("BEARER_TOKEN")

search_url = "https://api.twitter.com/2/tweets/search/recent"

# Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
# expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
query_params = {
    'max_results': '10',
    'query': 'lang:en -is:retweet (#funny OR #comedy OR #jokeoftheday)'
}
global_next_token = None


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2RecentSearchPython"
    return r

def connect_to_endpoint(url, params):
    response = requests.get(url, auth=bearer_oauth, params=params)
    # print(response.status_code)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def insert_next_token(query_params, tok):
    # Start from a clean slate no matter what
    query_params.pop("next_token", None)
    if not tok: return query_params
    
    # Record global state
    global global_next_token
    global_next_token = tok
    query_params["next_token"] = global_next_token

    # Return
    return query_params


def get_next_token_from_json_response(json_response):
    # Exit early if we don't have the data we need
    if not json_response: return None
    if not "meta" in json_response: return None
    meta = json_response["meta"]
    if not "next_token" in meta: return None

    # Return
    return meta["next_token"]

################################################################################
def initialize():
    parent_dir = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(parent_dir, "tweets")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def is_valid_tweet(tweet):
    if not "id" in tweet: return False
    if not "text" in tweet: return False
    return True


def is_next_token(tok):
    example_tok = "b26v89c19zqg8o3fpe166s4wxylsy1e90x7npkagygsjh"
    if type(tok) != type(example_tok): return False
    if len(tok) != len(example_tok): return False
    return True


# This is what we'll want to edit
def record_response(json_response):
    # data is valid after this line
    data = json_response["data"]
    if not data: return

    # Gather all the tweets into a list
    tweets = list()
    for tweet in data:
        if not is_valid_tweet(tweet): continue
        # Transform the tweet to the right schema
        formatted_tweet = [tweet["id"], tweet["text"]]
        tweets.append(formatted_tweet)

    append_tweets_to_csv(tweets)


def append_tweets_to_csv(tweets, data_dir=None):
    # data_dir is valid after this line
    if not data_dir or not os.path.isdir(data_dir): data_dir = initialize()

    csv_path = os.path.join(data_dir, "tweets.csv")
    # TODO append instead of overwrite
    with open(csv_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file,
                                delimiter='\xfe',
                                quotechar='\xff',
                                quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerows(tweets)


def next_token_filepath(data_dir=None):
    if not data_dir or not os.path.isdir(data_dir): data_dir = initialize()
    return os.path.join(data_dir, "next_token.txt")


# Write the value in global_next_token to the 'next token' file
def record_global_next_token():
    global global_next_token
    if not global_next_token: return

    with open(next_token_filepath(), 'a') as f:
        f.write(global_next_token)
    print(f"Writing global_next_token: {global_next_token}")


# Read from the 'next token' file into the value global_next_token
def read_global_next_token(data_dir=None):
    ntf = next_token_filepath()
    if not os.path.exists(ntf): return None
    global global_next_token

    # Read and return
    with open(ntf, 'r') as f:
        tok = f.read()
        if not is_next_token(tok): return None
        global_next_token = tok
    return global_next_token


def main():
    insert_next_token(query_params, read_global_next_token())
    for page in range(1):
        json_response = connect_to_endpoint(search_url, query_params)
        record_response(json_response)
        tok = get_next_token_from_json_response(json_response)
        insert_next_token(query_params, tok)
    record_global_next_token()


if __name__ == "__main__":
    main()
