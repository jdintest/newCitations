import update
import extract
import repositoryFunctions
import requests
import mongoSetup
from pymongo import MongoClient

##########Config#############

communitiesList = [4,22,23] #the list of DSpace Communities which contain theses.
yearToProcess = 2017 # All theses submitted after Jan.1 of this year will be processed. Ex. setting 2014 means all theses 2014-present will be processed.


############################





	




# setup up indexes on Mongo Collections
mongoSetup.setupMongoCollections()


# search repository for theses to process and write to Mongo
repositoryFunctions.writeHandlesToMongo(communitiesList,yearToProcess)

# read from Mongo to process with Grobid

allTheses = toProcess.find().batch_size(20)

#for thesis in allTheses:

for i in range(0,20):
    processThesis() 
