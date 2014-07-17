#!/usr/bin/python

    #===========================================================================
    # keep a version.txt file locally
    # have a version.txt file on the web
    # set up a cron job that grabs the version.txt file, downloads it, and compares it
    # if version is different, grab the update.zip. maybe this file could be part of the version.txt
    # unzip to ./files
    # chmod the script
    # run the script
    # clean up
    # update the version file to the new version
    #===========================================================================

import subprocess, json, urllib

download_root = "http://ispresso.net/sites/ispresso.net/files/"
version_file = "version.json"

urllib.urlretrieve (download_root + version_file, "webversion.json")

localversion = None
webversion = None
webfile = None

with open("version.json") as localfile:
    filecontents = json.load(localfile)
    localversion = filecontents["version"]
    
with open("webversion.json") as webfile:
    filecontents = json.load(webfile)
    webversion = filecontents["version"]
    webfile = filecontents["file"]

print "localversion = " + str(localversion) + " and webversion = " + str(webversion)

if float(localversion) < float(webversion):
    print "we are going to download"

    urllib.urlretrieve (download_root + webfile, "update.zip")

    unzip_cmd = "unzip update.zip -d files ".split()
    subprocess.call(unzip_cmd)
    
    chmod_cmd = "chmod +x /var/www/update/files/update.sh".split()
    subprocess.call(chmod_cmd)
    
    exec_cmd = "bash /var/www/update/files/update.sh".split()
    subprocess.call(exec_cmd)







