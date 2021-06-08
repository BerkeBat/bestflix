from threading import Condition
import math
import json
from flask.globals import request
from flask.helpers import flash
from dao import *
from flask import session, render_template
import boto3
from pycognito import Cognito
from boto3.dynamodb.conditions import Key, Attr
import random
import requests
import app as application


db = boto3.resource('dynamodb')
ses = boto3.client('ses')
sns = boto3.client('sns')
movie_table = db.Table('movie')
review_table = db.Table('review')
user_table = db.Table('user')

MOVIES_IN_DB = 200
user_pool_id = "ap-southeast-2_HXX7H0jCA"
user_pool_client_id = "63k988au5jv73iubjgk5f8lqps"


def post_review(username, movieid, review_text, vote, phone):
    success = False
    reviewid = "{}_{}".format(username, movieid)
    try:
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
        flash("Error posting review")
    else:
        send_review_email(get_user("dynamodb", username),
                          get_movie_by_id(movieid), get_review_by_id(reviewid))
        if phone != "":
            send_review_notification(get_user("dynamodb", username),
                                     get_movie_by_id(movieid), get_review_by_id(reviewid), phone)
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
                'email': email,
                'favourites': []
            }
        )
        success = True
    except:
        # print("register user failed", file=sys.stderr)
        flash("Error registering user.")

    else:
        send_ses_verification_email(email)
    return success


def log_in_user(username, password):
    success = False
    login_user = Cognito(user_pool_id, user_pool_client_id,
                         username=username)
    try:
        login_user.authenticate(password=password)
        success = True
    except:
        # print("error logging in/authenticating user.", file=sys.stderr)
        flash("Error authenticating user.")
    return success


def update_favourite(addremove, movieid):
    user_favourites = get_user("dynamodb", session['username'])['favourites']
    if(addremove == "add"):
        user_favourites.append(movieid)
    elif(addremove == "remove"):
        user_favourites.remove(movieid)
    try:
        user_table.update_item(
            Key={
                'username': session['username']
            },
            UpdateExpression='SET favourites = :val',
            ExpressionAttributeValues={':val': user_favourites}
        )
    except:
        # print("updating favourite (add/remove) failed.", file=sys.stderr)
        flash("Error upading favourite.")
    return


def get_favourites_details(favourites):
    movie_details_list = []
    try:
        for movie in favourites:
            movie_details_response = movie_table.get_item(
                Key={'movieid': movie})
            movie_details = movie_details_response['Item']
            movie_details_list.append(movie_details)
    except:
        flash("Error getting favourites")
    return movie_details_list


def get_user(service, username):
    try:
        if service == "dynamodb":
            user_response = user_table.get_item(Key={'username': username})
            user = user_response['Item']
        elif service == "cognito":
            # TODO returns none, get_users() works
            user_to_get = Cognito(
                user_pool_id, user_pool_client_id, username=username)
            user = user_to_get.get_user_obj(username=username,
                                            attribute_list=[
                                                {'Name': 'string', 'Email': 'string'}, ],
                                            attr_map={"email": "email"})
    except:
        user = None

    return user


def query_movie(term):
    query_filter_list = []
    movies = []
    searchable_attributes = ['title', 'star', 'director',
                             'genre', 'country', 'released', 'classification']
    try:
        for att in searchable_attributes:
            query_filter_list.append(
                "Attr('{}').contains('{}')".format(att, term.lower()))
        query_filter_expression = " | ".join(f for f in query_filter_list)
        movie_raw_response = db.Table('movie_searchable').scan(
            FilterExpression=eval(query_filter_expression)
        )
        movies = movie_raw_response['Items']
    except:
        # print("movie query failed. returning empty result")
        flash("Error querying movies.")
    return movies


def get_reviews(by, value):
    reviews = []
    try:
        review_response = review_table.scan(
            FilterExpression=Attr(by).eq(value)
        )
        reviews = review_response['Items']
    except:
        # print("review query failed. returning empty result", file=sys.stderr)
        flash("Error getting reviews.")
    return reviews


def get_review_by_id(reviewid):
    try:
        review_response = review_table.get_item(Key={'reviewid': reviewid})
        review = review_response['Item']
    except:
        review = None

    return review


def get_reviews_api(movieid):
    # data = {"movieid": '"' + movieid + '"'}
    # # r = requests.post(
    # #     'https://86k2j27yf4.execute-api.ap-southeast-2.amazonaws.com/get-reviews', json={"body": json.loads(str(data))})

    # # r = requests.get(
    # # "https://86k2j27yf4.execute-api.ap-southeast-2.amazonaws.com/get-reviews/" + movieid)
    # return r.json()
    return None


def get_movie_by_id(movieid):
    try:
        movie_response = movie_table.get_item(Key={'movieid': movieid})
        movie = movie_response['Item']
    except:
        movie = None

    return movie


def get_ses_verification_status(email):
    try:
        verification_attributes_response = ses.get_identity_verification_attributes(
            Identities=[
                email,
            ]
        )
    except:
        flash("Error getting verification status")
    else:
        try:
            return verification_attributes_response['VerificationAttributes'][email]['VerificationStatus']
        except:
            return "Error"


def send_ses_verification_email(email):
    try:
        ses.verify_email_identity(
            EmailAddress=email
        )
    except:
        flash("Error sending verification email")


def send_review_email(user, movie, review):
    recipient = user['email']
    email_subject = f"{user['username']}, thanks for your review on {movie['title']}"
    email_body = render_template(
        'email.html', user=user, movie=movie, review=review)
    try:
        ses.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': email_subject,
                },
            },
            Source="berkecloudcomputing@gmail.com",
        )
    except:
        flash("Error sending review email.")


def send_review_notification(user, movie, review, phone):
    topic_name = 'Movie_Review'
    sns.create_topic(Name=topic_name)
    message = f'''Hi { user['username'] },
                Thank you for your review on { movie['title'] }.\n
                Here's what you wrote:\n
                "{ review['review_text'] }"\n\n
                You voted this movie: { review['vote'] }\n\n
                We hope you enjoy BestFlix!\n\n
                Kind Regards,\n
                BestFlix'''
    sns.publish(PhoneNumber=phone, Message=message)


def get_readable_runtime(runtime):
    hours = math.floor(int(runtime)/60)
    mins = int(runtime) % 60
    return "{} hrs {} mins".format(hours, mins)


def get_random_movies(count):
    movies = []
    for i in range(count):
        movie = str(random.randint(1, MOVIES_IN_DB))
        if len(movie) == 1:
            movie = "00" + movie
        elif len(movie) == 2:
            movie = "0" + movie
        if movie not in movies:
            movies.append(movie)

    return movies
