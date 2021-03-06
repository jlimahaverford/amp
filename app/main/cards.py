import datetime as dt
import re
from enum import Enum
from typing import Tuple

from app.main.twitter_utils import get_status_oembed, get_status
from app.models import User
from app.main.db_utils import get_num_amps_from_tweet_id


class UserEvent(Enum):
    CREATED_ACCOUNT = 1
    LAST_SEEN = 2
    AMPED_TWEET = 3
    FOLLOWED_TWTTIER_USER = 4

    def display(self):
        return {
            1: "Join on ",
            2: "Last seen on ",
            3: "Amped on ",
            4: "Followed on "
        }[self.value]


class TweetEvent(Enum):
    TWEETED = 1
    RETWEETED = 2
    AMPED = 3

    def display(self):
        return {
            1: "Tweeted on ",
            2: "Retweeted on ",
            3: "Amped on ",
        }[self.value]


class UserCard:

    def __init__(self, user: User, event_tuple: Tuple[UserEvent, dt.datetime]=None):
        self.user = user
        if event_tuple is None:
            event_tuple = (UserEvent.LAST_SEEN, user.last_seen)
        self.event_tuple = event_tuple


class TweetCard:

    def __init__(self, tweet_id: int, num_amps: int=None, event_tuple: Tuple[TweetEvent, dt.datetime]=None, hide_media: bool=True):
        self.tweet_id = tweet_id
        if num_amps is None:
            num_amps = get_num_amps_from_tweet_id(tweet_id)
        self.num_amps = num_amps
        self.status = get_status(tweet_id=tweet_id)
        self.oembed = get_status_oembed(tweet_id=tweet_id, hide_media=hide_media)
        self.screen_name = self.status.user.screen_name
        if event_tuple is None:
            event_tuple = (TweetEvent.TWEETED, dt.datetime.fromtimestamp(self.status.created_at_in_seconds))
        self.event_tuple = event_tuple


class TwitterUserCard:

    def __init__(self, twitter_user):
        self.screen_name = twitter_user.screen_name
        self.profile_image_url = str.replace(twitter_user.profile_image_url, 'normal', '400x400')
        self.verified = twitter_user.verified
