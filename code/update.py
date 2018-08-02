from bs4 import BeautifulSoup, Comment
import requests
import extract
from pymongo import MongoClient
import dateutil.parser
import cleanup 

#MongoDB stuff
client = MongoClient()
db = client.citations
collection = db.citations


## Stuff for crossref API
crossref_prefix = "http://api.crossref.org/works?"


def extractCitations(fileName, metadata):

    '''
    Takes a grobid TEI/xml file generated by extract.py, parses out data
    '''

    
    ## load grobid data
    soup = BeautifulSoup(fileName, 'lxml')

    ## START PROCESSING
    citationsToFilter = soup("biblstruct")
    #citations = extract.filterCitations(citationsToFilter)
    citations = citationsToFilter

    #iterates through each citation
    for citation in citations:
        #dict to be returned w/ citation info
        citationResponse = {}

        citationResponse['id'] = metadata['handle'] + "-" + citation.attrs['xml:id']
        citationResponse['handle'] = metadata['handle']
        citationResponse['degree'] = metadata['degree']
        citationResponse['thesisDate'] = dateutil.parser.parse(metadata['thesisDate'])

        #data to be sent to crossref
        payload=""

        #grobid things - different parts of the citation
        articleAnalytic = citation.analytic
        articleMonogr = citation.monogr
        authors = citation("author")

        if len(authors) > 0:

            ##error checking
            if authors[0].persname.surname!= None: 
                payload = payload + authors[0].persname.surname.string + "+" 
        
        #get information on the monograph/journal if it exists
        if articleMonogr != None:
            if articleMonogr.title.string != None:
                if articleMonogr.title.attrs['level'] =='m':
                    citationResponse['type'] = "monograph"
                elif articleMonogr.title.attrs['level'] =='j':
                    citationResponse['type'] = "journal"
                citationResponse['titleMono'] = articleMonogr.title.string
                payload = payload + citationResponse['titleMono'] +"+"
            
            if articleMonogr.imprint != None :
                try:
                    date = articleMonogr.imprint.date.attrs['when'][:4]
                    citationResponse['date'] = dateutil.parser.parse(date)
                    payload= payload + citationResponse['date'] + "+"
        
                except:
                    pass                    
                
        #citation has both an analytic element and a monogr title (probably a journal article)
            if articleAnalytic != None and articleMonogr.title != None:

                #makes sure that title elements are not empty to avoid errors
                if articleAnalytic.title.string != None and articleMonogr.title.string != None:

                    #get article/chapter title
                    citationResponse['titleArticle'] = articleAnalytic.title.string
                    payload = payload + citationResponse['titleArticle']

                   
        
        else:
            pass

        citationResponse['payload'] = payload

        # uses function to identify "internet" resources
        citationResponse = extract.correctType(citationResponse)

        ## call CrossRef API
        citationResponse = extract.callCrossRef(citationResponse)
	
        ## reconcile any missing ISSN data using reconcile-csv service
        citationResponse = cleanup.reconcileTitle(citationResponse)


        # actually write the citation data to Mongo
        try:
            insertObj = collection.insert_one(citationResponse)
            print(citationResponse['id'])
        except:
            pass
