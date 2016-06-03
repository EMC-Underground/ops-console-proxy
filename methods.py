### All imports ###
import sched, time
import json
import multiprocessing
import requests
import datetime
import boto3

from botocore.client import Config
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
ecs_url = config['ecs_url']
ecs_user_id = config['ecs_user_id']
ecs_user_access_key = config['ecs_user_access_key']
ecs_installs_bucket = config['ecs_installs_bucket']
ess_srs_bucket = config['ess_srs_bucket']
hubot_url = config['hubot_url']

### Methods ###

# listener to give visibility into job completetion
def error_listener(event):
  if event.exception:
    print("The job failed...{0}".format(event.exception))
    print("{0}".format(event.traceback))
  else:
    print("The job worked!")

def refresh_srs():
  # Grab the file
  with open('config.json') as config_file:
    config = json.load(config_file)
  gduns = config['gduns']

  s3 = boto3.resource('s3',use_ssl=False,endpoint_url=ecs_url,aws_access_key_id=ecs_user_id,aws_secret_access_key=ecs_user_access_key,config=Config(s3={'addressing_style':'path'}))

  for gdun in gduns:
    url = srurl + str(gdun['num']) + srurl2
    r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
    if r.status_code == 200:
      sr_data = r.json()
      response = s3.Object(ess_srs_bucket,'{0}.json'.format(gdun['num'])).put(Body=json.dumps(sr_data))
      print(response)
    else:
      hubot_request = requests.post(hubot_url,data={'message':'Failed to update SRs for {0}'.format(gdun['name'])})

# Primary job function
def refresh_installs():
  # Grab the file
  with open('config.json') as config_file:
    config = json.load(config_file)
  gduns = config['gduns']

  s3 = boto3.resource('s3',use_ssl=False,endpoint_url=ecs_url,aws_access_key_id=ecs_user_id,aws_secret_access_key=ecs_user_access_key,config=Config(s3={'addressing_style':'path'}))

  for gdun in gduns:
    url = iburl1+str(gdun['num'])+iburl2
    r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
    if r.status_code == 200:
      array_data = r.json()
      response = s3.Object(ecs_installs_bucket,'{0}.json'.format(gdun['num'])).put(Body=json.dumps(array_data))
      print(response)
    else:
      hubot_request = requests.post(hubot_url,data={'message':'Failed to update installs for {0}'.format(gdun['name'])})
