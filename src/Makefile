HOME=/home/mailman
MAILMAN=/home/mailman/mailman

all: admin_wrapper admindb_wrapper archives_wrapper edithtml_wrapper options_wrapper listinfo_wrapper subscribe_wrapper roster_wrapper handle_opts_wrapper mail_wrapper alias_wrapper

admin_wrapper:
	gcc -o ${HOME}/cgi-bin/admin admin-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/admin

admindb_wrapper:
	gcc -o ${HOME}/cgi-bin/admindb admindb-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/admindb

archives_wrapper:
	gcc -o ${HOME}/cgi-bin/archives archives-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/archives

edithtml_wrapper:
	gcc -o ${HOME}/cgi-bin/edithtml edithtml-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/edithtml

options_wrapper: 
	gcc -o ${HOME}/cgi-bin/options options-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/options

listinfo_wrapper:
	gcc -o ${HOME}/cgi-bin/listinfo listinfo-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/listinfo

subscribe_wrapper:
	gcc -o ${HOME}/cgi-bin/subscribe subscribe-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/subscribe

roster_wrapper:
	gcc -o ${HOME}/cgi-bin/roster roster-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/roster

handle_opts_wrapper:
	gcc -o ${HOME}/cgi-bin/handle_opts handle_opts-wrapper.c
	chmod a+sx ${HOME}/cgi-bin/handle_opts

mail_wrapper:
	gcc -o ${MAILMAN}/mail/wrapper mail-wrapper.c
	chmod a+sx ${MAILMAN}/mail/wrapper

alias_wrapper:
	gcc -o ${MAILMAN}/bin/addaliases alias-wrapper.c
	chmod a+sx ${MAILMAN}/bin/addaliases
