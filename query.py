from __future__ import unicode_literals
from collections import namedtuple

from httplib2 import Http
import xml.etree.ElementTree as ET
import crslookup as CRSLookup
import re
from lxml import html

from time import strftime

import sqlite3

DO_CACHING = False
LOG_QUERIES = False
LOG_FILE =  "log/queries.log"

def setupCacheDB():
    QUERY_CACHE = sqlite3.connect("query_cache.db")
    QUERY_CACHE.execute("DROP TABLE IF EXISTS cache")
    QUERY_CACHE.execute("CREATE TABLE cache (url text, response blob)")
        
def logQuery(url,action):
    if(not LOG_QUERIES):
        return
    
    p = re.compile('(serialssolutions.com/api/[^/]+/)', re.IGNORECASE)
    url = p.sub('serialssolutions.com/api/UNIQUE_KEY/', url)
    
    with open(LOG_FILE, "a") as logFile:
        logFile.write(strftime("%Y-%m-%d %H:%M:%S") + "    " + action + "    " + url+"\n")
    
def makeRequest(url,nocache=False,overrideCache=False):
    # check cache
    if(DO_CACHING and not nocache and not overrideCache):
        QUERY_CACHE = sqlite3.connect("query_cache.db")
        try:
            result = QUERY_CACHE.execute("SELECT * FROM cache WHERE url=?",(url,))
        except sqlite3.OperationalError:
            # database isn't set up yet
            setupCacheDB()
            result = QUERY_CACHE.execute("SELECT * FROM cache WHERE url=?",(url,))
        cachedResponse = result.fetchone()
        if(cachedResponse is not None):   
            logQuery(url,"CACHE")
            QUERY_CACHE.commit()
            QUERY_CACHE.close()
            return str(cachedResponse[1])
    
    # not in cache/don't cache
    h = Http()
    response = h.request(url, headers={'Accept':'application/xml'})
    
    logQuery(url,"QUERY")
    
    # update cache
    if(DO_CACHING and not nocache):
        QUERY_CACHE.execute("DELETE FROM cache WHERE url=?",(url,))
        QUERY_CACHE.execute("INSERT INTO cache VALUES (?,?)",(url,sqlite3.Binary(response[1])))
        QUERY_CACHE.commit()
        QUERY_CACHE.close()
    
    return response[1]
    
def test_fake_find_publications(first,last):
    fakeResults = []
    fakeResults.append({"Title":"Computational Analysis of Phosphopeptide Binding to the Polo-Box Domain of the Mitotic Kinase PLK1 Using Molecular Dynamics Simulation"})
    fakeResults.append({"Title":"Correlations and beam splitters for quantum Hall anyons"})
    fakeResults.append({"Title":"Optical flux lattices for two-photon dressed states"})
    fakeResults.append({"Title":"Soft-phonon instability in zincblende HgSe and HgTe under moderate pressure: Ab initio pseudopotential calculations"})
    fakeResults.append({"Title":"Towards crystal structure prediction of complex organic compounds, a report on the fifth blind test"})
    fakeResults.append({"Title":"Designing Topological Bands in Reciprocal Space"})
    fakeResults.append({"Title":"Computational searches for iron carbide in the Earth's inner core"})
    fakeResults.append({"Title":"Evaluating Boundary Dependent Errors in QM/MM Simulations"})
    fakeResults.append({"Title":"Ligand Discrimination in Myoglobin from Linear-Scaling DFT+"})
    fakeResults.append({"Title":"Optical Flux Lattices for Ultracold Atomic Gases"})
    return fakeResults

# Symplectic - not implemented
    
def _sym_do_query(method,request):

    pass
    
def find_sym_id_of_researcher(firstName,lastName): 
    # GET /users?query=firstName+lastName
    pass

def find_sym_id_of_grant(grantID): 
    # GET /grants?query=grantID
    pass

def find_sym_id_of_pub(pubID): 
    # GET /publications?query=pubID
    pass
    
def find_sym_publications_by_researcher(researcherID):
    # GET /users/{id}/publications
    pass

def find_sym_pub_grant_links(researcherID):
    # GET /users/username-{username}/suggestions/relationships/pending
    # GET /users/username-{username}/suggestions/relationships
    pass

def sym_pub_grant_link(publicationID, grantID, addAndconfirm=False):
    # POST <import-user-relationship/> /relationships
    pass
    
def sym_researcher_grant_link(researcherID, grantID,addAndconfirm=False):
    # POST <import-user-relationship/> /relationships
    pass
    
def sym_confirm_link(linkID):
    # POST <accept/> /suggestions/relationships/{id}
    pass
    
# Look up
    
def find_grants_by_crs(crsID,orgName,OrgCode):
    fullName = find_full_name_by_crs(crsID)
    firstLastName = _crs_name_to_first_last(fullName)
    #print(firstLastName["FirstName"] + " - " + firstLastName["LastName"])
    return find_grants_by_first_last(firstLastName["FirstName"],firstLastName["LastName"], orgName, OrgCode)

def find_grants_by_first_last(firstName,lastName,orgName,orgCode):

    """Return a list of grants for a researcher by first and last name.
    Look up grants using GtR {http://gtr.rcuk.ac.uk/api},
    and copyright on Juliet
    
    Arguments:
        firstName:  the first name of the researcher. Can contain other 
                    initials to search for.
        lastName:   the surname of the researcher. Must be matched exactly
                    in any result.
        orgName:    the researcher's organisation, used to increase search
                    accuracy (but never matched)
        orgCode:    the GtR organisation id of the researcher's 
                    organisation. Must be matched 
    
    Returns:
        A list of Grants, each one matching the given first and last name
    Raises:
        NoResultError: The researcher can't be found on GtR
        XMLChildNotFoundError: The XML from GtR or Juliet did not have the expected nodes
        ET.ParseError: The XML was not able to be read.
    """
    
    researcher = None
    
    try:
        researchers = find_person_by_name(firstName,lastName,orgName,orgCode)
        
    except ET.ParseError:
        print("ParseError when attempting to search")
        raise
    except NoResultError:
        print("Researcher not found")
        raise
    
    projectsOutput = []
    
    try: 
        for researcher in researchers:
            projects = find_grants_by_researcher(researcher)
            for project in projects:
                projectsOutput.append(project)
            
            # if(len(projects) > 0):
                ## prevent multiple queries to get the same copyright info
                # cachedFunders = {}
                # for project in projects:
                    # try:
                        # projectCopyright = cachedFunders[project["ProjectFunder"]]
                    # except KeyError:
                        # try:
                            # copyrightResult = find_organisation_juliet_policy(project["ProjectFunder"])
                            # projectCopyright = "{3}: Found strengths- OAA: {0}, OAP: {1}, DA: {2}".format(copyrightResult["OAA"],copyrightResult["OAP"],copyrightResult["DA"],project["ProjectFunder"])
                        # except NotFoundError:
                            # projectCopyright = "Unable to find copyright policy for {0}".format(project["ProjectFunder"])
                        # cachedFunders[project["ProjectFunder"]] = projectCopyright
                            
                    # project["CopyrightInfo"] = "Check disabled" #projectCopyright
                    # project["Researcher"] = researcher
                    # projectsOutput.append(project)
    except ET.ParseError:
        print("ParseError when getting project list")
        raise
    
    return projectsOutput

# CRS Lookup

def find_full_name_by_crs(crsID):
    lu = CRSLookup.Lookup()
    with lu:
        user = lu.get_user(crsID)
    if(user is not None):
        return user.name
    else:
        raise NoResultError

# GTR - finding grants

def find_grants_by_title(grantTitle,orgName,orgCode):

    """Return a list of grants by title
    
    Arguments:
        grantTitle: the title to search for.
        orgName:    the researcher's organisation, used to increase search
                    accuracy (but never matched)
        orgCode:    the GtR organisation id of the researcher's 
                    organisation. Must be matched (default to Cambridge)
    
    Returns:
        A list of Projects. Some information is always returned as "?"
        (the GtR XML response does not contain these fields for this search)
    """
    url = "http://gtr.rcuk.ac.uk/search/project.xml?term={0}+{1}".format(grantTitle.replace(" ","+"),orgName)
    response = makeRequest(url)
    
    # get response
    root = ET.fromstring(response)
    
    projectList = _get_child_by_path(root,"results").getchildren()
    
    projectListOutput = []
    
    # loop through
    for elem in projectList:
        projectRoot = _get_child_by_path(elem,"projectComposition")
        
        leadResearchOrgCode = _get_child_by_path(projectRoot,"leadResearchOrganisation/id").text
        projectID = _get_child_by_path(projectRoot,"project/id").text
        projectName = _get_child_by_path(projectRoot,"project/title").text
        projectFunder = _get_child_by_path(projectRoot,"project/fund/funder/name").text
        # this isn't in this search
        #grantReference = _get_child_by_path(projectRoot,"project/grantReference").text
        #projectStatus = _get_child_by_path(projectRoot,"project/status").text
        
        poundValue = _get_child_by_path(projectRoot,"project/fund/valuePounds").text
        startDate = _get_child_by_path(projectRoot,"project/fund/start").text
        endDate = _get_child_by_path(projectRoot,"project/fund/end").text
        
        if(leadResearchOrgCode == orgCode):
            grant = Grant(projectID,projectName)
            grant.addFunding(projectFunder,"?",poundValue,"?")
            grant.addResearcher("?","?")
            grant.addDates(startDate,endDate)
            
            projectListOutput.append(grant)
    
    return projectListOutput

def match_person_by_name(looseMatch,peopleList,firstName,lastName,orgName,orgCode):

    """Match a first/last name pair against a list of people and return the first match
    
    Arguments:
        looseMatch: Whether to match loosely or not. A loose match 
                    matches whenever any part of the first name matches,
                    including by initial (ie, Fred R. Smith will 
                    loosely match Richard Smith, as the R will be matched
                    to the Richard). The last name must always be an
                    exact match. This will create some false positives,
                    as Richard Smith will loosely match Roderick Smith, so
                    a non-loose match should be run first.
        peopleList: A list of people, each with Organisation (the 
                    organisation code), ID, FirstName and LastName
        firstName:  The first name of the researcher to match
        lastName:   The last name of the researcher to match
        orgCode:    The GtR organisation ID to match (default to Cambridge)
    Returns:
        A list, where each element is a Researcher representing someone who matched
    Raises:
        NoResultError: Nobody was found who matches the researcher
    """

    outputPeople = []
    for person in peopleList:
        personOrg = person["Organisation"]
        personID = person["ID"]
        personFirst = person["FirstName"]
        personLast = person["LastName"]
    
        # perform checks
        firstNameMatch = (personFirst.lower() == firstName.lower() or
                        (looseMatch and personFirst[:1].lower() == firstName[:1].lower()) or
                        (looseMatch and firstName == ""))
        
        # Split up first name by . and (space) and match each 
        # part (eg match things like John A. Smith to John Smith).
        # This can also resolve situations where a researcher 
        # publishes under their middle name, as it will match
        # Fred J. Smith to John Smith.
        
        if(looseMatch and not firstNameMatch and (firstName.find(" ") != -1 or firstName.find(".") != -1)):
            firstNameParts = firstName.lower().replace("."," ").split(" ")
            for part in firstNameParts:
                if(len(part)>0):
                    firstNameMatch = firstNameMatch or (part == personFirst[:len(part)].lower())

        orgCodeMatch = personOrg == orgCode
        lastNameMatch = personLast.lower() == lastName.lower()
    
        # check if person matches
        if(firstNameMatch and lastNameMatch and orgCodeMatch):
            outputPerson = Researcher(person["FirstName"],person["LastName"],person["ID"],looseMatch,orgName,orgCode)
            outputPeople.append(outputPerson)
            
    return outputPeople

def find_person_by_name(firstName,lastName,orgName,orgCode):

    """Perform a GtR search to find researchers
    
    Arguments:
        firstName:  The first name to look up (as match_person_by_name)
        lastName:   The last name to look up
        orgName:    The organisation name, used to improve the search
        orgCode:    The organisation GtR ID, which must match that of the organisation (default is Cambridge)
    Returns:
        A list of Researchers representing people who matched
    Raises:
        NoResultError: Nobody was found who matches the researcher
    """
    
    # perform a gtr search of the form first+last+organisation
    
    url = "http://gtr.rcuk.ac.uk/search/person?term={0}+{1}+{2}".format(firstName.replace(" ","+"),lastName.replace(" ","+"),orgName)
    response = makeRequest(url)
    
    # get response
    root = ET.fromstring(response)
    
    # get people list
    peopleXML = _get_child_by_path(root,"results").getchildren()
    peopleList = []
    
    # read out XML data into a list
    for personOverview in peopleXML:
        person = _get_child_by_path(personOverview,"person")
        organisation = _get_child_by_path(personOverview,"organisation")
    
        personOrg = ''
        if(_get_child_by_path(organisation,"id") != None):
            personOrg = _get_child_by_path(organisation,"id").text

        personID = ''
        if(_get_child_by_path(person,"id") != None):
            personID = _get_child_by_path(person,"id").text

        personFirst = ''
        if(_get_child_by_path(person,"firstName") != None):
            personFirst = _get_child_by_path(person,"firstName").text

        personLast = ''
        if(_get_child_by_path(person,"surname") != None):
            personLast = _get_child_by_path(person,"surname").text
        
        peopleList.append({"FirstName":personFirst,"LastName":personLast,"ID":personID,"Organisation":personOrg})

    outputPeople = []    
    # try precise matching
    try:
        outputPeople += match_person_by_name(False,peopleList,firstName,lastName,orgName,orgCode)
    except NoResultError:
        pass

    try:
        looselyMatchedPeople = match_person_by_name(True,peopleList,firstName,lastName,orgName,orgCode)
        
        # add these people, avoiding duplicates
        for person in looselyMatchedPeople:
            unique = True
            for person2 in outputPeople:
                if(person.GtRID == person2.GtRID):
                    # already have them
                    break
            else:
                outputPeople.append(person)
    except NoResultError:
        pass

    if(not outputPeople):
        raise NoResultError
        
    return outputPeople

def find_grants_by_researcher(researcher):

    """Return a list of grants for a given researcher, using their GtR ID
    
    Arguments:
        researcher: The Researcher to get the GtR ID of, for example 721A5E95-7046-5284-993E-F5E39E665A9F
                        (the ID can be found as the last part of their url on GtR)
    Returns:
        A list of Grants
    """

    researcherId = researcher.GtRID
    
    url = "http://gtr.rcuk.ac.uk/person/{0}".format(researcherId)
    response = makeRequest(url)

    # get response
    root = ET.fromstring(response)
    projectList = _get_child_by_path(root,"projectSearchResult/results").getchildren()
    projectListOutput = []
    
    # loop through 
    for proElem in projectList:
        elem = _get_child_by_path(proElem, "projectComposition")
        projectElem = _get_child_by_path(elem,"project")
        
        projectID = _get_child_by_path(projectElem,"id").text
        projectName = _get_child_by_path(projectElem,"title").text
        projectFunder = _get_child_by_path(projectElem,"fund/funder/name").text
        grantReference = ""#_get_child_by_path(projectElem,"grantReference").text
        projectStatus = ""#_get_child_by_path(projectElem,"status").text
    
        poundValue = _get_child_by_path(projectElem,"fund/valuePounds").text
        startDate = _get_child_by_path(projectElem,"fund/start").text
        endDate = _get_child_by_path(projectElem,"fund/end").text
            
        grant = Grant(projectID,projectName)
        grant.addFunding(projectFunder,grantReference,poundValue,projectStatus)
        grant.addDates(startDate,endDate)
        
        # Find their role
        role = "";
        
        # Check if the project has a peopleList filled with collaborators
        
        if(_get_child_by_path(elem,"personRoles") != None):
            peopleList = _get_child_by_path(elem,"personRoles").getchildren()
    
            for person in peopleList:
                personId = _get_child_by_path(person,"id").text
                personRole = _get_child_by_path(person,"roles/role/name").text
                if(personId == researcherId):
                    if(personRole == "PRINCIPAL_INVESTIGATOR"):
                        role = "PI"
                        grant.addResearcher(researcher,role)
                        break;
                    if(personRole == "CO_INVESTIGATOR"):
                        role = "CI"
                        break;
                grant.addResearcher(researcher,role)
        if(role==""):
            role = "CI"
        grant.addResearcher(researcher,role)
            
        projectListOutput.append(grant)
        
        
    return projectListOutput


# Juliet - finding copyright information    

def find_organisation_juliet_policy(searchName):
    """Look up an organisation on JULIET and return their Open Access policy
    
    Arguments:
        searchName: The name to look for on Juliet (normally an acronym like BBSRC)
    Returns:
        A dict containing OAA, OAP and DA, which are the Juliet-assigned strengths
        of Open Access Archiving, Open Accesss Publishing and Data Archiving requirements
    Raises:
        NoResultError: Nobody was found who matches the researcher      
    """
    #h = Http()
    #response = h.request()
    url = "http://www.sherpa.ac.uk/juliet/api-epsilon.php?name={0}".format(searchName)
    response = makeRequest(url)
    
    # get response
    root = ET.fromstring(response)
    
    # get organisation list
    organisations = _get_child_by_path_noprefix(root,"funderlist").getchildren()
    
    # pick appropriate organisation
    # attempt to find which is correct by looking for a perfect match in either name
    for org in organisations:
        name1 = _get_child_by_path_noprefix(org,"fundernamelist/fundername/name_preferred").text
        name2 = _get_child_by_path_noprefix(org,"fundernamelist/fundername/name_alternative").text
        if(name1 == searchName or name2 == searchName):
            organisation = org
            break
    else:
        # no obvious matches
        raise NoResultError
    
    orgName = _get_child_by_path_noprefix(organisation,"fundernamelist/fundername/name_preferred")
    
    # get policies
    oaArchivingStrength = _get_child_by_path_noprefix(organisation,"pubspolicy/openaccessarchiving/mandate").get("strength")
    oaPublishingStrength = _get_child_by_path_noprefix(organisation,"pubspolicy/openaccesspublishing/mandate").get("strength")
    dataArchivingStrength = _get_child_by_path_noprefix(organisation,"datapolicy/openaccessarchiving/mandate").get("strength")
    
    return {"OAA":oaArchivingStrength,"OAP":oaPublishingStrength,"DA":dataArchivingStrength}

# RoMEO - finding copyright information for journals

def find_organisation_romeo_policy(searchISSN):
    romeoBaseUrl = "http://www.sherpa.ac.uk/romeo/api29.php?issn="
        
    #h = Http()
    #response = h.request(romeoBaseUrl + searchISSN)
    url = romeoBaseUrl + searchISSN
    response = makeRequest(url)
    
    root = ET.fromstring(response)
    
    try:
        # get organisation list
        journalDetails = _get_child_by_path_noprefix(root,"journals/journal")
        publisherDetails = _get_child_by_path_noprefix(root,"publishers/publisher")
        
        # journal data
        zetocPublisher = _get_child_by_path_noprefix(journalDetails,"zetocpub").text
        romeoPublisher = _get_child_by_path_noprefix(journalDetails,"romeopub").text
        
        # publisher data
        publisherName = _get_child_by_path_noprefix(publisherDetails,"name").text
        romeoColour = _get_child_by_path_noprefix(publisherDetails,"romeocolour").text
    except XMLChildNotFoundError:
        raise NoResultError("The journal with ISSN "+searchISSN+" could not be found on RoMEO")
    
    
    return {"zetocpub":zetocPublisher,"romeopub":romeoPublisher,"publisher":publisherName,"romeocolour":romeoColour}
  
# DOAJ - finding subject information for oa journals

def find_journal_DOAJ_subjects(searchISSN):
    doajBaseURL = "http://www.doaj.org/oai?verb=GetRecord&metadataPrefix=oai_dc&identifier=doaj.org:"
        
    response = makeRequest(doajBaseURL+searchISSN)
    
    root = ET.fromstring(response)

    # check if it's in their database
    try:
        x = _get_child_by_path_doaj(root,"error")
        raise NoResultError("Unable to find a DOAJ entry for ISSN "+searchISSN)
    except XMLChildNotFoundError:
        pass
    
    # get the subjects
    subjectXML = _get_child_by_path_doaj(root,"GetRecord/record/metadata")[0].findall("{http://purl.org/dc/elements/1.1/}subject")
    
    subjectList = []
    
    for subject in subjectXML:
        subjectList.append(subject.text)
        
    return subjectList

# Wikipedia html scrape

def find_journal_wiki_info(searchName):
    wikiBaseSearch = "http://en.wikipedia.org/w/index.php?action=edit&title="
    wikiExtraSearch = "_(journal)"
       
    # get html
    response = makeRequest(wikiBaseSearch+searchName.replace(" ","_"))
    data = html.document_fromstring(response)

    # "verify"
    if("Wikipedia does not have an article with this exact name" in data.text_content()):
        raise NoResultError("Wikipedia does not recognise journal "+searchName+" (no page)")
    
    # "check" for disambiguation page
    if("(disambiguation)" in data.text_content()):
        response = makeRequest(wikiBaseSearch+searchName.replace(" ","_")+wikiExtraSearch)
        data = html.document_fromstring(response)
    
    # parse html
    try:
        page = data.get_element_by_id("wpTextbox1").text_content()
    except KeyError:
        response = makeRequest(wikiBaseSearch+searchName.replace(" ","_")+wikiExtraSearch)
        data = html.document_fromstring(response)
        
    if("Wikipedia does not have an article with this exact name" in data.text_content()):
        raise NoResultError("Wikipedia does not recognise journal "+searchName+" (disambiguation)")
        
    try:
        page = data.get_element_by_id("wpTextbox1").text_content()
    except KeyError:
        raise NoResultError("Wikipedia does not recognise journal "+searchName+" (unexpected layout)")
    
    # scrapedData = []
    # for row in info_table:
        # try:
            # if("colspan" not in row[0].attrib): # otherwise it's a header
                # scrapedData.append((row[0].text_content(),row[1].text_content()))
        # except IndexError:
            # pass
            
    scrapedData = {}
    subpage = page[page.find("{{Infobox")+9:]
    info_table = subpage[:subpage.find("}}")].replace("\u2013","-").replace("\n","").split("| ")

    for row in info_table:
        if(row.find("<!--") != -1):
            row = row[:row.find("<!--")]
        
        data = row.replace("\t"," ").split("= ")
        try:
            scrapedData[data[0].replace(" ","").replace("\t","")] = data[1].replace("[","").replace("]","")
        except IndexError:
            pass
            
    # image? - doesn't work from the edit page
    image = None
    # try:
        # image = info_table.find_class("image")[0][0].attrib["src"]
        # image = "http://"+image[2:]
    # except IndexError:
        # pass
    
    # format data
    returnData = {}
    for scraped in scrapedData:
        if(scraped == "discipline"):
            returnData["Discipline"] = capitalise_first_words(scrapedData[scraped])
        if(scraped == "publisher"):
            returnData["Publisher"] = scrapedData[scraped]
        if(scraped == "frequency"):
            returnData["Frequency"] = scrapedData[scraped]
        if(scraped == "impact"):
            returnData["Impact Factor"] = scrapedData[scraped].replace(" ","")
        if(scraped == "history"):
            returnData["PublishHistory"] = scrapedData[scraped]
        if(scraped == "ISSN"):
            returnData["ISSN"] = scrapedData[scraped]
        if(scraped == "eISSN"):
            returnData["eISSN"] = scrapedData[scraped]
    
    if(image is not None):
        returnData["Image"] = image
    
    return returnData
    
# WorldCat Classify API

def find_journal_holdings_from_worldcat(journalISSN):

    baseURL = "http://classify.oclc.org/classify2/Classify?summary=true&issn="
    response = makeRequest(baseURL+journalISSN)
    data = ET.fromstring(response)

    try:
        results = _get_child_by_path(data,"work","{http://classify.oclc.org}")
        topResult = results

    except XMLChildNotFoundError:
        # probably more than one work...
        try: 
            worksList = _get_child_by_path(data,"works","{http://classify.oclc.org}")
            results = worksList.getchildren()
            topResult = results[0]

        except XMLChildNotFoundError:
            raise NoResultError("Journal "+journalISSN+" not found on WorldCat Classify")
        except IndexError:        
            raise NoResultError("Journal "+journalISSN+" not found on WorldCat Classify")        
    if (topResult):    
        resultData = topResult.attrib
        return {"Holdings":int(resultData["holdings"])}

    return {"Holdings": None}
    
# search.lib.cam.ac.uk API

def find_journal_cam_availability(journalISSN):

    print '\n\r[query.py] find_journal_cam_availability'

    baseURL = "http://search.lib.cam.ac.uk/sru.ashx?operation=searchRetrieve&version=1.1&maximumRecords=10&recordSchema=dc&query=format:journal%20"
    
    response = makeRequest(baseURL+journalISSN)
    data = ET.fromstring(response)
    
    ns = "{http://www.loc.gov/zing/srw/}"
    
    recordList = _get_child_by_path(data,"records",ns)
    record = recordList[0]
    branchList = _get_child_by_path(record,"extraRecordData",ns)
    
    branches = []
    
    for b in branchList:
        if(b.tag == "branch"):
            branches.append(b.text)
    
    return branches
   
# ulrichsweb

def find_journal_ulrichsweb_info(journalISSN,ULRICHS_KEY):

    print '[query.py] find_journal_ulrichsweb_info'

    baseURL = "http://ulrichsweb.serialssolutions.com/api/"+ULRICHS_KEY+"/search?query=issn:"
    
    #urlich TOU 3.v
    response = makeRequest(baseURL+journalISSN,nocache=True)
    data = ET.fromstring(response)
    
    status = _get_child_by_path_noprefix(data,"status").text
    rowCount = _get_child_by_path_noprefix(data,"numberOfRecords").text
    
    if(status == "Error"):
        errorMessage = _get_child_by_path_noprefix(data,"statusMessage").text
        raise NoResultError("UlrichsWeb error: "+errorMessage)
        
    if(int(rowCount) < 1):
        raise NoResultError("Journal "+journalISSN+" not found on Ulrichsweb")
    
    # if(int(rowCount) > 1):
        # raise NoResultError("Journal "+journalISSN+" ambiguous on Ulrichsweb (too many results)")
        
    results = _get_child_by_path_noprefix(data,"results")
    result = results[0]
    
    refereed = _get_child_text_if_exists(result,"refereed") == "true"
    openAccess = _get_child_text_if_exists(result,"openAccess") == "true"
    reviewed = _get_child_text_if_exists(result,"reviewed") == "true"
    active = _get_child_text_if_exists(result,"status") == "Active"
    description = _get_child_text_if_exists(result,"description")
    country = _get_child_text_if_exists(result,"country")
    frequency = _get_child_text_if_exists(result,"frequency")
    availableOnline = _get_child_text_if_exists(result,"availableOnline") == "true"
    title = _get_child_text_if_exists(result,"title")
    
    return {
        "Active":active,
        "Description":description,
        "Refereed":refereed,
        "OpenAccess":openAccess,
        "Reviewed":reviewed,
        "Country":country,
        "Frequency":frequency,
        "AvailableOnline":availableOnline,
        "Title":title
    }
    

 
def capitalise_first_words(string):
    string = string[:1].upper() + string[1:]
    words = string.split(" ")
    capWords = []
    for word in words: 
        if(word in "and|or|of|with|for"):
            capWords.append(word)
        else:
            capWords.append(word[:1].upper() + word[1:])
    return " ".join(capWords)
    
def crs_name_to_first_last(crsName):
    """ Names from the crs lookup are typically formatted:
        (Title) I. FirstName MiddleName Multiple-Word-Surname
        
        - Remove Title if present
        - Use final word as surname, replacing "-" with " " (space)
        - Use remainder as first name or initials
    """
    nameArray = crsName.split(" ")
    
    title = ""
    firstName = ""
    lastName = ""
    
    if(nameArray[0] == "Prof" or nameArray[0] == "Dr"):
        title = nameArray[0]
        nameArray.pop(0)
    
    lastName = nameArray.pop().replace("-"," ")
    
    firstName = " ".join(nameArray)
    
    return {"Title":title,"FirstName":firstName,"LastName":lastName}
    
def _lookup_researcher(firstName,lastName,orgName,orgCode):
    """Look up a researcher using GtR, first using exact matching and then using loose matching."""
    result = find_grants_by_first_last(firstName,lastName, orgName, orgCode)
    for project in result:
        print ("{0} funded: {1}".format(project.ProjectFunder,project.ProjectName))

def _get_child_text_if_exists(element,path,namePrefix=""):
    """Get the text of a child node of an XML element by following a path.
        Return None if there is an xml error """
    try:
        return _get_child_by_path(element,path,namePrefix).text
    except XMLChildNotFoundError:
        return None
    
def _get_child_by_path(element,path,namePrefix="{http://gtr.rcuk.ac.uk/api}"):
    """Get the child node of an XML element by following a path. All node names are prefixed with namePrefix"""

    pathChildren = path.split('/')
    for childName in pathChildren:
        if(element.tag == namePrefix + childName):
            return element
        element = element.find(namePrefix + childName)
    return element
    
def _get_child_by_path_doaj(element,path,namePrefix="{http://www.openarchives.org/OAI/2.0/}"):
    """Get the child node of an XML element by following a path. All node names are prefixed with namePrefix"""
    return _get_child_by_path(element,path,namePrefix)
    
def _get_child_by_path_noprefix(element,path):
    """Get a child node of an XML element by following a path. No prefix is used"""
    return _get_child_by_path(element,path,"")

class Error(Exception):
    """Base error class"""
    pass
    
class NoResultError(Error):
    """The search returned no matching results"""
    pass
    
class XMLChildNotFoundError(Error):
    """The XML node did not have the requested child. May mean the XML document has changed format"""
    pass

class Grant:
    GtRID = ""
    ProjectName = ""
    ProjectFunder = ""
    Status = ""
    GrantReference = ""
    StartDate = ""
    EndDate = ""
    PoundValue = 0
    
    Researcher = ""
    Role = ""
    
    def __init__(self,GtRID,ProjectName):
        self.GtRID = GtRID
        self.ProjectName = ProjectName
    
    def addFunding(self,ProjectFunder,GrantReference,PoundValue,Status):
        self.ProjectFunder = ProjectFunder
        self.GrantReference = GrantReference
        self.PoundValue = PoundValue
        self.Status = Status
        
    def addResearcher(self,Researcher,Role):
        self.Researcher = Researcher
        self.Role = Role
        
    def addDates(self,StartDate,EndDate):
        self.StartDate = StartDate
        self.EndDate = EndDate

class Researcher:
    FirstName = ""
    LastName = ""
    Organisation = ""
    OrgCode = ""
    
    LooseMatched = False
    GtRID = ""
        
    def __init__(self,FirstName,LastName,GtRID="",LooseMatched=False, orgname="", orgcode=""):
        self.FirstName = FirstName
        self.LastName = LastName
        self.GtRID = GtRID
        self.LooseMatched = LooseMatched
        self.Organisation = orgname
        self.OrgCode = orgcode
        