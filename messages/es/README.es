Pasos a dar para soportar un nuevo idioma
-----------------------------------------
Supongamos que vamos a soportar el idioma idioma Portugués (pt)
- Traducir las plantillas de $prefix/templates/en/*, aunque le resulte más útil traducir $prefix/templates/es/* dada la similitud de los idiomas.
- Seleccionar los ficheros que tienen cadenas a traducir, es decir, aquellos que tienen _("...") en el código fuente.
   $ find $prefix -exec grep -l "_(" {} \; > $prefix/messages/pygettext.files
- Quitar todos los ficheros de pygettext.files que no correspondan, *.pyc *.py~...
- Generar el catálogo, para ello se debe ejecutar:
   $ cd $prefix/messages
   $ $prefix/bin/pygettext.py -v `cat pygettext.files`
   $ mkdir -p pt/LC_MESSAGES
   #
   # No sería mala idea (en este caso) traducir README.es a README.pt :-)
   #
   $ mv messages.pot pt/LC_MESSAGES/catalog.pt
- traducir catalog.pt
- Generar mailman.mo:
   $ cd $prefix/messages/pt/LC_MESSAGES
   $ msgfmt -o mailman.mo catalog.pt
- Insertar en Defaults.py una línea en la variable LC_DESCRIPTIONS:
LC_DESCRIPTIONS = { 'es':     [_("Spanish (Spain)"),  'iso-8859-1'],
		    'pt':     [_("Portuguese"),       'iso-8859-1'], <----
                    'en':     [_("English (USA)"),    'us-ascii']
		   }
- Almacenar las plantillas del nuevo idioma en $prefix/templates/pt
- A partir de ahora podemos añadir a una lista el nuevo idioma:
   $ $prefix/bin/addlang -l <lista> pt


Pasos para sincronizar el catálogo
----------------------------------
- Generar el nuevo catálogo tal y como se describe antes y compararlo con el
que ya tenemos. Para compararlo tendremos que ejecutar:
   $ cd $prefix/messages
   $ $prefix/bin/pygettext.py -v `cat pygettext.files`
   $ mv messages.pot pt/LC_MESSAGES
   $ cd pt/LC_MESSAGES
   # Hay otra utilidad relacionada que hace los mismo: 'msgmerge'
   $ tupdate messages.pot catalog.pt > tmp
# Los mensajes antiguos quedan comentados al final del fichero tmp
# Los mensajes nuevos quedan sin traducir.
   $ vi tmp
# Traducir los mensajes nuevos
   $ mv tmp catalog.pt; rm messages.pot
   $ msgfmt -o mailman.mo catalog.pt

Para donar la traducción de un nuevo idioma
-------------------------------------------
Falta por concretar.
