/**
Functionality that visually moves grants into 'Your Grant' area.
There is no backend functionality associated with this
**/

function dragGrant_(ev) {
    ev.dataTransfer.setData("Text",ev.target.getAttribute("grant"));
}

function grantDropArea_(ev) {
    ev.preventDefault();
    var data=ev.dataTransfer.getData("Text");
    claimGrant(data)
}

function dragPub(ev) {
    ev.dataTransfer.setData("Text",ev.target.getAttribute("publication"));
}
function dropPubOnGrant(ev,grantID) {
    ev.preventDefault();
    var data=ev.dataTransfer.getData("Text");
    addPubToGrant(data,grantID)
}

function dropPubOnResultsBox(ev) {
    ev.preventDefault();
    var data=ev.dataTransfer.getData("Text");
    removePubFromGrants(data)
}

function allowDrop(ev) {
    ev.preventDefault();
}

function removePubFromGrants(pub) {
    searchBoxElement = document.getElementById("pub_search_results")
    pubElement = document.getElementById("pub_"+pub)
    
    pubElement.setAttribute("selected","false")
    if(searchBoxElement == null) {
        pubElement.parentNode.removeChild(pubElement)
    } else {
        searchBoxElement.appendChild(pubElement)                
    }
}

function addPubToGrant(pub,grant) {
    grantElement = document.getElementById("grant_pubs_"+grant)
    pubElement = document.getElementById("pub_"+pub)
    
    pubElement.setAttribute("selected","true")
    grantElement.appendChild(pubElement)
}

function getChosenPubs() {
    chosenList = []
    pubList = document.getElementsByName("publication-result");
    length = pubList.length;
    for(var i = 0; i < length; i++) {
        pub = pubList[i];
        if(pub.getAttribute("selected") == "true") {
            chosenList.push(pub.getAttribute("publication"))
        }
    }
    return chosenList
}

function getChosenGrants() {
    chosenList = []
    grantList = document.getElementsByName("grant-result");
    length = grantList.length;
    for(var i = 0; i < length; i++) {
        grant = grantList[i];
        if(grant.getAttribute("selected") == "true") {
            chosenList.push(grant.getAttribute("grant"))
        }
    }
    return chosenList
}

function updateMessage(researcher) {
    document.getElementById("no_results_chosen").hidden = (document.getElementById("chosen_box").innerHTML != "")
    
    hasGrantsLeft = false
    grantList = document.getElementsByName("grant-result");
    length = grantList.length;
    for(var i = 0; i < length; i++) {
        grant = grantList[i];
        if(grant.getAttribute("researcher") == researcher && grant.getAttribute("selected") == "false") {
            hasGrantsLeft = true
        }
    }

    message = document.getElementById("allchosen_"+researcher);
    if(message != null) {
        message.hidden = hasGrantsLeft
    }
}
function selectByResearcher(researcher) {
    grantList = document.getElementsByName("grant-result");
    length = grantList.length;
    for(var i = 0; i < length; i++) {
        grant = grantList[i];
        if(grant.getAttribute("researcher") == researcher && grant.getAttribute("selected") == "false") {
            selectRow(grant.getAttribute("grant"))
        }
    }
    updateMessage(researcher)
}

function claimGrant(id) {
    element = document.getElementById("grant_"+id)
    element.setAttribute("selected","true")
    target = document.getElementById("chosen_box")
    
    target.appendChild(element)
    updateMessage(element.getAttribute("researcher"))
}

function unclaimGrant(id) {
    element = document.getElementById("grant_"+id)
    element.setAttribute("selected","false")
    target = document.getElementById("researcher_box_"+element.getAttribute("researcher"))
    if(target == null) {
        element.parentNode.removeChild(element)
    } else {
        target.appendChild(element)
    }
    updateMessage(element.getAttribute("researcher"))
}

function selectRow(id) {
    element = document.getElementById("grant_"+id)
    if(element.getAttribute("selected") == "false") {
        claimGrant(id)
    } else {
        unclaimGrant(id)
    }
}