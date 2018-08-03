from pymongo import MongoClient

client = MongoClient()

db = client.citations
coll = db.journals

docs = coll.find()

for doc in docs:
    coll.update_one(
        {"id_journal":doc['id_journal']},{"$set": {"normalizedTitle":doc['main_title'].lower()}})
