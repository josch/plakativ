=======
CHANGES
=======

0.5.2 (2024-01-12)
------------------

 - support for pymupdf 1.23.0

0.5.1 (2022-07-23)
------------------

 - support for pymupdf 1.20.0

0.5 (2021-10-11)
----------------

 - support for HiDPI displays

0.4 (2021-03-04)
----------------

 - support raster images as input (everything supported by PIL or img2pdf)
 - add --remove-alpha to allow lossy conversion of images with alpha channel
 - raise error if none of --size, --factor or --maxpages is given
 - add --cover-page, --cutting-guides, --page-numbers and --poster-border
 - fix pdf dashed line syntax
 - the default unit is mm and not pt

0.3 (2020-06-10)
----------------

 - add freedesktop.org, appstream integration and icon
 - add command line interface
 - automatically flip poster dimensions for maximum output size
 - support pymupdf before version 1.14.5

0.2 (2020-03-03)
----------------

 - Add complex layout strategy

0.1 (2019-07-04)
----------------

 - Initial PyPI release
