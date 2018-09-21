import requests
#from thesis import Thesis
from citation import Paper
import dateutil.parser
from mongoConnector import MongoConnector
import time


class MSAcademic:
        
        def __init__(self):
                self.baseURL = "https://api.labs.cognitive.microsoft.com/academic/v1.0/evaluate?expr=And(Composite(AA.AfN=='brock university'),Y=2018)&model=latest&count=100&offset=0&orderby=D:desc&attributes=Id,E,J.JN,C.CN,RId,F.FN,Ti,Y,D,AA.AuN,AA.AuId,AA.AfN,AA.AfId"
                self.headers = {"Ocp-Apim-Subscription-Key":"ba7fae63586a4942bb49403fad4009d3"}
                self.mongoConn = MongoConnector()
                #self.highestProcessedID = int(self.mongoConn.getHighestItem())
                #self.LastHarvestDate = self.MongoConn.getLastHarvest() 

        def harvest(self):
                allPapers = []

                r = requests.get(self.baseURL, headers=self.headers)

                papers = r.json()['entities']

                print(len(papers))

                for paper in papers:
                        paper = Paper(paper)

                        doc = {"id":"MS" + str(paper.id)}
                        print("Writing to Mongo...")
                        try:
                                self.mongoConn.updateCollection("toProcess","add",doc)
                        except:
                                print("failed. already in collection")
                        print(doc)
