import csv
from pymongo import MongoClient

#MongoDB stuff
client = MongoClient()
db = client.citations
collection = db.journals


with open('../csvupload.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        journal = collection.update_one({"id_journal":int(row['id'])},{"$set":{"abbreviation":row['abbrev']}})
        print(journal)
