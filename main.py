from flask import Flask, render_template, request, redirect, url_for, g, session
import boto3
from pycognito import Cognito
from boto3.dynamodb.conditions import Key, Attr
import logging
import math
import requests

logging.basicConfig(level=logging.DEBUG)
db = boto3.resource('dynamodb')
movie_table = db.Table('movie')
review_table = db.Table('review')
user_pool_id = "ap-southeast-2_HXX7H0jCA"
user_pool_client_id = "63k988au5jv73iubjgk5f8lqps"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cc_assignment3_bestflix'

db = boto3.resource('dynamodb')

@app.route('/', methods=['GET', 'POST'])
def index():

    return render_template('index.html')

@app.route('/movie/<string:movieid>', methods=['GET', 'POST'])
def movie(movieid):
    show_post_error = False
    if request.method == 'POST':
        review_text = request.form['reviewarea']
        review_movieid = request.form['movieid']
        review_vote = request.form['voteValue']
        if not post_review(session['username'], review_movieid, review_text, review_vote):
            show_post_error = True

    
    reviews = get_reviews_by_movieid(movieid)    
    movie = get_movie_by_id(movieid)
    if movie != None:
        runtime_readable = "{} hrs {} mins".format(math.floor(int(movie['runtime'])/60), int(movie['runtime'])%60)
        return render_template('movie.html', movie=movie, runtime_readable = runtime_readable, reviews = reviews, show_post_error=show_post_error)
    return render_template('movie.html', movie=movie, reviews = reviews)

@app.route('/search', methods=['GET', 'POST'])
def search():
    search_term = request.args.get('search_term')
    movies = query_movie(search_term)

    return render_template('search.html', movies = movies, search_term = search_term)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_user = Cognito(user_pool_id, user_pool_client_id)
        email = request.form['email']
        username = request.form['username']
        password = request.form['pass']
        try:
            new_user.set_base_attributes(email=email)
            new_user.register(username, password)
            return redirect(url_for('login'))
        except:
            app.logger.warning("error registering user.")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['pass']
            login_user = Cognito(user_pool_id, user_pool_client_id,
            username=username)
            login_user.authenticate(password=password)
            app.logger.info("berke: log in success")
            session['username'] = username
            session['logged_in'] = True
            app.logger.info("username: {}, logged_in: {}".format(session['username'], session['logged_in']))
        except:
            app.logger.warning("error logging in/authenticating user.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('logged_in', None)
    return redirect(url_for('login'))

#region helper methods
def post_review(username, movieid, review_text, vote):
    app.logger.info("will post review: {} {} {} {}".format(username, movieid, review_text, vote))
    success = False
    reviewid = "{}_{}".format(username,movieid)
    try:
        if review_table.get_item(Key={'reviewid':reviewid}) == None:
            review_table.put_item(
                Item={
                    'reviewid': reviewid,
                    'user': username,
                    'movieid': movieid,
                    'review_text': review_text,
                    'vote': vote,
                }
            )
            success = True
    except:
        app.logger.warning("couldn't post review")
    return success

def register_user():
    return
        
def query_movie(term):
    query_filter_list = []
    movies = {}
    searchable_attributes = ['title', 'star', 'director', 'genre', 'country']
    try:
        for att in searchable_attributes:
            query_filter_list.append("Attr('{}').contains('{}')".format(att, term.lower()))
        query_filter_expression = " | ".join(f for f in query_filter_list)
        movie_raw_response = db.Table('movie_searchable').scan(
            FilterExpression=eval(query_filter_expression)
        )
        movies = movie_raw_response['Items']
    except:
        app.logger.warning("movie query failed. returning empty result")
    return movies

def get_reviews_by_movieid(movieid):
    reviews = []
    try:
        review_response = review_table.scan(
            FilterExpression=Attr('movieid').eq(movieid)
        )
        reviews = review_response['Items']
    except:
        app.logger.warning("review query failed. returning empty result")
    return reviews

def get_movie_by_id(movieid):
    try:
        movie_response = movie_table.get_item(Key={'movieid':movieid})
        movie = movie_response['Item']
    except:
        movie = None


    return movie
#endregion

if __name__ == '__main__':
  app.run(host='127.0.0.1', port=8080, debug=True)
 
