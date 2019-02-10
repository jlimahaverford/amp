from app import cache, twitter_api


@cache.memoize()
def get_status_oembed(tweet_id, hide_media=True):
    return twitter_api.GetStatusOembed(
        status_id=tweet_id,
        hide_media=hide_media)


@cache.memoize()
def get_status(tweet_id):
    return twitter_api.GetStatus(
        status_id=tweet_id,
        include_my_retweet=False,
        include_entities=False)


@cache.memoize()
def get_users_search(query, page, count=20):
    return twitter_api.GetUsersSearch(term=query, page=page, count=count)


@cache.memoize()
def get_user(twitter_username):
    return twitter_api.GetUser(screen_name=twitter_username)


@cache.memoize()
def get_user_timeline(twitter_username, count=10, include_rts=True, max_id=None):
    return twitter_api.GetUserTimeline(
        screen_name=twitter_username,
        count=count,
        include_rts=include_rts,
        max_id=max_id)
