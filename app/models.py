from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    amps = db.relationship('Amp', backref='amper', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)


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
