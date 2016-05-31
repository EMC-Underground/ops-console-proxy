### All imports ###
import sched, time
import json
import multiprocessing
import requests
import datetime
from requests_ntlm import HttpNtlmAuth

### Load config files and declare globals ###
with open('config.json') as config_file:
  config = json.load(config_file)

username = config['username']
password = config['password']
domain = config['domain']
iburl1 = config['iburl']
iburl2 = config['iburl2']
srurl = config['srurl']
srurl2 = config['srurl2']
auth_token = config['auth_token']

### Methods ###

# listener to give visibility into job completetion
def error_listener(event):
  if event.exception:
    print("The job failed...{0}".format(event.exception))
    print("{0}".format(event.traceback))
  else:
    print("The job worked!")

def refresh_srs():
    url = srurl + str(gdun) + srurl2
    r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
    if r.status_code == 200:
      sr_data = r.json()


# Primary job function
def refresh_installs():
  url = iburl1+str(gdun)+iburl2
  r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
  if r.status_code == 200:
    array_data = r.json()
