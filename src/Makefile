HOME=/home/mailman
CGI=${HOME}/cgi-bin
MAILMAN=${HOME}/mailman


all: admin_wrapper admindb_wrapper archives_wrapper edithtml_wrapper options_wrapper listinfo_wrapper subscribe_wrapper roster_wrapper handle_opts_wrapper mail_wrapper alias_wrapper private_wrapper

admin_wrapper:
	gcc -D SCRIPT="\"admin\"" -o ${CGI}/admin cgi-wrapper.c
	chmod a+sx ${CGI}/admin

admindb_wrapper:
	gcc -D SCRIPT="\"admindb\"" -o ${CGI}/admindb cgi-wrapper.c
	chmod a+sx ${CGI}/admindb

archives_wrapper:
	gcc -D SCRIPT="\"archives\"" -o ${CGI}/archives cgi-wrapper.c
	chmod a+sx ${CGI}/archives

edithtml_wrapper:
	gcc -D SCRIPT="\"edithtml\"" -o ${CGI}/edithtml cgi-wrapper.c
	chmod a+sx ${CGI}/edithtml

options_wrapper: 
	gcc -D SCRIPT="\"options\"" -o ${CGI}/options cgi-wrapper.c
	chmod a+sx ${CGI}/options

listinfo_wrapper:
	gcc -D SCRIPT="\"listinfo\"" -o ${CGI}/listinfo cgi-wrapper.c
	chmod a+sx ${CGI}/listinfo

subscribe_wrapper:
	gcc -D SCRIPT="\"subscribe\"" -o ${CGI}/subscribe cgi-wrapper.c
	chmod a+sx ${CGI}/subscribe

roster_wrapper:
	gcc -D SCRIPT="\"roster\"" -o ${CGI}/roster cgi-wrapper.c
	chmod a+sx ${CGI}/roster

handle_opts_wrapper:
	gcc -D SCRIPT="\"handle_opts\"" -o ${CGI}/handle_opts cgi-wrapper.c
	chmod a+sx ${CGI}/handle_opts

private_wrapper:
	gcc -D SCRIPT="\"private\"" -o ${CGI}/private cgi-wrapper.c
	chmod a+sx ${CGI}/private

mail_wrapper:
	gcc -o ${MAILMAN}/mail/wrapper mail-wrapper.c
	chmod a+sx ${MAILMAN}/mail/wrapper

alias_wrapper:
	gcc -o ${MAILMAN}/bin/addaliases alias-wrapper.c
	chmod a+sx ${MAILMAN}/bin/addaliases
