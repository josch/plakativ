TODO: use pdfrw, pypdf2

plakativ
========

Plakativ is German for "striking" or "eye-catching" and comes from the German
word "Plakat" which means poster in English.

This software allows one to stretch a PDF document across multiple pages that
can then be printed on a common inkjet printer and be glued together into a
larger poster.

Features
========

Plakativ allows one to make posters with three different goals in mind:

 - I want a poster of size X
 - I want a poster X times the input page size
 - I have X pages of paper and want to print the biggest possible poster on them

In contrast to other solutions, plakativ tries hard to find a page
configuration that wastes as little paper as possible, offering three different
layouter algorithms.

Comparison to PosteRazor
------------------------

http://posterazor.sourceforge.net/

PosteRazor served as the inspiration for this software. But in contrast to
PosteRazor, plakativ allows PDF documents as input and outputs PDF document
with the exact same quality as the input. It is thus not necessary anymore
to first do a lossy rasterization of an input PDF so that one can work with
PosteRazor.

Comparison to pdfposter
-----------------------

https://pdfposter.readthedocs.io/en/stable/

 - no GUI
 - cumbersome box definition
 - no page borders for glueing
 - superfluous empty pages
 - only very simple layouter
