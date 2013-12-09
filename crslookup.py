import collections
import itertools

import ldap
from ldap import filter
from ldap import ldapobject
from ldap.resiter import ResultProcessor

LDAP_LOOKUP_URL = "ldaps://ldap.lookup.cam.ac.uk"

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)

# This class allows us to instantiate a ResultProcessor object
# which allows us to retrieve results from an LDAP server
# synchronously, thus avoiding the need to handle very large
# results and allowing for faster retrieval:
class AsyncLDAP(ldapobject.LDAPObject, ResultProcessor):
    pass


class Lookup(object):
    """
    A basic interface into the lookup.cam.ac.uk service.
    """

    _LDAP_USER_SEARCH_BASE = ("ou=people, o=University of Cambridge,"
            "dc=cam,dc=ac,dc=uk")
    _LDAP_USER_SEARCH_ATTRS = ["uid", "mail", "displayName"]
    _LDAP_CRSID_FRAGMENT_SEARCH_ATTRS = ["uid", "displayName"]

    LookupUser = collections.namedtuple(
            "LookupUser", ["crsid", "name", "email"])

    def __init__(self, lookup_url=LDAP_LOOKUP_URL):
        if not lookup_url:
            raise ValueError(
                "A lookup_url must be provided, got: {!r}".format(lookup_url))

        self._ldap = AsyncLDAP(LDAP_LOOKUP_URL)
        self._is_connected = False
		
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

    def connect(self):
        self._ldap.simple_bind_s()
        self._is_connected = True

    def disconnect(self):
        if not self._ldap:
            raise RuntimeError(
                    "disconnect() called without a connection to disconnect.")
        ldap = self._ldap
        self._ldap = None
        self._is_connected = False
        ldap.unbind_s()

    def _ensure_connected(self):
        if not self._ldap:
            raise RuntimeError("Attempted to access ldap after disconnect()")
        if not self._is_connected:
            raise RuntimeError("Attempted to access ldap before connect() was "
                    "called.")

    def _user_search(self, crsids):
        self._ensure_connected()

        # Create a (uid=foo) filter for each crsid specified
        crsid_filters = (filter.filter_format("(uid=%s)", [crsid])
                for crsid in crsids)

        # Combine all the individual crsid filters with an OR operator
        crsids_filter = "(|%s)" % "".join(crsid_filters)

        return self._ldap.search_ext_s(self._LDAP_USER_SEARCH_BASE,
                ldap.SCOPE_ONELEVEL,
                filterstr=crsids_filter,
                attrlist=self._LDAP_USER_SEARCH_ATTRS)

    def _first(self, list_or_value):
        """
        If list_or_value is a collection (except strings), return the first 
        item, otherwise return list_or_value itself.
        """
        if (isinstance(list_or_value, collections.Container) and
                not isinstance(list_or_value, basestring)):
            if(list_or_value):
                return iter(list_or_value).next()
            return None
        return list_or_value

    def _create_user(self, search_result):
        return self.LookupUser(self._first(search_result.get("uid")),
                self._first(search_result.get("displayName")),
                self._first(search_result.get("mail")))

    def _users_from_results(self, search_results):
        return (self._create_user(result) for _, result in search_results)

    def _index_users_by_crsid(self, users):
        return dict((user.crsid, user) for user in users)
    

    def get_users(self, crsids):
        return self._index_users_by_crsid(
                self._users_from_results(
                        self._user_search(crsids)))

    def get_user(self, crsid):
        results = self.get_users([crsid])
        return results.get(crsid)

    # Performs the LDAP search for finding entries beginnning
    # with the provided crsid fragment and returns a list of results.
    def _fragment_search(self, crsid_fragment,size_limit=100,time_out=3):
        self._ensure_connected()

        # Don't search with an empty crsid_fragment, since returning all
        # the users in lookup is unlikely to be timely or desired!
        if ( crsid_fragment == '' ): return []

        # Create a filter looking for all the uids beginning with the crsid
        # fragment:
        crsid_fragment_filter = '(uid=' + crsid_fragment + '*)'

        # If we hit any exceptions when searching (a possible one being a timeout)
        # then return an empty list:
        try:
            # search_ext returns a message id that can
            # be turned into an iterator using class:
            # ldap.resiter.ResultProcessor.allresults
            # which we then slice to the required limit:
            msg_id = self._ldap.search_ext(self._LDAP_USER_SEARCH_BASE,
                ldap.SCOPE_ONELEVEL,
                filterstr=crsid_fragment_filter,
                attrlist=self._LDAP_CRSID_FRAGMENT_SEARCH_ATTRS,
                timeout=time_out,sizelimit=size_limit)
            return list(itertools.islice(self._ldap.allresults(msg_id),size_limit))
        except:
            pass

    # The format of each item returned by the ldap search is:
    # [100,[["uid=CRSID,ou=people,o=University of Cambridge,dc=cam,dc=ac,dc=uk",{"displayName":["DISPLAYNAME"],"uid": ["CRSID"]}]],2,[]],
    # This function turns that into:
    # { "id": "CRSID", "label": "CRSID (DISPLAYNAME)", "value": "CRSID" }
    # If the display name is empty or missing, then label becomes just "CRSID"
    def _format_match(self,match_list):
        uid = ''
        displayname = None
        # The uid should always be present, but the displayName
        # may not always be present:
        try:
            # These complex list of 1's and 0's are basically just
            # retrieving the uid and displayName from the results!
            uid = match_list[1][0][1]['uid'][0]
            displayname = match_list[1][0][1]['displayName'][0]
        except:
            pass
        label = uid
        if ( displayname ):
            label += " (" + displayname + ")"
        return { "id": uid, "label": label, "value": uid }

    # Returns a list of matches for entries beginning with the given
    # crsid fragment, limited by default to 100 results and a timeout
    # of 3 seconds:
    def get_matches(self, crsid_fragment, limit=100, time_out=3):
        return map(self._format_match,self._fragment_search(crsid_fragment,limit,time_out))
