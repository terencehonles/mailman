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
**                          Made it a root script so we could call setuid()
**
** Chmod this bitch 4755.
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
  NULL /* Sentinal, don't remove */
};


/* Might want to make this full path.  
   I can write whatever program named sendmail,
   so this isn't much for security.
*/
const char *LEGAL_PARENT_NAMES[] = {
  "sendmail",
  NULL /* Sentinal, don't remove */
};

/* Should make these arrays too... */
const int  LEGAL_PARENT_UID = 0;  /* mail's UID *//* actually, using smtp's */
const int  LEGAL_PARENT_GID = 0; /* mail's GID *//* actually, using smtp's */


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
	fprintf(f,"GOT UID %d.\n", getuid());
        return 0;
      }
    if(LEGAL_PARENT_GID != getgid())
      {
	fprintf(f,"GOT GID %d.\n", getgid());
        return 0;
      }
    return 1;
}

int valid_command(char *command){
  int i = 0;

  while(VALID_COMMANDS[i] != NULL)
    {
      if(!strcmp(command, VALID_COMMANDS[i]))
	{
	  return 1;
	}
      i++;
    }
  return 0;
}

void main(int argc, char **argv) {
  char  *command;
  int   i;
  
  f = fopen("/tmp/fart", "w+");
  if(argc < 2)
    {
      fprintf(f,"Usage: %s program [args...]\n", argv[0]);
      fflush(stdout);
      exit(0);
    }
  i = strlen(argv[1]) + strlen(COMMAND_LOCATION) + 2;
  command = (char *)malloc(sizeof(char) * i);
  sprintf(command, "%s/%s", COMMAND_LOCATION, argv[1]);

  if(!valid_command(argv[1])){
      fprintf(f,"Illegal command.\n");
    }
  else{
    if(legal_caller()) {
      setuid(geteuid());
      execv(command, &argv[1]);
    }
    else {
      fprintf(f,"Illegal caller!\n");
    }
  }
}
