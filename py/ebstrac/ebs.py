'''
Evidence-based scheduling routines.
'''

def history_to_plotdata(history, todo):
	'''
	History is a list of 

		(user, ticket, estimated_hours, actual_hours, velocity)

	tuples.

	Todo is a list of

		(user, ticket, estimated_hours, actual_hours)

	tuples.

	Given this data, we run 1,000 rounds of a Monte Carlo simulation.
	Each round generates one ship date.  We take all 1,000 ship dates,
	and generate two sets of coordinates:

		1. a probability density function for ship date, and

		2. box and whisker plots for each developer's ship date.

	'''

	raise "ebs.history_to_plotdata() is not implemented"

	return (), ()
