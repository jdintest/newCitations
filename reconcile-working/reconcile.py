"""
An example reconciliation service API for Google Refine 2.0.

See http://code.google.com/p/google-refine/wiki/ReconciliationServiceApi.
"""
import re
from pymongo import MongoClient
import callSFX

#For scoring results
from fuzzywuzzy import fuzz
from operator import itemgetter

from flask import Flask, request, jsonify, json
app = Flask(__name__)


## MongoDB stuff

conn = MongoClient()
db = conn.citations
collection = db.journals

# Basic service metadata. There are a number of other documented options
# but this is all we need for a simple service.
metadata = {
    "name": "Journal Reconciliation",
    "defaultTypes": {"id": "http://purl.org/ontology/bibo/Periodical", "name": "bibo:Periodical"}
}

# The data we'll match against.
journal_data = []
journals = collection.find({},{"id_journal":1,"main_title":1,"abbreviation":1,"_id":0}).batch_size(500)
for journal in journals:
    journal_data.append(journal)


def search(query,type):
    """
    Do a fuzzy match on Journals in MongoDB journals collection, returning results in
    Refine reconciliation API format. 
    
    The type parameter determines if the match is on main_title or abbreviation 
    
    For now, only exact matches are automatically matched, but this can be adjusted.
"""
    out = []
    query = query.lower()
    for item in journal_data:
        id_journal = item.get("id_journal","no_id")
        titleOrAbbrev = str(item.get(type,"nothing_found"))
        if titleOrAbbrev.lower() == query:
            match = True
        else:
            match = False

        #Construct a score using FuzzyWuzzy's token set ratio.
        #https://github.com/seatgeek/fuzzywuzzy
        score = fuzz.token_sort_ratio(query, titleOrAbbrev)
        out.append({
            "id": id_journal,
            "name": titleOrAbbrev,
            "score": score,
            "match": match,
            "type": [
                {
                    "id": "http://purl.org/ontology/bibo/Periodical",
                    "name": "bibo:Periodical",
                }
            ]
        })
    #Sort this list by score
    sorted_out = sorted(out, key=itemgetter('score'), reverse=True)
    return sorted_out[:10]

def jsonpify(obj):
    """
    Like jsonify but wraps result in a JSONP callback if a 'callback'
    query param is supplied.
    """
    try:
        callback = request.args['callback']
        response = app.make_response("%s(%s)" % (callback, json.dumps(obj)))
        response.mimetype = "text/javascript"
        return response
    except KeyError:
        return jsonify(obj)


def reconcile(reconType):
    #Look first for form-param requests.
    query = request.form.get('query')
    if query is None:
        #Then normal get param.s
        query = request.args.get('query')
    if query:
        # If the 'query' param starts with a "{" then it is a JSON object
        # with the search string as the 'query' member. Otherwise,
        # the 'query' param is the search string itself.
        if query.startswith("{"):
            query = json.loads(query)['query']
        results = search(query,reconType)
        return jsonpify({"result": results})
    # If a 'queries' parameter is supplied then it is a dictionary
    # of (key, query) pairs representing a batch of queries. We
    # should return a dictionary of (key, results) pairs.
    queries = request.form.get('queries')
    if queries:
        queries = json.loads(queries)
        results = {}
        for (key, query) in queries.items():
            results[key] = {"result": search(query['query'],reconType)}
        return jsonpify(results)

    # If neither a 'query' nor 'queries' parameter is supplied then
    # we should return the service metadata.
    return jsonpify(metadata)



@app.route("/reconcileTitles", methods=['POST', 'GET'])
def reconTitles():
    return reconcile("main_title")


@app.route("/reconcileAbbreviations", methods=['POST', 'GET'])
def reconAbbreviations():
    return reconcile("abbreviation")

@app.route("/callSFX", methods=['POST', 'GET'])
def returnAccess():
    #Look first for form-param requests.
    issn = request.form.get('issn')
    if issn is None:
        #Then normal get param.s
        issn = request.args.get('issn')
    date = request.form.get('date')
    if date is None:
        date = request.args.get('date')

    return callSFX.callSFX(issn, date)



if __name__ == '__main__':
    app.run(host='0.0.0.0')
