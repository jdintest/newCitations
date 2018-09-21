import requests
import dateutil.parser
from bs4 import BeautifulSoup, Comment
from urllib.parse import quote
from mongoConnector import MongoConnector
#import idutils
from habanero import Crossref
from paper import Paper
import json
import time

class Citation:
        
        def __init__(self, parentObject, citationResponse, citationID):

                self.id = str(parentObject.id) + "-b" + str(citationID)
                if parentObject.type == "thesis":
                        self.handle = parentObject.handle
                        #self.item = parentObject.id
                        self.degree = parentObject.degree
                if citationResponse.get("DOI") != None:
                        self.doi = citationResponse.get("DOI")
                self.parentDate = parentObject.date
                self.citationResponse = citationResponse
                self.dataForCrossRef = ''
                #self.MongoConn = MongoConnector()

        def getCrossRefMetadata(self):
                if hasattr(self, "doi") == True:
                        c = Crossref(mailto="jdingle@brocku.ca")
                        try:
                            r = c.works(ids = [self.doi])
                            r = r['message']
            
                            self.confidenceScore = r.get("score")
                            if r.get("issued") != None:
                                    self.date = dateutil.parser.parse("-".join(str(x) for x in r.get("issued")['date-parts'][0]))
                            
                            if r.get("type") == "journal-article":
                                self.type = "journal-article"
                                self.title = r['title'][0]
                                self.containerTitle = r['container-title'][0]
                                self.issn = r['ISSN']
                            elif r.get("type") == "book-chapter":
                                self.type = "book-chapter"
                                self.title = r['title'][0]
                                self.containerTitle = r['container-title'][0]
                                self.isbn = r['ISBN']
                            elif r.get("type") == "book" or r.get("type") == "monograph":
                                self.type = "monograph"
                                self.title = r['title'][0]
                                self.isbn = r['ISBN']
                            elif r.get("type") == "proceedings-article":
                                self.type="proceedings-article"
                                self.title = r['title'][0]
                                self.containerTitle = r['container-title'][0]
                                self.isbn = r['ISBN']
                            elif r.get("type") == "reference-entry":
                                self.type = "reference-entry"
                                self.isbn = r['ISBN']
                                self.title = r['title'][0]
                                    
                            self.source = "CrossRef"

                        except:
                            pass

        def extractMetadataNoDOI(self):

            if self.citationResponse.get("source") == "Microsoft Academic":
                self.author = self.citationResponse.get("ANF")
                if self.citationResponse.get("VFN") == None and (self.citationResponse.get("BV") == None or self.citationResponse.get("BV") == ""):
                    self.type ="monograph"
                    self.title = self.citationResponse.get("DN")

                elif self.citationResponse.get("BK") != None and self.citationResponse.get("DN") != None:
                    self.containerTitle = self.citationResponse.get("BK")
                    self.title = self.citationResponse.get("DN")
                    self.type = 'book-chapter'
                    
                else:
                    self.type = "journal-article"
                    self.containerTitle = self.citationResponse.get("BV")
                    self.title = self.citationResponse.get("DN")

                self.date = dateutil.parser.parse(str(self.citationResponse.get("Y")))


            elif self.citationResponse.get("source") == "CrossRef":

                for key,value in self.citationResponse.items():
                
                    setattr(self,key,value)

                if hasattr(self,"series-title") or hasattr(self,"volume-title"):
                    self.type = "monograph"
                else:
                    self.type="journal-article"

                        

        def extractMetadataFromCitationResponse(self):

                #grobid things - different parts of the citation
                articleAnalytic = self.citationResponse.analytic
                articleMonogr = self.citationResponse.monogr
                authors = self.citationResponse("author")
                ptr = self.citationResponse("ptr")
                doi = self.citationResponse.find("idno")

                if doi != None:
                    print("idno detected") 
                    try:
                        #self.doi = idutils.normalize_doi(doi.string)
                        print("looks like it worked")
                        self.doi = doi
                        #return None
                    except:
                        print("didn't work")
                        
                
                if len(authors) > 0:

                        ##error checking
                        if authors[0].persname.surname!= None: 
                                self.dataForCrossRef += authors[0].persname.surname.string + "+" 
                        
                #get information on the monograph/journal if it exists
                if articleMonogr != None:
                        if articleMonogr.title.string != None:
                                if articleMonogr.title.attrs['level'] =='m':
                                        self.type = "monograph"
                                elif articleMonogr.title.attrs['level'] =='j':
                                        self.type = "journal"
                                self.titleMono = articleMonogr.title.string
                                self.dataForCrossRef += self.titleMono + "+"
                                
                        if articleMonogr.imprint != None :
                                try:
                                        date = articleMonogr.imprint.date.attrs['when'][:4]
                                        self.date = dateutil.parser.parse(date)
                                        self.dataForCrossRef += citation.date + "+"
                
                                except:
                                        pass

                #citation has both an analytic element and a monogr title (probably a journal article)
                        if articleAnalytic != None and articleMonogr.title != None:

                                #makes sure that title elements are not empty to avoid errors
                                if articleAnalytic.title != None and articleMonogr.title.string != None:
                                        if articleAnalytic.title.string != None:

                                                #get article/chapter title
                                                self.titleArticle = articleAnalytic.title.string
                                                self.dataForCrossRef += self.titleArticle

                        
                        
                else:
                        pass
                        
                             
        
                        
                
        def correctType(self):

                '''
                correct type of citation to "internet", based on trial and error.

                '''
                fieldsToCheck = ['titleArticle','titleMono']
                internetMatches = ["retrieved from", "available at","available from"]
                                

                for field in fieldsToCheck:
                        if field in dir(self):
                                for match in internetMatches:
                                        if getattr(self, field).lower().find(match) != -1:
                                            self.type = "internet"
                                            break
                
        


        def CrossRefSearch(self):

                '''
                takes citation from grobid, calls Crossref for doi and ISSN data

                dict -> dict
                '''
                c = Crossref(mailto = "jdingle@brocku.ca")

                if self.type in ['journal','monograph']:
                    payload = quote(str(self.dataForCrossRef))
                    r = requests.get("https://api.crossref.org/works?query=" + payload + "&mailto=jdingle@brocku.ca")
                    if r.status_code == 200:
                        firstResponse = r.json()
                        if len(firstResponse['message']['items']) > 0:
                            response = r.json()['message']['items'][0]
                            self.confidenceScore = response['score']
                            #this error threshold of 60 was determined by trial and error. It can be adjusted to be more or less conservative.
                            if self.confidenceScore > 60:
                                self.doi = response['DOI']
                                self.getCrossRefMetadata()



                
        def cleanupForOutput(self):
            del self.dataForCrossRef
            del self.citationResponse
            #del self.MongoConn
            if hasattr(self,"issn") == True:
                self.issn = list(set(self.issn))
        
        def callSFX(self):

                '''
                takes the citation, calls SFX, returns the citation with access data included

                dict -> dict
                '''

                #sfx stuff:
                SFXbaseURL = "https://sfx.scholarsportal.info/brock?"

                if hasattr(self, "date") == True and hasattr(self, "issn") == True:
                        if self.date.year < 1900: #error checking for bad dates from grobid, replaces them with a reasonable stand-in
                                   date = 2015
                        else:
                                   date = self.date.year

                        r= requests.get(SFXbaseURL + "sid=dingle_test&issn=" + self.issn[0] + "&year=" + str(date))
                        if r.status_code == 200:
                                   response = r.text

                                   soup = BeautifulSoup(response,"lxml")

                                   #SFX returns a perl object as a comment in the <head> of the response page with contains a has_full_text value
                                   #this section parses that object to return the value
                                   head = soup.head

                                   for comments in head(text = lambda text:isinstance(text, Comment)):
                                           comments.extract()
                                   commentsSoup = BeautifulSoup(comments,"lxml")
                                   contextObj = commentsSoup.ctx_object_1.string
                                   #need to error check here b/c sometimes extra <> elements in the contextObj cause errors and mean no string is returned
                                   if contextObj != None:

                                           #the string indices 23 and 26 were found by trial and error. They should remain consistent as long as SFX doesn't change.
                                           hasFullText = contextObj[contextObj.rfind("sfx.has_full_text")+23 :(contextObj.rfind("sfx.has_full_text")+ 26)]

                                           if hasFullText == "yes": #uses the SFX has_full_text value
                                                   self.access = "electronic"
                                           elif response.find("Print Collection at the Library") != -1: #searches the page as a whole for this phrase
                                                   self.access = "print"
                                           else:
                                                   self.access = "none"
                        else:
                                self.access = "unknown"
                
                else:
                        self.access = "unknown"

        def callCatalogue(self):
                if hasattr(self,"isbn"):
                        for isbn in self.isbn:
                                r = requests.get('https://catalogue.library.brocku.ca/search/a?searchtype=i&searcharg=' + str(isbn))
                                if r.status_code == 200:
                                        if r.text.find("No matches found") == -1:
                                                self.access = "Library Catalogue"
                                                break
                                        else:
                                                self.access = "none"
        def callUnpaywall(self):
                if hasattr(self,"doi"):
                        r = requests.get("https://api.unpaywall.org/v2/" + self.doi + "?email=jdingle@brocku.ca")
                        if r.status_code == 200:
                                self.isOA = r.json()['is_oa']
                                self.journalIsOA = r.json()['journal_is_oa']
                        
        def reconcileTitle(self):

                '''
                tries to match against JUP journals list, first by issn, then by exact title or abbreviation match

                '''

                journalMatch = None
                if hasattr(self,"issn") == True:
                    issns = self.issn
                    for issn in issns:
                        journalMatch = self.MongoConn.journals.find_one({"issn":issn}) 
                                
                elif hasattr(self, "titleContainer") == True:
                    title = self.titleMono
                    journalMatch = self.MongoConn.journals.find_one({"$or":[{"main_title":title},{"all_titles":title},{"abbreviation":title}]})
                
                if journalMatch != None:
                    self.journalID = journalMatch['id_journal']
                    if hasattr(self, "issn") == True:
                        self.issn.insert(0,journalMatch['normalized_issn'])
                       
                    else:
                        self.issn = [journalMatch['normalized_issn']]
                
               



c = Crossref(mailto="jdingle@brocku.ca")


headers = {"Ocp-Apim-Subscription-Key":"ba7fae63586a4942bb49403fad4009d3"}
expr="And(Composite(AA.AfN=='brock university'),Y=2018)"

r= requests.get("https://api.labs.cognitive.microsoft.com/academic/v1.0/evaluate?expr="+expr+"&model=latest&count=5&offset=171&attributes=Id,E,J.JN,C.CN,RId,F.FN,Ti,Y,D,AA.AuN,AA.AuId,AA.AfN,AA.AfId", headers=headers)

data = r.json()['entities']



for entity in data:

    paper = Paper(entity)

    print(vars(paper))
    print("")

    paper.getReferencesDOI()

    if paper.references == None:
        paper.getReferencesNoDOI()

    if paper.references != None:
        citationID = 0
        for reference in paper.references:
            time.sleep(2)
            #print(reference)
            #print("")
            citationID += 1
            reference = Citation(paper,reference,citationID)
            reference.getCrossRefMetadata()
            if hasattr(reference,"doi") == False:
                reference.extractMetadataNoDOI()
            reference.callSFX()
            reference.callUnpaywall()
            reference.callCatalogue()
            reference.cleanupForOutput()
            print(vars(reference))
            print("")
    else:
        print("no references found")
        print("")
        

    

        


                     

        
                  
