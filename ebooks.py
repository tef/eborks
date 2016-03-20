from __future__ import print_function
import sys
import os
import tweepy
import HTMLParser
from pprint import pprint as print

html_parser = HTMLParser.HTMLParser()

def source_status_id(tweet):
    return tweet.retweeted_status.id

def connect():
    consumer_key = os.environ['TWITTER_CONSUMER_KEY']
    consumer_secret = os.environ['TWITTER_CONSUMER_SECRET']

    access_token = os.environ['TWITTER_ACCESS_TOKEN']
    access_token_secret = os.environ['TWITTER_ACCESS_TOKEN_SECRET']


    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    return tweepy.API(auth)

def retweeted(tweet):
    return tweet.text.startswith('RT') and getattr(tweet,'retweeted_status', None)

if __name__=="__main__":

    screen_name=os.environ['TWITTER_SOURCE_ACCOUNT']
    api = connect()

    # get most recent tweets of source account
    source_tweets = api.user_timeline(
        screen_name,
        count=200,
        trim_user=True,
        exclude_replies=False,
        include_rts=True,
    )

    # get most recent tweets of reposting account

    ebooks_tweets = api.user_timeline(
        screen_name="tef_ebooks",
        count=200,
        trim_user=True,
        exclude_replies=False,
        include_rts=True,
    )

    ebooks_retweets = [t for t in ebooks_tweets if retweeted(t)]
    ebooks_tweets = [t for t in ebooks_tweets if not (retweeted(t) or t.text.startswith('@'))]

    # get maximum date, id of ebooks tweets.

    max_ebooks_id = max(tweet.id for tweet in ebooks_tweets)
    max_ebooks_timestamp = max(tweet.created_at for tweet in ebooks_tweets)

    ebooks_retweet_ids = set(source_status_id(tweet) for tweet in ebooks_retweets)
    ebooks_tweet_ids = dict((tweet.text, tweet.id) for tweet in ebooks_tweets)

    new_tweet_ids = {}

    for tweet in source_tweets:
        if not retweeted(tweet):
            media = tweet._json['entities'].get('media')
            if media:
                for m in media:
                    source_url = m['media_url_https']
                    compressed_url = m['url']
                    tweet.text = tweet.text.replace(compressed_url, source_url)

            if tweet.text in ebooks_tweet_ids:
                new_tweet_ids[tweet.id] = ebooks_tweet_ids[tweet.text]

    def old_tweet(tweet):
        if retweeted(tweet):
            return source_status_id(tweet) in ebooks_retweet_ids or ('@'+screen_name in tweet.text)
        else:
            return (
                tweet.text.strip().startswith(('@','.','RT')) or
                tweet.id < max_ebooks_id or
                tweet.created_at < max_ebooks_timestamp or
                tweet.text in ebooks_tweet_ids
            )


    # build a map of old tweet ids to new tweet ids

    recent_source_tweets = sorted([tweet for tweet in source_tweets if not old_tweet(tweet)], key=lambda t: t.created_at)

    if '--dry-run' in sys.argv:
        for tweet in recent_source_tweets:
            if retweeted(tweet):
                print("retweet {}, #{}".format(tweet.text, source_status_id(tweet)))
            else:
                print("tweet:{} irt:{}".format(tweet.text, new_tweet_ids.get(tweet.in_reply_to_status_id)))
    else:
        for tweet in recent_source_tweets:
            if retweeted(tweet):
                status = api.retweet(id=source_status_id(tweet))
            else:
                text = html_parser.unescape(tweet.text)
                status = api.update_status(status=text, in_reply_to_status_id=new_tweet_ids.get(tweet.in_reply_to_status_id))
                new_tweet_ids[tweet.id] = status.id

