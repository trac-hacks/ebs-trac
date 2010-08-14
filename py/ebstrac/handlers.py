# Respond to HTTP requests.
#
# Copyright (c) 2010, Mark Bucciarelli <mark@crosscutmedia.com>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# 

from trac.core import *
from trac.web.main import \
	IRequestHandler, \
	RequestDone

def error(req, data):
	req.send_response(400)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req._send_cookie_headers()
	req.write(data)
	raise RequestDone

def ticketget(env, req, user):
	f = "ticketget"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	db = env.get_db_cnx()
	cursor = db.cursor()
	sql = "SELECT id, summary FROM ticket WHERE owner = %s " \
	    + "AND status != 'closed' ORDER BY id"
	cursor.execute(sql, (user,))

	a = []
	for row in cursor.fetchall():
		tid = row[0]
		tnm = row[1]
		a.append("%6d  %s" % (tid, tnm))
	a.append("\n")
	data = "\n".join(a)
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	raise RequestDone

def posthours(component, req, user, tid):
	f = "posthours"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)

	db = component.env.get_db_cnx()
	cursor = db.cursor()
	sql = "SELECT value FROM ticket_custom " \
	    + "WHERE name = 'actualhours' AND ticket = %s"
	cursor.execute(sql, (tid,))
	row = cursor.fetchone()
	if not row:
		efmt = "%s: ticket %s doesn't have actualhours custom field"
		error(req, efmt % (f, tid))

	val = float(row[0])
	newval = val + float(req.args['data'])
	component.log.debug("%s: setting actualhours to %.2f for ticket %s" % (f, newval, tid))

	sql = "UPDATE ticket_custom SET value = %s " \
	    + "WHERE ticket=%s AND name='actualhours'"
	cursor.execute(sql, (newval, tid))
	db.commit()

	data="OK"
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	raise RequestDone
