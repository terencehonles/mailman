/* common.h --- Prototypes for common routines
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

#include <stdlib.h>
#include <stdarg.h>
#include <syslog.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <unistd.h>

extern void fatal(const char*, int, const char*, ...);
extern void check_caller(const char*, gid_t);
extern int run_script(const char*, int, char**, char**);

/* bogus global variable used as a flag */
extern int running_as_cgi;

/* extern to reference this global from one of the wrapper mains */
extern const char* logident;


/* exit codes, so it's easier to distinguish what caused fatal errors when
 * looking at syslogs.
 */
#define GID_MISMATCH 2
#define SETREGID_FAILURE 3
#define EXECVE_FAILURE 4
#define MAIL_USAGE_ERROR 5
#define MAIL_ILLEGAL_COMMAND 6



/*
 * Local Variables:
 * c-file-style: "python"
 * End:
 */
