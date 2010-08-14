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

import time

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
	'''Lookup all open (status != closed) tickets for a user.'''
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
	'''Associate the hours someone worked with a ticket.'''
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

	oldval = float(row[0])
	delta = float(req.args['data'])
	newval = oldval + delta
	if newval < 0:
		efmt = "%s: can't end up with negative hours, task only has %s hours"
		error(req, efmt % (f, oldval))
	fmt = "%s: %s logged %.4f hours to ticket %s (new total=%s)"
	component.log.info(fmt % (f, user, delta, tid, newval))

	#
	# Don't allow time to be booked until an estimate has been made.
	#

	sql = "SELECT value FROM  ticket_custom " \
	    + "WHERE ticket=%s AND name='estimatedhours'"
	params = (tid,)
	cursor.execute(sql, params)
	row = cursor.fetchone()
	if not row:
		error(req, "You can't charge time until you " \
		    + "have made an estimate.")

	# if any exceptions, rollback everything
	ok = True
	try:
		sql = "UPDATE ticket_custom SET value = %s " \
		    + "WHERE ticket=%s AND name='actualhours'"
		params = (newval, tid)
		cursor.execute(sql, params)

		# Trac stores every ticket field change as a comment.
		# While I don't see where the comment text is that Trac
		# renders, I know it is not stored in the ticket_change
		# table.  However, Trac does enter a comment record, so
		# I'll mimic that behavior here.  
		sql = "SELECT max(oldvalue) FROM ticket_change " \
		    + "WHERE ticket = %s AND field = 'comment'"
		params = (tid, )
		cursor.execute(sql, params)
		row = cursor.fetchone()
		col_n = 0
		if row:
			col_n = int(row[0])
		col_n += 1

		dt = int(time.mktime(time.localtime()))
		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = (tid, dt, user, 'actualhours', oldval, newval)
		cursor.execute(sql, params)

		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = (tid, dt, user, 'comment', col_n, '')
		cursor.execute(sql, params)

		db.commit()
	except Exception, e:
		db.rollback()
		efmt = "%s: %s, sql=%s, params=%s"
		component.log.error(efmt % (f, e, sql, params))
		ok = False

	if ok:
		data="OK"
		req.send_response(200)
		req.send_header('Content-Type', 'plain/text')
		req.send_header('Content-Length', len(data))
		req.write(data)
		raise RequestDone
	else:
		error(req, "Internal error.")
