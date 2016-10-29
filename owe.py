import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
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
    images = db.images.count()
    redactions = db.redactions.count()
    return render_template('home.html', series=series, items=items, images=images, redactions=redactions)


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
    number = int(request.args.get('number', 200))
    redactions = list(db.redactions.find({'random_sample': {'$near': [random.random(), 0]}, 'width': {'$lte': 480}}).limit(number))
    total = db.redactions.count()
    return render_template('redactions.html', redactions=redactions, total=total)


@app.route('/redactions/browse/')
@app.route('/redactions/browse/<page>/')
def list_redactions(page=1):
    page = int(page)
    number = int(request.args.get('number', 100))
    sort = request.args.get('sort', 'barcode')
    start = (page - 1) * number
    db = get_db()
    redactions = list(db.redactions.find().sort(sort).skip(start).limit(number))
    total = db.redactions.count()
    return render_template('redactions.html', redactions=redactions, page=page, number=number, total=total)


@app.route('/redactions/tags/<tag>/')
@app.route('/redactions/tags/<tag>/<page>/')
def list_redactions_tags(tag, page=1):
    page = int(page)
    number = int(request.args.get('number', 100))
    sort = request.args.get('sort', 'barcode')
    start = (page - 1) * number
    db = get_db()
    redactions = list(db.redactions.find({'tags': tag}).sort(sort).skip(start).limit(number))
    total = db.redactions.find({'tags': tag}).count()
    return render_template('redactions.html', redactions=redactions, page=page, number=number, total=total, tag=tag)


@app.route('/redactions/explore/')
def browse_redactions():
    db = get_db()
    redactions = db.redactions.count()
    pipeline = [
        {
            '$group': {
                '_id': {'barcode': '$barcode', 'page': '$page'}
            }

        }
    ]
    pages = len(list(db.redactions.aggregate(pipeline)))
    pipeline = [
        {
            '$group': {
                '_id': {'barcode': '$barcode'}
            }

        }
    ]
    items = len(list(db.redactions.aggregate(pipeline)))
    return render_template('redactions_explore.html', redactions=redactions, pages=pages, items=items)


@app.route('/redactions/total/')
def highest_total_redactions():
    sort = request.args.get('sort', 'total')
    db = get_db()
    pipeline = [
        # {'$match': {'redacted': {'$exists': True}}},
        {'$group': {'_id': {'barcode': '$identifier', 'series': '$series', 'control_symbol': '$control_symbol'}, 'total': {'$sum': '$redacted.total'}, 'pages': {'$sum': 1}}},
        {'$project': {'_id': 1, 'total': 1, 'pages': 1, 'average': {'$divide': ['$total', '$pages']}}},
        {'$sort': {sort: -1}},
        {'$limit': 100}
    ]
    items = db.images.aggregate(pipeline)
    return render_template('list_redacted_total.html', items=items, sort=sort)


@app.route('/redactions/area/')
def highest_area_redactions():
    sort = request.args.get('sort', 'total')
    db = get_db()
    pipeline = [
        # {'$match': {'redacted': {'$exists': True}}},
        {'$group': {'_id': {'barcode': '$identifier', 'series': '$series', 'control_symbol': '$control_symbol'}, 'total': {'$sum': '$redacted.area'}, 'pages': {'$sum': 1}}},
        {'$project': {'_id': 1, 'total': 1, 'pages': 1, 'average': {'$divide': ['$total', '$pages']}}},
        {'$sort': {sort: -1}},
        {'$limit': 100}
    ]
    items = db.images.aggregate(pipeline)
    return render_template('list_redacted_area.html', items=items, sort=sort)


@app.route('/items/<barcode>/redactions/')
def item_redactions(barcode):
    db = get_db()
    pipeline = [
        {'$match': {'identifier': barcode}},
        {'$group': {'_id': '$identifier', 'total': {'$sum': '$redacted.total'}, 'area': {'$sum': '$redacted.area'}, 'percentage': {'$sum': '$redacted.percentage'}, 'pages': {'$sum': 1}}},
        {'$project': {'_id': 0, 'barcode': '$_id', 'total': 1, 'area': 1, 'percentage': {'$divide': ['$percentage', '$pages']}, 'pages': 1}}
    ]
    try:
        item = list(db.images.aggregate(pipeline))[0]
    except IndexError:
        item = {}
    try:
        return jsonify(item)
    except TypeError:
        return jsonify({})


@app.route('/redactions/pages/')
def highest_per_page():
    sort = request.args.get('sort', 'total')
    db = get_db()
    pages = db.images.find({'redacted': {'$exists': True}}).sort('redacted.' + sort, -1).limit(100)
    return render_template('show_redacted_pages.html', pages=pages, sort=sort)


if __name__ == '__main__':
    app.run(debug=True)
