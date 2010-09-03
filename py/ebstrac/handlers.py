# Various responses to an HTTP request.
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

# XXX: refactor this into a handlers sub-package; e.g., handers/tickets.py

def user_must_own_ticket(req, cursor, tid, user):
	'''Return True or False.'''
	sql = "SELECT owner FROM ticket WHERE id = %s"
	cursor.execute(sql, (tid,))
	row = cursor.fetchone()
	if not row:
		efmt = "ticket %s not found."
		error(req, efmt % (tid,))
	if row[0] != user:
		efmt = "ticket %s not owned by %s."
		error(req, efmt % (tid, user))

def pathinfouser_must_equal_remoteuser(req, user):
	'''The PATH_INFO user comes from the URL of the resource.
	The REMOTE_USER is the user that logged in during the HTTP
	authentication.  This method returns an error page if the two
	are not the same user.'''

	f = "pathinfouser_must_equal_remoteuser"

	if user is None:
		error(req, "%s: user is None" % (f,))
	
	u1 = req.remote_user
	if u1 != user:
		error(req, "User name mismatch ('%s' != '%s')." % (u1, user))

def is_tickets(req):
	'''
		/ebs/mark/tickets 
		/ebs/mark/tickets/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 3 and a[2] == 'tickets'

def gettickets(com, req):
	'''Lookup all open (status != closed) tickets for a user.'''
	f = "gettickets"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	a = req.path_info.strip('/').split('/')
	user = a[1]

	db = com.env.get_db_cnx()
	cursor = db.cursor()
	sql = "SELECT t.id, t.summary FROM ticket t, enum e " \
	    + "WHERE t.owner = %s AND e.name = t.priority " \
	    + "AND e.type = 'priority' " \
	    + "AND t.status != 'closed' ORDER BY e.value, t.id"
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

def is_fulltickets(req):
	'''
		/ebs/mark/fulltickets 
		/ebs/mark/fulltickets/
	'''
	a = req.path_info.strip('/').split('/')
	return  len(a) == 3 and a[2] == 'fulltickets'

def getfulltickets(com, req):
	'''Lookup all open (status != closed) tickets for a user.'''
	f = "getfulltickets"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	a = req.path_info.strip('/').split('/')
	user = a[1]

	db = com.env.get_db_cnx()
	cursor = db.cursor()

	sql = "SELECT id, summary, status, description " \
	    + "FROM ticket " \
	    + "WHERE owner = %s AND status != 'closed' " \
	    + "ORDER BY id"
	cursor.execute(sql, (user,))

	# XXX: not sure if I can reuse a cursor I am scanning.  (i suspect not.)
	c1 = db.cursor()
	sqlact = "SELECT value FROM ticket_custom " \
	    + "WHERE name = 'actualhours' AND ticket = %s"
	sqlest = "SELECT value FROM ticket_custom " \
	    + "WHERE name = 'estimatedhours' AND ticket = %s"

	a = []
	for (id, summary, status, desc) in cursor.fetchall():
		c1.execute(sqlact, (id,))
		act = 0
		row = c1.fetchone()
		if row: 
			act = row[0]
		c1.execute(sqlest, (id,))
		est = 0
		row = c1.fetchone()
		if row: 
			est = row[0]
		fmt = "-----------------------------------------------------------------\n" \
		    + "id      : %s\n" \
		    + "summary : %s\n" \
		    + "estimate: %s\n" \
		    + "actual  : %s\n" \
		    + "status  : %s\n" \
		    + "-----------------------------------------------------------------\n" \
		    + "%s\n"
		a.append(fmt % (id, summary, est, act, status, desc))
	a.append("\n")
	data = "\n".join(a)
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	raise RequestDone

def is_log(req):
	'''
		/ebs/mark/log
		/ebs/mark/log/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 3 and a[2] == 'log'

def getlog(com, req):
	'''Lookup all hours logged by user against all tickets.'''
	f = "getlog"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	a = req.path_info.strip('/').split('/')
	user = a[1]

	db = com.env.get_db_cnx()
	cursor = db.cursor()

	sql = "SELECT ticket, time, oldvalue, newvalue " \
  	    + "FROM ticket_change " \
	    + "WHERE author = %s " \
	    + "AND field = 'actualhours' " \
	    + "ORDER BY time"
	cursor.execute(sql, (user,))

	a = []
	sum = 0
	for row in cursor.fetchall():
		(tid, local_epoch_seconds, oldvalue, newvalue) = row
		#
		# After installing ebstrac plugin, when I closed old tickets
		# they got 'actualhours' ticket_change records where both the
		# old and the new value were empty.  These records raised
		# a TypeError when trying to convert to a float.
		#

		if not oldvalue and not newvalue:
			continue

		v0 = float(oldvalue)
		v1 = float(newvalue)
		hours = v1 - v0
		tm = time.localtime(local_epoch_seconds)
		a.append("%d\t%04d-%02d-%02d %02d:%02d\t%.3f" % (\
		    tid, 
		    tm[0],
		    tm[1],
		    tm[2],
		    tm[3],
		    tm[4],
		    hours
		    )
		)
		sum += hours
	a.append("total = %.3f" % (sum,))
	a.append("\n")
	data = "\n".join(a)
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	raise RequestDone


def is_hours(req):
	'''
		 /ebs/mark/ticket/1/hours
		 /ebs/mark/ticket/1/hours/
		 /ebs/mark/ticket/1/hours/2010-08-14
		 /ebs/mark/ticket/1/hours/2010-08-14/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) in (5, 6) and a[2] == 'ticket' and a[4] == 'hours'

def posthours(com, req):
	'''Associate the hours someone worked with a ticket.'''
	f = "posthours"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)

	a = req.path_info.strip('/').split('/')
	user = a[1]
	tid = a[3]
	dt = None
	if len(a) > 5:
		dt = a[5]

	db = com.env.get_db_cnx()
	cursor = db.cursor()

	user_must_own_ticket(req, cursor, tid, user)

	pathinfouser_must_equal_remoteuser(req, user)

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
		efmt = "%s: can't end up with negative hours, " \
		    + "task only has %s hours"
		error(req, efmt % (f, oldval))
	fmt = "%s: %s logging %.4f hours to ticket %s (new total=%s)"
	com.log.info(fmt % (f, user, delta, tid, newval))

	#
	# Don't allow time to be booked until an estimate has been made.
	#

	sql = "SELECT value FROM  ticket_custom " \
	    + "WHERE ticket=%s AND name='estimatedhours'"
	params = (tid,)
	cursor.execute(sql, params)
	row = cursor.fetchone()
	if not row or not row[0] or float(row[0]) < 0.01:
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
		if row and row[0]:
			col_n = int(row[0])
		col_n += 1

		tm = int(time.mktime(time.localtime()))

		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = (tid, tm, user, 'actualhours', oldval, newval)
		cursor.execute(sql, params)

		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = [tid, tm, user, 'comment', col_n, '']
		if dt is not None:
			params[-1] = 'posted on %d, applied to %s' % (tm, dt)
		cursor.execute(sql, params)

		db.commit()
	except Exception, e:
		db.rollback()
		efmt = "%s: %s, sql=%s, params=%s"
		com.log.error(efmt % (f, e, sql, params))
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

def is_estimate(req):
	'''
		/ebs/mark/ticket/1/estimate
		/ebs/mark/ticket/1/estimate/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 5 and a[2] == 'ticket' and a[4] == 'estimate'

def postestimate(com, req):
	'''Associate an estimate with a ticket.'''
	f = "postestimate"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)

	a = req.path_info.strip('/').split('/')
	user = a[1]
	tid = a[3]

	db = com.env.get_db_cnx()
	cursor = db.cursor()

	user_must_own_ticket(req, cursor, tid, user)

	pathinfouser_must_equal_remoteuser(req, user)

	sql = "SELECT value FROM ticket_custom " \
	    + "WHERE name = 'estimatedhours' AND ticket = %s"
	cursor.execute(sql, (tid,))
	row = cursor.fetchone()
	if not row:
		efmt = "%s: ticket %s doesn't have estimatedhours custom field"
		error(req, efmt % (f, tid))

	oldval = 0.0
	if row[0]:
		oldval = float(row[0])
	newval = float(req.args['data'])
	if newval < 0:
		efmt = "%s: can't have a negative estimate"
		error(req, efmt % (f, ))
	fmt = "%s: %s set estimate to %.4f hours for ticket %s (was %.4f)"
	com.log.info(fmt % (f, user, newval, tid, oldval))

	# if any exceptions, rollback everything
	ok = True
	try:
		sql = "UPDATE ticket_custom SET value = %s " \
		    + "WHERE ticket=%s AND name='estimatedhours'"
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
		if row and row[0]:
			col_n = int(row[0])
		col_n += 1

		dt = int(time.mktime(time.localtime()))
		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = (tid, dt, user, 'estimatedhours', oldval, newval)
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
		com.log.error(efmt % (f, e, sql, params))
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


def is_status(req):
	'''
		 /ebs/mark/ticket/1/status
		 /ebs/mark/ticket/1/status/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 5 and a[2] == 'ticket' and a[4] == 'status'

def poststatus(com, req):
	'''Change a ticket's status.'''
	f = "poststatus"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)

	a = req.path_info.strip('/').split('/')
	user = a[1]
	tid = a[3]

	db = com.env.get_db_cnx()
	cursor = db.cursor()

	user_must_own_ticket(req, cursor, tid, user)

	pathinfouser_must_equal_remoteuser(req, user)

	sql = "SELECT status, resolution FROM ticket WHERE id = %s"
	cursor.execute(sql, (tid,))

	row = cursor.fetchone()
	oldval = row[0]
	oldresolutionval = row[1]
	newval = req.args['data']

	# Sanity checking on status. (SQL will put in whatever we say.)

	if oldval == 'closed' and newval == 'closed':
		error(req, 'ticket already closed')

	if oldval in ('new', 'reopened') and newval == 'reopened':
		error(req, 'ticket already open')

	if oldval == 'closed' and newval != 'reopened':
		error(req, "ticket is closed, so the only valid new status " \
		    + "is 'reopened'")

	if oldval in ('new', 'reopened') and newval != 'closed':
		error(req, "ticket is open, only valid new status is " \
		    + "'closed'")

	# If any exceptions, rollback everything.
	ok = True
	try:
		tm = int(time.mktime(time.localtime()))

		resolution = ''
		if newval == 'closed':
			resolution = 'fixed'

		sql = "UPDATE ticket " \
		    + "SET status = %s, resolution = %s "\
		    + "WHERE id = %s"
		params = (newval, resolution, tid)
		cursor.execute(sql, params)

		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = (tid, tm, user, 'status', oldval, newval)
		cursor.execute(sql, params)

		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = (tid, tm, user, 'resolution', oldresolutionval,
		    resolution)
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
		if row and row[0]:
			col_n = int(row[0])
		col_n += 1

		sql = "INSERT INTO ticket_change ( " \
		    + "ticket, time, author, field, oldvalue, newvalue" \
		    + ") VALUES ( " \
		    + "%s, %s, %s, %s, %s, %s" \
		    + ")"
		params = [tid, tm, user, 'comment', col_n, '']
		cursor.execute(sql, params)

		db.commit()

	except Exception, e:
		db.rollback()
		efmt = "%s: %s, sql=%s, params=%s"
		com.log.error(efmt % (f, e, sql, params))
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

