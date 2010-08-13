from trac.core import *
from trac.web.main import IRequestHandler

def error(req, data):
	req.send_response(400)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req._send_cookie_headers()
	req.write(data)
	raise RequestDone

def ticketget(req):
	if req.method != 'GET':
		handlers.error(req, "not a GET")

	data = "Hello, world!"
	req.send_response(200)
	req.send_header('Content-Type', 'plain/text')
	req.send_header('Content-Length', len(data))
	req._send_cookie_headers()
	req.write(data)
	raise RequestDone
