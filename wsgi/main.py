#!/usr/bin/env python
# encoding: utf8

import time, re, sys, os, os.path, glob
from pprint import pprint, pformat
from urllib import quote
from fnmatch import fnmatch
import bottle
from bottle import (route, run, default_app, 
    request, response, redirect,
    Bottle, static_file, 
    jinja2_template as template, html_escape)

bottle.TEMPLATE_PATH.append('./templates')
# [os.path.join(os.path.realpath(os.path.dirname(__file__)), 'templates') ]

static_app = Bottle()
SITE_STATIC_FILES = '|'.join(map(re.escape, [
    'favicon.ico',
    'robots.txt'
]))
@static_app.route('/<filename:path>')
#@static_app.route('/<filename:re:.*(%s)' % SITE_STATIC_FILES)
def server_static(filename):
    return static_file(filename, root='static')

dict_app = Bottle()
dict_app.hostnames = ['def.est.im',]

@route('/name/<name>')
def nameindex(name='Stranger'):
    return '<strong>Hello, %s!</strong>' % name

@dict_app.route('/')
@dict_app.route('/<query>')
def index(query=''):
    q = request.query.get('q', '')
    if q:
        return redirect('/%s' % quote(q), code=301)
    return template('index.html', query=query.decode('utf8', 'replace'), req=request.query)

tools_app = Bottle()
tools_app.hostnames = ['t.est.im']

@tools_app.route('/ip')
def show_ip():
    return request.environ.get('REMOTE_ADDR', '')

@tools_app.route('/ua')
def show_ua():
    return request.environ.get('HTTP_USER_AGENT', '')


# @ToDo: rewrire http://bottlepy.org/docs/dev/_modules/bottle.html
# http://bottlepy.org/docs/dev/api.html

def application(environ, start_response):
    # how to propagate static resources
    default_app().mount('/static', static_app)

    hostname = environ.get('HTTP_HOST', '')
    all_apps = [tools_app, dict_app]+default_app
    for app in all_apps:
        """
        https://github.com/defnull/bottle/blob/0.11.6/bottle.py#L3226
        default_app() will be the the last registered BottlePy App
        iteration ends at default_app()
        """
        hostnames = getattr(app, 'hostnames', [])
        # print hostname, hostnames, all_apps
        if filter(lambda x:fnmatch(hostname, x), hostnames):
            return app(environ, start_response)
    return default_app()(environ, start_response)


if '__main__' == __name__:
    try:
        import readline, rlcompleter; readline.parse_and_bind("tab: complete")
    except:
        pass

    DEV_APP = tools_app # dict_app
    if getattr(DEV_APP, 'hostnames', None):
        DEV_APP.hostnames.append('10.0.18.3:8002')
    else:
        DEV_APP.hostnames = ['10.0.18.3:8002']
    DEV_APP.mount('/static', static_app)

    __import__('BaseHTTPServer').BaseHTTPRequestHandler.address_string = lambda x:x.client_address[0]
    from django.utils import autoreload
    def dev_server():
        run(application, host='0.0.0.0', port=8002, debug=True)
    autoreload.main(dev_server)
