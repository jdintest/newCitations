from thesis import Thesis
from repository import Repository
from citation import Citation

from mongoConnector import MongoConnector
from pymongo import MongoClient
from bs4 import BeautifulSoup, Comment
import dateutil.parser
import requests

#starts by defining repo
repo = Repository()

#setup Mongo connection and ensure indexes are created
mongoConn = MongoConnector()
mongoConn.setupCollections()

#harvest theses from 2018, store IDs in Mongo to be processed
repo.harvest(2013)

#process a batch of theses
#ProcessTheses(20)

def ProcessThesis():

        failed = None
        thesis_item = mongoConn.getThesisToProcess()

        thesis = Thesis(thesis_item)
        
        try:
                thesis.getBitstream()
        except:
                failed = "getting bitstream"
                
        try:
                thesis.callGrobid()
        except:
                failed = "Grobid problem"
                
        try:
                thesis.extractCitations()
        except:
                failed = "extracting citations"
                

        try:
                thesis.updateDB()
        except:
                failed = "updating database"
        
        
        if failed != None:
                mongoConn.updateCollection('failed', 'add', thesis)
                print("failed at : " + failed)
        else:
                
                mongoConn.updateCollection('processed', 'add', thesis)
                print("success! processed " + thesis.handle)

        mongoConn.updateCollection('toProcess', 'delete', thesis)
        

        
        
