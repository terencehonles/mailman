#include <stdio.h>


const int  LEGAL_PARENT_UID = 9001;  /* mailman's UID */
const int  LEGAL_PARENT_GID = 6; /* mailman's GID */

const char* SENDMAIL_CMD = "/usr/sbin/sendmail";
const char* ALIAS_FILE   = "/etc/aliases";
const char* WRAPPER      = "/home/mailman/mailman/mail/wrapper";

/* 
** is the parent process allowed to call us?
*/
int LegalCaller() 
{
    /* compare to our parent's uid */
    if(LEGAL_PARENT_UID != getuid()) 
      {
	printf("GOT UID %d.\n", getuid());
        return 0;
      }
    if(LEGAL_PARENT_GID != getgid())
      {
	printf("GOT GID %d.\n", getgid());
        return 0;
      }
    return 1;
}

void AddListAliases(char *list)
{
  FILE *f;
  int  err = 0;

  f = fopen(ALIAS_FILE ,"a+");
  if (f == NULL)
    {
      err = 1;
      f = stderr;
      fprintf(f, "\n\n***********ERROR!!!!***********\n");
      fprintf(f, "Could not write to the /etc/aliases file.\n");
      fprintf(f, "Please become root, add the lines below to that file,\n");
      fprintf(f, "And then run the command %s -bi\n", SENDMAIL_CMD);
    }

  fprintf(f, "\n\n#-- %s -- mailing list aliases:\n", list);
  fprintf(f, "%s: \t|\"%s post %s\"\n", list, WRAPPER, list);
  fprintf(f, "%s-admin: \t|\"%s mailowner %s\"\n", list, WRAPPER, list);
  fprintf(f, "%s-request: \t|\"%s mailcmd %s\"\n", list, WRAPPER, list);
  fprintf(f, "# I think we don't want this one... it'll change the unix from line...\n");
  fprintf(f, "#owner-%s: \t%s-admin\n", list, list);
  fprintf(f, "#%s-owner: \t%s-admin\n", list, list);
  fprintf(f, "\n");
  fclose(f);

  if (!err)
    {
      printf("Rebuilding alias database...\n");
      execlp(SENDMAIL_CMD, SENDMAIL_CMD, "-bi");
    }
}

void main(int argc, char **argv, char **env) 
{
  char  *command;
  int   i;

  if(argc != 2)
    {
      printf("Usage: %s [list-name]\n", argv[0]);
      exit(0);
    }
  if(LegalCaller()) 
    {
      setuid(geteuid());
      AddListAliases(argv[1]);
    }
  else
    {
      printf("Illegal caller!\n");
    }
}

