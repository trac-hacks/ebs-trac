from trac.core import *
from trac.web.main import IRequestHandler

def error(req, data):
	req.send_response(400)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req._send_cookie_headers()
	req.write(data)

def ticketget(env, req, user):
	f = "ticketget"
	if req.method != 'GET':
		return handlers.error(req, "%s: expected a GET" % f)
	
	db = env.get_db_cnx()
	cursor = db.cursor()
	sql = "SELECT id, summary FROM ticket WHERE owner = %s " \
	    + "AND status != 'closed' ORDER BY id"
	cursor.execute(sql, (user,))

	a = ["All open tasks for user %s:" % (user,)]
	for row in cursor.fetchall():
		tid = row[0]
		tnm = row[1]
		a.append("%6d  %s" % (tid, tnm))
	a.append("\n")
	data = "\n".join(a)
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	#req._send_cookie_headers()
	req.write(data)
