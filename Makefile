work/ebstrac.egg: py/ebstrac.py py/setup.py work/
	(cd work; python ../py/setup.py bdist_egg)

work/: 
	mkdir work
	

install: work/dist/ebstrac-*.egg
	easy_install work/dist/ebstrac-*.egg

clean:
	rm -rf ./work/
