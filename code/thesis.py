import requests
from citation import Citation
import dateutil.parser
import datetime
from bs4 import BeautifulSoup, Comment
from urllib.parse import quote


class Thesis:
        def __init__(self, itemNumber):
                
                self.id = str(itemNumber)
                self.baseURL ="https://dr.library.brocku.ca/rest"
                self.allMetadata = self.getMetadata()
                self.handle = self.allMetadata['handle']
                self.degree = self.allMetadata['degree']
                self.thesisDate = self.allMetadata['thesisDate']
                self.harvestedOn = datetime.datetime.now()
        
        def getPDF(self):
                
                bitstreams = []
                r = requests.get(self.baseURL + "/items/" + str(self.id) + '/bitstreams')
                bitstreamList = r.json()
                for bitstream in bitstreamList:
                        if bitstream['mimeType'] == 'application/pdf':
                                bitstreams.append(bitstream['id'])
                if len(bitstreams) > 0:
                        r= requests.get(self.baseURL + "/bitstreams/" + str(bitstreams[0]) + "/retrieve")
                        self.pdf = r.content
                else:
                        return "not found"

        
        def getMetadata(self):
                metadata = {"item":self.id}
                r = requests.get(self.baseURL + "/items/" +str(self.id) + '/metadata')
                if r.status_code == 200:
                        response = r.json()
                        
                        for field in response:
                                if field['key'] == "dc.identifier.uri":
                                        metadata['handle'] = field['value']
                                if field['key'] == "dc.degree.name":
                                        metadata['degree']= field['value']
                                if field['key'] =="dc.date.accessioned":
                                        metadata['thesisDate'] = field['value']
                return metadata
        
                
        def callGrobid(self):
                '''
                takes a pdf bitstream and processes it with Grobid, returns a grobid TEI/xml bitstream

                bytes -> bytes

                '''
                
                url = "http://cloud.science-miner.com/grobid/api/processReferences"
                files = {"input": self.pdf}

                r = requests.post(url,files=files)
                if r.status_code == 200:
                        
                        self.grobidResponse =  r.content
                else:
                        return "failed"
        
        def filterCitations(self,citations):

                '''
                
                takes a list of citations from grobid, allows user input to filter incorrectly identified citations, returns updated list
                
                list -> list
                
                '''
                
                startIndex = 0
                stopIndex = 0

                # iterates forward until a good citation is found
                for citation in citations:
                        print(" ")
                        print(citation)
                        print(" ")

                        reply = None
                        
                        while reply not in ["y","n"]:
                                reply = input("Is this a citation? (y/n) ")
                                print(reply)

                        if reply =="y":
                                break

                        startIndex = startIndex + 1


                #iterates backward until a good citation is found
                for citation in reversed(citations):
                        print(" ")
                        print(citation)
                        print(" ")

                        reply = None
                        
                        while reply not in ["y","n"]:
                                reply = input("Is this a citation? (y/n) ")
                                print(reply)

                        if reply =="y":
                                break

                        stopIndex = stopIndex - 1
                        
                if stopIndex < 0:
                        citations = citations[:stopIndex]
                if startIndex > 0:
                        citations = citations[startIndex:]
                        
                        
                return citations
                
        
        def extractCitations(self):

                '''
                Takes a grobid TEI/xml file generated by extract.py, parses out data
                '''

                self.citations = []
                
                ## load grobid data
                soup = BeautifulSoup(self.grobidResponse, 'lxml')

                ## START PROCESSING
                citationsToFilter = soup("biblstruct")
                citations = self.filterCitations(citationsToFilter)
                

                #iterates through each citation
                for citationXML in citations:
                
                        citation = Citation(self,citationXML)

                        citation.extractMetadataFromCitationXML()

                        # uses function to identify "internet" resources
                        citation.correctType()

                        ## call CrossRef API
                        citation.callCrossRef()
                
                        ## reconcile any ISSN/title
                        #citation.reconcileTitle()
                        
                        ## call CrossRef API
                        citation.callSFX()

                        print(vars(citation))
                        self.citations.append(vars(citation))

        def updateDB(self):

                processedInsert = {"id":self.id,"handle":self.handle,"harvestedOn":self.harvestedOn}
                print(processedInsert)

                #self.MongoConn.updateCollection("processed", processedInsert, "add")

                #self.MongoConn.updateCollection("toProcess", self, "delete")

                for citation in self.citations:
                        try:
                                #self.MongoConn.updateCollection("citaitons", citation, "add")
                                print(citation['id'])
                        except:
                                pass

                        

                       



                        
