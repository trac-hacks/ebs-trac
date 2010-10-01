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

def pdf(pdf_data):
	'''
	Plot a probability density function.

	Data is a list of (x, y) tuples.  X-axis are dates, and y-axis
	is a number bedtween 0 and 100% (probability is represented as
	a percentage).

	Return plot as a string.
	'''

	if not pdf_data:
		return "No data to plot"

	mindt = pdf_data[0][0]
	maxdt = pdf_data[-1][0]

	cmds = 'set terminal dumb\n' \
	    '\n' \
	    'set xdata time\n' \
	    'set timefmt "%%Y-%%m-%%d"\n' \
	    'set format x "%%m-%%d"\n' \
	    'set xtics out nomirror\n' \
	    'unset ytics\n' \
	    'unset title\n' \
	    'unset key\n' \
	    'set yrange [0:100]\n' \
	    'set xrange ["%s":"%s"]\n' \
	    'plot "-" using 1:2 pt 24\n' \
	    % (mindt, maxdt)

	for x, y in pdf_data:
		cmds += "%s %s\n" % (x, y)

	return gnuplot_wrapper(cmds)

def box_and_whisker(dev_data):
	'''
	Plot a box and whisker graph of developer shipdates.

	Data is a list of

		(name, min, quartile1, median, quartile3, max) 

	tuples.
	'''

	raise "plotter.box_and_whisker() is not implemented"

	return ''


