/* alias-wrapper.c --- wrapper to allow the mailman user to modify the aliases
 * database.
 *
 * Copyright (C) 1998 by the Free Software Foundation, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software 
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#include <stdio.h>

/* passed in from configure script */
const int  LEGAL_PARENT_UID = ALIAS_UID;     /* mailman's UID */
const int  LEGAL_PARENT_GID = ALIAS_GID;     /* mail's GID */

const char* SENDMAIL_CMD = "/usr/sbin/sendmail";
const char* ALIAS_FILE   = "/etc/aliases";
const char* WRAPPER      = "/home/mailman/mailman/mail/wrapper";

/* 
** is the parent process allowed to call us?
*/
int
LegalCaller() 
{
	/* compare to our parent's uid */
	if (LEGAL_PARENT_UID != getuid()) {
		printf("GOT UID %d.\n", getuid());
		return 0;
	}
	if (LEGAL_PARENT_GID != getgid()) {
		printf("GOT GID %d.\n", getgid());
		return 0;
	}
	return 1;
}


void
AddListAliases(char *list)
{
	FILE *f;
	int  err = 0;

	f = fopen(ALIAS_FILE ,"a+");
	if (f == NULL) {
		err = 1;
		f = stderr;
		fprintf(f, "\n\n***********ERROR!!!!***********\n");
		fprintf(f, "Could not write to the /etc/aliases file.\n");
		fprintf(f, "Please become root, add the lines below to\n");
		fprintf(f, "that file, and then run the command:\n");
		fprintf(f, "%s -bi\n", SENDMAIL_CMD);
	}

	fprintf(f, "\n\n#-- %s -- mailing list aliases:\n", list);
	fprintf(f, "%s: \t|\"%s post %s\"\n", list, WRAPPER, list);
	fprintf(f, "%s-admin: \t|\"%s mailowner %s\"\n", list, WRAPPER, list);
	fprintf(f, "%s-request: \t|\"%s mailcmd %s\"\n", list, WRAPPER, list);
	fprintf(f, "# I think we don't want this one...\n");
	fprintf(f, "it'll change the unix from line...\n");
	fprintf(f, "#owner-%s: \t%s-admin\n", list, list);
	fprintf(f, "#%s-owner: \t%s-admin\n", list, list);
	fprintf(f, "\n");
	fclose(f);

	if (!err) {
		printf("Rebuilding alias database...\n");
		execlp(SENDMAIL_CMD, SENDMAIL_CMD, "-bi");
	}
}


int
main(int argc, char **argv, char **env) 
{
	char  *command;
	int   i;

	if (argc != 2) {
		printf("Usage: %s [list-name]\n", argv[0]);
		exit(0);
	}
	if (LegalCaller()) {
		setuid(geteuid());
		AddListAliases(argv[1]);
	}
	else {
		printf("Illegal caller!\n");
		return 1;
	}
	return 0;
}



/*
 * Local Variables:
 * c-file-style: "python"
 * End:
 */
