from datetime import datetime
from app import db, login
from hashlib import md5
from sqlalchemy.orm import backref
from time import time
import jwt

from app import app

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


twitter_user_follow = db.Table('twitter_user_follow',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('twitter_user_id', db.Integer, db.ForeignKey('twitter_user.id')))


class TwitterUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_username = db.Column(db.String(15), index=True, unique=True)
    tweets = db.relationship('Tweet', backref='tweeter', lazy='dynamic')

    def __repr__(self):
        return '<TwitterUser {}>'.format(self.twitter_username)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    amps = db.relationship('Amp', backref=backref('amper', uselist=False), lazy='dynamic')
    active_amp_id = db.Column(db.Integer)
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    twitter_follows = db.relationship(
        'TwitterUser', secondary=twitter_user_follow,
        primaryjoin=(twitter_user_follow.c.user_id == id),
        secondaryjoin=(twitter_user_follow.c.twitter_user_id == TwitterUser.id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_active_amp_id(self):
        amp = Amp.query.filter_by(user_id=self.id, is_active=True).first()
        if amp is None:
            self.active_amp_id = None
        else:
            app.logger.info('Amp ID: {}'.format(amp.id))
            self.active_amp_id = amp.id

    def get_active_amp(self):
        return Amp.query.filter_by(id=self.active_amp_id).first()

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow_twitter_user(self, twitter_user):
        if not self.is_following_twitter_user(twitter_user):
            self.twitter_follows.append(twitter_user)

    def unfollow_twitter_user(self, twitter_user):
        if self.is_following_twitter_user(twitter_user):
            self.twitter_follows.remove(twitter_user)

    def is_following_twitter_user(self, twitter_user):
        return self.twitter_follows.filter(
            twitter_user_follow.c.twitter_user_id == twitter_user.id).count() > 0

    def is_following_twitter_username(self, twitter_username):
        twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
        if twitter_user is None:
            return False
        return self.is_following_twitter_user(twitter_user)

    def amp_tweet(self, tweet):
        if self.is_amping_something():
            self.unamp()
        amp = Amp(user_id=self.id, tweet_id=tweet.id, is_active=True)
        db.session.add(amp)
        self.set_active_amp_id()

    def unamp(self):
        if self.is_amping_something():
            self.get_active_amp().deactivate()
            self.set_active_amp_id()

    def is_amping_something(self):
        return self.active_amp_id is not None


    def is_amping_tweet(self, tweet_id):
        if self.is_amping_something():
            if self.get_active_amp().tweet_id == tweet_id:
                return True
        return False

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_user_id = db.Column(db.Integer, db.ForeignKey('twitter_user.id'))
    body = db.Column(db.String(280))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Tweet - ID: {}, Timestamp: {}>'.format(self.id, self.timestamp)

    @classmethod
    def from_twitter_tweet(cls, twitter_tweet):
        twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_tweet.user.screen_name).first()
        return cls(
            id=twitter_tweet.id,
            twitter_user_id=twitter_user.id,
            body=twitter_tweet.text,
            timestamp=datetime.fromtimestamp(twitter_tweet.created_at_in_seconds))


class Amp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_active = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return '<Amp {}, {}>'.format(self.user_id, self.tweet_id)

    def deactivate(self):
        self.is_active = False
