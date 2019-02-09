from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required

from app import db, twitter_api
from app.main.forms import EditProfileForm, SearchForm
from app.models import User, TwitterUser, Tweet, Amp
from app.main import bp
from app.main.db_utils import get_amp_dict_from_ids, get_amp_dict_leaderboard
from app.main.utils import get_bigger_twitter_user_image_url


@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    #  TODO: Implement pagination using query()....pagination()
    #  TODO: Implement "Tweeted at <timestamp>"
    result_dict = get_amp_dict_leaderboard()
    cards = [
        dict(status_id=t, amp_count=amp_count, **twitter_api.GetStatusOembed(status_id=t, hide_media=False))
        for t, amp_count in result_dict.items()]
    return render_template('index.html', title='Home', cards=cards)


@bp.route('/user/<username>')
@login_required
def user(username):
    #  TODO: Implement pagination
    #  TODO: Implement "Amped at <timestamp>"
    user = User.query.filter_by(username=username).first_or_404()
    amps = Amp.query.filter_by(user_id=user.id).order_by(Amp.timestamp.desc()).limit(10).all()
    tweet_ids = [amp.tweet_id for amp in amps]
    timestamps = [amp.timestamp for amp in amps]
    result_dict = get_amp_dict_from_ids(tweet_ids)
    cards = [dict(
        status_id=t,
        amp_count=result_dict.get(t, 0),
        **twitter_api.GetStatusOembed(status_id=t, hide_media=True))
            for t in tweet_ids]
    return render_template('user.html', user=user, cards=cards)


@bp.route('/twitter_user/<twitter_username>', defaults={'max_id': None})
@bp.route('/twitter_user/<twitter_username>/<max_id>')
@login_required
def twitter_user(twitter_username, max_id):
    #  TODO: Implement pagination using 'max_id' and 'since'
    #  TODO: Implement "Tweeted at <timestamp>"
    twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    if twitter_user is None:
        twitter_user = TwitterUser(twitter_username=twitter_username)
        db.session.add(twitter_user)
        db.session.commit()
        current_app.logger.info('Added TwitterUser: {}'.format(twitter_username))
    tweets = twitter_api.GetUserTimeline(screen_name=twitter_username, count=10, include_rts=True, max_id=max_id)
    tweet_ids = [t.id for t in tweets]
    result_dict = get_amp_dict_from_ids(tweet_ids)
    cards = [dict(status_id=t, amp_count=result_dict.get(t, 0),
                  **twitter_api.GetStatusOembed(status_id=t, hide_media=False))
             for t in tweet_ids]
    return render_template('twitter_user.html', cards=cards)


@bp.route('/twitter_user_search', methods=['GET', 'POST'])
@login_required
def twitter_user_search():
    form = SearchForm()
    if form.validate_on_submit():
        return redirect(url_for('main.twitter_user_search_results', query=form.query.data, page=1))
    return render_template('twitter_user_search.html', title='Twitter User Search', form=form)


@bp.route('/twitter_user_search_results/<query>', defaults={'page': 1})
@bp.route('/twitter_user_search_results/<query>/<page>')
@login_required
def twitter_user_search_results(query, page):
    page = int(page)
    title = 'Twitter User Search: "{}", Page: {}'.format(query, page)
    twitter_users = twitter_api.GetUsersSearch(term=query, page=page, count=20)
    twitter_user_dicts = [tu.AsDict() for tu in twitter_users]
    for tud in twitter_user_dicts:
        tud['profile_image_url'] = get_bigger_twitter_user_image_url(tud['profile_image_url'])
    return render_template(
        'twitter_user_search_results.html',
        title=title,
        query=query,
        twitter_user_dicts=twitter_user_dicts,
        page=page)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@bp.route('/follow_twitter_user/<twitter_username>')
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
    return redirect(url_for('main.twitter_user', twitter_username=twitter_username))


@bp.route('/unfollow_twitter_user/<twitter_username>')
@login_required
def unfollow_twitter_user(twitter_username):
    twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    if twitter_user is None:
        #  TODO: Replace with actual error
        flash('Error: Twitter User {} not found.'.format(twitter_username))
        return redirect(url_for('main.index'))
    current_user.unfollow_twitter_user(twitter_user)
    db.session.commit()
    flash('You are no longer following @{}.'.format(twitter_username))
    return redirect(url_for('main.twitter_user', twitter_username=twitter_username))


@bp.route('/amp_tweet/<tweet_id>')
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
    return redirect(url_for('main.user', username=current_user.username))


@bp.route('/unamp_tweet')
@login_required
def unamp_tweet():
    amp = current_user.get_active_amp()
    tweet = Tweet.query.filter_by(id=amp.tweet_id).first()
    twitter_user = TwitterUser.query.filter_by(id=tweet.twitter_user_id).first()
    twitter_username = twitter_user.twitter_username
    current_user.unamp()
    db.session.commit()
    flash("You unamp'ed @{}'s tweet!".format(twitter_username))
    return redirect(url_for('main.user', username=current_user.username))


@bp.route('/who_amping_tweet/<tweet_id>', defaults={'page': 1})
@bp.route('/who_amping_tweet/<tweet_id>/<page>')
@login_required
def who_amping_tweet(tweet_id, page):
    page = int(page)
    card = twitter_api.GetStatusOembed(status_id=tweet_id)
    title = "Who's Amping {}'s Tweet?".format(card['author_name'])
    results = db.session.query(
        User, Amp).filter(
        User.id == Amp.user_id).filter(
        Amp.tweet_id == tweet_id).filter(
        Amp.is_active).order_by(
        Amp.timestamp.desc()).all()
    return render_template(
        'who_amping_tweet.html',
        title=title,
        results=results,
        tweet_id=tweet_id,
        card=twitter_api.GetStatusOembed(status_id=tweet_id),
        page=page)
