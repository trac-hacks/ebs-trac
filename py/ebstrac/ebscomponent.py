# Evidence-Based Scheduling Trac component.
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

import re

from trac.core import *
from trac.web.main import IRequestHandler

import ebstrac

class EBSComponent(Component):
	implements(IRequestHandler)

	def __init__(self):
		'''register handlers'''
		h = ebstrac.handlers
		self.handlers = (
		    (h.is_tickets, h.get_tickets),
		    (h.is_fulltickets, h.get_fulltickets),
		    (h.is_log, h.get_log),
		    (h.is_hours, h.post_hours),
		    (h.is_minutes, h.post_minutes),
		    (h.is_estimate, h.post_estimate),
		    (h.is_status, h.post_status),
		    (h.is_history, h.get_history),
		    (h.is_clock, h.post_clock),
		    (h.is_shipdate, h.get_shipdate),
		)
	
	def match_request(self, req):
		return req.path_info.startswith('/ebs/')

	def process_request(self, req):

		self.log.debug("PATH_INFO: %s" % (req.path_info,))

		for testfcn, handlerfcn in self.handlers:
			rval = testfcn(req)
			#self.log.debug("%s: %s" % (testfcn.__doc__, rval))
			if rval:
				handlerfcn(self, req)

		# Handlers raise a ResponseDone when done, so we only get
		# here if the request was not matched with a registered
		# handler.

		ebstrac.handlers.error(req, "invalid url")
