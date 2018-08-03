import requests
import dateutil.parser
from bs4 import BeautifulSoup, Comment
from urllib.parse import quote
from mongoConnector import MongoConnector
import idutils
from habanero import Crossref

class Citation:
        
        def __init__(self, parentThesis, citationXML):

                self.id = parentThesis.handle + "-" + citationXML.attrs['xml:id']
                self.handle = parentThesis.handle
                self.item = parentThesis.item
                self.degree = parentThesis.degree
                self.thesisDate = parentThesis.thesisDate
                self.citationXML = citationXML
                self.dataForCrossRef = ''
                self.type = "unknown"
                self.MongoConn = MongoConnector()

        def extractMetadataFromCitationXML(self):

                #grobid things - different parts of the citation
                articleAnalytic = self.citationXML.analytic
                articleMonogr = self.citationXML.monogr
                authors = self.citationXML("author")
                ptr = self.citationXML("ptr")
                doi = self.citationXML.find("idno")

                if doi != None:
                    print("idno detected") 
                    try:
                        self.doi = idutils.normalize_doi(doi.string)
                        print("looks like it worked")
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
                
        


        def CrossRefDOI(self):
            if hasattr(self, "doi") == True:
                c = Crossref(mailto="jdingle@brocku.ca")
                try:
                    r = c.works(ids = [self.doi])
                    r = r['message']
                    if r.get("type") == "journal-article":
                        self.type = "journal"
                        self.titleArticle = r['title'][0]
                        self.titleMono = r['container-title'][0]
                    elif r.get("type" == "book-chapter"):
                        self.type = "chapter"
                        self.titleArticle = r['title'][0]
                        self.titleMono = r['container-title'][0]
                        self.isbn = r['ISBN'][0]
                    elif r.get("type") == "book":
                        self.type = "monograph"
                        self.titleMono = r['title'][0]
                        self.isbn = r['ISBN'][0]
                    self.date = dateutil.parser.parse("-".join(r['issued']['date-parts'][0]))
                    self.confidenceScore = r['score']
                except:
                    pass


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
                                self.CrossRefDOI()



                
        def cleanupForOutput(self):
            del self.dataForCrossRef
            del self.citationXML
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
                
               


                
                  
