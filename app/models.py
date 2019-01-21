from datetime import datetime
from app import db, login
from hashlib import md5

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    amps = db.relationship('Amp', backref='amper', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)


class TwitterUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_username = db.Column(db.String(15), index=True, unique=True)
    tweets = db.relationship('Tweet', backref='tweeter', lazy='dynamic')

    def __repr__(self):
        return '<TwitterUser {}>'.format(self.twitter_username)


class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_user_id = db.Column(db.Integer, db.ForeignKey('twitter_user.id'))
    body = db.Column(db.String(280))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Tweet {}>'.format(self.body)


class Amp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Amp {}, {}>'.format(self.user_id, self.tweet_id)
