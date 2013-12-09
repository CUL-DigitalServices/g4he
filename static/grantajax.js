// from www.w3schools.com (with minor modification)

/* no real error handling on the AJAX calls */

nodebug = true; /* make it possible to remove all debug messages */
if(!window.console || nodebug){ window.console = {log: function(){} }; } 


function doNameSearch(first,last,crs) {
    var xmlhttp;
    if (window.XMLHttpRequest) {// code for IE7+, Firefox, Chrome, Opera, Safari
        xmlhttp=new XMLHttpRequest();
    } else {// code for IE6, IE5
        xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    xmlhttp.onreadystatechange = function() {
        if (xmlhttp.readyState==4 && xmlhttp.status==200) {
            mainContent = document.getElementById("main_content")
            mainContent.innerHTML=xmlhttp.responseText;

            console.log(xmlhttp.responseText);
            console.log('- - - - - - - - - - -');
            
            //clean up already present rows
            claimedGrants = getChosenGrants()
            newResults = mainContent.querySelectorAll("[name=grant-result]")
            count = newResults.length
            for(var i = 0; i < count; i++) {
                result = newResults[i]
                resultGrantID = result.getAttribute("grant")
                if(claimedGrants.indexOf(resultGrantID) != -1) {
                    result.parentNode.removeChild(result)
                    updateMessage(result.getAttribute("researcher"))
                }
            }
        }
    }
    xmlhttp.open("GET","get_grants_by_name?first="+first+"&last="+last+"&crs="+crs,true);
    xmlhttp.send();
}

function doPublicationSearch(first,last,crs) {
    var xmlhttp;
    if (window.XMLHttpRequest) {// code for IE7+, Firefox, Chrome, Opera, Safari
        xmlhttp=new XMLHttpRequest();
    } else {// code for IE6, IE5
        xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    xmlhttp.onreadystatechange = function() {
        if (xmlhttp.readyState==4 && xmlhttp.status==200) {
            mainContent = document.getElementById("main_content")
            mainContent.innerHTML=xmlhttp.responseText;
            
            //clean up already present rows
            claimedPubs = getChosenPubs()
            newResults = mainContent.querySelectorAll("[name=publication-result]")
            count = newResults.length
            for(var i = 0; i < count; i++) {
                result = newResults[i]
                resultPubID = result.getAttribute("publication")
                if(claimedPubs.indexOf(resultPubID) != -1) {
                    result.parentNode.removeChild(result)
                }
            }
        }
    }
    xmlhttp.open("GET","get_publications_by_person?first="+first+"&last="+last+"&crs="+crs,true);
    xmlhttp.send();
}

function getMoreResults(searchString) {
    var xmlhttp;
    if (window.XMLHttpRequest) {// code for IE7+, Firefox, Chrome, Opera, Safari
        xmlhttp=new XMLHttpRequest();
    } else {// code for IE6, IE5
        xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    xmlhttp.onreadystatechange = function() {
        if (xmlhttp.readyState==4 && xmlhttp.status==200) {
            document.getElementById("search_by_title_results").innerHTML=xmlhttp.responseText;
        }
    }
    xmlhttp.open("GET","search_by_title?term="+searchString,true);
    xmlhttp.send();
}
