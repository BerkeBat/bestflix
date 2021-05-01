from flask import Flask, render_template, request, redirect, url_for, g, session
import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import math

logging.basicConfig(level=logging.DEBUG)
db = boto3.resource('dynamodb')
movie_table = db.Table('movie')
review_table = db.Table('review')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'

db = boto3.resource('dynamodb')
movie_table = db.Table('movie')

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/movie/<string:movieid>', methods=['GET', 'POST'])
def movie(movieid):
    if request.method == 'POST':
        review_text = request.form['reviewarea']
        review_movieid = request.form['movieid']
        review_vote = request.form['voteValue']
        post_review(review_movieid, review_text, review_vote)
    
    
    reviews = get_reviews_by_movieid(movieid)    
    movie = get_movie_by_id(movieid)
    if movie != None:
        runtime_readable = "{} hrs {} mins".format(math.floor(int(movie['runtime'])/60), int(movie['runtime'])%60)
        return render_template('movie.html', movie=movie, runtime_readable = runtime_readable, reviews = reviews)
    return render_template('movie.html', movie=movie, reviews = reviews)

@app.route('/search/<string:search_term>')
def search(search_term):
    # if request.method == 'POST':
    #     search_term = request.form['search_term']
    #     return redirect("/search/" + search_term)
    movies = query_movie(search_term)

    return render_template('search.html', movies = movies, search_term = search_term)


@app.route('/search_redirect', methods=['GET', 'POST'])
def search_redirect():
    search_term = request.form['search_term']
    return redirect("/search/" + search_term)

def post_review(movieid,review_text, vote):
    try:
        review_table.put_item(
            Item={
                'movieid': movieid,
                'user': 'test',
                'review_text': review_text,
                'vote': vote,
            }
        )
    except:
        app.logger.warning("couldn't post review")
        
def query_movie(term):
    query_filter_list = []
    movies = {}
    searchable_attributes = ['title', 'star', 'director', 'genre', 'country']
    for att in searchable_attributes:
        query_filter_list.append("Attr('{}').contains('{}')".format(att, term.lower()))
    query_filter_expression = " | ".join(f for f in query_filter_list)
    app.logger.info("berke: " + query_filter_expression)
    try:
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

if __name__ == '__main__':
  app.run(host='127.0.0.1', port=8080, debug=True)
 
