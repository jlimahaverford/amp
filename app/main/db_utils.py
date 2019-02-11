from flask import current_app
from sqlalchemy import func
from sqlalchemy.sql import label

from app import cache, db
from app.models import Amp, User

TWEETS_PER_PAGE = 10


@cache.memoize()
def get_num_amps_from_tweet_id(tweet_id):
    result = db.session.query(
        label('amps', func.count(Amp.user_id))).filter_by(
        is_active=True, tweet_id=tweet_id).group_by(
        Amp.tweet_id).first()
    return 0 if result is None else result[0]


@cache.memoize()
def get_amps_from_tweet_ids(tweet_ids, num_tweets=TWEETS_PER_PAGE):
    return dict(db.session.query(
        Amp.tweet_id, label('amps', func.count(Amp.user_id))).filter_by(
        is_active=True).filter(
        Amp.tweet_id.in_(tweet_ids)).group_by(
        Amp.tweet_id).order_by(
        'amps desc').limit(
        num_tweets).all())


@cache.memoize()
def get_amps_for_index(page):
    return db.session.query(
        Amp.tweet_id, label('amps', func.count(Amp.user_id))).filter_by(
        is_active=True).group_by(
        Amp.tweet_id).order_by(
        'amps desc').paginate(
        page, current_app.config['TWEETS_PER_PAGE'], False)


@cache.memoize()
def get_amps_by_user(user_id, page):
    return Amp.query.filter_by(
        user_id=user_id, is_active=False).order_by(
        Amp.timestamp.desc()).paginate(
        page, current_app.config['TWEETS_PER_PAGE'], False)


@cache.memoize()
def get_users_amping_tweet(tweet_id, page):
    return db.session.query(
        User, Amp).filter(
        User.id == Amp.user_id).filter(
        Amp.tweet_id == tweet_id).filter(
        Amp.is_active).order_by(
        Amp.timestamp.asc()).paginate(
        page, current_app.config['TWEETS_PER_PAGE'], False)
