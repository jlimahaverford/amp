from enum import Enum
from app import cache, twitter_api


class TwitterCacheType(Enum):
    STATUS_OEMBED = 1
    STATUS = 2


def get_status_oembed(tweet_id, hide_media=True):
    key = (TwitterCacheType.STATUS_OEMBED, tweet_id)
    value = cache.get(key)
    if value is None:
        value = twitter_api.GetStatusOembed(
            status_id=tweet_id,
            hide_media=hide_media)
        cache.set(key, value)
    return value


def get_status(tweet_id):
    key = (TwitterCacheType.STATUS, tweet_id)
    value = cache.get(key)
    if value is None:
        value = twitter_api.GetStatus(
            status_id=tweet_id,
            include_my_retweet=False,
            include_entities=False)
        cache.set(key, value)
    return value
