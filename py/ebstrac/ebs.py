'''
Evidence-based scheduling routines.
'''

from datetime import timedelta, date
import random

def count_workdays(dt0, dt1, daysoff=(5,6)):
	'''
	Return the all weekdays between and including the two dates.

		>>> from datetime import date
		>>> dt0 = date(2010, 9, 3)  # Friday
		>>> dt1 = date(2010, 9, 6)  # Monday
		>>> d = count_workdays(dt0, dt1)
		>>> d.next()
		datetime.date(2010, 9, 3)
		>>> d.next()
		datetime.date(2010, 9, 6)
	'''

	for n in range((dt1 - dt0).days + 1):
		d = dt0 + timedelta(n)
		if d.weekday() not in daysoff:
			yield d

def advance_n_workdays(dt0, n, daysoff = (5,6)):
	'''
	Count forward n work days.

		>>> from datetime import date
		>>> dt0 = date(2010, 9, 3)  # Friday

	If we need one day of work, we return a date that is one
	work day later than the date passed in.
	
		>>> advance_n_workdays(dt0, 1)
		datetime.date(2010, 9, 6)

	If we need five days of work, we return a date that is
	five work days later than the date passed in.

		>>> advance_n_workdays(dt0, 5)
		datetime.date(2010, 9, 10)

	We can use this to advance to the first work day if the current
	day falls on a weekend.

		>>> dt0 = date(2010, 9, 4)  # Saturday
		>>> advance_n_workdays(dt0, 0)
		datetime.date(2010, 9, 6)

	Note that to be consistent, this means that if we want to
	advance one work day from a Saturday, we end up on a Tuesday.

		>>> dt0 = date(2010, 9, 4)  # Saturday
		>>> advance_n_workdays(dt0, 1)
		datetime.date(2010, 9, 7)
	'''

	#
	# We start counting on the first work day.  If the start date
	# passed in is not a work day, then advance to the first one.
	#

	looplimit = 8
	i = 0
	while dt0.weekday() in daysoff:
		i += 1
		dt0 += timedelta(1)
		if i > looplimit:
			raise ValueError("Logic error, looping forever.")


	day_n = 1
	workday_n = 0
	while workday_n < n:
		d = dt0 + timedelta(day_n)
		if d.weekday() not in daysoff:
			workday_n += 1
		day_n += 1

	return  dt0 + timedelta(day_n - 1)

def availability_from_timecards(timecards):
	'''
	Compute average hours available per weekday per dev.

			   September 2010   
			Su Mo Tu We Th Fr Sa
				  1  2  3  4
			 5  6  7  8  9 10 11
			12 13 14 15 16 17 18
			19 20 21 22 23 24 25
			26 27 28 29 30      
                    
		>>> from datetime import date
		>>> day1 = date(2010, 9, 3)
		>>> day2 = date(2010, 9, 6)
		>>> timecards = (
		... ('mark', day1, 10.0),
		... ('mark', day2, 8.0),
		... ('paul', day1, 4.0),
		... )
		>>> d = availability_from_timecards(timecards)
		>>> d['mark']
		9.0
		>>> d['paul']
		4.0
	'''

	if not timecards:
		return {}

	totalhours = {}
	firstday = {}
	lastday = {}
	for dev, dt, hours in timecards:
		try:
			if lastday[dev] < dt:
				lastday[dev] = dt
		except KeyError:
			lastday[dev] = dt
		try:
			if dt < firstday[dev]:
				firstday[dev] = dt
		except KeyError:
			firstday[dev] = dt
		try:
			totalhours[dev] += hours
		except KeyError:
			totalhours[dev] = hours

	averages = {}
	for dev in totalhours.keys():
		dt0 = firstday[dev]
		dt1 = lastday[dev]
		n = len(list(count_workdays(dt0, dt1)))
		if n > 0:
			averages[dev] = totalhours[dev]/float(n)

	return averages
		

def history_to_dict(history):
	'''
	Turn history tuples into a dictionary where we can lookup the
	list of velocities for a given dev.

		>>> history = (
		... ('mark', 1, 1.0, 1.0, 1.0),
		... )
		>>> history_to_dict(history)
		{'mark': [1.0]}
	'''

	if not history:
		return {}

	d = {}
	for dev, ticket, est, act, velocity in history:
		if not d.has_key(dev):
			d[dev] = []
		d[dev].append(velocity)
	return d

def list_to_pdf(list):
	'''
	Given a list dates, return the probability density function.

	The return value is (element, probability_density) tuples.
	We represent the density as the closest integer percentage.

		>>> list_to_pdf( (3, 1, 1, 2) )
		((1, 50), (2, 75), (3, 100))
	'''

	trials_n = len(list)

	count = {}
	for x in list:
		try:
			count[x] += 1
		except KeyError:
			count[x] = 1
	a = []
	for x, n in count.items():
		a.append( (x,  n / float(trials_n)) )
	a = sorted(a, key = lambda x: x[0])
	pdf = []
	density = 0.0
	for x, probability  in a:
		density += probability
		percentage = int(0.5 + density * 100.0)
		pdf.append( (x, percentage) )

	return tuple(pdf)

def percentile(a, p):
	'''
	Given a list of elements, return the percentile.

		>>> percentile( (1,2,3), 0.50)
		2
	'''

	n = len(a)
	i = int(n * p)
	if abs((n * p) - i) < 0.000001:
		q = (a[i] + a[i - 1]) / 2.
	else:
		q = a[i]
	return q
	
def quartiles(a):
	'''
	Given list of sorted items, return q1, median q3 tuple

	If the list has an odd number of entries, the median is the
	middle number.

		>>> q = quartiles( (1, 2, 3, 4, 5, 6, 7) )
		>>> q[1]
		4

	The first quartile is the element such that at least 25% of the
	values are less than or equal to it.

		>>> q[0]
		2

	Likewise, the third quartile is the element such that at least
	75% of the values are less than or equal to it.

		>>> q[2]
		6

	Note that 5 doesn't work, because 5/7. = 71%, and the criteria
	is that at least 75% of the elements are less than or equal to q3.

	Shorter lists also work.

		>>> quartiles( (1,2,3,4,5) )
		(2, 3, 4)

	Even lists exercise a different logic flow.

		>>> quartiles( (1,2,3,4,5,6) )
		(2, 3.5, 5)

	The first quartile and third quartile seem incorrect, but they are
	consistent with the method we are using:

		1. multiply length of list by percentile

			q1		q2		q3
			----------	-------		----------
			0.25*6=1.5	0.5*6=3		0.75*6=4.5

		2. if result is a whole number, compute value half-way
		   between number at that position (one-based) and next

			q1		q2		q3
			----------	-------		----------
			n/a       	3+4/2.=3.5	n/a
	
		3. otherwise, round up to next int and take value at
		   that position (again, one-based indexing of list)

			q1		q2		q3
			----------	-------		----------
			a[2] = 2	n/a		a[5] =  5


	With a list of one entry, they should all come back the same.

		>>> quartiles( (1,))
		(1, 1, 1)

	With a list of two entries, we should get three different values.

		>>> quartiles( (1,2))
		(1, 1.5, 2)
	'''

	return percentile(a, 0.25), percentile(a, 0.50), percentile(a, 0.75)
	
def devquartiles_from_labordays(dev_labordays, trials_n):
	'''
	Compute descriptive statistics for each developer's ship date.

	Return value is
	
		(
			('a', min_a, q1_a, q2_a, q3_a, max_a),
			('b', min_b, q1_b, q2_b, q3_b ,max_b),
		)
	
	where stats are on ship date:
	
		q1 = first quartile (25'th percentile)
		q2 = second quartile (50'th percentile, or median)
		q3 = third quartile (75'th percentile)

	Note that the input to this routine is labordays so we can
	compute descriptive stats without worrying about days off.
	Once we have the stats, we convert to working days.
	'''

	seconds_per_halfday = 60 * 60 * 24 / 2
	rval = []
	for dev, labordays in dev_labordays.items():
		pdf = list_to_pdf(labordays)
		min = pdf[0][0]
		max = pdf[-1][0]

		daysleft = [daysleft for daysleft, density in pdf]
		td1, td2, td3 = map(timedelta, quartiles(daysleft))

		#
		# Adding a timedelta of 82,800 seconds (23 hours worth)
		# to a date does not advance it by one day.  We want to
		# round to the closest day, so we can't just add the day 
		# delta's returned by quartiles(), as they may be floats.
		#

		if td1.seconds > seconds_per_halfday:
			td1 = td1 + timedelta(1)
		if td2.seconds > seconds_per_halfday:
			td2 = td2 + timedelta(1)
		if td3.seconds > seconds_per_halfday:
			td3 = td3 + timedelta(1)

		#
		# Now that we have the number of labordays required to
		# each quartile, we can convert to work days, to put in
		# terms of shipping date.
		#

		today = date.today()
		min = advance_n_workdays(today, min)
		q1 = advance_n_workdays(today, td1.days)
		q2 = advance_n_workdays(today, td2.days)
		q3 = advance_n_workdays(today, td3.days)
		max = advance_n_workdays(today, max)

		rval.append( (dev, min, q1, q2, q3, max), )

	return tuple(rval)
	

def history_to_plotdata(history, todo, dev_to_dailyworkhours):
	'''
	History is a list of 

		(dev, ticket, estimated_hours, actual_hours, velocity)

	tuples.

	Todo is a list of (dev, ticket, est_hrs, act_hrs, todo_hrs)
	tuples.

	Timecards is a list of (dev, date, total_hours) tuples.  One
	entry for each unique dev/date combination.

	Given this data, we run 1,000 rounds of a Monte Carlo simulation.
	Each round generates one ship date.  We take all 1,000 ship dates,
	and generate two sets of coordinates:

		1. a probability density function for ship date, and

		2. box and whisker plots for each developer's ship date.

	We use the timecard data to get an estimate of how many hours
	each developer is available per week.

		XXX: To model vacations, available hours should be in DB.

	See ebs.txt for the unit tests.
	'''


	dev_to_velocities = history_to_dict(history)

	# How many Markov trials do we run.
	trials_n = 1000

	startdt = date.today()
	shipdates = []
	dev_to_daysleftlist = {}
	for trial_i in range(trials_n):

		# How many hours of work does each dev have?  Use randomly
		# selected velocity to estimate this.
		dev_to_hrsleft = {}
		for dev, ticket, est, act, left in todo:
			# velocity = est/actual.
			# new est. = est / v
			v = random.choice(dev_to_velocities[dev])
			hrsleft = (est - act)/v

			if hrsleft < 0.0:
				efmt = "don't support tickets with "\
				    "actual > estimate.  ticket #%s, "\
				    "act=%.2f, est=%.2f, velocity=%.2f"
				raise ValueError(efmt % (ticket, act, est, v))
			try:
				dev_to_hrsleft[dev] += hrsleft
			except KeyError:
				dev_to_hrsleft[dev] = hrsleft

		# How many days of work left does each dev have?
		# Use number of hours per day each dev works on average.
		dev_to_daysleft = {}
		for dev, hrs in dev_to_hrsleft.items():
			daysleft = hrs/dev_to_dailyworkhours[dev]
			dev_to_daysleft[dev] = daysleft
			if not dev_to_daysleftlist.has_key(dev):
				dev_to_daysleftlist[dev] = []
			dev_to_daysleftlist[dev].append(daysleft)

		# Find max # of work days left across all devs.
		labordays_till_done = max(dev_to_daysleft.values())

		#
		# Convert labor days to calendar days.  This is ship date.
		# 
		# We keep developer day in raw (that is, non-calendar)
		# days because that what we need to compute median and
		# other descriptive stats.  Once the stats are computed,
		# then we convert to calendar.
		#

		shipdate = advance_n_workdays(startdt, labordays_till_done)
		shipdates.append(shipdate)

	pdf = list_to_pdf(shipdates)

	devs = devquartiles_from_labordays(dev_to_daysleftlist, trials_n)

	return pdf, devs

if __name__ == '__main__':
	import doctest
	doctest.testmod()
	doctest.testfile('ebs.txt')
