import json
from habanero import Crossref

class Paper:

    def __init__(self, entity):

        self.metadata = json.loads(entity['E'])
        self.references = None
        self.doi = self.metadata.get("DOI")
        self.entity = entity
        self.id = entity['Id']
        self.date = entity.get("D")
        self.authors = entity.get("AA")
        self.field = entity.get("F")
        self.type="paper"

       
    def getReferencesDOI(self):

        if self.doi != None:
            c = Crossref(mailto="jdingle@brocku.ca")
            
            try:
                response = c.works(ids = [self.doi])
                response = response['message']
            except:
                print("something went wrong")
                pass
            
            self.work_type = response.get("type")
            self.references = response.get("reference")

            if self.references != None:
                citations = []            
                for reference in self.references:

                    citations.append(self.processReference(reference,"CrossRef"))

                self.references = citations
            
    def getReferencesNoDOI(self):

        if self.metadata.get("PR") != None:
            self.references = self.metadata.get("PR")
            
        elif self.entity.get("RId") != None:
            self.references = self.entity.get("RId")
            
        citations = []
        if self.references != None:
    
            for reference in self.references:
                time.sleep(5)
                
                expr="Id=" + str(reference)
                

                r= requests.get("https://api.labs.cognitive.microsoft.com/academic/v1.0/evaluate?expr="+expr+"&model=latest&attributes=E,Ti,Y,J.JN,C.CN", headers=headers)
                MsAcademicData = r.json()['entities']

                for entity in MsAcademicData:
                    citations.append(self.processReference(entity,"Microsoft Academic"))                  
                    

        if len(citations)>0:
            self.references = citations

    def processReference(self,citation,source):

        if source == "Microsoft Academic":
            response = json.loads(citation['E'])
            response['source'] = "Microsoft Academic"
            if citation.get("Y") != None:
                response['Y'] = citation.get("Y")

            return response
            
        elif source == "CrossRef":
            response = citation
            response['source'] = "CrossRef"

            return response

        else:
            print("not a valid source")

