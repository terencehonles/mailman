/*
** mail-wrapper.c:
** generic wrapper that will take info from a environment 
** variable, and pass it to two commands.
**
** Copyright (C) 1998 by the Free Software Foundation, Inc.
**
** This program is free software; you can redistribute it and/or
** modify it under the terms of the GNU General Public License
** as published by the Free Software Foundation; either version 2
** of the License, or (at your option) any later version.
** 
** This program is distributed in the hope that it will be useful,
** but WITHOUT ANY WARRANTY; without even the implied warranty of
** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
** GNU General Public License for more details.
** 
** You should have received a copy of the GNU General Public License
** along with this program; if not, write to the Free Software 
** Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 0211-1307, USA.
**
** 10-17-96 : Hal Schechner (hal-j@channel21.com)
**
** 12-14-96 : John Viega    (viega@list.org)
**                          changed to work on 1 command, take a list of
**                          valid commands, just pass on argv, and use
**                          execvp() Also threw in some useful feedback for
**                          when there's a failure, mainly for future
**                          debugging.  Made it a root script so we could
**                          call setuid()
**
** Chmod this 4755.
**
*/
#include <stdio.h>

const char *COMMAND_LOCATION = "/home/mailman/mailman/scripts";

extern int errno;
FILE *f;

const char *VALID_COMMANDS[] = {
	"post", 
	"mailcmd",
	"mailowner",
	NULL				     /* Sentinal, don't remove */
};


/* Might want to make this full path.  I can write whatever program named
 * sendmail, so this isn't much for security.
*/
const char *LEGAL_PARENT_NAMES[] = {
	"sendmail",
	NULL				     /* Sentinal, don't remove */
};


/* Should make these arrays too... */
const int  LEGAL_PARENT_UID = 1;	     /* mail's UID */
const int  LEGAL_PARENT_GID = 1;	     /* mail's GID */


/*
** what is the name of the process with pid of 'pid'
*/
char *
get_process_name(int pid)
{
	FILE *proc;
	char fname[30];
	char tmp[255];
	static char procname[255];

	sprintf(fname, "/proc/%d/status", pid);
	proc = fopen(fname, "r");
	fgets(tmp, 256, proc);
	sscanf(tmp, "Name:   %s\n", procname);
	fclose(proc);
	return procname;
}


int
valid_parent(char *parent)
{
	int i = 0;

	while (LEGAL_PARENT_NAMES[i] != NULL) {
		if (!strcmp(parent, LEGAL_PARENT_NAMES[i])) {
			return 1;
		}
		i++;
	}
	return 0;
}


/* 
** is the parent process allowed to call us?
*/
int
legal_caller()
{
	/* compare to our parent's uid */
	if (LEGAL_PARENT_UID != getuid()) {
		/*	fprintf(f,"GOT UID %d.\n", getuid()); */
		printf("GOT UID %d.\n", getuid());
		return 0;
	}
	if (LEGAL_PARENT_GID != getgid()) {
		/* fprintf(f,"GOT GID %d.\n", getgid()); */
		printf("GOT GID %d.\n", getgid());
		return 0;
	}
	return 1;
}


int
valid_command(char *command)
{
	int i = 0;

	while (VALID_COMMANDS[i] != NULL) {
		if (!strcmp(command, VALID_COMMANDS[i])) {
			return 1;
		}
		i++;
	}
	return 0;
}


int
main(int argc, char **argv)
{
	char  *command;
	int   i;
  
	if (argc < 2) {
		printf("Usage: %s program [args...]\n", argv[0]);
		fflush(stdout);
		exit(0);
	}
	i = strlen(argv[1]) + strlen(COMMAND_LOCATION) + 2;
	command = (char *)malloc(sizeof(char) * i);
	sprintf(command, "%s/%s", COMMAND_LOCATION, argv[1]);

	if (!valid_command(argv[1])) {
		printf("Illegal command.\n");
	}
	else {
		if (legal_caller()) {
			setuid(geteuid());
			execv(command, &argv[1]);
		}
		else {
			printf("Illegal caller!\n");
		}
	}
}


/*
 * Local Variables:
 * c-file-style: "python"
 * End:
 */
