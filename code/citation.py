import requests
import dateutil.parser
from bs4 import BeautifulSoup, Comment
from urllib.parse import quote
from mongoConnector import MongoConnector
#import idutils
from habanero import Crossref

class Citation:
        
        def __init__(self, parentObject, citationResponse, citationID):

                self.id = str(parentObject.id) + str(citationID)
                if parentObject.type == "thesis":
                        self.handle = parentObject.handle
                        #self.item = parentObject.id
                        self.degree = parentObject.degree
                if citationResponse.get("DOI") != None:
                        self.doi = citationResponse.get("DOI")
                self.parentDate = parentObject.date
                self.citationResponse = citationResponse
                self.dataForCrossRef = ''
                self.type = "unknown"
                self.MongoConn = MongoConnector()

        def getCrossRefMetadata(self):
                if hasattr(self, "doi") == True:
                        c = Crossref(mailto="jdingle@brocku.ca")
                        try:
                            r = c.works(ids = [self.doi])
                            r = r['message']
            
                            self.date = r.get("issued") #fix this at some point to parse date
                            self.confidenceScore = r.get("score")
                            
                            if r.get("type") == "journal-article":
                                self.type = "journal-article"
                                self.titleArticle = r['title'][0]
                                self.titleMono = r['container-title'][0]
                                self.issn = r['ISSN']
                            elif r.get("type") == "book-chapter":
                                self.type = "chapter"
                                self.titleArticle = r['title'][0]
                                self.titleMono = r['container-title'][0]
                                self.isbn = r['ISBN']
                            elif r.get("type") == "book":
                                self.type = "monograph"
                                self.titleMono = r['title'][0]
                                self.isbn = r['ISBN']
                            elif r.get("type") == "proceedings-article":
                                self.type="proceedings"
                                self.titleArticle = r['title'][0]
                                self.titleMono = r['container-title'][0]
                                self.isbn = r['ISBN']
                            self.source = "CrossRef"

                        except:
                            pass

        def extractMetadataNoDOI(self):

            if self.source == "Microsoft Academic":
                self.author = citationResponse.get("ANF")
                if citationResponse.get("VFN") == None and (citationResponse.get("BV") == None or citationResponse.get("BV") == ""):
                    self.type ="monograph"
                    self.titleMono = citationResponse.get("DN")

                elif citationResponse.get("BK") != None and citationResponse.get("DN") != None:
                    self.titleMono = citationResponse.get("BK")
                    self.titleArticle = citationResponse.get("DN")
                    self.type = 'book-chapter'
                    
                else:
                    self.type = "journal-article"
                    self.titleMono = citationResponse.get("BV")
                    self.titleArticle = citationResponse.get("DN")

                self.date = citationResponse.get("Y")

            elif self.source == "CrossRef":

                for key,value in citationResponse.items():
                    #print(key,value)
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
                        self.doi = idutils.normalize_doi(doi.string)
                        print("looks like it worked")
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
            del self.MongoConn
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
                if hasattr(self,"ISBN"):
                        for isbn in self.isbn:
                                r = requests.get('https://catalogue.library.brocku.ca/search/a?searchtype=i&searcharg=' + str(isbn))
                                if r.status_code == 200:
                                        if r.text.find("No matches found") == -1:
                                                self.access = "Library Catalogue"
                                                break
                

                        
        def reconcileTitle(self):

                '''
                tries to match against JUP journals list, first by issn, then by exact title or abbreviation match

                '''

                journalMatch = None
                if hasattr(self,"issn") == True:
                    issns = self.issn
                    for issn in issns:
                        journalMatch = self.MongoConn.journals.find_one({"issn":issn}) 
                                
                elif hasattr(self, "titleMono") == True:
                    title = self.titleMono
                    journalMatch = self.MongoConn.journals.find_one({"$or":[{"main_title":title},{"all_titles":title},{"abbreviation":title}]})
                
                if journalMatch != None:
                    self.journalID = journalMatch['id_journal']
                    if hasattr(self, "issn") == True:
                        self.issn.insert(0,journalMatch['normalized_issn'])
                       
                    else:
                        self.issn = [journalMatch['normalized_issn']]
                
               




        
                  
