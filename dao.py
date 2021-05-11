from threading import Condition
from dao import *
from flask import session
import boto3
from pycognito import Cognito
from boto3.dynamodb.conditions import Key, Attr, AttributeNotExists
import sys

db = boto3.resource('dynamodb')
movie_table = db.Table('movie')
review_table = db.Table('review')
user_table = db.Table('user')

user_pool_id = "ap-southeast-2_HXX7H0jCA"
user_pool_client_id = "63k988au5jv73iubjgk5f8lqps"

def post_review(username, movieid, review_text, vote):
    success = False
    reviewid = "{}_{}".format(username, movieid)
    print("will post review: {} {} {}".format(reviewid, review_text, vote), file=sys.stderr)
    try:
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
        )
    except:
        print("couldn't post review", file=sys.stderr)
    success = True
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
        print("register user failed", file=sys.stderr)

    return success

def log_in_user(username, password):
    success = False
    login_user = Cognito(user_pool_id, user_pool_client_id,
            username=username)
    try:
        login_user.authenticate(password=password)
        success = True
    except:
        print("error logging in/authenticating user.", file=sys.stderr)
    return success

def update_favourite(addremove, movieid):
    user_favourites = get_user("dynamodb", session['username'])['favourites']
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
        print("updating favourite (add/remove) failed.", file=sys.stderr)
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

def get_user(service, username):
    try:
        if service == "dynamodb":
            user_response = user_table.get_item(Key={'username':username})
            user = user_response['Item']
        elif service == "cognito":
            #TODO returns none, get_users() works
            user_to_get = Cognito(user_pool_id, user_pool_client_id, username=username)
            user = user_to_get.get_user_obj()
    except:
        user = None

    return user
def query_movie(term):
    query_filter_list = []
    movies = []
    searchable_attributes = ['title', 'star', 'director', 'genre', 'country', 'released', 'classification']
    try:
        for att in searchable_attributes:
            query_filter_list.append("Attr('{}').contains('{}')".format(att, term.lower()))
        query_filter_expression = " | ".join(f for f in query_filter_list)
        movie_raw_response = db.Table('movie_searchable').scan(
            FilterExpression=eval(query_filter_expression)
        )
        movies = movie_raw_response['Items']
    except:
        print("movie query failed. returning empty result")
    return movies

def get_reviews(by, value):
    reviews = []
    try:
        review_response = review_table.scan(
            FilterExpression=Attr(by).eq(value)
        )
        reviews = review_response['Items']
    except:
        print("review query failed. returning empty result", file=sys.stderr)
    return reviews

def get_movie_by_id(movieid):
    try:
        movie_response = movie_table.get_item(Key={'movieid':movieid})
        movie = movie_response['Item']
    except:
        movie = None


    return movie