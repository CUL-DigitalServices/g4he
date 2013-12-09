from __future__ import unicode_literals
from lxml import html
from httplib2 import Http
import query
import difflib
import json

# used to make fake API responses pre-implementation
from random import randint

import sqlite3

# uses the data from http://www.scimagojr.com/journalrank.php
# this data uses , instead of . in numbers
# precise request url http://www.scimagojr.com/journalrank.php?category=0&area=0&year=2011&country=&order=sjr&page=0&min=0&min_type=cd&out=xls
# http://www.scimagojr.com/howtocite.php

def _str_to_num(str):
    str = str.replace(",",".")
    try:
        return int(str)
    except ValueError:
        return float(str)
        
def _fix_issn_import(str):
    str = str.replace("=","");
    str = str.replace("\"","");
    str = str[0:4]+"-"+str[4:]
    return str

def _make_database():
    data = importData();
    
    database = sqlite3.connect("journal_data.db")
    
    database.execute("DROP TABLE IF EXISTS journals")                    
    database.execute("CREATE TABLE journals (name text, country text, issn text, rank_sjr real, rank_hindex real, rank_citeperdoc real)")
    
    for journal in data:
        journalName = journal["name"]
        journalCountry = journal["country"]
        journalISSN = journal["issn"]
        ranking_sjr = journal["rank_sjr"]
        ranking_hindex = journal["rank_hindex"]
        ranking_citeperdoc = journal["rank_citeperdoc"]
        database.execute("INSERT INTO journals VALUES (?,?,?,?,?,?)",(journalName,journalCountry,journalISSN,ranking_sjr,ranking_hindex,ranking_citeperdoc))
    
    database.commit()
    database.close()
    
def find_journal_by_identifier(identifierKey,identifier):
    database = sqlite3.connect("journal_data.db")
    if(identifierKey=="ISSN"):
        result = database.execute("SELECT * FROM journals WHERE issn=?",(identifier,))
    else:
        result = database.execute("SELECT * FROM journals WHERE name=?",(identifier,))
    data = result.fetchone()
    database.close()
    
    if(data is None):
        raise DataNotFound
    
    return data
    
def find_journal_by_name(searchName):

    # get any matches
    nameWords = searchName.lower().split(" ")
    
    wordQueries = []
    for word in nameWords:
        if(len(word) > 3):
            wordQueries.append("%"+word[0:-3]+"%")
        
    database = sqlite3.connect("journal_data.db")
    queryString = "name like ? OR "*(len(wordQueries)-1) +" name like ?"
    result = database.execute("SELECT * FROM journals WHERE "+queryString, tuple(wordQueries))
    data = result.fetchall()
    database.close()
    
    results = []
    
    for journal in data:
        journalWords = journal[0].lower().split(" ")
        journalScore = -len(journalWords)*0.1
        for nword in nameWords:
            for jword in journalWords:
                ratio = difflib.SequenceMatcher(None,jword,nword).ratio()
                if(ratio>0.75):
                    journalScore += ratio + 0.1
                    #print(journal["name"] + " ("+jword+", "+nword+")")
                    break
        if(journalScore/len(nameWords) > 0.5):
            results.append((journal[0],journalScore/len(nameWords)))
    def getscore(r): return r[1]
    
    return sorted(results,key=getscore,reverse=True)
    
def find_journal_by_name_slow(searchName):
    # get all the data to search through in python
    database = sqlite3.connect("journal_data.db")
    result = database.execute("SELECT * FROM journals")
    data = result.fetchall()
    database.close()
    
    nameWords = searchName.lower().split(" ")
    
    results = []
    
    for journal in data:
        journalWords = journal[0].lower().split(" ")
        journalScore = -len(journalWords)*0.1
        for nword in nameWords:
            for jword in journalWords:
                ratio = difflib.SequenceMatcher(None,jword,nword).ratio()
                if(ratio>0.75):
                    journalScore += ratio + 0.1
                    #print(journal["name"] + " ("+jword+", "+nword+")")
                    break
        if(journalScore/len(nameWords) > 0.5):
            results.append((journal[0],journalScore/len(nameWords)))
    def getscore(r): return r[1]
    
    return sorted(results,key=getscore,reverse=True)

def importData():
    data = html.parse("excelexport.html")
    rows = data.findall("body/table/tbody/tr")

    outputData = []
    
    for row in rows:
        try:
            journalName = row[1].text
            journalCountry = row[12].text
            journalISSN = _fix_issn_import(row[2].text)
            ranking_sjr = _str_to_num(row[3].text)
            ranking_hindex = _str_to_num(row[4].text)
            ranking_citeperdoc = _str_to_num(row[10].text)
            outputData.append({"name":journalName,"country":journalCountry,"issn":journalISSN,
                                "rank_sjr":ranking_sjr,"rank_hindex":ranking_hindex,
                                "rank_citeperdoc":ranking_citeperdoc})
        except IndexError:
            pass
    
    return outputData
    
def exportData():
    data = importData()
    myFile = open('journaldata.csv', 'w')
    myFile.write("ISSN,SJR,HINDEX,CITEPER\n")
    for journal in data:
        myFile.write(str(journal["issn"])+","+str(journal["rank_sjr"])+","+str(journal["rank_hindex"])+","+str(journal["rank_citeperdoc"])+"\n")
    myFile.close()
    
   
    
class Rank:
    ID = ""
    Name = ""
    ShortName = ""
    Description = ""
    
    def normalise(self,value):
        return value
        
    def __init__(self,id,shortname="",name="",description="",normalise=None):
        self.ID = id
        self.ShortName = shortname
        self.Name = name
        self.Description = description
        if(normalise is not None):
            self.normalise = normalise

def sjr_normalise(value):
    if(value <= 0.132): return 0
    if(value <= 0.286): return 1
    if(value <= 0.690): return 2
    if(value <= 36.194): return 3
    return -1

def hindex_normalise(value):
    if(value <= 4): return 0
    if(value <= 1): return 1
    if(value <= 29): return 2
    if(value <= 734): return 3
    return -1
    
def citeper_normalise(value):
    if(value <= 0.15): return 0
    if(value <= 0.57): return 1
    if(value <= 1.5): return 2
    if(value <= 105.57): return 3
    return -1
    
def wcholdings_normalise(value):
    # these are fairly arbitrary  7573
    if(value <= 100): return 0
    if(value <= 1000): return 1
    if(value <= 2000): return 2
    return 3
    
SJRRank = Rank("SJR","SJR","SJR Ranking","A ranking based on Impact Factor, but where each citation is weighted by the ranking of the other paper",normalise=sjr_normalise)
HIndexRank = Rank("HINDEX","h-i","h-index","To have an h-index of N, a journal must have published at least N papers, each of which have N citations",normalise=hindex_normalise)
CiteperRank = Rank("CITEPER","Cites","Avg. Citations","The average number of citations in each paper",normalise=citeper_normalise)
WorldCatHoldingsRank = Rank("WCHOLD","Holdings","WorldCat Holdings","The holdings count on WorldCat",normalise=wcholdings_normalise)

class JournalFact:
    value = None
    source = None
    
    def __init__(self, value,source):
        self.value = value
        self.source = source

class Journal:
    Name = None
    ISSN = None
    eISSN = None
    Country = None
    
    Publisher = None
    RomeoColour = None
    ZetocPublisher = None
    
    Ranks = []
    Subjects = []
    
    Active = None
    Refereed = None
    Reviewed = None
    OpenAccess = None
    AvailableOnline = None
    
    Frequency = None
    Description = None
    
    Discipline = None
    PublishHistory = None
    
    WorldCatHoldings = None
    CamLibraryHoldings = None
    
    Image = None
    
    Sources = []
    
    RankInfo = {
            "CITEPER":CiteperRank,
            "HINDEX":HIndexRank,
            "SJR":SJRRank,
            "WCHOLD":WorldCatHoldingsRank
        }
    
    def __init__(self,name=None,issn=None):
        self.set_fact("Name",name,"initial",True)
        self.set_fact("ISSN",issn,"initial",True)
        
        self.Ranks = {
            "CITEPER":None,
            "HINDEX":None,
            "SJR":None,
            "WCHOLD":None
        }
        self.Subjects = []
        self.Sources = []
    
    def to_json(self):
        attrList = dir(self)
        
        dataOutput = {}
        rankOutput = {}
        sources = {}
        for attr in attrList:
            fact = getattr(self,attr)
            
            # facts
            if(fact.__class__ == JournalFact):
                dataOutput[attr] = fact.value
                sources[attr] = fact.source
            
        # rank
        for rank in self.Ranks:
            rankOutput[rank] = self.get_rank(rank)
            
        dataOutput["Ranks"] = rankOutput
        dataOutput["Sources"] = sources
        
        return json.dumps(dataOutput)
    
    def set_fact(self,fact,value,source,overwrite=False):
        if(value is None):
            return
            
        try:
            attribute = getattr(self,fact);
        except AttributeError:
            print("Tried to set non-existent Journal fact "+fact)
            raise
        
        
        if(attribute is None):
            setattr(self,fact,JournalFact(value,[source]))
        else:
            currentSources = self.get_source(fact)
            currentValue = self.get_fact(fact)
            if(value == currentValue):
                if(source not in currentSources):
                    setattr(self,fact,JournalFact(currentValue,currentSources + [source]))
            else:
                if(overwrite):
                    setattr(self,fact,JournalFact(value,[source]))
        
    def get_fact(self,fact):
        try:
            attribute = getattr(self,fact);
        except AttributeError:
            print("Tried to get non-existent Journal fact "+fact)
            raise
        
        if(attribute.__class__ == JournalFact):
            return attribute.value
        else:
            return attribute
            
    def has_fact(self,fact):
        try:
            attribute = getattr(self,fact);
            return attribute is not None
        except AttributeError:
            return False
            
    def get_source(self,fact):
        try:
            attribute = getattr(self,fact);
        except AttributeError:
            print("Tried to get non-existent Journal source for "+fact)
            raise
        
        if(attribute.__class__ == JournalFact):
            return attribute.source
        else:
            return None
    
    def get_rank(self,name):
        try:
            return self.Ranks[name]
        except KeyError:
            return None
        
    def set_rank(self,name,score):
        self.Ranks[name] = score
    
    def get_rank_info(self,name):
        try:
            return self.RankInfo[name]
        except KeyError:
            raise NoSuchRank("There is no rank with name "+name)
    
    def populate_from_SJR_data(self,overwrite=False):
        sourceName = "sjr"
        if(self.get_fact("ISSN") is None and self.get_fact("Name") is None):
            raise NoIdentifingData("To populate from SJR, either Name or ISSN must be set")
            
        matchType = "ISSN" if self.get_fact("ISSN") is not None else "Name"
        matchValue = self.get_fact("ISSN") if matchType == "ISSN" else self.get_fact("Name")
        matchKey = "issn" if matchType == "ISSN" else "name"
        
        try:
            journal = find_journal_by_identifier(matchKey,matchValue)
        except DataNotFound:
            self.Sources.append(("sjr",False))
            return
            
        # matched, populate (don't populate the search key)
        if(matchType is not "Name"): self.set_fact("Name",journal[0],sourceName,overwrite)
        self.set_fact("Country",journal[1],sourceName,overwrite)
        if(matchType is not "ISSN"): self.set_fact("ISSN",journal[2],sourceName,overwrite)
        
        self.set_rank("SJR",journal[3])
        self.set_rank("HINDEX",journal[4])
        self.set_rank("CITEPER",journal[5])
        
        self.Sources.append(("sjr",True))
    
    def populate_from_ROMEO(self,overwrite=False):
        sourceName = "romeo"
        if(self.get_fact("ISSN") is None):
            raise NoIdentifingData("To populate from RoMEO, ISSN must be set")
        
        try:
            result = query.find_organisation_romeo_policy(self.get_fact("ISSN"))
            
            self.set_fact("RomeoColour",result["romeocolour"],sourceName,overwrite)
            self.set_fact("ZetocPublisher",result["zetocpub"],sourceName,overwrite)
            self.set_fact("Publisher",result["publisher"],sourceName,overwrite)
        except query.NoResultError:
            self.Sources.append(("romeo",False))
            return

        self.Sources.append(("romeo",True))
        
    def populate_from_DOAJ(self,overwrite=False):
        sourceName = "doaj"
        if(self.get_fact("ISSN") is None):
            raise NoIdentifingData("To populate from DOAJ, ISSN must be set")
            
        try:
            data = query.find_journal_DOAJ_subjects(self.get_fact("ISSN"))
        except query.NoResultError:
            self.Sources.append(("doaj",False))
            return
        
        self.Subjects = data
    
        self.Sources.append(("doaj",True))
        
    def populate_from_ulrichsweb(self,ulrichkey,overwrite=False):
        sourceName = "ulrich"
        if(self.get_fact("ISSN") is None):
            raise NoIdentifingData("To populate from UlrichsWeb, ISSN must be set")
        
        try:
            result = query.find_journal_ulrichsweb_info(self.get_fact("ISSN"))
        except query.NoResultError:
            raise
            self.Sources.append(("ulrich",False))
            return
        except query.XMLChildNotFoundError:
            raise
            self.Sources.append(("ulrich",False))
            return
        
        self.set_fact("Active",result["Active"],sourceName,overwrite)
        self.set_fact("Description",result["Description"],sourceName,overwrite)
        self.set_fact("Refereed",result["Refereed"],sourceName,overwrite)
        self.set_fact("OpenAccess",result["OpenAccess"],sourceName,overwrite)
        # Reviewed: "Indication of whether the serial has a review in the Ulrich's record"
        # self.set_fact("Reviewed",result["Reviewed"],sourceName,overwrite)
        self.set_fact("Country",result["Country"],sourceName,overwrite)
        self.set_fact("Frequency",result["Frequency"],sourceName,overwrite)
        self.set_fact("AvailableOnline",result["AvailableOnline"],sourceName,overwrite)
        self.set_fact("Name",result["Title"],sourceName,overwrite)
    
        self.Sources.append(("ulrich",True))
        
    def populate_from_wiki(self,overwrite=False,fixISSN=True):
        sourceName = "wiki"
        if(self.get_fact("Name") is None):
            raise NoIdentifingData("To populate from Wikipedia, Name must be set")
        
        try:
            data = query.find_journal_wiki_info(self.get_fact("Name"))
        except query.NoResultError:
            self.Sources.append(("wiki",False))
            return
        
        # fix ISSN/eISSN issues
        if(fixISSN and data.has_key("ISSN") and data.has_key("eISSN")): 
            self.set_fact("ISSN",data["ISSN"],sourceName,True)
            self.set_fact("eISSN",data["eISSN"],sourceName,True)
        else:
            # just apply normally
            if(data.has_key("ISSN")):
                self.set_fact("ISSN",data["ISSN"],sourceName,overwrite)
            if(data.has_key("eISSN")):
                self.set_fact("eISSN",data["eISSN"],sourceName,overwrite)
        
        
        if(data.has_key("Image")): 
            self.set_fact("Image",data["Image"],sourceName,overwrite)
        if(data.has_key("PublishHistory")): 
            self.set_fact("PublishHistory",data["PublishHistory"],sourceName,overwrite)
        if(data.has_key("Discipline")): 
            self.set_fact("Discipline",data["Discipline"],sourceName,overwrite)
        
        self.Sources.append(("wiki",True))
    
    def populate_from_worldcat_classify(self,overwrite=False):

        sourceName = "worldcat_classify"
        if(self.get_fact("ISSN") is None):
            raise NoIdentifingData("To populate from WorldCat Classify, ISSN must be set")
           
        try:
            data = query.find_journal_holdings_from_worldcat(self.get_fact("ISSN"))
        except query.NoResultError:
            self.Sources.append((sourceName,False))
            return
        
        if(data.has_key("Holdings")): 
            self.set_rank("WCHOLD",data["Holdings"])
            # self.set_fact("WorldCatHoldings",data["Holdings"],sourceName,overwrite)
            
        self.Sources.append((sourceName,True))
    
    def populate_from_cam_search(self,overwrite=False):
        sourceName = "cam_search"
        if(self.get_fact("ISSN") is None):
            raise NoIdentifingData("To populate from Cam Search, ISSN must be set")
        
        try:
            locations = query.find_journal_cam_availability("0036-8075")
        except query.NoResultError:
            self.Sources.append((sourceName,False))
            return
        
        self.set_fact("CamLibraryHoldings",locations,sourceName,overwrite)
        
        self.Sources.append((sourceName,True))
    
    def countryInitials(self):
        nameWords = self.Country.split(" ")
        initials = ""
        for word in nameWords:
            initials += word[0]
        return initials
        
class Error(Exception):
	"""Base error class"""
	pass
	
class DataNotFound(Error):
	"""Attempted to populate but couldn't find a match"""
	pass
class NoSuchRank(Error):
	"""Attempted to look up a rank which did not exist"""
	pass
class NoIdentifingData(Error):
	"""Attempted to populate without any identifying data"""
	pass
