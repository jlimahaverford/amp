from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, Markup
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import func
from sqlalchemy.sql import label

from app import app, db, twitter_api
from app.forms import EditProfileForm, LoginForm, RegistrationForm, SearchForm
from app.models import User, TwitterUser, Tweet, Amp
from app.forms import ResetPasswordRequestForm
from app.email import send_password_reset_email
from app.forms import ResetPasswordForm


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/')
@app.route('/index')
@login_required
def index():
    results = db.session.query(
        Amp.tweet_id, label('amps', func.count(Amp.user_id))).filter_by(
        is_active=True).group_by(
        Amp.tweet_id).order_by(
        'amps').limit(
        10).all()
    #  TODO: Implement pagination using query()....pagination()
    cards = [
        dict(status_id=t, amp_count=amp_count, **twitter_api.GetStatusOembed(status_id=t, hide_media=False))
        for t, amp_count in results]
    return render_template('index.html', title='Home', cards=cards)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if (user is None) or (not user.check_password(form.password.data)):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    amps = Amp.query.filter_by(user_id=user.id).order_by(Amp.timestamp.desc()).limit(10).all()
    tweet_ids = [amp.tweet_id for amp in amps]
    timestamps = [amp.timestamp for amp in amps]
    cards = [
        dict(status_id=t, **twitter_api.GetStatusOembed(status_id=t, hide_media=True))
        for t in tweet_ids]
    return render_template('user.html', user=user, cards=cards)


@app.route('/twitter_user/<twitter_username>')
@login_required
def twitter_user(twitter_username):
    twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    if twitter_user is None:
        twitter_user = TwitterUser(twitter_username=twitter_username)
        db.session.add(twitter_user)
        db.session.commit()
        app.logger.info('Added TwitterUser: {}'.format(twitter_username))
    #  TODO: Add pagination using 'max_id' and 'since'
    tweets = twitter_api.GetUserTimeline(screen_name=twitter_username, count=10, include_rts=False)
    cards = [
        dict(status_id=t.id, **twitter_api.GetStatusOembed(status_id=t.id, hide_media=True))
        for t in tweets]
    return render_template('twitter_user.html', cards=cards)


@app.route('/twitter_user_search', methods=['GET', 'POST'])
@login_required
def twitter_user_search():
    app.logger.info('entered /twitter_user_search endpoint.')
    title = 'Twitter User Search'
    form = SearchForm()
    if form.validate_on_submit():
        query = form.query.data
        page = 1
        # app.logger.info('about to get user list')
        #  TODO: Add pagination ( GetUsersSearch(term=None, page=1, count=20, include_entities=None) )
        # us = twitter_api.GetUsersSearch(term=query, page=page, count=20)
        # users = [u.AsDict() for u in us]
        # app.logger.info('retrieved user list')
        title = 'Twitter User Search: {}, Page: {}'.format(query, page)
        return redirect(url_for('twitter_user_search_results', query=query, page=page))
    return render_template('twitter_user_search.html', title='Twitter User Search', form=form)


@app.route('/twitter_user_search_results/<query>/<page>')
@login_required
def twitter_user_search_results(query, page):
    page = int(page)
    title = 'Twitter User Search: "{}", Page: {}'.format(query, page)
    twitter_users = twitter_api.GetUsersSearch(term=query, page=page, count=20)
    twitter_user_dicts = [tu.AsDict() for tu in twitter_users]
    return render_template(
        'twitter_user_search_results.html',
        title=title,
        query=query,
        twitter_user_dicts=twitter_user_dicts,
        page=page)



@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@app.route('/follow_twitter_user/<twitter_username>')
@login_required
def follow_twitter_user(twitter_username):
    twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    if twitter_user is None:
        twitter_user = TwitterUser(twitter_username=twitter_username)
        db.session.add(twitter_user)
        db.session.commit()
        twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    current_user.follow_twitter_user(twitter_user)
    db.session.commit()
    flash('You are now following {}!'.format(twitter_username))
    return redirect(url_for('twitter_user', twitter_username=twitter_username))


@app.route('/unfollow_twitter_user/<twitter_username>')
@login_required
def unfollow_twitter_user(twitter_username):
    twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    if twitter_user is None:
        #  TODO: Replace with actual error
        flash('Error: Twitter User {} not found.'.format(twitter_username))
        return redirect(url_for('index'))
    current_user.unfollow_twitter_user(twitter_user)
    db.session.commit()
    flash('You are no longer following @{}.'.format(twitter_username))
    return redirect(url_for('twitter_user', twitter_username=twitter_username))


@app.route('/amp_tweet/<tweet_id>')
@login_required
def amp_tweet(tweet_id):
    tweet = Tweet.query.filter_by(id=tweet_id).first()
    if tweet is None:
        twitter_tweet = twitter_api.GetStatus(tweet_id)
        db.session.add(Tweet.from_twitter_tweet(twitter_tweet))
        db.session.commit()
        tweet = Tweet.query.filter_by(id=tweet_id).first()
    twitter_user = TwitterUser.query.filter_by(id=tweet.twitter_user_id).first()
    twitter_username = twitter_user.twitter_username
    current_user.amp_tweet(tweet)
    db.session.commit()
    flash("You amp'ed @{}'s tweet!".format(twitter_username))
    return redirect(url_for('user', username=current_user.username))


@app.route('/unamp_tweet')
@login_required
def unamp_tweet():
    amp = current_user.get_active_amp()
    tweet = Tweet.query.filter_by(id=amp.tweet_id).first()
    twitter_user = TwitterUser.query.filter_by(id=tweet.twitter_user_id).first()
    twitter_username = twitter_user.twitter_username
    current_user.unamp()
    db.session.commit()
    flash("You unamp'ed @{}'s tweet!".format(twitter_username))
    return redirect(url_for('user', username=current_user.username))


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template(
        'reset_password_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)
