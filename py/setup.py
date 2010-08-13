from setuptools import find_packages, setup

pkg='ebstrac'
setup(
	name		= pkg, 
	version		= '1',
	description	= 'Trac Plugin for evidence-based scheduling',
	url		= 'http://github.com/mbucc/ebs-trac',
	author		= 'Mark Bucciarelli',
	author_email	= 'mark@crosscutmedia.com',
	license		= 'ISC',
	packages	= find_packages(),
	entry_points	= {'trac.plugins': '%s = ebstrac' % pkg},
)
