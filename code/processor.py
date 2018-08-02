from pymongo import MongoClient

class Processor:
	def __init__(self):
		self.mongoConn = MongoConnector()
	
	def checkGrobid(self):

		# make sure grobid is running
		try:
			r = requests.get("http://localhost:8081/api/isalive")
		except:
			return "grobid not running"
			

		if r.text == "true":
			return "Grobid is working."
		else:
			return "Grobid not running. Start it and try again."
	
	def checkThesisNeedsProcessing(self.thesis):
		
		if thesis.date > mongoConn.getLastHarvestDate()
	
	
	def processThesis(self):
		#gets one thesis (by DSpace item number) from MongoDB toProcess collection
		item = repositoryFunctions.getThesisToProcess()
		#gets metadata for thesis via DSpace API
		citationResponse = repositoryFunctions.getMetadata(item)
		#locates bitstream of thesis via DSpace API
		bitstreams=repositoryFunctions.getBitstream(item)
		#tries to download pdf of thesis to process
		try:
			pdf = repositoryFunctions.downloadBitstream(bitstreams)
		except:
			repositoryFunctions.moveToFailedCollection(citationResponse)
			repositoryFunctions.deleteProcessedThesis(item)
			exit()
		#if pdf retrieved, send it to grobid for processing
		grobidResponse = extract.callGrobid(pdf)
		#checking if grobid fails
		if grobidResponse == "failed":
			repositoryFunctions.moveToFailedCollection(citationResponse)
			repositoryFunctions.deleteProcessedThesis(item)
		#if grobid doesn't fail, process the thesis and then move it to MongoDB processed collection
		else:
			citationFinal = update.extractCitations(grobidResponse, citationResponse)

			repositoryFunctions.moveToProcessedCollection(citationResponse)
			repositoryFunctions.deleteProcessedThesis(item)

