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
** Chmod this bitch 4755.
**
*/
#include <stdio.h>

const char *COMMAND = "/home/mailman/mailman/cgi/admin";

/* Might want to make this full path.  
   I can write whatever program named sendmail,
   so this isn't much for security.
*/
const char *LEGAL_PARENT_NAMES[] = {
  "httpd",
  NULL /* Sentinal, don't remove */
};

/* Should make these arrays too... */
const int  LEGAL_PARENT_UID = 60001;  /* nobody's UID */
const int  LEGAL_PARENT_GID = 60001; /* nobody's GID */


/*
** what is the name of the process with pid of 'pid'
*/
char *get_process_name(int pid) {
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


int valid_parent(char *parent){
  int i = 0;

  while(LEGAL_PARENT_NAMES[i] != NULL)
    {
      if(!strcmp(parent, LEGAL_PARENT_NAMES[i]))
	{
	  return 1;
	}
      i++;
    }
  return 0;
}

/* 
** is the parent process allowed to call us?
*/
int legal_caller() {
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

void main(int argc, char **argv, char **env) {
  char  *command;
  int   i;
  command = (char *)malloc(sizeof(char) * i);

  if(legal_caller()) {
    setuid(geteuid());
    execve(COMMAND, &argv[0], env);
  }
    else {
      printf("Illegal caller!\n");
    }
}

