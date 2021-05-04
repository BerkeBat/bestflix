from threading import Condition
from flask import Flask, render_template, request, redirect, url_for, g, session
import boto3
from pycognito import Cognito
from boto3.dynamodb.conditions import Key, Attr, AttributeNotExists
import logging
import math
import requests

logging.basicConfig(level=logging.DEBUG)
db = boto3.resource('dynamodb')
movie_table = db.Table('movie')
review_table = db.Table('review')
user_table = db.Table('user')
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
    session['user']['favourites'] = get_user(session['username'])['favourites']
    if request.method == 'POST':
        if request.form['form-type'] == "review":
            review_text = request.form['reviewarea']
            review_movieid = request.form['movieid']
            review_vote = request.form['voteValue']
            if not post_review(session['username'], review_movieid, review_text, review_vote):
                show_post_error = True
        elif request.form['form-type'] == "favourite_add":
            update_favourite("add", request.form['movieid'])
        elif request.form['form-type'] == "favourite_remove":
            update_favourite("remove", request.form['movieid'])
        return redirect(request.form['callback'])
    reviews = get_reviews("movieid", movieid)    
    movie = get_movie_by_id(movieid)
    if movie != None:
        user_already_favourited = True if movie['movieid'] in session['user']['favourites'] else False
        app.logger.info(session['user']['favourites'])
        app.logger.info("already: " + str(user_already_favourited))
        runtime_readable = "{} hrs {} mins".format(math.floor(int(movie['runtime'])/60), int(movie['runtime'])%60)
        return render_template('movie.html', 
        movie=movie, runtime_readable = runtime_readable, reviews = reviews, show_post_error=show_post_error, user_already_favourited=user_already_favourited)
    return "<a href='/'><h1>Movie not found, click to return home.</h1></a>"
@app.route('/search', methods=['GET', 'POST'])
def search():
    search_term = request.args.get('search_term')
    movies = query_movie(search_term)

    return render_template('search.html', movies = movies, search_term = search_term)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['pass']
        if (register_user(email, username, password)):
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['pass']
        if(log_in_user(username, password)):
            app.logger.info("log in success")
            session['username'] = username
            session['user'] = get_user(username)
            session['logged_in'] = True
            app.logger.info("username: {}, logged_in: {}".format(session['username'], session['logged_in']))
            return redirect("/user/" + session['username'])

    return render_template('login.html')

@app.route('/user/<string:username>')
def user(username):
    user = get_user(username)
    user_favourites = get_favourites_details(user['favourites'])
    user_reviews = get_reviews("user", user['username'])
    app.logger.info("view user: " + username)
    app.logger.info(user_favourites)


    return render_template('user.html', user=user, user_favourites=user_favourites, user_reviews=user_reviews)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('logged_in', None)
    return redirect(url_for('login'))

#region helper methods
def post_review(username, movieid, review_text, vote):
    success = False
    reviewid = "{}_{}".format(username, movieid)
    app.logger.info("will post review: {} {} {}".format(reviewid, review_text, vote))
    # try:
    # if not review_table.get_item(Key={'reviewid':reviewid}):
    review_table.put_item(
        Item={
            'reviewid': reviewid,
            'user': username,
            'movieid': movieid,
            'movietitle': get_movie_by_id(movieid)['title'],
            'review_text': review_text,
            'vote': vote,
        },
        ConditionExpression="attribute_not_exists(reviewid)"
    )
    success = True
    # except:
    #     app.logger.warning("couldn't post review")
    return success

def register_user(email, username, password):
    success = False
    try:
        new_user = Cognito(user_pool_id, user_pool_client_id)
        new_user.set_base_attributes(email=email)
        new_user.register(username, password)
        user_table.put_item(
            Item={
                'username': username,
                'favourites': []
            }
        )
        success = True
    except:
        app.logger.warning("register user failed")

    return success

def log_in_user(username, password):
    success = False
    login_user = Cognito(user_pool_id, user_pool_client_id,
            username=username)
    try:
        login_user.authenticate(password=password)
        success = True
    except:
        app.logger.warning("error logging in/authenticating user.")
    return success

def update_favourite(addremove, movieid):
    user_favourites = get_user(session['username'])['favourites']
    if(addremove=="add"):
        user_favourites.append(movieid)
    elif(addremove=="remove"):
        user_favourites.remove(movieid)
    try:
        user_table.update_item(
            Key={
                'username':session['username']
            },
            UpdateExpression='SET favourites = :val',
            ExpressionAttributeValues={':val': user_favourites}
        )
    except:
        app.logger.warning("updating favourite (add/remove) failed.")
    return  

def get_favourites_details(favourites):
    movie_details_list = []
    try:
        for movie in favourites:
            movie_details_response = movie_table.get_item(Key={'movieid':movie})
            movie_details = movie_details_response['Item']
            movie_details_list.append(movie_details)
    except:
        print("Error getting favourites")
    return movie_details_list


def get_user(username):
    try:
        user_response = user_table.get_item(Key={'username':username})
        user = user_response['Item']
    except:
        user = None

    return user
def query_movie(term):
    query_filter_list = []
    movies = []
    searchable_attributes = ['title', 'star', 'director', 'genre', 'country', 'released']
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

def get_reviews(by, value):
    reviews = []
    try:
        review_response = review_table.scan(
            FilterExpression=Attr(by).eq(value)
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
 
