/* _mailman.c --- Extension module for improved performance
 *
 * Copyright (C) 2000 by the Free Software Foundation, Inc.
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

/* Python 2.1 will include a neat new function called sys._getframe() which
 * can be used to get the stack frame of the caller of a function.  From
 * there, we get that function's locals and globals and use it to craft a
 * dictionary for string interpolation (after i18n translation).
 *
 * Until Python 2.1 is released, this extension module provides the same
 * functionality.  It is distributed under Distutils so it should be
 * relatively easy to install.  It is optional though, and if not found,
 * Mailman falls back to a slower, but tried-and-true method.
 */

#include "Python.h"
#include "compile.h"
#include "frameobject.h"


static char getframe_doc[] =
"_getframe([depth]) -> frameobject\n\
\n\
Return a frame object from the call stack.  If optional integer depth is\n\
given, return the frame object that many calls below the top of the stack.\n\
If that is deeper than the call stack, ValueError is raised.  The default\n\
for depth is zero, returning the frame at the top of the call stack.\n\
\n\
This function should be used for internal and specialized\n\
purposes only.";

static PyObject *
getframe(PyObject *self, PyObject *args)
{
	PyFrameObject *f = PyThreadState_Get()->frame;
	int depth = -1;

	if (!PyArg_ParseTuple(args, "|i:_getframe", &depth))
		return NULL;

	while (depth > 0 && f != NULL) {
		f = f->f_back;
		--depth;
	}
	if (f == NULL) {
		PyErr_SetString(PyExc_ValueError,
				"call stack is not deep enough");
		return NULL;
	}
	Py_INCREF(f);
	return (PyObject*)f;
}


static PyMethodDef methods[] = {
	{"_getframe", getframe, METH_VARARGS, getframe_doc},
	{NULL, NULL}			     /* sentinel */
};


void init_mailman(void) 
{
	(void)Py_InitModule("_mailman", methods);
}



/*
 * Local Variables:
 * c-file-style: "python"
 * End:
 */
