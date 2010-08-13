py/dist/ebstrac-*.egg: py/ebstrac/*.py py/setup.py
	(cd py; python setup.py bdist_egg)

install: py/dist/ebstrac-*.egg
	easy_install py/dist/ebstrac-*.egg

clean:
	rm -rf py/dist/ py/build py/ebstrac.egg-info
	find ./py -name "*.pyc" | xargs rm -f
