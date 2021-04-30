from flask import Flask, render_template, request, redirect, url_for, g
import boto3
from boto3.dynamodb.conditions import Key, Attr

app = Flask(__name__)

db = boto3.resource('dynamodb')
movie_table = db.Table('movie')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/movie/<string:movieid>')
def movie(movieid):
    movie = get_movie_by_id(movieid)
    return render_template('movie.html', movie=movie)


def get_movie_by_id(movieid):
    try:
        movie_response = movie_table.get_item(Key={'movieid':movieid})
        movie = movie_response['Item']
    except:
        movie = None

    return movie

if __name__ == '__main__':
  app.run(host='127.0.0.1', port=8080, debug=True)
 
