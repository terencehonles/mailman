# FILES=admindbpreamble.html adminsubscribeack.txt adminunsubscribeack.txt admlogin.html approve.txt article.html bounce.txt checkdbs.txt convert.txt cronpass.txt headfoot.html help.txt listinfo.html masthead.txt newlist.txt nopass.txt options.html postack.txt postauth.txt postheld.txt private.html reenable.txt refuse.txt roster.html subauth.txt subscribeack.txt subscribe.html unsub.txt userpass.txt verify.txt
FILES=$(shell cat status | sed -e 's/ .*$$//')
TARGET=/var/home/mailman/templates/ru

TFILES=$(addprefix $(TARGET),$(FILES))

diff_args=-ub

all:
	@echo there is nothing to do

diff-%: %
	@-(cd ../en/ ; cvs -z6 diff $(diff_args) -r$(shell fgrep $< status | awk '{ print $$2; }') $<)

check:
	(cd ../en/ ; cvs -z6 status ) | ./s2s.py

todo:
	@cat status | while read name version status rest; do [ "$$status" == "done" ] || echo $$name; done | sort

done:
	@cat status | while read name version status rest; do [ "$$status" == "done" ] && echo $$name; done | sort

started:
	@cat status | while read name version status rest; do [ "$$status" == "started" ] && echo $$name; done | sort

status-%: %
	@cat status | fgrep $<

install:
	sudo install -d $(TARGET)
	sudo install $(FILES) $(TARGET)
