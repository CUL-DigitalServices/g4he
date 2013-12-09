g4he
====

Gateway to research grant-journal association &amp; Journal comparison site


Author: Digital Services, The University of Cambridge

Last updated: 2013-11-28


------------
Introduction
------------

This README contains an overview of the project and basic configuration options

This functionality was created under a JISC funded project

It uses the Gateway to Research API's from rcuk

for more information please see:

http://blogs.rcuk.ac.uk/files/2013/11/GtR_Application_Programming_Interface_v2.0.pdf
found on http://blogs.rcuk.ac.uk/2013/11/19/gateway-to-research-data-refresh-november-2013/

------------
Installation
------------

Change configuration file: config.json

you will need to insert the correct keys for your institution

The Crsid functionality is currently cambridge university specific, however, 
any ldap enabled institution should be able to extend and use it

---------
Debugging
---------

The javascript has the option to log to the console

see: static/grantaja.js

set nodebug = false to allow debugging

--------
Cacheing
--------

If Caching is enabled then queries will be cached to a SQLite database

This uses the sqlite3 module


---------
Licensing
---------
G4HE - released under Apache License

lxml - shipped under BSD license (http://lxml.de/index.html#license)

libxml2 and libxslt2 - shipped under the MIT license

httplib2 - shipped under the MIT license (https://code.google.com/p/httplib2/)

cherrypy - shipped under BSD license (http://docs.cherrypy.org/stable/intro/license.html)

python-ldap - shipped under the python license (https://pypi.python.org/pypi/python-ldap/)
