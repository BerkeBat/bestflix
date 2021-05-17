from flask.helpers import flash
from dao import *
from flask import Flask, render_template, request, redirect, url_for, g, session
import logging
import math

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cc_assignment3_bestflix'


@app.route('/', methods=['GET', 'POST'])
def index():

    return render_template('index.html')


@app.route('/movie/<string:movieid>', methods=['GET', 'POST'])
def movie(movieid):

    if request.method == 'POST':
        if request.form['form-type'] == "review":
            review_text = request.form['reviewarea']
            review_movieid = request.form['movieid']
            review_vote = request.form['voteValue']
            if not post_review(session['username'], review_movieid, review_text, review_vote):
                flash("Error posting review.")
        elif request.form['form-type'] == "favourite_add":
            update_favourite("add", request.form['movieid'])
        elif request.form['form-type'] == "favourite_remove":
            update_favourite("remove", request.form['movieid'])
        return redirect(request.form['callback'])
    reviews = get_reviews("movieid", movieid)
    movie = get_movie_by_id(movieid)
    if movie != None:
        runtime_readable = get_readable_runtime(movie['runtime'])
        if session['logged_in']:
            session['user']['favourites'] = get_user(
                "dynamodb", session['username'])['favourites']
            user_already_favourited = True if movie['movieid'] in session['user']['favourites'] else False
            # app.logger.info(session['user']['favourites'])
            # app.logger.info("already: " + str(user_already_favourited))
            return render_template('movie.html', movie=movie, runtime_readable=runtime_readable, reviews=reviews, user_already_favourited=user_already_favourited)
        return render_template('movie.html', movie=movie, runtime_readable=runtime_readable, reviews=reviews)
    else:
        return "<a href='/'><h1>Movie not found, click to return home.</h1></a>"


@app.route('/search', methods=['GET', 'POST'])
def search():
    search_term = request.args.get('search_term')
    movies = query_movie(search_term)

    return render_template('search.html', movies=movies, search_term=search_term)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['pass']
        if (register_user(email, username, password)):
            return redirect(url_for('login'))
        else:
            flash("Could not register. Try a different email/username")
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['pass']
        if(log_in_user(username, password)):
            app.logger.info("log in success")
            session['username'] = username
            session['user'] = get_user("dynamodb", username)
            # session['cognito_user'] = get_user("cognito", username)
            session['logged_in'] = True
            app.logger.info("username: {}, logged_in: {}".format(
                session['username'], session['logged_in']))
            return redirect("/user/" + session['username'])
        else:
            flash("Could not login. Check correct details entered.")

    return render_template('login.html')


@app.route('/user/<string:username>', methods=['GET', 'POST'])
def user(username):
    user = get_user("dynamodb", username)
    cognito_user = get_user("cognito", username)
    user_favourites = get_favourites_details(user['favourites'])
    user_reviews = get_reviews("user", user['username'])
    verification_status = get_ses_verification_status(user['email'])
    app.logger.info("awd: " + verification_status)

    return render_template('user.html', user=user, cognito_user=cognito_user, user_favourites=user_favourites, user_reviews=user_reviews, verification_status=verification_status)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session['logged_in'] = False
    return redirect(url_for('login'))


if __name__ == '__main__':

    app.run(host='127.0.0.1', port=8080, debug=True)
