from pymongo import MongoClient

class MongoConnector:

        def __init__(self):
                self.client = MongoClient()
                self.db = self.client.citations
                self.citations = self.db.citations
                self.journals = self.db.journals
                self.toProcess = self.db.toProcess
                self.processed = self.db.processed
                self.failed = self.db.failed

        def updateCollection(self, collection, action, item ):

                if action == "add":
                        getattr(self, collection).insert(item)
                elif action == "delete":
                        getattr(self,collection).remove({'id':item['id']})
                
        def setupCollections(self):
                self.citations.create_index("id",unique=True)
                self.toProcess.create_index("handle",unique=True)

                print("Indexes created")
        
        def getThesisToProcess(self):

                collection = self.toProcess
                item = collection.find_one()['item']

                return item
        
        def getHighestItem(self):

                return self.processed.find_one(sort=[("item",-1)])['item']
                        

        def writeHandlesToMongo(communities,year):

                for community in communities:
                        collections = getCollections(community)
                        for collection in collections:
                                theses = getTheses(collection)
                                try:
                                        getSinceDate(theses,year)
                                except:
                                        continue
