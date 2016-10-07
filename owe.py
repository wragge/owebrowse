import os
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.son import SON
from flask_paginate import Pagination
import random

MONGOLAB_URL = os.environ['MONGOLAB_URL']

app = Flask(__name__)


def get_db():
    dbclient = MongoClient(MONGOLAB_URL)
    db = dbclient.get_default_database()
    return db


@app.route('/')
def home():
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$series"}}
    ]
    series = len(list(db.items.aggregate(pipeline)))
    items = db.items.find({'digitised_status': True}).count()
    images = db.images.find().count()
    return render_template('home.html', series=series, items=items, images=images)


@app.route('/series/')
def list_series():
    pipeline = [
        {"$group": {"_id": "$series", "total": {"$sum": 1}, "digitised": {"$sum": {"$cond": ["$digitised_status", 1, 0]}}}},
        {"$project": {"_id": 0, "series": "$_id", "total": "$total", "digitised": "$digitised"}},

        {"$sort": {"series": 1}}
    ]
    db = get_db()
    series = list(db.items.aggregate(pipeline))
    print series
    return render_template('list_series.html', series=series)


@app.route('/series/<identifier>/')
def show_series(identifier, start=None):
    series = identifier.replace('-', '/')
    db = get_db()
    digitised = db.items.find({'series': series, 'digitised_status': True}).count()
    items = db.items.find({'series': series}).count()
    images = db.images.find({'series': series}).count()
    return render_template('show_series.html', series=series, items=items, digitised=digitised, images=images)


@app.route('/series/<identifier>/browse/')
def browse_series(identifier):
    start = request.args.get('start', None)
    series = identifier.replace('-', '/')
    db = get_db()
    if start:
        items = list(db.items.find({'series': series, 'digitised_status': True, 'control_symbol': {'$gte': start}}).sort('control_symbol', ASCENDING).limit(11))
        previous = list(db.items.find({'series': series, 'digitised_status': True, 'control_symbol': {'$lt': start}}).sort('control_symbol', DESCENDING).limit(10))
        try:
            previous = previous[-1]['control_symbol']
        except IndexError:
            previous = None
    else:
        items = list(db.items.find({'series': series, 'digitised_status': True}).sort('control_symbol', ASCENDING).limit(11))
        previous = None
    next = items.pop()
    next = next['control_symbol']
    for item in items:
        item['images'] = db.images.find({'identifier': item['identifier']}).sort('page', ASCENDING)
    return render_template('browse_series.html', series=series, items=items, previous=previous, next=next)


@app.route('/items/<identifier>/')
def show_item(identifier):
    db = get_db()
    item = db.items.find_one({'identifier': identifier})
    images = db.images.find({'identifier': identifier}).sort('page', 1)
    series = item['series']
    control = item['control_symbol']
    next = db.items.find({'series': series, 'control_symbol': {'$gt': control}, 'digitised_status': True}).sort('control_symbol', ASCENDING).limit(1)
    try:
        next_item = next.next()
    except StopIteration:
        next_item = None
    previous = db.items.find({'series': series, 'control_symbol': {'$lt': control}, 'digitised_status': True}).sort('control_symbol', DESCENDING).limit(1)
    try:
        previous_item = previous.next()
    except StopIteration:
        previous_item = None

    return render_template('show_item.html', item=item, images=images, next_item=next_item, previous_item=previous_item)


@app.route('/items/<identifier>/pages/<page>/')
def show_page(identifier, page):
    db = get_db()
    page = int(page)
    item = db.items.find_one({'identifier': identifier})
    image = db.images.find_one({'identifier': identifier, 'page': page})
    next = db.images.find({'identifier': identifier, 'page': {'$gt': page}}).sort('page', ASCENDING).limit(1)
    try:
        next_page = next.next()
    except StopIteration:
        next_page = None
    previous = db.images.find({'identifier': identifier, 'page': {'$lt': page}}).sort('page', DESCENDING).limit(1)
    try:
        previous_page = previous.next()
    except StopIteration:
        previous_page = None

    return render_template('show_page.html', item=item, image=image, next_page=next_page, previous_page=previous_page)


@app.route('/browse/')
def browse():
    series = request.args.get('series', None)
    print series
    if not series:
        return redirect(url_for('list_series'))
    else:
        control = request.args.get('control', None)
        db = get_db()
        if control:
            items = db.items.find({'series': series, 'control_symbol': control, 'digitised_status': True}).limit(1)
        else:
            items = db.items.find({'series': series, 'digitised_status': True}).sort('control_symbol', ASCENDING).limit(1)
        item = items[0]
        identifier = item['identifier']
    return redirect('/items/{}/'.format(identifier))


@app.route('/redactions/')
def redactions():
    db = get_db()
    redactions = list(db.redactions.find({'random_sample': {'$near': [random.random(), 0]}, 'width': {'$lte': 500}}).limit(500))
    return render_template('redactions.html', redactions=redactions)


@app.route('/redactions/<page>')
def browse_redactions():
    page = int(request.args.get('page', 1))
    number = int(request.args.get('number', 200))
    start = (page - 1) * number
    page += 1
    db = get_db()
    redactions = list(db.redactions.find({'width': {'$lte': 500}}).sort('random_id').skip(start).limit(number))
    return render_template('redactions.html', redactions=redactions, page=page)



if __name__ == '__main__':
    app.run(debug=True)