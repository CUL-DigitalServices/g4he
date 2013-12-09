from __future__ import unicode_literals
import cherrypy
import query
import journalimport
import json
import os.path

from iso_country_codes import COUNTRY

# Fix for issue:
# https://bitbucket.org/cherrypy/cherrypy/issue/1100/cherrypy-322-gives-engine-error-when
from cherrypy.process import servers
def fake_wait_for_occupied_port(host, port): return
servers.wait_for_occupied_port = fake_wait_for_occupied_port
# End fix for issue

class QueryPage:
    def __init__(self, config):
        self.allconfig = config
        
    def get_css(self):
        return '<link rel="stylesheet" type="text/css" href="/static/journal.css"><link rel="stylesheet" type="text/css" href="/static/index.css">'
        
    def get_ajax_js(self):
        """
            embeds the js that has the function that call:
                get_publications_by_person
                get_grants_by_name
                search_by_title
        """
        return '<script src="/static/grantajax.js"></script>'
        
    def get_move_js(self):
        return '<script src="/static/movegrants.js"></script>'
        
    def get_searchbox(self):
        return '''
            <div class='groupingbox'>
            <div class='header'>Grant Search</div>
            <form action="javascript:void(0);"><input type="text" placeholder="First Name" id="search_first" name="first" />
            <input type="text" placeholder="Last Name" id="search_last" name="last" />
            <input type="submit" value="Search" onclick="doNameSearch(document.getElementById('search_first').value,document.getElementById('search_last').value,'')"/>
            </form>
            /
            <form action="javascript:void(0);"><input type="text" placeholder="CRS ID" class="small_textbox" id="search_crs" name="crs" />
            <input type="submit" value="Search" onclick="doNameSearch('','',document.getElementById('search_crs').value)"/>
            </form>
            </div>
            
            <div class='groupingbox'>
            <div class='header'>Publication Search</div>
            <form action="javascript:void(0);"><input type="text" placeholder="First Name" id="search_first_pub" name="first" />
            <input type="text" placeholder="Last Name" id="search_last_pub" name="last" />
            <input type="submit" value="Search" onclick="doPublicationSearch(document.getElementById('search_first_pub').value,document.getElementById('search_last_pub').value,'')"/>
            </form>
            /
            <form action="javascript:void(0);"><input type="text" placeholder="CRS ID" class="small_textbox" id="search_crs_pub" name="crs" />
            <input type="submit" value="Search" onclick="doPublicationSearch('',''.value,document.getElementById('search_crs_pub').value)"/>
            </form>
            </div>'''
        
    def get_titlesearch(self):
        return '''
            <form action="javascript:void(0);"><input class="large_textbox" type="text" placeholder="Grant Title" id="titlesearch" />
            <input type="submit" value="Search" onclick="getMoreResults(document.getElementById('titlesearch').value)" /></form>'''
    
    def trim_name(self,name):
        #remove subtitle if present on longer titles
        if(len(name) > 70):
            # get rid of subtitle
            if(name.find(":") != -1):
                name = name.split(":")[0]
                return self.trim_name(name)
            return name[:67]+"&hellip;"
        return name
        
    def get_result_row_html(self,project,researcherID):
        try:
            matchCSS = "match_weak" if project.Researcher.LooseMatched else "match_strong"
        except(AttributeError):
            matchCSS = "match_search"
        rowID = "search_"+str(hash(project.ProjectName))
        
        returnHTML = ""
        
        # start row
        returnHTML += "<div ondrop='dropPubOnGrant(event,\""+rowID+"\")' ondragover='allowDrop(event)' name='grant-result' researcher='"+researcherID+"' grant='"+rowID+"' id='grant_"+rowID+"' selected='false'>"
        
        # grant info section
        returnHTML += "<div class='result "+matchCSS+"' onclick='selectRow(\""+rowID+"\")'>"
        
        if(project.GrantReference == "?"):
            returnHTML += "<div class='projectinfobox'>"+project.ProjectFunder+"</div>"
        else:
            returnHTML += "<div class='projectinfobox'>"+project.ProjectFunder+" - "+project.GrantReference+"</div>"
        if(project.Role != "?"):
            returnHTML += "<div class='projectinfobox'>"+project.Role+"</div>"
        returnHTML += "<div class='projectrightinfobox'>&pound;{:,d}</div>".format(int(project.PoundValue))
        returnHTML += "<div class='projecttitle'>"
        returnHTML += self.trim_name(project.ProjectName)
        returnHTML += "</div>"
        
        # end info section
        returnHTML += "</div>"
        
        # pubs section
        returnHTML += "<div class='grantpubs' id='grant_pubs_"+rowID+"'>"
        returnHTML += "</div>"
        
        # end row
        returnHTML += "</div>"
        return returnHTML
    
    def get_publication_html(self,publication,researcherID):
        pubID = str(hash(publication["Title"]))
        returnHTML = ""
        returnHTML += "<div draggable='true' ondragstart='dragPub(event)' name='publication-result' class='publication-result' id='pub_"+pubID+"' publication='"+pubID+"'>"
        returnHTML += "<div onclick='removePubFromGrants(\""+pubID+"\")' class='rollovershow floatingbutton'>X</div>"
        returnHTML += publication["Title"]
        returnHTML += "</div>"
        return returnHTML
            
    def index(self):
        # title
        pageHTML = "<title>Researcher search results</title>"
        
        # css and js box
        pageHTML += self.get_move_js()+self.get_ajax_js()+self.get_css()
        csvResults = ""
        
        pageHTML += "<div class='centrebox'>"
        
        # your grants
        pageHTML += "<div class='groupingbox'>"
        pageHTML += "<div class='header'>Your Grants..</div>"
        pageHTML += "<div id='no_results_chosen' class='result result_fake'>No grants selected - Click on your grants below to add them</div>"
        pageHTML += "<div id='chosen_box'></div>"
        pageHTML += "</div>"
        
        pageHTML += "<div class='groupingbox'>"
        
        # the search
        pageHTML += self.get_searchbox()
        
        # main content
        pageHTML += "<div id='main_content'>"
        
        pageHTML += "</div>"
        pageHTML += "</div>"
        
        pageHTML += "</div>" # close the centrebox
        
        return pageHTML
    index.exposed = True

    def search_by_title(self,term=""):
        """
            Extends functionality of get_grants_by_name to search those
            results by the title of the grant
        """
        returnString = ""
        try:
            result = query.find_grants_by_title(term,self.allconfig["keys"]["orgname"],self.allconfig["keys"]["orgcode"])
        except query.NoResultError:
            return "No results found"
        
        maxCount = 5
        for project in result:
            maxCount -= 1
            if(maxCount < 0): break
            rowID = "search_"+str(hash(project.ProjectName))
            termID = "search_"+str(hash(term))
            
            returnString += self.get_result_row_html(project,"search_"+termID)
            
        return returnString
    search_by_title.exposed = True
    
    def get_grants_by_name(self,first="",last="",crs=""):
        """ Return all Grants from the GTR database based against
        a search based on name of priniciple/co investigator on the grant
        The calls to gtr are configured in the config file.
        
        Called from static/grantajax.js
        
        Args:
            first: the first name  - this is not case sensitive.
            last: the last name - this is not case sensitive
            crs: this is the cambridge specific CRSID that is sent to
                LDAP to get full details
            
        Returns:
            html code to embed directly on the page        
        """
        searchInfo = "No search performed!"
        # if we have crs, use that
        if(crs != ""):
            try:
                fullName = query.find_full_name_by_crs(crs)
                firstLastName = query.crs_name_to_first_last(fullName)
                first = firstLastName["FirstName"]
                last = firstLastName["LastName"]
                result = query.find_grants_by_first_last(first,last,self.allconfig["keys"]["orgname"],self.allconfig["keys"]["orgcode"])
                searchInfo = "Sources: "
                searchInfo += "<searchterm>crs lookup</searchterm>"
                searchInfo += "<searchterm>GtR</searchterm>"
                searchInfo += " - Search terms: "
                searchInfo += "<searchterm><searchkey>crs</searchkey><searchvalue>"+crs+"</searchvalue></searchterm>"
                searchInfo += " - Looked up: "
                searchInfo += "<searchterm><searchkey>first name</searchkey><searchvalue>"+first+"</searchvalue></searchterm>"
                searchInfo += "<searchterm><searchkey>last name</searchkey><searchvalue>"+last+"</searchvalue></searchterm>"
            except query.NoResultError:
                return "<div class='centrebox'>No results found</div>"
        else:
            # look up researcher by name
            try: 
                result = query.find_grants_by_first_last(first,last,self.allconfig["keys"]["orgname"], self.allconfig["keys"]["orgcode"])
                searchInfo = "Sources: "
                searchInfo += "<searchterm>GtR</searchterm>"
                searchInfo += " - Search terms: "
                if(first!=""):
                    searchInfo += "<searchterm><searchkey>first name</searchkey><searchvalue>"+first+"</searchvalue></searchterm>"
                searchInfo += "<searchterm><searchkey>last name</searchkey><searchvalue>"+last+"</searchvalue></searchterm>"
            except query.NoResultError:
                return "<div class='centrebox'>No results found</div>"
        
        pageHTML = ""
        csvResults = ""
        
        # search information
        pageHTML += "<div class='groupingbox'>"
        pageHTML += "<div class='header'>Search Information</div>"
        pageHTML += "<div class='subtext'>"+searchInfo+"</div>"
        pageHTML += "</div>"
       # print(len(result))
        # prepare data for output
        researcherList = set()
        for project in result:
            
            writtenName = project.Researcher.FirstName + " " + project.Researcher.LastName
            
            researcherList.add(writtenName)
            # also create the CSV data
            csvResults += "{0},{1},{2},{3},{4},{5}<br/>".format(project.ProjectName.replace(",",""),project.ProjectFunder,project.GrantReference,project.StartDate,project.EndDate,project.PoundValue)
            
            
        # output
        for researcher in researcherList:
            researcherID = str(hash(researcher))
            
            pageHTML += "<div class='groupingbox'>"
            pageHTML += "<div class='floatingbutton' onclick=selectByResearcher(\""+researcherID+"\")>Add all</div>"
            pageHTML += "<div class='header'>"+researcher+"</div>"
            pageHTML += "<div id='researcher_box_"+researcherID+"'>"
            pageHTML += "<div id='allchosen_"+researcherID+"' hidden='true' class='result result_fake'>All this researcher's grants have been added</div>"
                                
            for project in result:
                # check if it is for this researcher
                writtenName = project.Researcher.FirstName + " " + project.Researcher.LastName
                if(researcherID == str(hash(writtenName))):
                    # add the row
                    pageHTML += self.get_result_row_html(project,researcherID)
            
            pageHTML += "</div>"
            pageHTML += "</div>"

        pageHTML += "<div class='groupingbox'>"
        pageHTML += "<div class='header'>Search for more</div>"
        pageHTML += "<div id='search_by_title_results'></div>"+self.get_titlesearch()
        pageHTML += "</div>" # close the grouping box
        
        pageHTML += "</div>" # close the centerbox
        # csv box
        csvResults = "<div class='csv'>"+csvResults+"</div>"
        return pageHTML + csvResults
    get_grants_by_name.exposed = True

    def get_publications_by_person(self,first="",last="",crs=""):
        """ This functionality should return publications against a person
        This has not been implemented
        Just returns dummy results
        Called from static/grantajax.js
        
        Args:
            first: the first name  - this is not case sensitive.
            last: the last name - this is not case sensitive
            crs: this is the cambridge specific CRSID that is sent to
                LDAP to get full details
            
        Returns:
            html code to embed directly on the page
        """

        searchInfo = "No search performed!"
        # if we have crs, use that
        if(crs != ""):
            try:
                fullName = query.find_full_name_by_crs(crs)
                firstLastName = query.crs_name_to_first_last(fullName)
                first = firstLastName["FirstName"]
                last = firstLastName["LastName"]
                result = query.test_fake_find_publications(first,last)
                searchInfo = "Sources: "
                searchInfo += "<searchterm>crs lookup</searchterm>"
                searchInfo += "<searchterm>GtR</searchterm>"
                searchInfo += " - Search terms: "
                searchInfo += "<searchterm><searchkey>crs</searchkey><searchvalue>"+crs+"</searchvalue></searchterm>"
                searchInfo += " - Looked up: "
                searchInfo += "<searchterm><searchkey>first name</searchkey><searchvalue>"+first+"</searchvalue></searchterm>"
                searchInfo += "<searchterm><searchkey>last name</searchkey><searchvalue>"+last+"</searchvalue></searchterm>"
            except query.NoResultError:
                return "<div class='centrebox'>No results found</div>"
        else:
            # look up researcher by name
            try: 
                result = query.test_fake_find_publications(first,last)
                searchInfo = "Sources: "
                searchInfo += "<searchterm>GtR</searchterm>"
                searchInfo += " - Search terms: "
                if(first!=""):
                    searchInfo += "<searchterm><searchkey>first name</searchkey><searchvalue>"+first+"</searchvalue></searchterm>"
                searchInfo += "<searchterm><searchkey>last name</searchkey><searchvalue>"+last+"</searchvalue></searchterm>"
            except query.NoResultError:
                return "<div class='centrebox'>No results found</div>"
        
        pageHTML = ""
        
        pageHTML += "<div class='groupingbox' ondrop='dropPubOnResultsBox(event)' ondragover='allowDrop(event)'>"
        pageHTML += "<div class='header'>Search Results</div>"
        
        pageHTML += "<div id='pub_search_results'>"
        for publication in result:
            pageHTML += self.get_publication_html(publication,"XXX")
        
        pageHTML += "</div>"
        pageHTML += "</div>"
        
        return pageHTML
    get_publications_by_person.exposed = True

    def get_journal_info(self,journalname=None,json=False):

        # has to do the parsing every time for now - quite slow        
        # find the required journal
        
        # do search

        journals = journalimport.find_journal_by_name(journalname)
        
        # output
        pageHTML = self.get_css() +"<p><form action='get_journal_info'><input name='journalname' type='text' placeholder='Name Search'></input><input type='submit' value='Submit'></form></p>"
        
        journals = journals[0:8]
        
        for journalResult in journals:
            journal = journalimport.Journal(name=journalResult[0])
            
            journal.populate_from_SJR_data()
            journal.populate_from_wiki()
            journal.populate_from_worldcat_classify()
            journal.populate_from_ROMEO()
            journal.populate_from_DOAJ()
            journal.populate_from_ulrichsweb(self.allconfig["keys"]["ULRICHS_KEY"])
            
            if(json):
                return journal.to_json()
            
            backgroundImage = journal.get_fact("Image")
            
            if(backgroundImage is not None):
                pageHTML += "<div class='journal journalimage' style='background-image:url(\""+backgroundImage+"\")'>"
            else:
                pageHTML += "<div class='journal journalnoimage'>"
            
            pageHTML += "<div class='searchscore'>Search Match: "+str(int(round(journalResult[1]*100)))+"</div>"
            
            pageHTML += "<div class='infobox'>"
            pageHTML += "<div class='name'>{0}</div>".format(journal.get_fact("Name"))
            pageHTML += "<div class='issn'>ISSN {0}</div>".format(journal.get_fact("ISSN"))
            if(journal.has_fact("eISSN")):
                pageHTML += "<div class='issn'>eISSN {0}</div>".format(journal.get_fact("eISSN"))
            
            #pageHTML += "<div class='country'>{0}</div>".format(journal.countryInitials())
            if(journal.Publisher is not None):
                pageHTML += "<div class='publisher'>{0}</div>".format(journal.get_fact("Publisher"))
            if(journal.PublishHistory is not None):
                pageHTML += "<div class='firstPublished'>{0}</div>".format(journal.get_fact("PublishHistory"))
            if(journal.Discipline is not None):
                pageHTML += "<div class='discipline'>{0}</div>".format(journal.get_fact("Discipline"))
            if(journal.Description is not None):
                pageHTML += "<div class='journaldescription'>{0}</div>".format(journal.get_fact("Description"))
            
            pageHTML += "</div>"
            
            icon_active = self._get_fact_icon(journal,"Active","active.png")
            text_active = self._get_fact_text(journal,"Active","active","inactive")
            
            icon_refereed = self._get_fact_icon(journal,"Refereed","refereed.png")
            text_refereed = self._get_fact_text(journal,"Refereed","refereed","not refereed")
            
            icon_openaccess = self._get_fact_icon(journal,"OpenAccess","openaccess.png")
            text_openaccess = self._get_fact_text(journal,"OpenAccess","Open Access","not Open Access")
             
            icon_availableonline = self._get_fact_icon(journal,"AvailableOnline","availableonline.png")
            text_availableonline = self._get_fact_text(journal,"AvailableOnline","available online","not available online")
               
            if(journal.RomeoColour != "Unknown" and journal.get_fact("RomeoColour") is not None):
                icon_romeo = "romeo_" + journal.get_fact("RomeoColour") + ".png"
                text_romeo = "This journal is RoMEO "+journal.get_fact("RomeoColour")
            else:
                icon_romeo = "unknown.png"
                text_romeo = "This journal is not on RoMEO"
                
            if(journal.get_fact("Country") is not None):
                icon_country = self._get_country_icon(journal.get_fact("Country"))
                text_country = journal.get_fact("Country")
            else:
                icon_country = "unknown.png"
                text_country = "Country unknown"
            
            
            pageHTML += "<div class='icons'>"
            pageHTML += "<img class='icon' src='/static/icons/{0}'></img>".format(icon_active)
            pageHTML += "<img class='icon' src='/static/icons/{0}'></img>".format(icon_refereed)
            pageHTML += "<img class='icon' src='/static/icons/{0}'></img>".format(icon_openaccess)
            pageHTML += "<img class='icon' src='/static/icons/{0}'></img>".format(icon_romeo)
            pageHTML += "<img class='icon' src='/static/icons/{0}'></img>".format(icon_country)
            pageHTML += "<img class='icon' src='/static/icons/{0}'></img>".format(icon_availableonline)
            pageHTML += "<div class='description'>{0}</div>".format(text_active)
            pageHTML += "<div class='description'>{0}</div>".format(text_refereed)
            pageHTML += "<div class='description'>{0}</div>".format(text_openaccess)
            pageHTML += "<div class='description'>{0}</div>".format(text_romeo)
            pageHTML += "<div class='description'>{0}</div>".format(text_country)
            pageHTML += "<div class='description'>{0}</div>".format(text_availableonline)
            pageHTML += "</div>"
            
            # if(journal.Subjects):
                # pageHTML += "<div class='subjects'>"
                # for subject in journal.Subjects:
                    # pageHTML += "<div class='subject'>"+subject+"</div>"
                # pageHTML += "</div>"
                
            
            pageHTML += "<div class='rankingbox'>"
             
            for rank in journal.Ranks:
                name = journal.get_rank_info(rank).ShortName
                score = journal.get_rank(rank)
                normalscore = journal.get_rank_info(rank).normalise(score)
                desc = journal.get_rank_info(rank).Description
                pageHTML += "<div class='ranking rank-"+str(normalscore)+"' title='"+desc+"'>"+name+": "+str(score)+"</div>"
                #pageHTML += "<div class='description'>"+desc+"</div>
            
            pageHTML += "</div>"
            
            pageHTML += "<div class='sourceicons'>"
            for source in journal.Sources:
                if(source[0] == "cam_search"):
                    img = source[0]+".png"
                else:
                    img = source[0]+".ico"
                pageHTML += "<img class='"+("greyscale" if not source[1] else "") + "' src='/static/icons/"+img+"'></img>"
            pageHTML += "</div>"
            
            pageHTML += "</div>"
        
        pageHTML += "Data sources: RoMEO, SJR, DOAJ, Wikipedia, Ulrichsweb, WorldCat Classify"
        
        return pageHTML
    get_journal_info.exposed = True

    def _get_country_icon(self,countryName):
        for c in COUNTRY:
            if COUNTRY[c].lower() == countryName.lower():
                return "flags/"+c.lower()+".png"
         
    def _get_fact_icon(self,journal,fact,icon):
        if(journal.get_fact(fact) is not None):
            return ("not_" if not journal.get_fact(fact) else "") + icon
        else:
            return "unknown.png"
   
    def _get_fact_text(self,journal,fact,success,failure):
        # This journal is success
        # This journal is failure
        # No source for fact
        if(journal.get_fact(fact) is not None):
            return "This journal is " + (failure if not journal.get_fact(fact) else success)
        else:
            return "No source for "+fact
            


#static user defined items
config = json.load(open(os.path.join(os.path.dirname(__file__), 'config.json')))
#json.load(open('/tmp/config.json'))

current_dir = os.path.dirname(os.path.abspath(__file__)) + os.path.sep

#dynamic items
config["global"]["log.error_file"] =  os.path.join(current_dir, 'log/errors.log')

config["/"] = {"tools.staticdir.root": current_dir}
    
cherrypy.quickstart(QueryPage(config["codespecific"]),config=config)