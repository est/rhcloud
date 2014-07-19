#!/usr/bin/env python
# encoding: utf8

import datetime, time, re, sys, os, os.path, glob
from pprint import pprint, pformat
from urllib import quote
from fnmatch import fnmatch

import pystardict

import peewee
import bottle
from bottle import (route, run, default_app, 
    request, response, redirect,
    Bottle, static_file, 
    jinja2_template as template, html_escape)

rel_path = lambda x: os.path.join(os.path.realpath(os.path.dirname(__file__)), x)

bottle.TEMPLATE_PATH.append(rel_path('templates'))
STATIC_ROOT = rel_path('static')

dictionary = pystardict.Dictionary(rel_path('def/stardict-dictd-web1913-2.4.2/dictd_www.dict.org_web1913'))

# db = peewee.SqliteDatabase(rel_path('db.sqlite3'))


def create_db_conn():
    return peewee.MySQLDatabase('backend', 
        host=os.environ.get('OPENSHIFT_MYSQL_DB_HOST', '127.0.0.1'), 
        port=int(os.environ.get('OPENSHIFT_MYSQL_DB_PORT', '3306')),
        user='bu',
        passwd='bupassword@',
    )


class DbConn(object):
    _db_conn = None
    def __new__(cls, *args, **kwargs):
        if cls._db_conn is None:
            cls._db_conn = create_db_conn()
        return cls._db_conn

    def __init__(self):
        self._db_conn.get_conn().errorhandler = self.retry_conn
            
    # handle connect timeout issues
    # poor-man's connection pool
    def retry_conn(self, errorclass, errorvalue):
        if isinstance(errorvalue, self.connection.OperationalError): 
            # and errorvalue[0]==2006:
            # exc, value, tb = sys.exc_info()
            # while tb.tb_next:
            #     tb = tb.tb_next
            #     # print tb.tb_frame.f_locals.keys()
            # frame = tb.tb_frame
            print 're-conn'
            self._db_conn = create_db_conn()
            self._db_conn.get_conn().errorhandler = self.retry_conn
        else:
            print errorclass, errorvalue, type(errorvalue), self.connection.OperationalError


def remote_addr(req):
    proxy = [x.strip() for x in req.environ.get('HTTP_X_FORWARDED_FOR', '').split(',')]
    ip = req.environ.get('REMOTE_ADDR', '').strip().lower()
    # check out OPENSHIFT_INTERNAL_IP
    if ip == req.environ.get('SERVER_ADDR', '').strip().lower():
        return proxy[0]
    else:
        return ip
    
def is_crawler(req):
    ua = req.environ.get('HTTP_USER_AGENT', '')
    ua_l = ua.lower()
    if 'spider' in ua_l or 'bot' in ua_l and not re.search(r'Mozilla[ \/]\d\.\d\W', ua):
        return True
    else:
        return False


# static app for devel

static_app = Bottle()

@static_app.route('/<filename:path>')
#@static_app.route('/<filename:re:.*(%s)' % SITE_STATIC_FILES)
def server_static(filename):
    return static_file(filename, root=STATIC_ROOT)

# default app

@route('/name/<name>')
def nameindex(name='Stranger'):
    return '<strong>Hello, %s!</strong>' % name

# dict app

dict_app = Bottle()
dict_app.hostnames = ['def.est.im', '*.def.est.im']

class DictRecords(peewee.Model):
    user_id = peewee.IntegerField(null=True)
    client_ip = peewee.CharField(max_length=40)
    user_agent = peewee.CharField(max_length=128)
    word = peewee.CharField(max_length=32)
    date = peewee.DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], index=True)

    class Meta:
        database = DbConn()

@dict_app.route(r'/\:history')
def history():
    response.content_type = 'text/plain'
    sq = DictRecords.select(DictRecords.date, DictRecords.word)
    return '\n'.join([ '%s, %s' % (x.date, x.word) for x in sq])

@dict_app.route('/')
@dict_app.route('/<query>')
def index(query=''):
    q = request.query.get('q', '')
    if q:
        return redirect('/%s' % quote(q), code=301)
    q = query.decode('utf8', 'replace')

    try:
        ans = dictionary.dict[q.title()]
    except KeyError:
        response.status = 404
        return template('index.html', query=q, req=request.query)
        
    # try:
    if not is_crawler(request):
        DictRecords.create(
            client_ip=remote_addr(request), 
            user_agent=request.environ.get('HTTP_USER_AGENT', ''),
            word=q,
            date = datetime.datetime.utcnow()
        )
    # except:
    #     s.connect('/var/lib/openshift/5146b48c4382ec6a30000098/app-root/runtime/data/pdb.sock')
    #     print os.path.abspath('pdb.sock')
    #     f = s.makefile()
    #     pdb.Pdb(stdin=f, stdout=f).set_trace()
    return template('index.html', query=q, req=request.query, content=ans)

@dict_app.route('/robots.txt')
def robots():
    response.content_type = 'text/plain'
    return """
Sitemap: http://%s/sitemap.xml

User-agent: *
Disallow: /:status
""".strip() % dict_app.hostnames[0]

@dict_app.route('/alert.js')
def alert():
    response.content_type='application/javascript'
    return 'alert(0)';

@dict_app.route('/sitemap.xml')
def sitemap():
    response.content_type = 'text/xml'
    recent_words = [
        ('hello', '2013-02-28'),
        ('world', '2013-02-28'),
    ]
    recent_words_xml = '\n'.join([
        ('  <url><loc>http://def.est.im/%s</loc>'
        '<changefreq>monthly</changefreq>'
        '<lastmod>%s</lastmod></url>') % (x, y) for x, y in recent_words
    ])
    return """
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>http://def.est.im/</loc><changefreq>hourly</changefreq><lastmod>%s</lastmod></url>
%s
</urlset>
""".strip() % (datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:01:01Z'), recent_words_xml,)
# datetime.date.today().isoformat()

tools_app = Bottle()
tools_app.hostnames = ['t.est.im', '*.t.est.im']


class RequestRecord(peewee.Model):
    user_id = peewee.IntegerField(null=True)
    client_ip = peewee.CharField(max_length=80)
    user_agent = peewee.CharField(max_length=140)
    referer = peewee.CharField(max_length=256)
    item = peewee.CharField(max_length=32)
    date = peewee.DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], index=True)

    class Meta:
        database = DbConn()


@tools_app.route('/ip<ext:re:\.?\w*>')
def ip(ext):
    "Client IP address"
    return remote_addr(request)

@tools_app.route('/ip/history')
def ip_history():
    response.content_type = 'text/plain'
    return ''

@tools_app.route('/ua<ext:re:\.?\w*>')
def user_agent(ext):
    "Client User-agent"
    return request.environ.get('HTTP_USER_AGENT', '')

@tools_app.route('/uid<ext:re:\.?\w*>', group='test')
def uid_tool(ext):
    return 'uid inter lookup tool.'

@tools_app.route('/echo<ext:re:\.?\w*>')
def echo_headers(ext):
    response.content_type = 'text/plain'
    return pformat(request.environ)


@tools_app.route('/h<ext:re:\.?\w*>')
def http_headers(ext):
    response.content_type = 'text/plain'
    return '\n'.join([
        '%s:\t%s' % ('-'.join(map(str.title, k[5:].split('_'))) , v) for k, v in request.environ.iteritems()
        if k.lower().startswith('http_')
    ])

@tools_app.route('/robots.txt')
def robots():
    response.content_type = 'text/plain'
    return """
User-agent: *
Disallow: /:status

Sitemap: http://%s/sitemap.xml
""".strip() % tools_app.hostnames[0] 

@tools_app.route('/')
def index():
    tools = [{
        'path': tools_app.router.build(x.rule, ext=''), 
        'name': x.callback.__name__.replace('_', ' '), 
        'desc': x.callback.__doc__ or ''} for x in tools_app.routes 
        if x.rule.endswith('<ext:re:\.?\w*>')]
    return template('tools_app_index.html', tools=tools)



# fix db conn timeout issue
# mysql> SET SESSION wait_timeout = 60;
# mysql> SHOW VARIABLES LIKE 'wait_timeout';




# @ToDo: rewrire http://bottlepy.org/docs/dev/_modules/bottle.html
# http://bottlepy.org/docs/dev/api.html

def application(environ, start_response):
    # how to propagate static resources
    # default_app().mount('/static', static_app)


    p = environ.get('PATH_INFO', '')
    f = os.path.join(STATIC_ROOT, 'root') + p
    if '.' in p and '..' not in p and '/' not in p[1:] and \
        os.path.isfile(f):
        environ['PATH_INFO'] = '/root' + p
        return static_app(environ, start_response)


    hostname = environ.get('HTTP_HOST', '').lower()
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

    DEV_APP = dict_app # dict_app

    local_ip = ['10.*', '127.*', '192.*']
    if getattr(DEV_APP, 'hostnames', None):
        DEV_APP.hostnames.extend(local_ip)
    else:
        DEV_APP.hostnames = local_ip
    DEV_APP.mount('/static/', static_app)

    __import__('BaseHTTPServer').BaseHTTPRequestHandler.address_string = lambda x:x.client_address[0]

    DictRecords.create_table(fail_silently=True)
    # from django.utils import autoreload
    # def dev_server():
    #     run(application, host='0.0.0.0', port=8002, debug=True)
    # autoreload.main(dev_server)
    run(application, host='0.0.0.0', port=8002, reload=True)
