import requests
from thesis import Thesis
import dateutil.parser
from mongoConnector import MongoConnector
import time


class Repository:
        
        def __init__(self):
                self.baseURL = "https://dr.library.brocku.ca/rest"
                self.communities = ['4','22','23'] # communities which contain theses in Brock DSpace
                self.collections = self.getAllCollections() # all collections which contain theses
                self.mongoConn = MongoConnector()
                #self.highestProcessedID = int(self.mongoConn.getHighestItem())
                #self.LastHarvestDate = self.MongoConn.getLastHarvest() 

        def harvest(self, lastHarvestDate):
                allTheses = []

                for collection in self.collections:
                        theses = self.getTheses(collection)
                        for thesis_item in theses:
                                time.sleep(1)
                                try:
                                    thesis = Thesis(thesis_item)
                                except:
                                    print("something went wrong")
                                    break
                                if dateutil.parser.parse(thesis.thesisDate) >= dateutil.parser.parse(str(lastHarvestDate) + "-01-01T00:00:00Z "):
                                        doc = {"item":thesis_item,"handle":thesis.handle}
                                        print("Writing to Mongo...")
                                        try:
                                            self.mongoConn.updateCollection("toProcess","add",doc)
                                        except:
                                            print("failed. already in collection")
                                        print(doc)

        def harvestSinceLastProcessed(self):
                allTheses = []

                for collection in self.collections:
                        theses = self.getTheses(collection)
                        for thesis_item in theses:
                                if thesis_item > self.highestProcessedID:
                                        doc = {"item":thesis_item}
                                        print(doc)
                                        print("Writing to Mongo...")
                                        try:
                                            self.mongoConn.updateCollection("toProcess","add",doc)
                                        except:
                                            print("Failed. Item already in processing queue.")
                                else:
                                    break


        def getCollections(self, community):
                
                '''
                receives a DSpace community ID, returns a list of collections in the community
                int -> list

                '''

                headers = {"accept":"application/json"}
                r = requests.get(self.baseURL + "/communities/" + str(community) + "/collections",headers=headers)
                theses = r.json()
                collections = []
                
                for item in theses:
                        collections.append(item['id'])

                return collections
        
        def getAllCollections(self):
                allCollections = []

                for community in self.communities:
                        collectionsInCommunity = self.getCollections(community)
                        for collection in collectionsInCommunity:
                                allCollections.append(collection)

                return allCollections
        
        def getTheses(self,collection):
                headers = {"accept":"application/json"}
                r = requests.get(self.baseURL + "/collections/" + str(collection)+ "/items?limit=1500",headers=headers)
                theses = r.json()
           
                theses = sorted(theses, key=lambda k:k['id'], reverse=True)

                theses_ids = []

                for thesis in theses:
                        theses_ids.append(thesis['id'])
                
                return theses_ids

