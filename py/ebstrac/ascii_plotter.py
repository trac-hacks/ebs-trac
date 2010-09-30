'''
Generate ASCII plots.
'''

import subprocess

def gnuplot_wrapper(plotcommands):
	'''
	Wrapper around gnuplot.  Pass in string that includes a list
	of commands.
	'''

	try:
		p = subprocess.Popen(
		    'gnuplot',
		    bufsize = 0,		# unbuffered
		    stdin = subprocess.PIPE,
		    stdout = subprocess.PIPE,
		    stderr = subprocess.PIPE
		    )

		#
		# Wait for process to end and don't deadlock on 
		# lots of stderr output.
		#

#		s = '''set terminal dumb 70 20
#plot sin(x)
#'''
		(l1, l2) = p.communicate(plotcommands)
		if p.returncode < 0:
			raise "gnuplot died with signal %d" %  -p.returncode
		elif p.returncode != 0:
			raise "gnuplot failed, stderr = %s" % ''.join(l2)
		else:
			# return code = 0, normal termination.
			pass
	except OSError, e:
		raise

	return l1

def percentile(pdf_data, n):
	'''
	Given list of (x,y) tuples, compute the n'th percentile of the
	y-values.

	'''

	raise "plotter.percentile() not implemented."

	return None

	
def pdf(pdf_data):
	'''
	Plot a probability density function.

	Data is a list of (x, y) tuples.  X-axis are dates, and y-axis
	is a number bedtween 0 and 100% (probability is represented as
	a percentage).

	Return plot as a string.
	'''

	raise "plotter.pdf() is not implemented"

	return ''

def box_and_whisker(dev_data):
	'''
	Plot a box and whisker graph of developer shipdates.

	Data is a list of

		(name, min, quartile1, median, quartile3, max) 

	tuples.
	'''

	raise "plotter.box_and_whisker() is not implemented"

	return ''


