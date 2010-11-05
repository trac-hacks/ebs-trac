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

# XXX: refactor into handlers subdirectory with one module per resource.
# XXX: Audit that malicious input is handled properly.

from time import time, localtime, strftime, mktime, strptime
from datetime import date, timedelta, datetime
import re
import urllib

# Hack so unit tests run if Trac not installed.
testing = False

try:
	from trac.core import *
	from trac.web.main import \
		IRequestHandler, \
		RequestDone
except ImportError:
	if testing:
		pass

import ebs
import ascii_plotter as plotter

magicname='EvidenceBasedSchedulingTimeClockPage'

def string_to_float(s):
	'''
	In ticket_change, the value can be None, empty string, multiple
	spaces, or a number.

	Handle all these, and return a float.  None, empty and whitespace
	count as 0.0.

		>>> string_to_float(None)
		0.0
		>>> string_to_float('')
		0.0
		>>> string_to_float('    ')
		0.0

	Returns an error page if, after our best efforts, we get a 
	ValueError converting the string to a float.
	'''

	if not s:
		return 0.0

	p = re.compile(r'^\s*$')
	if p.match(s):
		return 0.0

	try:
		return float(s)
	except ValueError, ve:
		error(req, 
		    "can't cast '%s' to float: %s" % (s, ve))

def error(req, data):
	if data[-1] != '\n':
		data += '\n'
	req.send_response(400)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req._send_cookie_headers()
	req.write(data)
	raise RequestDone

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

def get_tickets(com, req):
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
	req.write('\n')
	raise RequestDone

def is_fulltickets(req):
	'''
		/ebs/mark/fulltickets 
		/ebs/mark/fulltickets/
	'''
	a = req.path_info.strip('/').split('/')
	return  len(a) == 3 and a[2] == 'fulltickets'

def get_fulltickets(com, req):
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

	# XXX: not sure if I can reuse a cursor I am scanning.  (I suspect not.)
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
	req.write('\n')
	raise RequestDone

def is_log(req):
	'''
		/ebs/mark/log
		/ebs/mark/log/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 3 and a[2] == 'log'

def lookup_timecards(req, db):
	'''
	Look through ticket_change table and pull hours worked
	by day by user.

	Total hours worked by each user on each day, and return a list of
	(user, day, hours) tuples.
	'''

	cursor = db.cursor()
	cursor1 = db.cursor()

	sql =					\
	    "SELECT "				\
	        "author, "			\
	        "ticket, "			\
		"time, "			\
		"oldvalue, "			\
		"newvalue "			\
	    "FROM "				\
		"ticket_change "		\
	    "WHERE " 				\
	        "field = 'actualhours' "	\
	    "ORDER BY "				\
		"time"
	cursor.execute(sql)

	d = {}
	for row in cursor.fetchall():
		# Split here, not in for in case fetchall() returns nothing.
		user, tid, epoch_seconds, oldvalue, newvalue = row

		v0 = string_to_float(oldvalue)
		v1 = string_to_float(newvalue)
		hours = v1 - v0

		if hours < 0.000001:
			continue

		# Hours that are booked to a different date have the
		# actual date stored in the related comment field.

		sql = 					\
		    "SELECT "				\
			"newvalue "			\
		    "FROM "				\
			"ticket_change " 		\
		    "WHERE "				\
			"author = %s AND "		\
		        "field = 'comment' AND "	\
		        "time = %s AND "		\
		        "newvalue LIKE 'posted on %'"
		cursor1.execute(sql, (user, epoch_seconds))
		row = cursor1.fetchone()
		if row:
			# 'posted on 1285010611, applied to 2010-09-09'
			a1 = row[0].split()
			s = a1[-1]
			year, month, day = map(int, s.split('-'))
			dt = date(year, month, day)
		else:
			dt = date.fromtimestamp(epoch_seconds)

		try:
			d[user, dt] += hours
		except KeyError:
			d[user, dt] = hours

	if not d:
		return ()

	a = []
	for (user, dt), hours in d.items():
		a.append( (user, dt, hours) )

	return sorted(a, 
	    key = lambda x: x[0].lower() + x[1].strftime("%Y%m%d")
	    )


def get_log(com, req):
	'''Lookup all hours logged by user against all tickets.'''
	f = "getlog"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	a = req.path_info.strip('/').split('/')
	user = a[1]

	db = com.env.get_db_cnx()
	cursor = db.cursor()
	cursor1 = db.cursor()

	sql = "SELECT ticket, time, oldvalue, newvalue " \
	    + "FROM ticket_change " \
	    + "WHERE author = %s " \
	    + "AND field = 'actualhours' " \
	    + "ORDER BY time"
	cursor.execute(sql, (user,))

	a = []
	sum = 0
	for row in cursor.fetchall():
		(tid, epoch_seconds, oldvalue, newvalue) = row

		v0 = string_to_float(oldvalue)
		v1 = string_to_float(newvalue)
		hours = v1 - v0

		# Hours that are booked to a different date have the actual
		# date stored in the related comment field.

		sql = "SELECT newvalue FROM ticket_change " \
		    + "WHERE author = %s " \
		    + "AND field = 'comment' " \
		    + "AND time = %s " \
		    + "AND newvalue LIKE 'posted on %'"
		cursor1.execute(sql, (user, epoch_seconds))
		row = cursor1.fetchone()
		if row:
			# 'posted on 1285010611, applied to 2010-09-09'
			a1 = row[0].split()
			dt = a1[-1]
		else:
			tm = localtime(epoch_seconds)
			dt ="%04d-%02d-%02d" % (tm[0], tm[1], tm[2])
		#a.append("%d\t%s\t%.3f" % (tid, dt, hours))
		a.append((tid, dt, hours))
		sum += hours

	# sort by dt			
	a = sorted(a, key=lambda x: x[1])
	a = ["%d\t%s\t%.3f" % (tid, dt, hours) for tid, dt, hours in a]
	a.append("total = %.3f" % (sum,))
	a.append("\n")
	data = "\n".join(a)
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	req.write('\n')
	raise RequestDone

def lookup_todo(req, db, milestone):
	'''
	Return a list of 

		(user, ticket, estimated_hours, actual_hours, left)

	tuples for all tickets that are open for the given milestone.

	We include tickets with a zero estimate.
	'''

	cursor = db.cursor()

	sql = '''SELECT 
		t.id,
		t.owner,
		e.hours as estimate,
		a.hours as actual
	FROM
		ticket t, 
		(
			SELECT 
				ticket,
				CASE value
				    WHEN '' THEN 0.0
				    ELSE CAST(value as float)
				END AS hours
			FROM
				ticket_custom
			WHERE
				name = 'estimatedhours'
		) e,
		(
			SELECT 
				ticket,
				CASE value
				    WHEN '' THEN 0.0
				    ELSE CAST(value as float)
				END AS hours
			FROM
				ticket_custom
			WHERE
				name = 'actualhours'
		) a
	WHERE
		t.id = e.ticket AND
		e.ticket = a.ticket AND
		t.status <> 'closed' AND
		t.milestone = %s
	ORDER BY
		t.owner,
		t.id
	'''

	cursor.execute(sql, (milestone,))

	#
	# NOTE: 
	#	The ticket owner can change.  
	#	The SQL above assumes the last ticket owner "wins";
	#	that is, get's credit for the full estimate and actual
	#	values.
	#
	#	We could dive into the ticket change table and pull out
	#	which users charged which hours, but we'll just keep the
	#	biz rule that once you own a ticket, it stays with you.
	#


	# Trac allows you to put in whatever string for owner.
	# We'll at least catch case differences here.
	rows = sorted(cursor.fetchall(), 
	    key = lambda x: x[1].lower() + "%015d" % x[0])

	a = []
	for (tid, owner, est, act) in rows:
		
		#
		# If a ticket has actual hours, it is supposed to have an
		# estimate.  Enforce this strictly---make the user fix 
		# the data.  With this data situaion, it is not possible
		# to make a good estimate.
		#

		thresh = 0.000001
		if est < thresh and act > thresh:
			efmt = "Ticket %d has actual hours but a "  \
			    "zero estimate---fix data and re-run."
			error(req, efmt % tid)

		# XXX: remove calculated value (est - act) from tuple.
		todo = est - act
		a.append((owner, tid, est, act, todo))

	return tuple(a)


def lookup_history(db):
	'''
	Return a list of 

		(user, ticket, estimated_hours, actual_hours, velocity)

	tuples for all tickets closed as "fixed" that had time booked
	to them.
	'''

	cursor = db.cursor()

	sql = '''SELECT 
		t.id,
		t.owner,
		e.hours as estimate,
		a.hours as actual
	FROM
		ticket t, 
		(
			SELECT 
				ticket,
				CASE value
				    WHEN '' THEN 0.0
				    ELSE CAST(value as float)
				END AS hours
			FROM
				ticket_custom
			WHERE
				name = 'estimatedhours'
		) e,
		(
			SELECT 
				ticket,
				CASE value
				    WHEN '' THEN 0.0
				    ELSE CAST(value as float)
				END AS hours
			FROM
				ticket_custom
			WHERE
				name = 'actualhours'
		) a
	WHERE
		t.id = e.ticket AND
		e.ticket = a.ticket AND
		t.status = 'closed' AND
		t.resolution = 'fixed'
	ORDER BY
		t.owner,
		t.id
	'''

	cursor.execute(sql)

	#
	# NOTE: 
	#	The ticket owner can change.  
	#	The SQL above assumes the last ticket owner "wins";
	#	that is, get's credit for the full estimate and actual
	#	values.
	#
	#	We could dive into the ticket change table and pull out
	#	which users charged which hours, but we'll just keep the
	#	biz rule that once you own a ticket, it stays with you.
	#


	# Trac allows you to put in whatever string for owner.
	# We'll at least catch case differences here.
	rows = sorted(cursor.fetchall(), 
	    key = lambda x: x[1].lower() + "%015d" % x[0])

	a = []
	for (tid, owner, est, act) in rows:
		
		#
		# Tickets with zero actual hours are not interesting.
		# In fact, they are invalid---probably resolution was
		# wrong.  Should have been "Invalid" or "Won't Fix" 
		# instead of "Fixed".
		#

		if not act > 0.0:
			continue

		#
		# Skip tickets with zero estimate as well, that gives
		# a velocity of zero which causes divide-by-zero errors.
		#

		if not est > 0.0:
			continue

		# Per Joel on Softare,
		#
		# 	velocity = estimate / actual
		#

		velocity = est / act
		a.append((owner, tid, est, act, velocity))

	return tuple(a)


def is_history(req):
	'''
		/ebs/mark/history
		/ebs/mark/history/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 3 and a[2] == 'history'

def get_history(com, req):
	'''Report history of hours and tickets across all users.'''
	f = "gethistory"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	a = req.path_info.strip('/').split('/')
	user = a[1]

	db = com.env.get_db_cnx()
	history = lookup_history(db)

	#for (owner, tid, est, act, velocity) in history:
	data = "\n".join(["%-10s %6d %5.2f %5.2f %5.2f" % h for h in history])
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	req.write('\n')
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

def add_hours_to_ticket(com, req, user, tid, delta, dt=None):
	'''Associate the hours someone worked with a ticket.'''

	f = "add_hours_to_ticket"

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

	oldval = string_to_float(row[0])
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
	if not row or not row[0] or string_to_float(row[0]) < 0.01:
		error(req, "You can't charge time until you " \
		    + "have made an estimate.")

	# if any exceptions, rollback everything
	ok = True
	try:
		sql = "UPDATE ticket_custom SET value = %s " \
		    + "WHERE ticket=%s AND name='actualhours'"
		params = (newval, tid)
		cursor.execute(sql, params)

		#
		# Trac stores every ticket field change as a comment.
		# While I don't see where the comment text is that Trac
		# renders, I know it is not stored in the ticket_change
		# table.  However, Trac does enter a comment record, so
		# I'll mimic that behavior here.  
		#

		sql = "SELECT max(oldvalue) FROM ticket_change " \
		    + "WHERE ticket = %s AND field = 'comment'"
		params = (tid, )
		cursor.execute(sql, params)
		row = cursor.fetchone()
		col_n = 0
		if row and row[0]:
			
			#
			# If you have added a new ticket comment that is a reply
			# to an existing comment, then Trac stores the oldvalue
			# as:
			#
			#	<replied_to_comment#>.<new_comment_#>
			#
			# and casting to an int fails.
			#

			last_comment_number = row[0].split('.')[-1]
			col_n = int(last_comment_number)
		col_n += 1

		tm = int(time())

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

		# Here's where we store the actual date the time change is for.
		# (When hours posted were not for today.)
		if dt is not None:
			params[-1] = 'posted on %d, applied to %s' % (tm, dt)
		cursor.execute(sql, params)

		db.commit()
	except Exception, e:
		db.rollback()
		efmt = "%s: %s, sql=%s, params=%s"
		com.log.error(efmt % (f, e, sql, params))
		ok = False

	return ok

def add_hours_and_return(com, req, hours):
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	a = req.path_info.strip('/').split('/')
	user = a[1]
	tid = a[3]
	dt = None
	if len(a) > 5:
		dt = a[5]
	ok = add_hours_to_ticket(com, req, user, tid, hours, dt)
	if ok:
		data="OK"
		req.send_response(200)
		req.send_header('Content-Type', 'plain/text')
		req.send_header('Content-Length', len(data))
		req.write(data)
		req.write('\n')
		raise RequestDone
	else:
		error(req, "Internal error.")

def post_hours(com, req):
	hours = string_to_float(req.args['data'])
	add_hours_and_return(com, req, hours)

def is_minutes(req):
	'''
		 /ebs/mark/ticket/1/minutes
		 /ebs/mark/ticket/1/minutes/
		 /ebs/mark/ticket/1/minutes/2010-08-14
		 /ebs/mark/ticket/1/minutes/2010-08-14/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) in (5, 6) and a[2] == 'ticket' and a[4] == 'minutes'

def post_minutes(com, req):
	hours = string_to_float(req.args['data'])
	hours = hours / 60.
	add_hours_and_return(com, req, hours)

def is_estimate(req):
	'''
		/ebs/mark/ticket/1/estimate
		/ebs/mark/ticket/1/estimate/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 5 and a[2] == 'ticket' and a[4] == 'estimate'

def post_estimate(com, req):
	'''Associate an estimate with a ticket.'''
	f = "post_estimate"
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
		oldval = string_to_float(row[0])
	newval = string_to_float(req.args['data'])
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
			last_comment_number = row[0].split('.')[-1]
			col_n = int(last_comment_number)
		col_n += 1

		dt = int(time())
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
		req.write('\n')
		raise RequestDone
	else:
		error(req, "Internal error.")


def is_clock(req):
	'''
		/ebs/mark/clock
		/ebs/mark/clock/950
	'''
	a = req.path_info.strip('/').split('/')
	
	return len(a) in (3, 4) and a[2] == 'clock'

def lookup_clocktext(cursor):
	'''
	Return None if wiki page does not exist.
	Return '' if wiki page exists, but is empty.
	'''

	global magicname

        cursor.execute(
	    "SELECT "
		"w1.text "
	     "FROM "
		 "wiki w1,"
                 "(SELECT name, max(version) AS ver "
                  "FROM wiki WHERE name = %s GROUP BY name) w2 "
	    "WHERE "
		 "w1.version = w2.ver AND "
		 "w1.name = w2.name",
	     (magicname,)
	     )
	row = cursor.fetchone()
	if row:
		return row[0]
	else:
		return None
	
def update_clocktext(com, req, db, cursor, user, ip, data):
	'''
	We use wiki page to store current state of time clock for all users.

	Format of page is detailed in at least two other places in this 
	module.

	Create wiki page if it doesn't exist.

	Return True on success, False if exception on insert.
	'''

	global magicname

	# Trac wiki versioning is one-based, not zero-based.
	initial_trac_wiki_version = 1

	#
	#  data = ( (uid1, tid1, dt1, tm1), (uid2, tid2, dt2, tm2), ...)
	# 
	# This next step was fragile on initial deployment ("not enough
	# args for format string"), so do it less Pythonically so we
	# can put good info in error message for debugging.
	#

 	#text = "\r".join(["%s %d %s %s" % row for row in data])

	a = []
	for row in data:
		try:
			a.append("%s %s %s %s" % tuple(row))
		# TypeError catches both not enough args and type errors,
		# like trying to print a string with a '%d' format.
		except TypeError, te:
			efmt = "update_clocktext failed: %s raised %s"
			error(req, efmt % (str(row), te))
	text = "\r".join(a)

        cursor.execute(
	    "SELECT max(version) FROM wiki WHERE name = %s GROUP BY name",
	     (magicname,)
	     )
	version = initial_trac_wiki_version
	row = cursor.fetchone()
	version = row[0]

	ok = True
	
	if not version:
		# First time, insert page record.

		sql = "INSERT INTO wiki ("	\
			"name, "	\
			"version, "	\
			"time, "	\
			"author, "	\
			"ipnr, "	\
			"text, "	\
			"readonly "	\
		    ") VALUES ("	\
			"%s, "	\
			"%s, "	\
			"%s, "	\
			"%s, "	\
			"%s, "	\
			"%s, "	\
			"%s "	\
		    ")"
		
		params = (
		    magicname,
		    version,
		    time(), 
		    user,
		    ip, 
		    text,
		    1
		    )
	else:
		# To avoid having a zillion revisions for this one wiki
		# page, we keep re-using version 1.
		sql = \
		    "UPDATE wiki SET "	\
			"text = %s "	\
		    "WHERE "	\
			"name = %s AND version = %s"
		params = (text, magicname, version)

	try:
		cursor.execute(sql, params)
		db.commit()
	except Exception, e:
		db.rollback()
		efmt = "%s: %s, sql=%s, params=%s"
		com.log.error(efmt % (f, e, sql, params))
		ok = False

	return ok


def elapsed_hours(dt, tm):
	'''
	Compute elapsed time between dt ("YYYY-MM-DD") and tm ("HH:MM:SS")
	and now. (EDT)

	If no timezone specified, strptime() uses -1 for the tm_isdst 
	(daylight savings flag), which expresses the time as localtime,
	not UTC.

		>>> import time
		>>> s = "2010-09-30 08:02:41"
		>>> time.strptime(s, "%Y-%m-%d %H:%M:%S")
		(2010, 9, 30, 8, 2, 41, 3, 273, -1)

	This is what we want, as all clock times are handled in server's
	localtime.

	We return the difference in hours.

		>>> t0 = localtime(time.time() - 60 * 60)
		>>> dt = time.strftime("%Y-%m-%d", t0)
		>>> tm = time.strftime("%H:%M:%S", t0)
		>>> elapsed_hours(dt, tm)
		1.0

	Even if only one minute has elapsed.

		>>> t0 = localtime(time.time() - 60 * 1)
		>>> dt = time.strftime("%Y-%m-%d", t0)
		>>> tm = time.strftime("%H:%M:%S", t0)
		>>> "%.3f" % elapsed_hours(dt, tm)
		'0.017'
		
	Method does no rounding.  Thirty seconds is 3/360'ths
	of an hour.

		>>> t0 = localtime(time.time() - 30 * 1)
		>>> dt = time.strftime("%Y-%m-%d", t0)
		>>> tm = time.strftime("%H:%M:%S", t0)
		>>> "%.5f" % elapsed_hours(dt, tm)
		'0.00833'
	'''

	fmt = "%Y-%m-%d %H:%M:%S"
	s = " ".join((dt, tm))
	t0 = mktime(strptime(s, fmt))
	t1 = int(time())
	return (t1 - t0) / float(60 * 60)


def stop_clock(com, req, user, ticketid, dt, tm):
	'''
	Compute elapsed time since dt and tm and add hours to ticket
	for user.

	Return the hours we logged.
	'''

	hours = elapsed_hours(dt, tm)
	ok = add_hours_to_ticket(com, req, user, ticketid, hours)
	if not ok:
		error(req, "Internal error.")
	return hours

def post_clock(com, req):
	'''
	We store clock data in a wiki page with the "magic" name

		EvidenceBasedSchedulingTimeClockPage

	Each row of text is a record, with the following space-delimited
	columns:
		1. user id
		2. ticket id
		3. date
		4. time

	If there is no record for a user, they have no row.  We store the 
	current state only.
	'''

	global magicname
	f = "post_clock"

	a = req.path_info.strip('/').split('/')
	user = a[1]
	tid = None
	if len(a) == 4:
		try:
			tid = int(a[3])
		except TypeError:
			error(req, "%s must be a ticket number" % a[3])

	pathinfouser_must_equal_remoteuser(req, user)

	db = com.env.get_db_cnx()
	cursor = db.cursor()
	s = lookup_clocktext(cursor)
	if s is None:
		s = ''

	# Get clock data from wiki page.  Each row of text is a record,
	# with the following space-delimited columns:
	#
	# 	1. user id
	# 	2. ticket id
	# 	3. date
	# 	4. time
	#
	# Trac uses carriage returns to indicate newlines in wiki text.
	#

	lines = s.split('\r')
	a = []
	last = ()
	for line in lines:
		if not line.strip():
			continue
		columns = line.split(' ')
		if columns[0] == user:
			last = columns[1:]
			# Remove old entry from data array
			continue
		a.append(columns)
	if last:
		lasttid = int(last[0])
		lastdt = last[1]
		lasttm = last[2]

	# $ ebscp <verb> clock
	data = ""
	verb = req.args['data'].lower()
	if verb == 'stop':
		if last:
			hours_logged = stop_clock(com, req, user, *last)
			data = "Logged %.3f hours to ticket %d" % \
			    (hours_logged, lasttid)
		else:
			# nothing running, so nothing to stop.
			pass
	elif verb == 'clear':
		# Leave user out of data array (as it is now)
		pass
	elif verb == 'start':

		if not tid:
			error(req, "What ticket you are starting to work on?")

		if last:

			#
			# Errors are things that should stop a shell
			# script with a non-zero return value.  This case
			# doesn't qualify.
			#

			if tid == lasttid:
				hours = elapsed_hours(lastdt, lasttm)
				msg = "Clock already running for ticket %d, " \
				    "started %.2f hours ago."
				data = msg % (tid, hours)

				# XXX: routine should have one exit point.
				req.send_response(200)
				req.send_header('Content-Type', 'plain/text')
				req.send_header('Content-Length', len(data))
				req.write(data)
				req.write('\n')
				raise RequestDone

			# 
			# We have a running clock for a different ticket.
			# Compute the elapsed time and log the hours to 
			# the ticket.
			#

			hours_logged = stop_clock(com, req, user, *last)
			data = "Logged %.3f hours to ticket %d" % \
			    (hours_logged, lasttid)

		epoch_seconds = int(time())
		a.append( (
		    user, 
		    tid, 
		    strftime("%Y-%m-%d", localtime(epoch_seconds)),
		    strftime("%H:%M:%S", localtime(epoch_seconds))
		    ) )

		if data:
			data += ", and started clock for ticket %d." % tid
		else:
			data = "Started clock for ticket %d." % tid

	# Update the magic wiki page to the next version.

	if not update_clocktext(com, req, db, cursor, user, req.remote_addr, a):
		error(req, 
		    "Boom!  (Probably some DB issue, check server logs.)")

	if not data:
		data="OK"

	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	req.write('\n')
	raise RequestDone


def is_status(req):
	'''
		 /ebs/mark/ticket/1/status
		 /ebs/mark/ticket/1/status/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 5 and a[2] == 'ticket' and a[4] == 'status'

def post_status(com, req):
	'''Change a ticket's status.'''
	f = "post_status"
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

	if oldval in ('new', 'reopened', 'assigned') and newval == 'reopened':
		error(req, 'ticket already open')

	if oldval == 'closed' and newval != 'reopened':
		error(req, "ticket is closed, so the only valid new status " \
		    + "is 'reopened'")

	if oldval in ('new', 'reopened', 'assigned') and newval != 'closed':
		error(req, "ticket is open, only valid new status is " \
		    + "'closed'")

	# If any exceptions, rollback everything.
	ok = True
	try:
		tm = int(mktime(localtime()))

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
		req.write('\n')
		raise RequestDone
	else:
		error(req, "Internal error.")

def is_shipdate(req):
	'''
		/ebs/mark/shipdate/Event%20Demo
		/ebs/mark/shipdate/Event%20Demo/
	'''
	a = req.path_info.strip('/').split('/')
	return len(a) == 4 and a[2] == 'shipdate'

def extract_dev_hrs(req):
	'''
		>>> class T: pass
		>>> t = T()
		>>> t.path_info = '/test/Event%20Demo/%3fmark=8'
		>>> extract_dev_hrs(t)
		{'mark': 8.0}

	If invalid query argument, return an error.
	'''

	s = urllib.unquote(req.path_info)
	
	if '?' not in s:
		return {}
	
	try:
		rval = {}
		path, arglist = s.split('?')
		args = arglist.split('&')
		for arg in args:
			dev, hrs = arg.split('=')
			rval[dev] = string_to_float(hrs)
	except Exception, e:
		error(req, "Unexpected query string format: %s" % e)

	return rval

def history_to_avgvelocity(history):
	'''
		>>> h = [
		... ('dev1', 100, 1.0, 2.0, 0.5),
		... ('dev1', 101, 2.0, 2.5, 0.8),
		... ]
		>>> d = history_to_avgvelocity(h)
		>>> "%.6f" % d['dev1']
		'0.666667'
		
	'''

	te = {}
	ta = {}
	for dev, ticket, est, act, velocity in history:
		try:
			te[dev] += est
		except KeyError:
			te[dev] = est
		try:
			ta[dev] += act
		except KeyError:
			ta[dev] = act
	d = {}
	for dev, est in te.items():
		d[dev] = te[dev]/float(ta[dev])

	return d

def get_shipdate(com, req):
	'''Report shipdate of hours and tickets across all users.'''
	f = "get_shipdate"
	if req.method != 'GET':
		error(req, "%s: expected a GET" % f)
	
	a = req.path_info.strip('/').split('/')
	user = a[1]
	milestone = a[3]

	db = com.env.get_db_cnx()
	cursor = db.cursor()

	if not milestone:
		error(req, 'Invalid URL, no milestone given.')

	# Use unquote_plus() so we can use the plus sign for spaces.
	milestone = urllib.unquote(milestone)
	if '?' in milestone:
		milestone = milestone.split('?')[0]

	todo = lookup_todo(req, db, milestone)

	if not todo:
		data = "No tasks assigned to Milestone '%s'\n" % milestone
		req.send_response(200)
		req.send_header('Content-Type', 'plain/text')
		req.send_header('Content-Length', len(data))
		req.write(data)
		raise RequestDone

	history = lookup_history(db)
	timecards = lookup_timecards(req, db)

	dev_to_dailyworkhours = ebs.availability_from_timecards(timecards)
	dev_hrs = extract_dev_hrs(req)
	for dev in dev_to_dailyworkhours.keys():
		if dev_hrs.has_key(dev):
			dev_to_dailyworkhours[dev] = dev_hrs[dev]

	pdf_data, dev_data = \
	    ebs.history_to_plotdata(history, todo, dev_to_dailyworkhours)
	pdf_plot = plotter.pdf(pdf_data)

	mindt = pdf_data[0][0]
	days = [(dt - mindt).days for dt, density in pdf_data]
	q05 = mindt + timedelta(ebs.percentile(days, 0.05))
	q50 = mindt + timedelta(ebs.percentile(days, 0.50))
	q95 = mindt + timedelta(ebs.percentile(days, 0.95))

	
	a = []

	a.append("Schedule for Milestone '%s'" % milestone)
	a.append("=====================================")
	a.append("Generated on %s" \
	    % datetime.now().strftime("%Y-%m-%d at %H:%M")
	    )
	a.append("")

	a.append("Probability Density of Ship Date")
	a.append("-------------------------------------")
	a.append("")
	a.append(pdf_plot)
	a.append("")
	a.append("       5'th percentile = %s" % q05)
	a.append("      50'th percentile = %s" % q50)
	a.append("      95'th percentile = %s" % q95)
	a.append("")
	a.append("")

	dev_plot = plotter.box_and_whisker(dev_data)

	a.append("Developer Ship Dates")
	a.append("-------------------------------------")
	a.append("")
	a.append(dev_plot)
	a.append("")
	a.append("")

	a.append("Developer Summary")
	a.append("-------------------------------------")
	a.append("")
	a.append("              |  tickets  |  total   | hrs per  |")
	a.append("              |     **    | est. hrs | work day | avg vel")
	a.append("    ----------+-----------+----------+----------+----------")

	#
	# Compute avg. velocity for each developer.
	#

	dev_to_avgvelocity = history_to_avgvelocity(history)
	for dev, hrs in dev_to_dailyworkhours.items():
		tickets = 0
		tot_est = 0
		no_estimate_n = 0
		overbudget_n = 0
		for dev1, ticket, est, act, diff in todo:
			if dev == dev1:
				if est < 0.0001:
					no_estimate_n += 1
                                # If they have an open ticket where
                                # they have charged more time than
                                # estimated, then don't _reduce_ the
                                # hours left of work!  Just skip it.
				elif est >= act:
					tot_est += est - act
					tickets += 1
				else:
					overbudget_n += 1
				
		a.append("     %-8s | %2d/%2d/%2d  | %7.1f  | %7.1f  |%8.2f" \
		    % (dev[:8], tickets, overbudget_n, no_estimate_n, tot_est, 
		    hrs, dev_to_avgvelocity[dev]))
		a.append("    ----------+-----------+----------+----------+----------")
	a.append("")
	a.append("            ** N1/ N2/ N3")
	a.append("                 N1 = open tickets, with act <= est")
	a.append("                 N2 = open tickets over budget (act > est)")
	a.append("                 N3 = open tickets with no estimate")


	data = "\n".join(a)
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req.write(data)
	req.write('\n')
	raise RequestDone

if __name__ == '__main__':
	testing = True
	import doctest
	doctest.testmod()
