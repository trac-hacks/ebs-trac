MANDIR=/usr/local/share/man
# OpenBSD installs man pages to
#MANDIR=/usr/local/man

BINDIR=/usr/local/bin

py/dist/ebstrac-*.egg: py/ebstrac/*.py py/setup.py
	(cd py; python setup.py bdist_egg)

install: py/dist/ebstrac-*.egg
	easy_install py/dist/ebstrac-*.egg


install-client: \
		$(MANDIR)/man1/ebsls.1 \
		$(MANDIR)/man1/ebscp.1 \
		$(MANDIR)/man5/ebsconf.5 \
		$(BINDIR)/ebsls \
		$(BINDIR)/ebscp \

$(MANDIR)/man1/ebsls.1: man/ebsls.1
	mkdir -p $(MANDIR)/man1
	cp man/ebsls.1 $(MANDIR)/man1
	
$(MANDIR)/man5/ebsconf.5: man/ebsconf.5
	mkdir -p $(MANDIR)/man5
	cp man/ebsconf.5 $(MANDIR)/man5

$(MANDIR)/man1/ebscp.1: man/ebscp.1
	mkdir -p $(MANDIR)/man1
	cp man/ebscp.1 $(MANDIR)/man1

$(BINDIR)/ebsls: bin/ebsls
	cp bin/ebsls $(BINDIR)/
	chmod +x $(BINDIR)/ebsls

$(BINDIR)/ebscp: bin/ebscp
	cp bin/ebscp $(BINDIR)/
	chmod +x $(BINDIR)/ebscp

clean:
	rm -rf py/dist/ py/build py/ebstrac.egg-info
	find ./py -name "*.pyc" | xargs rm -f
