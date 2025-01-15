import praw
import pandas as pd
from typing import List, Dict
import re 
import json
from tqdm import tqdm
import time
import os

# @dataclass
# class subreddit:
    

class RedditDataDownloader:
    def __init__(self,file_path_creds):
        self.reddit = self.initialize_reddit(file_path_creds)
        self.subreddit_df = None
        self.request_count = 0
        self.start_time = time.time()


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

    def rate_limit(self):
        """Rate limit to ensure no more than 100 requests per minute."""
        self.request_count += 1
        if self.request_count >= 30:
            elapsed_time = time.time() - self.start_time
            if elapsed_time < 60:
                sleep_time = 70 - elapsed_time
                print(f"Rate limit reached. Sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time)
            self.request_count = 0
            self.start_time = time.time()


    # get the posts from the subreddit
    def get_subreddits(self, subreddits: List[str], method_limits: Dict[str, int], top_time_filter: str = 'month') -> pd.DataFrame:
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
        self.subreddit_df = df
        return df


    def get_comments(self, submission_id):
        """Retrieve comments for a submission."""
        comments_data = []
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=30)
            comments = submission.comments.list()
            for comment in comments:
                try:
                    comments_data.append({
                        'submission_id': submission_id,
                        'comment_id': comment.id,
                        'comment_body': comment.body,
                        'comment_score': comment.score,
                        'comment_created_utc': comment.created_utc,
                        # 'comment_parent_id': comment.parent_id,
                    })
                except Exception as e:
                    print(f"Error processing comment: {e}")
                    time.sleep(65)
                    print('Sleeping for 65 seconds')
        except Exception as e:
            print(f"Error processing submission: {e}")
            comments_data.append({
                'submission_id': submission_id,
                'comment_id': str(e),
                'comment_body': str(e),
                'comment_score': str(e),
                'comment_created_utc': str(e)
            })
        return comments_data

    def process_submissions(self, df, batch_size=100, output_dir='comments_data'):
        """Retrieve comments for each submission and create a DataFrame in batches."""
        all_comments = []
        batch_count = 0

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for submission_id in tqdm(df['id'], desc="Processing submissions"):
            self.rate_limit()
            if pd.notna(submission_id):  # Ensure submission_id is not NaN
                try:
                    all_comments.extend(self.get_comments(submission_id))
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(65)
                    print('Sleeping for 65 seconds')

            # Save batch to file and clear memory
            if len(all_comments) >= batch_size:
                self.save_batch_to_file(all_comments, output_dir, batch_count)
                all_comments = []  # Clear the list to save memory
                batch_count += 1
                print(f"Batch {batch_count} saved.")

        # Save any remaining comments
        if all_comments:
            self.save_batch_to_file(all_comments, output_dir, batch_count)
            print(f"Final batch saved.")

    def save_batch_to_file(self, comments, output_dir, batch_count):
        """Save a batch of comments to a pickle file."""
        df = pd.DataFrame(comments)
        if not df.empty:
            file_path = os.path.join(output_dir, f'batch_{batch_count}.pkl')
            df.to_pickle(file_path)

    def combine_batches(self, output_dir='comments_data', combined_file='combined_comments.pkl'):
        """Combine all saved DataFrames into one and save as a pickle file."""
        all_dfs = []
        for file_name in os.listdir(output_dir):
            if file_name.endswith('.pkl'):
                file_path = os.path.join(output_dir, file_name)
                df = pd.read_pickle(file_path)
                all_dfs.append(df)
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df.to_pickle(combined_file)
        print(f"Combined DataFrame saved as {combined_file}")


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
    all_limit = 30

    method_limits = {
        'hot': all_limit,
        'new': all_limit,
        'controversial': all_limit,
        'rising': all_limit,
        'top': all_limit
    }

    # Define time filter for top posts
    filter_top_method = 'week'  # Options: 'hour', 'day', 'week', 'month', 'year', 'all'

    # Get posts and create DataFrame

    df = reddit_obj.get_subreddits( list_of_subreddits, method_limits=method_limits, top_time_filter=filter_top_method)
    print('subreddit df:\n',df)
    # Process submissions and comments

    reddit_obj.process_submissions(df)

    # Combine all saved batches into one DataFrame
    reddit_obj.combine_batches()

