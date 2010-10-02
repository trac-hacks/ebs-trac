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

#		s = '''set terminal dumb
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
		return "No probability density data to plot"

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

	if not dev_data:
		return "No developer data to plot"

	#
	# By default, gnuplot only plots box-and-whisker plots vertically.
	# There is a work around, but I didn't bother looking it up as I'm
	# already at velocity 2.0 for this ticket.  :)
	#
	# So, we need an integer for the x-value of each box, so map dev
	# names to integers here.  We'll use the names as the tic labels.
	#

	# for xrange
	xmin = 0

	i = xmin + 1
	dev_to_x = {}
	for row in dev_data:
		dev_to_x[row[0]] = i
		i += 1
	xmax = i 

	# set xtics ('mark' 1, 'paul' 2)
	a = []
	for dev, idx in dev_to_x.items():
		a.append("\"%s\" %d" % (dev, idx))
	xticlabels = ",".join(a)
		
	cmds = 'set terminal dumb\n' \
	    '\n' \
	    'set ydata time\n' \
	    'set timefmt "%%Y-%%m-%%d"\n' \
	    'set format y "%%m-%%d"\n' \
	    '\n' \
	    'set ytics out nomirror\n' \
	    'unset mytics\n' \
	    '\n' \
	    'set xtics (%s)\n' \
	    'unset mxtics\n' \
	    '\n' \
	    'unset key\n' \
	    'unset border\n' \
	    '\n' \
	    'set bars 4.0\n' \
	    'set style fill empty\n' \
	    'set xrange [%d:%d]\n' \
	    'plot "-" using 1:3:2:6:5 with candlesticks\n' \
	    % (xticlabels, xmin, xmax)

	#
	# Example of what input data should look like:
	#
	#	3 2010-10-04 2010-10-19 2010-11-01 2010-11-19 2011-03-15
	#

	for dev, min, q1, q2, q3, max in dev_data:
		cmds += "%d %s %s %s %s %s\n" % \
		    (dev_to_x[dev], min, q1, q2, q3, max)

	return gnuplot_wrapper(cmds)
