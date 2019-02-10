from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required

from app import db, twitter_api
from app.main.forms import EditProfileForm, SearchForm
from app.models import User, TwitterUser, Tweet, Amp
from app.main import bp
from app.main.db_utils import get_amp_dict_from_ids, get_amp_dict_leaderboard, get_num_amps_from_tweet_id
from app.main.cards import UserCard, UserEvent, TweetCard, TwitterUserCard
from app.main.twitter_utils import get_status


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
    title = 'Home'
    result_dict = get_amp_dict_leaderboard()
    tweet_cards = [
        TweetCard(tweet_id=tweet_id, num_amps=num_amps, hide_media=False)
        for tweet_id, num_amps in result_dict.items()]
    return render_template('index.html', title=title, tweet_cards=tweet_cards)


@bp.route('/user/<username>')
@login_required
def user(username):
    #  TODO: Implement pagination
    #  TODO: Implement "Amped at <timestamp>"
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    user_card = UserCard(user=user)
    title = "{}'s Profile".format(user.username)

    current_amp = Amp.query.filter_by(
        id=user.active_amp_id).first()
    current_amp_tweet_card = TweetCard(tweet_id=current_amp.tweet_id, hide_media=False)

    amps = Amp.query.filter_by(
        user_id=user.id, is_active=False).order_by(
        Amp.timestamp.desc()).paginate(
        page, current_app.config['TWEETS_PER_PAGE'], False)
    tweet_ids, timestamps = zip(*[(amp.tweet_id, amp.timestamp) for amp in amps.items])
    result_dict = get_amp_dict_from_ids(list(set(tweet_ids)))
    tweet_cards = [TweetCard(tweet_id=tweet_id, num_amps=result_dict.get(tweet_id, 0))
             for tweet_id in tweet_ids]

    next_url = (url_for('main.user', username=username, page=amps.next_num)
                if amps.has_next else None)
    prev_url = (url_for('main.user', username=username, page=amps.prev_num)
                if amps.has_prev else None)
    return render_template(
        'user.html', title=title, user_card=user_card,
        current_amp_tweet_card=current_amp_tweet_card, tweet_cards=tweet_cards,
        next_url=next_url, prev_url=prev_url)


@bp.route('/twitter_user/<twitter_username>', defaults={'max_id': None})
@bp.route('/twitter_user/<twitter_username>/<max_id>')
@login_required
def twitter_user(twitter_username, max_id):
    #  TODO: Implement pagination using 'max_id' and 'since'
    #  TODO: Implement "Tweeted at <timestamp>"
    title = "@{}'s Profile".format(twitter_username)
    twitter_user = TwitterUser.query.filter_by(twitter_username=twitter_username).first()
    if twitter_user is None:
        twitter_user = TwitterUser(twitter_username=twitter_username)
        db.session.add(twitter_user)
        db.session.commit()
        current_app.logger.info('Added TwitterUser: {}'.format(twitter_username))

    twitter_user_card = TwitterUserCard(twitter_api.GetUser(screen_name=twitter_username))
    tweets = twitter_api.GetUserTimeline(screen_name=twitter_username, count=10, include_rts=True, max_id=max_id)
    tweet_ids = [t.id for t in tweets]
    result_dict = get_amp_dict_from_ids(tweet_ids)
    tweet_cards = [TweetCard(tweet_id=tweet_id, num_amps=result_dict.get(tweet_id, 0), hide_media=False)
             for tweet_id in tweet_ids]
    return render_template(
        'twitter_user.html',
        title=title,
        twitter_user_card=twitter_user_card,
        tweet_cards=tweet_cards)


@bp.route('/twitter_user_search', methods=['GET', 'POST'])
@login_required
def twitter_user_search():
    form = SearchForm()
    if form.validate_on_submit():
        return redirect(url_for('main.twitter_user_search_results', query=form.query.data))
    return render_template('twitter_user_search.html', title='Twitter User Search', form=form)


@bp.route('/twitter_user_search_results/<query>')
@login_required
def twitter_user_search_results(query):
    page = request.args.get('page', 1, type=int)
    title = 'Twitter User Search: {}'.format(query)
    twitter_users = twitter_api.GetUsersSearch(term=query, page=page, count=20)
    twitter_user_cards = [TwitterUserCard(tu) for tu in twitter_users]
    next_url = url_for('main.twitter_user_search_results', query=query, page=page+1)
    prev_url = (url_for('main.twitter_user_search_results', query=query, page=page-1)
                if page > 1 else None)
    return render_template(
        'twitter_user_search_results.html', title=title, query=query,
        twitter_user_cards=twitter_user_cards, page=page, next_url=next_url,
        prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    title = 'Edit Profile'
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
    return render_template('edit_profile.html', title=title, form=form)


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
        twitter_tweet = get_status(tweet_id)
        db.session.add(Tweet.from_twitter_tweet(twitter_tweet))
        db.session.commit()
        tweet = Tweet.query.filter_by(id=tweet_id).first()
    twitter_user = TwitterUser.query.filter_by(id=tweet.twitter_user_id).first()
    twitter_username = twitter_user.twitter_username
    current_user.amp_tweet(tweet)
    db.session.commit()
    flash("You amp'ed @{}'s tweet!".format(twitter_username))
    return redirect(url_for('main.index'))


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
    return redirect(url_for('main.index'))


@bp.route('/who_amping_tweet/<tweet_id>')
@login_required
def who_amping_tweet(tweet_id):
    tweet_id = int(tweet_id)
    page = request.args.get('page', 1, type=int)

    tweet_card = TweetCard(tweet_id=tweet_id, hide_media=False)
    title = "Who's Amping @{}'s Tweet?".format(tweet_card.screen_name)
    amps = db.session.query(
        User, Amp).filter(
        User.id == Amp.user_id).filter(
        Amp.tweet_id == tweet_id).filter(
        Amp.is_active).order_by(
        Amp.timestamp.asc()).paginate(
        page, current_app.config['TWEETS_PER_PAGE'], False)
    user_cards = [
        UserCard(user, (UserEvent.AMPED_TWEET, amp.timestamp))
        for user, amp in amps.items]

    next_url = (url_for('main.who_amping_tweet', tweet_id=tweet_id, page=amps.next_num)
                if amps.has_next else None)
    prev_url = (url_for('main.who_amping_tweet', tweet_id=tweet_id, page=amps.prev_num)
                if amps.has_prev else None)
    return render_template(
        'who_amping_tweet.html',
        title=title,
        user_cards=user_cards,
        tweet_id=tweet_id,
        tweet_card=tweet_card,
        next_url=next_url,
        prev_url=prev_url)
