### All imports ###
import sched, time
import json
import multiprocessing
import requests
import datetime
import boto3
import os
import sys
import memcached

from botocore.client import Config
from requests_ntlm import HttpNtlmAuth
from werkzeug.contrib.cache import MemcachedCache
from werkzeug.contrib.cache import SimpleCache

# Load environment variables
try:
  ecs_url = os.environ['ecs_url']
except KeyError:
  print('ERROR: The ${0} env var hasn\'t been set. Please set it with "export {0}=<{0}>" or '
        '"set {0}=<{0}>", depending on the OS'.format('ecs_url'))
  sys.exit(1)

try:
  ecs_user_id = os.environ['ecs_user_id']
except KeyError:
  print('ERROR: The ${0} env var hasn\'t been set. Please set it with "export {0}=<{0}>" or '
        '"set {0}=<{0}>", depending on the OS'.format('ecs_user_id'))
  sys.exit(1)

try:
  ecs_user_access_key = os.environ['ecs_user_access_key']
except KeyError:
  print('ERROR: The ${0} env var hasn\'t been set. Please set it with "export {0}=<{0}>" or '
        '"set {0}=<{0}>", depending on the OS'.format('ecs_user_access_key'))
  sys.exit(1)

try:
  config_file_name = os.environ['config_file_name']
except KeyError:
  print('ERROR: The ${0} env var hasn\'t been set. Please set it with "export {0}=<{0}>" or '
        '"set {0}=<{0}>", depending on the OS'.format('config_file_name'))
  sys.exit(1)

### Load config files and declare globals ###
config = load_config()

cache = SimpleCache()
username = config['username']
password = config['password']
domain = config['domain']
iburl1 = config['iburl']
iburl2 = config['iburl2']
srurl = config['srurl']
srurl2 = config['srurl2']
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

def load_config():
  s3 = boto3.resource('s3',
                      use_ssl=False,
                      endpoint_url=ecs_url,
                      aws_access_key_id=ecs_user_id,
                      aws_secret_access_key=ecs_user_access_key,
                      config=Config(s3={'addressing_style':'path'}))
  config_bucket = s3.Bucket('app-config-files')
  config_object = config_bucket.Object(config_file_name).get()
  return json.loads(config_object['Body'].read())

def load_gduns():
  s3 = boto3.resource('s3',
                      use_ssl=False,
                      endpoint_url=ecs_url,
                      aws_access_key_id=ecs_user_id,
                      aws_secret_access_key=ecs_user_access_key,
                      config=Config(s3={'addressing_style':'path'}))
  config_bucket = s3.Bucket('pacnwinstalls')
  config_object = config_bucket.Object("PNWandNCAcustomers.json").get()
  return json.loads(config_object['Body'].read())

def get_installs(gdun):
  payload_id = "installs/{0}".format(gdun)
  payload = cache.get(payload_id)
  if payload is None:
    gdunSpecs = load_gduns()
    for gdunSpec in gdunSpecs:
      if gdunSpec['gduns'] == gdun:
        url = iburl1+str(gdunSpec['gduns'])+iburl2
        r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
        if r.status_code == 200:
          payload = json.dumps(r.json())
          cache.set(payload_id,payload,timeout=60*60*24)
          s3 = boto3.resource('s3',
                              use_ssl=False,
                              endpoint_url=ecs_url,
                              aws_access_key_id=ecs_user_id,
                              aws_secret_access_key=ecs_user_access_key,
                              config=Config(s3={'addressing_style':'path'}))
          s3.Object(ecs_installs_bucket,'{0}.json'.format(gdunSpec['gduns'])).put(Body=payload)
          return payload
        else:
          hubot_request = requests.post(hubot_url,data={'message':'Failed to update installs for {0}'.format(gdunSpec['customer'])})
          return None
  return payload

def get_srs(gdun):
  payload_id = "SRs/{0}".format(gdun)
  payload = cache.get(payload_id)
  if payload is None:
    gdunSpecs = load_gduns()
    for gdunSpec in gdunSpecs:
      if gdunSpec['gduns'] == gdun:
        url = srurl+str(gdunSpec['gduns'])+srurl2
        r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
        if r.status_code == 200:
          payload = json.dumps(r.json())
          cache.set(payload_id,payload,timeout=60*60*24)
          s3 = boto3.resource('s3',
                              use_ssl=False,
                              endpoint_url=ecs_url,
                              aws_access_key_id=ecs_user_id,
                              aws_secret_access_key=ecs_user_access_key,
                              config=Config(s3={'addressing_style':'path'}))
          s3.Object(ess_srs_bucket,'{0}.json'.format(gdunSpec['gduns'])).put(Body=payload)
          return payload
        else:
          hubot_request = requests.post(hubot_url,data={'message':'Failed to update SRs for {0}'.format(gdunSpec['customer'])})
          return None
  return payload

def refresh_srs():
  # Grab the file
  # with open('config.json') as config_file:
  #  config = json.load(config_file)
  gduns = load_gduns()

  s3 = boto3.resource('s3',use_ssl=False,endpoint_url=ecs_url,aws_access_key_id=ecs_user_id,aws_secret_access_key=ecs_user_access_key,config=Config(s3={'addressing_style':'path'}))

  for gdun in gduns:
    url = srurl + str(gdun['gduns']) + srurl2
    r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
    if r.status_code == 200:
      sr_data = r.json()
      response = s3.Object(ess_srs_bucket,'{0}.json'.format(gdun['gduns'])).put(Body=json.dumps(sr_data))
      print(response)
    else:
      hubot_request = requests.post(hubot_url,data={'message':'Failed to update SRs for {0}'.format(gdun['customer'])})

# Primary job function
def refresh_installs():
  # Grab the file
  # with open('config.json') as config_file:
  #   config = json.load(config_file)
  gduns = load_gduns()

  s3 = boto3.resource('s3',use_ssl=False,endpoint_url=ecs_url,aws_access_key_id=ecs_user_id,aws_secret_access_key=ecs_user_access_key,config=Config(s3={'addressing_style':'path'}))

  for gdun in gduns:
    url = iburl1+str(gdun['gduns'])+iburl2
    r = requests.get(url,auth=HttpNtlmAuth('{0}\\{1}'.format(domain,username),password))
    if r.status_code == 200:
      array_data = r.json()
      response = s3.Object(ecs_installs_bucket,'{0}.json'.format(gdun['gduns'])).put(Body=json.dumps(array_data))
      print(response)
    else:
      hubot_request = requests.post(hubot_url,data={'message':'Failed to update installs for {0}'.format(gdun['customer'])})
