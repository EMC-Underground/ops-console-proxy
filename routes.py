# Imports
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler import events
import os
import methods

# Globals
app = Flask(__name__)
scheduler = BackgroundScheduler()
port = int(os.getenv('VCAP_APP_PORT', 8080))

# Uncomment if you need to debug the site
# app.debug = True

# Routes
@app.route('/')
def hello_world():
  return 'Hello World!'

@app.route('/installs/update/', methods=['PUT'])
def update_installs():
  methods.refresh_installs()
  return 'OK'

@app.route('/installs/<gdun>/', methods=['GET'])
def get_install_base(gdun):
  response = methods.get_installs(gdun)
  if response is None:
    abort(500)
  else:
    return response

@app.route('/srs/update/', methods=['PUT'])
def update_srs():
  methods.refresh_srs()
  return 'OK'

@app.route('/srs/<gdun>/', methods=['GET'])
def get_install_base(gdun):
  response = methods.get_srs(gdun)
  if response is None:
    abort(500)
  else:
    return response

# Start App
if __name__ == '__main__':
  scheduler.add_job(methods.refresh_installs, 'interval', hours=24)
  scheduler.add_job(methods.refresh_srs, 'interval', minutes=15)
  scheduler.add_listener(methods.error_listener, events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR)
  scheduler.start()

  try:
    app.run(host='0.0.0.0', port=port)

  except (KeyboardInterrupt, SystemExit):
    # Not strictly necessary if daemonic mode is enabled but should be done if possible
    scheduler.shutdown()
