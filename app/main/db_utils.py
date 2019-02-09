from sqlalchemy import func
from sqlalchemy.sql import label

from app import db
from app.models import Amp

TWEETS_PER_PAGE = 10


def get_amp_dict_from_ids(tweet_ids, num_tweets=TWEETS_PER_PAGE):
    return dict(db.session.query(
        Amp.tweet_id, label('amps', func.count(Amp.user_id))).filter_by(
        is_active=True).filter(
        Amp.tweet_id.in_(tweet_ids)).group_by(
        Amp.tweet_id).order_by(
        'amps desc').limit(
        num_tweets).all())


def get_amp_dict_leaderboard(num_tweets=TWEETS_PER_PAGE):
    return dict(db.session.query(
        Amp.tweet_id, label('amps', func.count(Amp.user_id))).filter_by(
        is_active=True).group_by(
        Amp.tweet_id).order_by(
        'amps desc').limit(
        num_tweets).all())
