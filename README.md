[![Travis Status](https://travis-ci.org/josch/plakativ.svg?branch=master)](https://travis-ci.org/josch/plakativ)
[![Appveyor Status](https://ci.appveyor.com/api/projects/status/32r7s2skrgm9ubva/branch/master?svg=true)](https://ci.appveyor.com/project/josch/plakativ/branch/master)

plakativ
========

Plakativ is German for "striking" or "eye-catching" and comes from the German
word "Plakat" which means poster in English.

This software allows one to stretch a PDF document across multiple pages that
can then be printed on a common inkjet printer, cut and glued together into a
larger poster.

Features
========

Plakativ allows one to create a poster using one of three different approaches:

 - I want a poster of size X
 - I want a poster X times the input page page area
 - I have X pages of paper and want to print the biggest possible poster on them

Plakativ works on Windows, Linux and MacOS. It offers a GUI based on tkinter, a
command line interface and can be used as a Python module. Everything is inside
a single file.

Demo
====

![](demo.gif)

[//]: # (To make a new Video, run:)
[//]: # (ffmpeg -f x11grab -framerate 30 -video_size 800x600 -i :0.0+41,46 -preset ultrafast -c:v libx264 -crf 0 out.mp4)
[//]: # (ffmpeg -i out.mp4 -ss 00:00:04.000 -r 2.5 plakativ%04d.png)
[//]: # (convert -loop 0 plakativ*.png +map -layers Optimize plakativ.gif)
[//]: # (gifsicle -b -O3 plakativ.gif)

The demo shows a user choosing between the three different ways to define the
poster size. Either my picking a size that the input will be fit into, by
multiplying the area of the input page or by maximizing the poster size, given
a number of pages one is willing to print on.

Bugs
====

https://gitlab.mister-muffin.de/josch/plakativ/issues

TODO
====

While basic functionality is implemented, lots of work remains to be done:

 - help button
 - print poster borders
 - print cutting guides
 - changing units
 - changing language
 - adding [advanced and complex layouters](https://stackoverflow.com/questions/39306507/)
 - make PyMuPDF dependency optional
 - optionally, use pdfrw and/or pypdf2 to read/write PDF
 - improve command line interface
 - improve module interface

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
 - scaling by width/height makes doubling unintuitive
