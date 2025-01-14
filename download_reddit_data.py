import praw
import pandas as pd
from typing import List, Dict
import re 
import json
from tqdm import tqdm
import time

# @dataclass
# class subreddit:
    

class RedditDataDownloader:
    def __init__(self,file_path_creds):
        self.reddit = self.initialize_reddit(file_path_creds)
        self.subreddit_df = None


    def initialize_reddit(self,file_path) -> praw.Reddit:
        """Initialize and return Reddit API instance."""

        with open(file_path, 'r') as file:
            content = file.read().strip()
            if not content:
                raise ValueError("File is empty")
            credentials = json.loads(content)

        return praw.Reddit(
            client_id=credentials['CLIENT_ID'],
            client_secret=credentials['CLIENT_SECRET'],
            user_agent=credentials['USER_AGENT']
        )


    # get the posts from the subreddit
    def get_posts(self, subreddits: List[str], method_limits: Dict[str, int], top_time_filter: str = 'month') -> pd.DataFrame:
        """
        Fetch posts from specified subreddits using different sorting methods.
        
        Args:
            reddit: Reddit API instance
            subreddits: List of subreddit names
            method_limits: Dictionary of method names and their post limits
            top_time_filter: Time filter for top posts ('hour', 'day', 'week', 'month', 'year', 'all')
        """
        all_posts = []
        
        for subreddit_name in tqdm(subreddits, desc='Subreddits'):
            subreddit = self.reddit.subreddit(subreddit_name)
            
            for method, limit in method_limits.items():
                # Handle 'top' posts separately due to time_filter parameter
                if method == 'top':
                    submissions = subreddit.top(limit=limit, time_filter=top_time_filter)
                else:
                    submissions = getattr(subreddit, method)(limit=limit)
                
                # Extract post data
                for submission in submissions:
                    all_posts.append({
                        'id': submission.id,
                        'title': submission.title,
                        'score': submission.score,
                        'num_comments': submission.num_comments,
                        'created_utc': submission.created_utc,
                        'text': submission.selftext,
                        'subreddit': submission.subreddit.display_name,
                        'method': f"{method}_{top_time_filter}" if method == 'top' else method
                    })
        
        df = pd.DataFrame(all_posts)
        df.drop_duplicates(subset=['id'], inplace=True)
         =df
        return df










if __name__ == '__main__':

    file_path = '/Users/andre/Documents/Python_local/sentiment_analyses/reddit_creds.json'
    reddit_obj = RedditDataDownloader(file_path)



    # general subreddits + coin specific subreddits
    list_of_subreddits = [
        #solana
        'solana','SolanaMemeCoins',
        #eth 
        'ethereum','ethtrader','ethfinance','ethermining','ethstaker',
        #bitcoin
        'Bitcoin', 'BitcoinBeginners', 'btc', 'BitcoinMarkets',
        #general crypto info 
        'CryptoCurrency','Superstonk','Crypto_General','Crypto_Currency_News','CryptocurrencyICO','SatoshiStreetBets','CryptoTradingFloor','crypto','CryptoCurrencies','CryptoCurrencyClassic','CryptoExchange','CryptoNews','CryptoMarkets','crypto_currency'
        ]

    list_of_subreddits_test = ['solana']
    # Define limits for each method
    all_limit = 1

    method_limits = {
        'hot': all_limit,
        'new': all_limit,
        'controversial': all_limit,
        'rising': all_limit,
        'top': all_limit
    }

    # Define time filter for top posts
    filter_top_method = 'month'  # Options: 'hour', 'day', 'week', 'month', 'year', 'all'

    # Get posts and create DataFrame
    df = reddit_obj.get_posts( list_of_subreddits_test, method_limits=method_limits, top_time_filter=filter_top_method)

    print(df) 
