/*
** generic wrapper that will take info from a environment 
** variable, and pass it to two commands.
**
** 10-17-96 : Hal Schechner
** 12-14-96 : John Viega -- changed to work on 1 command, 
**                          take a list of valid commands,
**                          just pass on argv, and use execvp()
**                          Also threw in some useful feedback for when there's
**                          a failure, mainly for future debugging.
**
** 03-31-98 : John Viega -- Consolidated all CGI wrappers into 1,
**                          removed checking the command name, (it was
**                          not real security anyway...) and changed it to use
**                          syslog on error.  This definitely doesn't have any of
**                          Hal's code left ;-)
**                        
*/
#include <stdio.h>
#include <stdarg.h>
#include <syslog.h>

#define COMMAND "/home/mailman/mailman/cgi/" ## SCRIPT 
#define LOG_IDENT "Mailman-wrapper (" ## SCRIPT ## ")"

const int  LEGAL_PARENT_UID = 60001;  /* nobody's UID */
const int  LEGAL_PARENT_GID = 60001; /* nobody's GID */

/*
** Report an error then exit.
*/
void err(char *format, ...)
{
  char log_entry[1024];

  va_list arg_ptr;
  va_start(arg_ptr, format);
  vsprintf(log_entry, format, arg_ptr);
  va_end(arg_ptr);

  // Write to the console, maillog is often mostly ignored,
  // and root should definitely know about any problems.
  openlog(LOG_IDENT, LOG_CONS, LOG_MAIL);
  syslog(LOG_ERR, "%s", log_entry);
  closelog();
  exit(0);
}

/* 
** is the parent process allowed to call us?
*/
void check_caller() {
    /* compare to our parent's uid */
    if(LEGAL_PARENT_UID != getuid()) 
      {
	err("Attempt to exec cgi %s made by uid %d", LEGAL_PARENT_UID,
	    getuid());
      }
    if(LEGAL_PARENT_GID != getgid())
      {
	err("Attempt to exec cgi %s made by gid %d", LEGAL_PARENT_GID,
	    getgid());
      }
}

void main(int argc, char **argv, char **env) 
{
  int   i;

  check_caller();
  // If we get here, the caller is OK.
  setuid(geteuid());
  execve(COMMAND, &argv[0], env);
  err("execve of %s failed!", COMMAND);
}
