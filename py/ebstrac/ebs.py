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
	'''

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
	Compute average hours available per weekday per user.

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
	for user, dt, hours in timecards:
		try:
			if lastday[user] < dt:
				lastday[user] = dt
		except KeyError:
			lastday[user] = dt
		try:
			if dt < firstday[user]:
				firstday[user] = dt
		except KeyError:
			firstday[user] = dt
		try:
			totalhours[user] += hours
		except KeyError:
			totalhours[user] = hours

	averages = {}
	for user in totalhours.keys():
		dt0 = firstday[user]
		dt1 = lastday[user]
		n = len(list(count_workdays(dt0, dt1)))
		if n > 0:
			averages[user] = totalhours[user]/float(n)

	return averages
		

def history_to_dict(history):
	'''
	Turn history tuples into a dictionary where we can lookup the
	list of velocities for a given user.

		>>> history = (
		... ('mark', 1, 1.0, 1.0, 1.0),
		... )
		>>> history_to_dict(history)
		{'mark': [1.0]}
	'''

	if not history:
		return {}

	d = {}
	for user, ticket, estimated_hours, actual_hours, velocity in history:
		if not d.has_key(user):
			d[user] = []
		d[user].append(velocity)
	return d

def history_to_plotdata(history, todo, timecards):
	'''
	History is a list of 

		(user, ticket, estimated_hours, actual_hours, velocity)

	tuples.

	Todo is a list of (user, ticket, est_hrs, act_hrs, todo_hrs)
	tuples.

	Timecards is a list of (user, date, total_hours) tuples.  One
	entry for each unique user/date combination.

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

	user_to_dailyworkhours = availability_from_timecards(timecards)

	user_to_velocities = history_to_dict(history)

	# How many hours left does each user have?
	user_to_hours = {}
	for user, ticket, est, act, left in todo:
		v = random.choice(user_to_velocities[user])
		try:
			user_to_hours[user] += v * (est - act)
		except KeyError:
			user_to_hours[user] = v * (est - act)

	# How many days of work left does each user have?	
	user_to_days = {}
	for user, hours in user_to_hours.items():
		user_to_days[user] = hours / user_to_dailyworkhours[user]

	# Days till ship date is worker who finishes last.
	labordays_till_done = max(user_to_days.values())

	# Convert labor days to calendar days.
	shipdate = advance_n_workdays(date.today(), labordays_till_done)

	return ( (shipdate, 100),), ()

if __name__ == '__main__':
	import doctest
	doctest.testmod()
	doctest.testfile('ebs.txt')
