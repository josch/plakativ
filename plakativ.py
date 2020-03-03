#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Plakativ allows to create posters bigger than the page size one's own printer
# is able to print on by enlarging the input PDF, cutting it into smaller
# pieces and putting each of them onto a paper size that can be printed
# normally. The result can then be glued together into a bigger poster.
#
# Copyright (C) 2019 Johannes 'josch' Schauer
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3 as published by the
# Free Software Foundation.

from collections import OrderedDict
import math
import fitz
import tkinter
import tkinter.filedialog
import sys
import argparse
import os.path
import platform

VERSION = "0.2"

PAGE_SIZES = OrderedDict(
    [
        ("custom", (None, None)),
        ("A0 (841 mm × 1189 mm)", (841, 1189)),
        ("A1 (594 mm × 841 mm)", (594, 841)),
        ("A2 (420 mm × 594 mm)", (420, 594)),
        ("A3 (297 mm × 420 mm)", (297, 420)),
        ("A4 (210 mm × 297 mm)", (210, 297)),
        ("A5 (148 mm × 210 mm)", (148, 210)),
        ("Letter (8.5 in × 11 in)", (215.9, 279.4)),
        ("Legal (8.5 in × 14 in)", (215.9, 355.6)),
        ("Tabloid (11 in × 17 in)", (279.4, 431.8)),
    ]
)


def mm_to_pt(length):
    return (72.0 * length) / 25.4


def pt_to_mm(length):
    return (25.4 * length) / 72.0


class PlakativException(Exception):
    pass


class PageNrOutOfRangeException(PlakativException):
    pass


class LayoutNotComputedException(PlakativException):
    pass


def simple_cover(n, m, x, y):
    pages_x_portrait = math.ceil(n / x)
    pages_y_portrait = math.ceil(m / y)
    pages_x_landscape = math.ceil(n / y)
    pages_y_landscape = math.ceil(m / x)
    if pages_x_portrait * pages_y_portrait <= pages_x_landscape * pages_y_landscape:
        pages_x = pages_x_portrait
        pages_y = pages_y_portrait
        portrait = True
        size = pages_x * x, pages_y * y
    else:
        pages_x = pages_x_landscape
        pages_y = pages_y_landscape
        portrait = False
        size = pages_x * y, pages_y * x
    config = list()
    for py in range(pages_y):
        for px in range(pages_x):
            if portrait:
                posx = px * x
                posy = py * y
            else:
                posx = px * y
                posy = py * x
            config.append((posx, posy, portrait))
    return config, size


# the function complex_cover() is based on a heuristic proposed by
# stackoverflow user m69 https://stackoverflow.com/users/4907604/m69 as a reply
# to this question https://stackoverflow.com/questions/39306507
#
# In addition to computing the number of required rectangles it also returns
# the position of the rectangles.
#
# In contrast to the solution by m69 this algorithm mandates at least one page
# in each corner of the result. This means that the minimum solution size is
# four. The advantage is, that the layout computed by this algorithm will
# always be completely be inside the poster without leaving the poster area.
# This in turn will make assembling the poster easier.
#
# This heuristic is not optimal. We always use a regular simple cover for the
# hole in the center (if it exists) but there are situations where the hole in
# the center should be covered by a complex cover instead. We do not consider
# this improvement because:
#   - it's required very seldom
#   - it makes the resulting layout more complicated to glue together
#   - there is no proof that the improved version is optimal either
#   - we save some cpu cycles
def complex_cover(n, m, x, y):
    # each tuple-entry represents one of the corners of the poster
    # upper-left, upper-right, lower-right, lower-left
    portrait = (
        (True, True, True, False),
        (True, True, False, False),
        (True, False, True, False),
        (True, False, False, True),
        (True, False, False, False),
    )
    X = lambda r, d: x if portrait[r][d] else y
    Y = lambda r, d: y if portrait[r][d] else x
    if x == y:
        # if page sizes are square, only one rotation has to be checked
        num_rotations = 1
    elif n == m:
        # if the poster size is a square, rotation 4 and 5 (which are itself
        # just rotations of rotations 2 and 1, respectively) do not need to be
        # checked
        num_rotations = 3
    else:
        num_rotations = 5
    minimum = math.ceil((n * m) / (x * y))
    config, _ = simple_cover(n, m, x, y)
    cover = len(config)
    if cover == minimum:
        return config

    for r in range(num_rotations):
        # w0 -> width of upper left corner pages
        for w0 in range(1, math.ceil(n / X(r, 0))):
            # w1 -> width of upper right corner pages
            w1 = math.ceil((n - w0 * X(r, 0)) / X(r, 1))
            if w1 < 0:
                w1 = 0
            # h0 -> height of upper left corner pages
            for h0 in range(1, math.ceil(m / Y(r, 0))):
                # h3 -> height of lower left corner pages
                h3 = math.ceil((m - h0 * Y(r, 0)) / Y(r, 3))
                if h3 < 0:
                    h3 = 0
                # w2 -> width of lower right corner pages
                for w2 in range(1, math.ceil(n / X(r, 2))):
                    # w3 -> width of lower left corner pages
                    w3 = math.ceil((n - w2 * X(r, 2)) / X(r, 3))
                    if w3 < 0:
                        w3 = 0
                    # h2 -> height of lower right corner pages
                    for h2 in range(1, math.ceil(m / Y(r, 2))):
                        # h1 -> height of upper right corner pages
                        h1 = math.ceil((m - h2 * Y(r, 2)) / Y(r, 1))
                        if h1 < 0:
                            h1 = 0
                        newconfig = list()
                        # upper-left (w0,h0)
                        for i in range(w0):
                            for j in range(h0):
                                newconfig.append(
                                    (i * X(r, 0), j * Y(r, 0), portrait[r][0])
                                )
                        # upper-right (w1,h1)
                        for i in range(w1):
                            for j in range(h1):
                                newconfig.append(
                                    (
                                        n - w1 * X(r, 1) + i * X(r, 1),
                                        j * Y(r, 1),
                                        portrait[r][1],
                                    )
                                )
                        # lower-right (w2,h2)
                        for i in range(w2):
                            for j in range(h2):
                                newconfig.append(
                                    (
                                        n - w2 * X(r, 2) + i * X(r, 2),
                                        m - h2 * Y(r, 2) + j * Y(r, 2),
                                        portrait[r][2],
                                    )
                                )
                        # lower-left (w3,h3)
                        for i in range(w3):
                            for j in range(h3):
                                newconfig.append(
                                    (
                                        i * X(r, 3),
                                        m - h3 * Y(r, 3) + j * Y(r, 3),
                                        portrait[r][3],
                                    )
                                )

                        # if neither rectangle 0 overlaps with rectangle 2 nor
                        # does rectangle 1 overlap with rectangle 3 in the center,
                        # then a center cover has to be added
                        X4 = n - w0 * X(r, 0) - w2 * X(r, 2)
                        Y4 = m - h1 * Y(r, 1) - h3 * Y(r, 3)
                        simple_config = []
                        if X4 > 0 and Y4 > 0:
                            simple_config, (sx, sy) = simple_cover(X4, Y4, x, y)
                            # shift the results such that they are in the center
                            for (cx, cy, p) in simple_config:
                                newconfig.append(
                                    (
                                        w0 * X(r, 0) + (X4 - sx) / 2 + cx,
                                        h1 * Y(r, 1) + (Y4 - sy) / 2 + cy,
                                        p,
                                    )
                                )
                        else:
                            X4 = n - w1 * X(r, 1) - w3 * X(r, 3)
                            Y4 = m - h0 * Y(r, 0) - h2 * Y(r, 2)
                            if X4 > 0 and Y4 > 0:
                                simple_config, (sx, sy) = simple_cover(X4, Y4, x, y)
                                # shift the results such that they are in the center
                                for (cx, cy, p) in simple_config:
                                    newconfig.append(
                                        (
                                            w3 * X(r, 3) + (X4 - sx) / 2 + cx,
                                            h0 * Y(r, 0) + (Y4 - sy) / 2 + cy,
                                            p,
                                        )
                                    )
                        total = len(newconfig)
                        # shortcut to cut computation short in case a
                        # solution with the minimal possible number of
                        # pages is found
                        if total == minimum:
                            return newconfig
                        if total < cover:
                            cover = total
                            config = newconfig
    return config


class Plakativ:
    def __init__(self, infile, pagenr=0):
        self.doc = fitz.open(infile)
        self.pagenr = pagenr

    # set page number -- first page is 0
    def set_input_pagenr(self, pagenr):
        if pagenr < 0 or pagenr >= len(self.doc):
            raise PageNrOutOfRangeException(
                "%d is not between 0 and %d (inclusive)" % (pagenr, len(self.doc))
            )

        self.pagenr = pagenr

    def get_input_pagenums(self):
        return len(self.doc)

    def get_input_page_size(self):
        width = self.doc[self.pagenr].getDisplayList().rect.width
        height = self.doc[self.pagenr].getDisplayList().rect.height
        return (width, height)

    def get_image(self, zoom):
        mat_0 = fitz.Matrix(zoom, zoom)
        pix = (
            self.doc[self.pagenr].getDisplayList().getPixmap(matrix=mat_0, alpha=False)
        )
        return pix.getImageData("ppm")

    def compute_layout(
        self,
        mode,
        postersize=None,
        mult=None,
        npages=None,
        pagesize=(210, 297),
        border=(0, 0, 0, 0),
        strategy="simple",
    ):
        border_top, border_right, border_bottom, border_left = border

        self.layout = {
            "output_pagesize": pagesize,
            "border_top": border_top,
            "border_right": border_right,
            "border_bottom": border_bottom,
            "border_left": border_left,
        }

        printable_width = self.layout["output_pagesize"][0] - (
            border_left + border_right
        )
        printable_height = self.layout["output_pagesize"][1] - (
            border_top + border_bottom
        )
        inpage_width = pt_to_mm(self.doc[self.pagenr].getDisplayList().rect.width)
        inpage_height = pt_to_mm(self.doc[self.pagenr].getDisplayList().rect.height)

        if mode in ["size", "mult"]:
            if mode == "size":
                # fit the input page size into the selected postersize
                poster_width = postersize[0]
                poster_height = (poster_width * inpage_height) / inpage_width
                if poster_height > postersize[1]:
                    poster_height = postersize[1]
                    poster_width = (poster_height * inpage_width) / inpage_height
            elif mode == "mult":
                area = inpage_width * inpage_height * mult
                poster_width = math.sqrt(area * inpage_width / inpage_height)
                poster_height = math.sqrt(area * inpage_height / inpage_width)
            else:
                raise Exception("unsupported mode: %s" % mode)
        elif mode == "npages":
            # stupid bruteforce algorithm to determine the largest printable
            # postersize with N pages
            best_area = 0
            best = None
            for x in range(1, npages + 1):
                for y in range(1, npages + 1):
                    if x * y > npages:
                        continue
                    width_portrait = x * printable_width
                    height_portrait = y * printable_height

                    poster_width = width_portrait
                    poster_height = (poster_width * inpage_height) / inpage_width
                    if poster_height > height_portrait:
                        poster_height = height_portrait
                        poster_width = (poster_height * inpage_width) / inpage_height

                    area_portrait = poster_width * poster_height

                    if area_portrait > best_area:
                        best_area = area_portrait
                        best = (poster_width, poster_height)

                    width_landscape = x * printable_height
                    height_landscape = y * printable_width

                    poster_width = width_landscape
                    poster_height = (poster_width * inpage_height) / inpage_width
                    if poster_height > height_landscape:
                        poster_height = height_landscape
                        poster_width = (poster_height * inpage_width) / inpage_height

                    area_landscape = poster_width * poster_height

                    if area_landscape > best_area:
                        best_area = area_landscape
                        best = (poster_width, poster_height)

            poster_width, poster_height = best

            if strategy == "complex":
                # bisect poster sizes until we find the largest size that can
                # be printed given the available number of pages

                # we already know the maximum size for a solution utilizing the
                # simple cover algorithm, so this will be the minimum known
                # poster size
                min_area_mult = (poster_width * poster_height) / (
                    inpage_width * inpage_height
                )
                # to avoid floating point errors later
                min_area_mult *= 0.9999
                min_area_npages = len(
                    complex_cover(
                        poster_width, poster_height, printable_width, printable_height
                    )
                )

                # the maximum possible size is a poster of the area created by
                # multiplying the individual page areas by the maximum number
                # of pages available
                max_area_mult = (npages * printable_width * printable_height) / (
                    inpage_width * inpage_height
                )
                max_area_npages = len(
                    complex_cover(
                        math.sqrt(max_area_mult) * inpage_width,
                        math.sqrt(max_area_mult) * inpage_height,
                        printable_width,
                        printable_height,
                    )
                )

                while True:
                    if abs(min_area_mult - max_area_mult) < 0.001:
                        break
                    new_area_mult = (min_area_mult + max_area_mult) / 2
                    new_area_npages = len(
                        complex_cover(
                            math.sqrt(new_area_mult) * inpage_width,
                            math.sqrt(new_area_mult) * inpage_height,
                            printable_width,
                            printable_height,
                        )
                    )
                    if new_area_npages > npages:
                        max_area_mult = new_area_mult
                    else:
                        min_area_mult = new_area_mult

                poster_width = inpage_width * math.sqrt(min_area_mult)
                poster_height = inpage_height * math.sqrt(min_area_mult)

        else:
            raise Exception("unsupported mode: %s" % mode)

        pages_x_portrait = math.ceil(poster_width / printable_width)
        pages_y_portrait = math.ceil(poster_height / printable_height)

        pages_x_landscape = math.ceil(poster_width / printable_height)
        pages_y_landscape = math.ceil(poster_height / printable_width)

        portrait = True
        if pages_x_portrait * pages_y_portrait > pages_x_landscape * pages_y_landscape:
            portrait = False

        if portrait:
            pages_x = pages_x_portrait
            pages_y = pages_y_portrait
        else:
            pages_x = pages_x_landscape
            pages_y = pages_y_landscape

        # size of the bounding box of all pages after they have been glued together
        if portrait:
            self.layout["overallsize"] = (
                pages_x * printable_width + (border_right + border_left),
                pages_y * printable_height + (border_top + border_bottom),
            )
        else:
            self.layout["overallsize"] = (
                pages_x * printable_height + (border_top + border_bottom),
                pages_y * printable_width + (border_right + border_left),
            )

        # position of the poster relative to upper left corner of layout["overallsize"]
        if portrait:
            self.layout["posterpos"] = (
                border_left + (pages_x * printable_width - poster_width) / 2,
                border_top + (pages_y * printable_height - poster_height) / 2,
            )
        else:
            self.layout["posterpos"] = (
                border_bottom + (pages_x * printable_height - poster_width) / 2,
                border_right + (pages_y * printable_width - poster_height) / 2,
            )

        # positions are relative to self.layout["posterpos"]
        self.layout["positions"] = []
        for y in range(pages_y):
            for x in range(pages_x):
                if portrait:
                    posx = (
                        x * printable_width
                        - (pages_x * printable_width - poster_width) / 2
                    )
                    posy = (
                        y * printable_height
                        - (pages_y * printable_height - poster_height) / 2
                    )
                else:
                    posx = (
                        x * printable_height
                        - (pages_x * printable_height - poster_width) / 2
                    )
                    posy = (
                        y * printable_width
                        - (pages_y * printable_width - poster_height) / 2
                    )
                self.layout["positions"].append((posx, posy, portrait))

        if strategy == "complex":
            positions_complex = complex_cover(
                poster_width, poster_height, printable_width, printable_height
            )

            if len(positions_complex) < len(self.layout["positions"]):
                self.layout["positions"] = positions_complex
                # figure out the borders around the final poster by analyzing
                # the computed positions and storing the largest border size in
                # each dimension
                poster_top = poster_right = poster_bottom = poster_left = 0
                for (posx, posy, p) in self.layout["positions"]:
                    if p:
                        top = posy - border_top
                        if top < 0 and -top > poster_top:
                            poster_top = -top
                        right = posx + printable_width + border_right - poster_width
                        if right > 0 and right > poster_right:
                            poster_right = right
                        bottom = posy + printable_height + border_bottom - poster_height
                        if bottom > 0 and bottom > poster_bottom:
                            poster_bottom = bottom
                        left = posx - border_left
                        if left < 0 and -left > poster_left:
                            poster_left = -left
                    else:
                        top = posy - border_left
                        if top < 0 and -top > poster_top:
                            poster_top = -top
                        right = posx + printable_height + border_top - poster_width
                        if right > 0 and right > poster_right:
                            poster_right = right
                        bottom = posy + printable_width + border_right - poster_height
                        if bottom > 0 and bottom > poster_bottom:
                            poster_bottom = bottom
                        left = posx - border_bottom
                        if left < 0 and -left > poster_left:
                            poster_left = -left
                self.layout["overallsize"] = (
                    poster_width + poster_left + poster_right,
                    poster_height + poster_top + poster_bottom,
                )

                self.layout["posterpos"] = (poster_left, poster_top)

        # size of output poster is always proportional to size of input page
        self.layout["postersize"] = poster_width, poster_height

        if mode == "size":
            mult = (poster_width * poster_height) / (inpage_width * inpage_height)
            npages = len(self.layout["positions"])
        elif mode == "mult":
            postersize = poster_width, poster_height
            npages = len(self.layout["positions"])
        elif mode == "npages":
            postersize = poster_width, poster_height
            mult = (poster_width * poster_height) / (inpage_width * inpage_height)
        else:
            raise Exception("unsupported mode: %s" % mode)

        return postersize, mult, npages

    def render(self, outfile):
        if not hasattr(self, "layout"):
            raise LayoutNotComputedException()

        inpage_width = pt_to_mm(self.doc[self.pagenr].getDisplayList().rect.width)

        outdoc = fitz.open()

        for (x, y, portrait) in self.layout["positions"]:
            if portrait:
                page_width = mm_to_pt(self.layout["output_pagesize"][0])
                page_height = mm_to_pt(self.layout["output_pagesize"][1])
            else:
                page_width = mm_to_pt(self.layout["output_pagesize"][1])
                page_height = mm_to_pt(self.layout["output_pagesize"][0])
            page = outdoc.newPage(
                -1, width=page_width, height=page_height  # insert after last page
            )

            if portrait:
                target_x = x - self.layout["border_left"]
                target_y = y - self.layout["border_top"]
                target_width = self.layout["output_pagesize"][0]
                target_height = self.layout["output_pagesize"][1]
            else:
                target_x = x - self.layout["border_bottom"]
                target_y = y - self.layout["border_left"]
                target_width = self.layout["output_pagesize"][1]
                target_height = self.layout["output_pagesize"][0]
            target_xoffset = 0
            target_yoffset = 0
            if target_x < 0:
                target_xoffset = -target_x
                target_width += target_x
                target_x = 0
            if target_y < 0:
                target_yoffset = -target_y
                target_height += target_y
                target_y = 0
            if target_x + target_width > self.layout["postersize"][0]:
                target_width = self.layout["postersize"][0] - target_x
            if target_y + target_height > self.layout["postersize"][1]:
                target_height = self.layout["postersize"][1] - target_y

            targetrect = fitz.Rect(
                mm_to_pt(target_xoffset),
                mm_to_pt(target_yoffset),
                mm_to_pt(target_xoffset + target_width),
                mm_to_pt(target_yoffset + target_height),
            )

            factor = inpage_width / self.layout["postersize"][0]
            sourcerect = fitz.Rect(
                mm_to_pt(factor * target_x),
                mm_to_pt(factor * target_y),
                mm_to_pt(factor * (target_x + target_width)),
                mm_to_pt(factor * (target_y + target_height)),
            )

            page.showPDFpage(
                targetrect,  # fill the whole page
                self.doc,  # input document
                self.pagenr,  # input page number
                clip=sourcerect,  # part of the input page to use
            )

        outdoc.save(outfile, garbage=4, deflate=True)


# from Python 3.7 Lib/idlelib/configdialog.py
# Copyright 2015-2017 Terry Jan Reedy
# Python License
class VerticalScrolledFrame(tkinter.Frame):
    """A pure Tkinter vertically scrollable frame.

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    """

    def __init__(self, parent, *args, **kw):
        tkinter.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        vscrollbar = tkinter.Scrollbar(self, orient=tkinter.VERTICAL)
        vscrollbar.pack(fill=tkinter.Y, side=tkinter.RIGHT, expand=tkinter.FALSE)
        canvas = tkinter.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=vscrollbar.set,
            width=240,
        )
        canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=tkinter.TRUE)
        vscrollbar.config(command=canvas.yview)

        # Reset the view.
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = interior = tkinter.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior, anchor=tkinter.NW)

        # Track changes to the canvas and frame width and sync them,
        # also updating the scrollbar.
        def _configure_interior(event):
            # Update the scrollbars to match the size of the inner frame.
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)

        interior.bind("<Configure>", _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the inner frame's width to fill the canvas.
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())

        canvas.bind("<Configure>", _configure_canvas)

        return


# From Python 3.7 Lib/tkinter/__init__.py
# Copyright 2000 Fredrik Lundh
# Python License
#
# add support for 'state' and 'name' kwargs
# add support for updating list of options
class OptionMenu(tkinter.Menubutton):
    """OptionMenu which allows the user to select a value from a menu."""

    def __init__(self, master, variable, value, *values, **kwargs):
        """Construct an optionmenu widget with the parent MASTER, with
        the resource textvariable set to VARIABLE, the initially selected
        value VALUE, the other menu values VALUES and an additional
        keyword argument command."""
        kw = {
            "borderwidth": 2,
            "textvariable": variable,
            "indicatoron": 1,
            "relief": tkinter.RAISED,
            "anchor": "c",
            "highlightthickness": 2,
        }
        if "state" in kwargs:
            kw["state"] = kwargs["state"]
            del kwargs["state"]
        if "name" in kwargs:
            kw["name"] = kwargs["name"]
            del kwargs["name"]
        tkinter.Widget.__init__(self, master, "menubutton", kw)
        self.widgetName = "tk_optionMenu"
        self.callback = kwargs.get("command")
        self.variable = variable
        if "command" in kwargs:
            del kwargs["command"]
        if kwargs:
            raise tkinter.TclError("unknown option -" + list(kwargs.keys())[0])
        self.set_values([value] + list(values))

    def __getitem__(self, name):
        if name == "menu":
            return self.__menu
        return tkinter.Widget.__getitem__(self, name)

    def set_values(self, values):
        menu = self.__menu = tkinter.Menu(self, name="menu", tearoff=0)
        self.menuname = menu._w
        for v in values:
            menu.add_command(
                label=v, command=tkinter._setit(self.variable, v, self.callback)
            )
        self["menu"] = menu

    def destroy(self):
        """Destroy this widget and the associated menu."""
        tkinter.Menubutton.destroy(self)
        self.__menu = None


class Application(tkinter.Frame):
    def __init__(self, master=None, plakativ=None):
        super().__init__(master)
        self.master = master
        self.master.title("plakativ")

        self.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

        if plakativ is not None:
            self.plakativ = plakativ

        self.canvas = tkinter.Canvas(self, bg="black")
        self.canvas.pack(fill=tkinter.BOTH, side=tkinter.LEFT, expand=tkinter.TRUE)
        self.canvas_size = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.bind("<Configure>", self.on_resize)

        frame_right = tkinter.Frame(self)
        frame_right.pack(side=tkinter.TOP, expand=tkinter.TRUE, fill=tkinter.Y)

        top_frame = tkinter.Frame(frame_right)
        top_frame.pack(fill=tkinter.X)

        tkinter.Button(top_frame, text="Open PDF", command=self.on_open_button).pack(
            side=tkinter.LEFT, expand=tkinter.TRUE, fill=tkinter.X
        )
        tkinter.Button(top_frame, text="Help", state=tkinter.DISABLED).pack(
            side=tkinter.RIGHT, expand=tkinter.TRUE, fill=tkinter.X
        )

        frame1 = VerticalScrolledFrame(frame_right)
        frame1.pack(side=tkinter.TOP, expand=tkinter.TRUE, fill=tkinter.Y)

        self.input = InputWidget(frame1.interior)
        self.input.pack(fill=tkinter.X)
        self.input.set(1, (0, 0))
        if hasattr(self, "plakativ"):
            self.input.callback = self.on_input

        self.pagesize = PageSizeWidget(frame1.interior)
        self.pagesize.pack(fill=tkinter.X)
        self.pagesize.set(False, (210, 297))
        if hasattr(self, "plakativ"):
            self.postersize.callback = self.on_pagesize

        self.bordersize = BorderSizeWidget(frame1.interior)
        self.bordersize.pack(fill=tkinter.X)
        self.bordersize.set(15.0, 15.0, 15.0, 15.0)
        if hasattr(self, "plakativ"):
            self.postersize.callback = self.on_bordersize

        self.postersize = PostersizeWidget(frame1.interior)
        self.postersize.pack(fill=tkinter.X)
        self.postersize.set("size", (False, (594, 841)), 1.0, 1)
        if hasattr(self, "plakativ"):
            self.postersize.callback = self.on_postersize

        self.layouter = LayouterWidget(frame1.interior)
        self.layouter.pack(fill=tkinter.X)
        self.layouter.set("simple")
        if hasattr(self, "plakativ"):
            self.postersize.callback = self.on_layouter

        output_group = tkinter.LabelFrame(frame1.interior, text="Output options")
        output_group.pack(fill=tkinter.X)

        tkinter.Checkbutton(
            output_group, text="Print cutting guides", state=tkinter.DISABLED
        ).pack(anchor=tkinter.W)
        tkinter.Checkbutton(
            output_group, text="Print poster border", state=tkinter.DISABLED
        ).pack(anchor=tkinter.W)
        tkinter.Checkbutton(
            output_group, text="Print page number", state=tkinter.DISABLED
        ).pack(anchor=tkinter.W)
        tkinter.Checkbutton(
            output_group, text="Print layout cover page", state=tkinter.DISABLED
        ).pack(anchor=tkinter.W)

        option_group = tkinter.LabelFrame(frame1.interior, text="Program options")
        option_group.pack(fill=tkinter.X)

        tkinter.Label(option_group, text="Unit:", state=tkinter.DISABLED).grid(
            row=0, column=0, sticky=tkinter.W
        )
        unit = tkinter.StringVar()
        unit.set("mm")
        OptionMenu(option_group, unit, ["mm"], state=tkinter.DISABLED).grid(
            row=0, column=1, sticky=tkinter.W
        )

        tkinter.Label(option_group, text="Language:", state=tkinter.DISABLED).grid(
            row=1, column=0, sticky=tkinter.W
        )
        language = tkinter.StringVar()
        language.set("English")
        OptionMenu(option_group, language, ["English"], state=tkinter.DISABLED).grid(
            row=1, column=1, sticky=tkinter.W
        )

        bottom_frame = tkinter.Frame(frame_right)
        bottom_frame.pack(fill=tkinter.X)

        self.save_button = tkinter.Button(
            bottom_frame,
            text="Save PDF",
            command=self.on_save_button,
            state=tkinter.DISABLED,
        )
        self.save_button.pack(side=tkinter.LEFT, expand=tkinter.TRUE, fill=tkinter.X)

        quit_button = tkinter.Button(
            bottom_frame, text="Exit", command=self.master.destroy
        )
        quit_button.pack(side=tkinter.RIGHT, expand=tkinter.TRUE, fill=tkinter.X)

    def on_input(self, value):
        _, pagesize = self.pagesize.value
        pagenum, _ = value
        mode, (custom_size, size), mult, npages = self.postersize.value
        bordersize = self.bordersize.value
        strategy = self.layouter.value
        self.plakativ.set_input_pagenr(pagenum - 1)
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, pagesize, bordersize, strategy
        )
        self.postersize.set(mode, (custom_size, size), mult, npages)
        self.draw()
        width, height = self.plakativ.get_input_page_size()
        return "%.02f" % pt_to_mm(width), "%.02f" % pt_to_mm(height)

    def on_pagesize(self, value):
        _, pagesize = value
        pagenum, _ = self.input.value
        mode, (custom_size, size), mult, npages = self.postersize.value
        bordersize = self.bordersize.value
        strategy = self.layouter.value
        self.plakativ.set_input_pagenr(pagenum - 1)
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, pagesize, bordersize, strategy
        )
        self.postersize.set(mode, (custom_size, size), mult, npages)
        self.draw()

    def on_bordersize(self, value):
        _, pagesize = self.pagesize.value
        pagenum, _ = self.input.value
        mode, (custom_size, size), mult, npages = self.postersize.value
        strategy = self.layouter.value
        self.plakativ.set_input_pagenr(pagenum - 1)
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, pagesize, value, strategy
        )
        self.postersize.set(mode, (custom_size, size), mult, npages)
        self.draw()

    def on_postersize(self, value):
        mode, (custom_size, size), mult, npages = value
        pagenum, _ = self.input.value
        _, pagesize = self.pagesize.value
        border = self.bordersize.value
        strategy = self.layouter.value
        self.plakativ.set_input_pagenr(pagenum - 1)
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, pagesize, border, strategy
        )
        self.draw()
        return (mode, (custom_size, size), mult, npages)

    def on_layouter(self, value):
        _, pagesize = self.pagesize.value
        pagenum, _ = self.input.value
        mode, (custom_size, size), mult, npages = self.postersize.value
        border = self.bordersize.value
        self.plakativ.set_input_pagenr(pagenum - 1)
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, pagesize, border, value
        )
        self.postersize.set(mode, (custom_size, size), mult, npages)
        self.draw()

    def on_resize(self, event):
        self.canvas_size = (event.width, event.height)
        self.draw()

    def draw(self):
        # clean canvas
        self.canvas.delete(tkinter.ALL)

        if not hasattr(self, "plakativ"):
            self.canvas.create_text(
                self.canvas_size[0] / 2,
                self.canvas_size[1] / 2,
                text='Click on the "Open PDF" button in the upper right.',
                fill="white",
            )
            return

        canvas_padding = 10

        width, height = self.plakativ.get_input_page_size()

        # factor to convert from input page dimensions (given in pt) into
        # canvas dimensions (given in pixels)
        zoom_0 = min(
            self.canvas_size[0]
            / width
            * self.plakativ.layout["postersize"][0]
            / (self.plakativ.layout["overallsize"][0] + canvas_padding),
            self.canvas_size[1]
            / height
            * self.plakativ.layout["postersize"][1]
            / (self.plakativ.layout["overallsize"][1] + canvas_padding),
        )

        img = self.plakativ.get_image(zoom_0)
        tkimg = tkinter.PhotoImage(data=img)

        # factor to convert from output poster dimensions (given in mm) into
        # canvas dimensions (given in pixels)
        zoom_1 = min(
            self.canvas_size[0]
            / (self.plakativ.layout["overallsize"][0] + canvas_padding),
            self.canvas_size[1]
            / (self.plakativ.layout["overallsize"][1] + canvas_padding),
        )

        # draw image on canvas
        self.canvas.create_image(
            (self.canvas_size[0] - zoom_1 * self.plakativ.layout["overallsize"][0]) / 2
            + zoom_1 * self.plakativ.layout["posterpos"][0],
            (self.canvas_size[1] - zoom_1 * self.plakativ.layout["overallsize"][1]) / 2
            + zoom_1 * self.plakativ.layout["posterpos"][1],
            anchor=tkinter.NW,
            image=tkimg,
        )
        self.canvas.image = tkimg

        # self.canvas.create_text(
        #    self.canvas_size[0] / 2,
        #    self.canvas_size[1] / 2,
        #    text="%d" % len(self.plakativ.layout["positions"]),
        #    fill="grey",
        #    font=("TkDefaultFont", 40),
        #    anchor=tkinter.CENTER,
        # )

        # draw rectangles
        # TODO: also draw numbers indicating the page number
        for (x, y, portrait) in self.plakativ.layout["positions"]:
            x0 = (x + self.plakativ.layout["posterpos"][0]) * zoom_1 + (
                self.canvas_size[0] - zoom_1 * self.plakativ.layout["overallsize"][0]
            ) / 2
            y0 = (y + self.plakativ.layout["posterpos"][1]) * zoom_1 + (
                self.canvas_size[1] - zoom_1 * self.plakativ.layout["overallsize"][1]
            ) / 2
            if portrait:
                page_width = self.plakativ.layout["output_pagesize"][0] * zoom_1
                page_height = self.plakativ.layout["output_pagesize"][1] * zoom_1
                top = self.plakativ.layout["border_top"] * zoom_1
                right = self.plakativ.layout["border_right"] * zoom_1
                bottom = self.plakativ.layout["border_bottom"] * zoom_1
                left = self.plakativ.layout["border_left"] * zoom_1
            else:
                # page is rotated 90 degrees clockwise
                page_width = self.plakativ.layout["output_pagesize"][1] * zoom_1
                page_height = self.plakativ.layout["output_pagesize"][0] * zoom_1
                top = self.plakativ.layout["border_left"] * zoom_1
                right = self.plakativ.layout["border_top"] * zoom_1
                bottom = self.plakativ.layout["border_right"] * zoom_1
                left = self.plakativ.layout["border_bottom"] * zoom_1
            # inner rectangle
            self.canvas.create_rectangle(
                x0,
                y0,
                x0 + page_width - left - right,
                y0 + page_height - top - bottom,
                outline="blue",
            )
            # outer rectangle
            self.canvas.create_rectangle(
                x0 - left,
                y0 - top,
                x0 - left + page_width,
                y0 - top + page_height,
                outline="red",
            )

        # filename = "out_%03d.ps" % len(self.plakativ.layout["positions"])
        # self.canvas.postscript(file=filename)
        # print("saved ", filename)

    def on_open_button(self):
        filename = tkinter.filedialog.askopenfilename(
            parent=self.master,
            title="foobar",
            filetypes=[("pdf documents", "*.pdf"), ("all files", "*")],
            initialdir="/home/josch/git/plakativ",
            initialfile="test.pdf",
        )
        if filename == ():
            return
        self.filename = filename
        self.plakativ = Plakativ(self.filename)
        # compute the splitting with the current values
        mode, (custom_size, size), mult, npages = self.postersize.value
        _, pagesize = self.pagesize.value
        border = self.bordersize.value
        strategy = self.layouter.value
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, pagesize, border, strategy
        )
        # update input widget
        width, height = self.plakativ.get_input_page_size()
        self.input.set(1, ("%.02f" % pt_to_mm(width), "%.02f" % pt_to_mm(height)))
        self.input.nametowidget("spinbox_pagenum").configure(
            to=self.plakativ.get_input_pagenums()
        )
        self.input.nametowidget("label_of_pagenum").configure(
            text="of %d" % self.plakativ.get_input_pagenums()
        )
        # update postersize widget
        self.postersize.set(mode, (custom_size, size), mult, npages)
        # draw preview in canvas
        self.draw()
        # enable save button
        self.save_button.configure(state=tkinter.NORMAL)
        # set callback function
        self.input.callback = self.on_input
        self.pagesize.callback = self.on_pagesize
        self.bordersize.callback = self.on_bordersize
        self.postersize.callback = self.on_postersize
        self.layouter.callback = self.on_layouter

    def on_save_button(self):
        base, ext = os.path.splitext(os.path.basename(self.filename))
        filename = tkinter.filedialog.asksaveasfilename(
            parent=self.master,
            title="foobar",
            defaultextension=".pdf",
            filetypes=[("pdf documents", "*.pdf"), ("all files", "*")],
            initialdir="/home/josch/git/plakativ",
            initialfile=base + "_poster" + ext,
        )
        if filename == "":
            return
        self.plakativ.render(filename)


class LayouterWidget(tkinter.LabelFrame):
    def __init__(self, parent, *args, **kw):
        tkinter.LabelFrame.__init__(self, parent, text="Layouter", *args, **kw)

        self.callback = None

        self.variables = {"strategy": tkinter.StringVar()}

        def callback(varname, idx, op):
            assert op == "w"
            self.on_strategy(self.variables["strategy"].get())

        self.variables["strategy"].trace("w", callback)

        layouter1 = tkinter.Radiobutton(
            self, text="Simple", variable=self.variables["strategy"], value="simple"
        )
        layouter1.pack(anchor=tkinter.W)
        layouter3 = tkinter.Radiobutton(
            self, text="Complex", variable=self.variables["strategy"], value="complex"
        )
        layouter3.pack(anchor=tkinter.W)

    def on_strategy(self, value):
        if getattr(self, "value", None) is None:
            return
        strategy = self.value
        self.set(value)

    def set(self, strategy):
        # before setting self.value, check if the effective value is different
        # from before or otherwise we do not need to execute the callback in
        # the end
        state_changed = True
        if getattr(self, "value", None) is not None:
            state_changed = self.value != strategy
        # execute callback if necessary
        if state_changed and self.callback is not None:
            pagesize = self.callback(strategy)
        self.value = strategy
        if self.variables["strategy"].get() != strategy:
            self.variables["strategy"].set(strategy)


class InputWidget(tkinter.LabelFrame):
    def __init__(self, parent, *args, **kw):
        tkinter.LabelFrame.__init__(self, parent, text="Input properties", *args, **kw)

        self.callback = None

        self.variables = {
            "pagenum": tkinter.IntVar(),
            "width": tkinter.StringVar(),
            "height": tkinter.StringVar(),
        }

        def callback(varname, idx, op):
            assert op == "w"
            self.on_pagenum(self.variables["pagenum"].get())

        self.variables["pagenum"].trace("w", callback)

        tkinter.Label(self, text="Use page").grid(row=0, column=0, sticky=tkinter.W)
        tkinter.Spinbox(
            self,
            increment=1,
            from_=1,
            to=100,
            width=3,
            name="spinbox_pagenum",
            textvariable=self.variables["pagenum"],
        ).grid(row=0, column=1, sticky=tkinter.W)
        tkinter.Label(self, text="of 1", name="label_of_pagenum").grid(
            row=0, column=2, sticky=tkinter.W
        )
        tkinter.Label(self, text="Width:").grid(row=1, column=0, sticky=tkinter.W)
        tkinter.Label(self, textvariable=self.variables["width"]).grid(
            row=1, column=1, sticky=tkinter.W
        )
        tkinter.Label(self, text="mm", name="size_label_width_mm").grid(
            row=1, column=2, sticky=tkinter.W
        )
        tkinter.Label(self, text="Height:").grid(row=2, column=0, sticky=tkinter.W)
        tkinter.Label(self, textvariable=self.variables["height"]).grid(
            row=2, column=1, sticky=tkinter.W
        )
        tkinter.Label(self, text="mm", name="size_label_height_mm").grid(
            row=2, column=2, sticky=tkinter.W
        )

    def on_pagenum(self, value):
        if getattr(self, "value", None) is None:
            return
        _, size = self.value
        self.set(value, size)

    def set(self, pagenum, pagesize):
        # before setting self.value, check if the effective value is different
        # from before or otherwise we do not need to execute the callback in
        # the end
        state_changed = True
        if getattr(self, "value", None) is not None:
            state_changed = self.value != (pagenum, pagesize)
        # execute callback if necessary
        if state_changed and self.callback is not None:
            pagesize = self.callback((pagenum, pagesize))
        self.value = (pagenum, pagesize)
        width, height = pagesize
        if self.variables["pagenum"].get() != pagenum:
            self.variables["pagenum"].set(pagenum)
        if self.variables["width"].get() != width:
            self.variables["width"].set(width)
        if self.variables["height"].get() != height:
            self.variables["height"].set(height)


class PageSizeWidget(tkinter.LabelFrame):
    def __init__(self, parent, *args, **kw):
        tkinter.LabelFrame.__init__(
            self, parent, text="Size of output pages", *args, **kw
        )

        self.callback = None

        self.variables = {
            "dropdown": tkinter.StringVar(),
            "width": tkinter.DoubleVar(),
            "height": tkinter.DoubleVar(),
        }

        for k, v in self.variables.items():
            # need to pass k and v as function arguments so that their value
            # does not get overwritten each loop iteration
            def callback(varname, idx, op, k_copy=k, v_copy=v):
                assert op == "w"
                getattr(self, "on_" + k_copy)(v_copy.get())

            v.trace("w", callback)

        OptionMenu(self, self.variables["dropdown"], *PAGE_SIZES.keys()).grid(
            row=1, column=0, columnspan=3, sticky=tkinter.W
        )

        tkinter.Label(
            self, text="Width:", state=tkinter.DISABLED, name="size_label_width"
        ).grid(row=2, column=0, sticky=tkinter.W)
        tkinter.Spinbox(
            self,
            format="%.2f",
            increment=0.01,
            from_=0,
            to=100,
            width=5,
            state=tkinter.DISABLED,
            name="spinbox_width",
            textvariable=self.variables["width"],
        ).grid(row=2, column=1, sticky=tkinter.W)
        tkinter.Label(
            self, text="mm", state=tkinter.DISABLED, name="size_label_width_mm"
        ).grid(row=2, column=2, sticky=tkinter.W)

        tkinter.Label(
            self, text="Height:", state=tkinter.DISABLED, name="size_label_height"
        ).grid(row=3, column=0, sticky=tkinter.W)
        tkinter.Spinbox(
            self,
            format="%.2f",
            increment=0.01,
            from_=0,
            to=100,
            width=5,
            state=tkinter.DISABLED,
            name="spinbox_height",
            textvariable=self.variables["height"],
        ).grid(row=3, column=1, sticky=tkinter.W)
        tkinter.Label(
            self, text="mm", state=tkinter.DISABLED, name="size_label_height_mm"
        ).grid(row=3, column=2, sticky=tkinter.W)

    def on_dropdown(self, value):
        custom_size, size = self.value
        if value == "custom":
            custom_size = True
        else:
            custom_size = False
            size = PAGE_SIZES[value]
        self.set(custom_size, size)

    def on_width(self, value):
        if getattr(self, "value", None) is None:
            return
        custom_size, (_, height) = self.value
        self.set(custom_size, (value, height))

    def on_height(self, value):
        if getattr(self, "value", None) is None:
            return
        custom_size, (width, _) = self.value
        self.set(custom_size, (width, value))

    def set(self, custom_size, pagesize):
        # before setting self.value, check if the effective value is different
        # from before or otherwise we do not need to execute the callback in
        # the end
        state_changed = True
        if getattr(self, "value", None) is not None:
            state_changed = self.value != (custom_size, pagesize)
        # execute callback if necessary
        if state_changed and self.callback is not None:
            self.callback((custom_size, pagesize))
        self.value = (custom_size, pagesize)
        width, height = pagesize
        if custom_size:
            self.nametowidget("size_label_width").configure(state=tkinter.NORMAL)
            self.nametowidget("spinbox_width").configure(state=tkinter.NORMAL)
            self.nametowidget("size_label_width_mm").configure(state=tkinter.NORMAL)
            self.nametowidget("size_label_height").configure(state=tkinter.NORMAL)
            self.nametowidget("spinbox_height").configure(state=tkinter.NORMAL)
            self.nametowidget("size_label_height_mm").configure(state=tkinter.NORMAL)
        else:
            self.nametowidget("size_label_width").configure(state=tkinter.DISABLED)
            self.nametowidget("spinbox_width").configure(state=tkinter.DISABLED)
            self.nametowidget("size_label_width_mm").configure(state=tkinter.DISABLED)
            self.nametowidget("size_label_height").configure(state=tkinter.DISABLED)
            self.nametowidget("spinbox_height").configure(state=tkinter.DISABLED)
            self.nametowidget("size_label_height_mm").configure(state=tkinter.DISABLED)
        # only set variables that changed to not trigger multiple variable tracers
        if custom_size:
            if self.variables["dropdown"].get() != "custom":
                self.variables["dropdown"].set("custom")
        else:
            val = dict(zip(PAGE_SIZES.values(), PAGE_SIZES.keys()))[(width, height)]
            if self.variables["dropdown"].get() != val:
                self.variables["dropdown"].set(val)
        if self.variables["width"].get() != width:
            self.variables["width"].set(width)
        if self.variables["height"].get() != height:
            self.variables["height"].set(height)


class BorderSizeWidget(tkinter.LabelFrame):
    def __init__(self, parent, *args, **kw):
        tkinter.LabelFrame.__init__(
            self, parent, text="Output Borders/Overlap", *args, **kw
        )

        self.callback = None

        self.variables = dict()
        for i, (n, label) in enumerate(
            [
                ("top", "Top:"),
                ("right", "Right:"),
                ("bottom", "Bottom:"),
                ("left", "Left:"),
            ]
        ):
            self.variables[n] = tkinter.DoubleVar()
            # need to pass k and v as function arguments so that their value
            # does not get overwritten each loop iteration
            def callback(varname, idx, op, k_copy=n, v_copy=self.variables[n]):
                assert op == "w"
                getattr(self, "on_" + k_copy)(v_copy.get())

            self.variables[n].trace("w", callback)

            tkinter.Label(self, text=label).grid(row=i, column=0, sticky=tkinter.W)
            tkinter.Spinbox(
                self,
                format="%.2f",
                increment=1.0,
                from_=0,
                to=100,
                width=5,
                textvariable=self.variables[n],
            ).grid(row=i, column=1)
            tkinter.Label(self, text="mm").grid(row=i, column=2)

    def on_top(self, value):
        if getattr(self, "value", None) is None:
            return
        _, right, bottom, left = self.value
        self.set(value, right, bottom, left)

    def on_right(self, value):
        if getattr(self, "value", None) is None:
            return
        top, _, bottom, left = self.value
        self.set(top, value, bottom, left)

    def on_bottom(self, value):
        if getattr(self, "value", None) is None:
            return
        top, right, _, left = self.value
        self.set(top, right, value, left)

    def on_left(self, value):
        if getattr(self, "value", None) is None:
            return
        top, right, bottom, _ = self.value
        self.set(top, right, bottom, value)

    def set(self, top, right, bottom, left):
        # before setting self.value, check if the effective value is different
        # from before or otherwise we do not need to execute the callback in
        # the end
        state_changed = True
        if getattr(self, "value", None) is not None:
            state_changed = self.value != (top, right, bottom, left)
        # execute callback if necessary
        if state_changed and self.callback is not None:
            self.callback((top, right, bottom, left))
        self.value = top, right, bottom, left
        # only set variables that changed to not trigger multiple variable tracers
        if self.variables["top"].get() != top:
            self.variables["top"].set(top)
        if self.variables["right"].get() != right:
            self.variables["right"].set(right)
        if self.variables["bottom"].get() != bottom:
            self.variables["bottom"].set(bottom)
        if self.variables["left"].get() != left:
            self.variables["left"].set(left)


class PostersizeWidget(tkinter.LabelFrame):
    def __init__(self, parent, *args, **kw):
        tkinter.LabelFrame.__init__(self, parent, text="Poster Size", *args, **kw)

        self.callback = None

        self.variables = {
            "radio": tkinter.StringVar(),
            "dropdown": tkinter.StringVar(),
            "width": tkinter.DoubleVar(),
            "height": tkinter.DoubleVar(),
            "multiplier": tkinter.DoubleVar(),
            "pages": tkinter.IntVar(),
        }

        for k, v in self.variables.items():
            # need to pass k and v as function arguments so that their value
            # does not get overwritten each loop iteration
            def callback(varname, idx, op, k_copy=k, v_copy=v):
                assert op == "w"
                getattr(self, "on_" + k_copy)(v_copy.get())

            v.trace("w", callback)

        tkinter.Radiobutton(
            self,
            text="Fit into width/height",
            variable=self.variables["radio"],
            value="size",
            state=tkinter.DISABLED,
            name="size_radio",
        ).grid(row=0, column=0, columnspan=3, sticky=tkinter.W)

        OptionMenu(
            self,
            self.variables["dropdown"],
            *PAGE_SIZES.keys(),
            #            state=tkinter.DISABLED,
            name="size_dropdown",
        ).grid(row=1, column=0, columnspan=3, sticky=tkinter.W, padx=(27, 0))

        tkinter.Label(
            self, text="Width:", state=tkinter.DISABLED, name="size_label_width"
        ).grid(row=2, column=0, sticky=tkinter.W, padx=(27, 0))
        tkinter.Spinbox(
            self,
            format="%.2f",
            increment=0.1,
            from_=0,
            to=10000,
            width=5,
            textvariable=self.variables["width"],
            state=tkinter.DISABLED,
            name="size_spinbox_width",
        ).grid(row=2, column=1, sticky=tkinter.W)
        tkinter.Label(
            self, text="mm", state=tkinter.DISABLED, name="size_label_width_mm"
        ).grid(row=2, column=2, sticky=tkinter.W)

        tkinter.Label(
            self, text="Height:", state=tkinter.DISABLED, name="size_label_height"
        ).grid(row=3, column=0, sticky=tkinter.W, padx=(27, 0))
        tkinter.Spinbox(
            self,
            format="%.2f",
            increment=0.1,
            from_=0,
            to=10000,
            width=5,
            textvariable=self.variables["height"],
            state=tkinter.DISABLED,
            name="size_spinbox_height",
        ).grid(row=3, column=1, sticky=tkinter.W)
        tkinter.Label(
            self, text="mm", state=tkinter.DISABLED, name="size_label_height_mm"
        ).grid(row=3, column=2, sticky=tkinter.W)

        tkinter.Radiobutton(
            self,
            text="Factor of input page area",
            variable=self.variables["radio"],
            value="mult",
            state=tkinter.DISABLED,
            name="mult_radio",
        ).grid(row=4, column=0, columnspan=3, sticky=tkinter.W)
        tkinter.Label(
            self,
            text="Multipler:",
            state=tkinter.DISABLED,
            name="mult_label_multiplier",
        ).grid(row=5, column=0, sticky=tkinter.W, padx=(27, 0))
        tkinter.Spinbox(
            self,
            format="%.2f",
            increment=0.01,
            from_=0,
            to=10000,
            width=6,
            textvariable=self.variables["multiplier"],
            state=tkinter.DISABLED,
            name="mult_spinbox_multiplier",
        ).grid(row=5, column=1, sticky=tkinter.W)
        tkinter.Label(
            self, text="%", state=tkinter.DISABLED, name="mult_label_perc"
        ).grid(row=5, column=2, sticky=tkinter.W)

        tkinter.Radiobutton(
            self,
            text="Fit into X output pages",
            variable=self.variables["radio"],
            value="npages",
            state=tkinter.DISABLED,
            name="npages_radio",
        ).grid(row=6, column=0, columnspan=3, sticky=tkinter.W)
        tkinter.Label(
            self, text="# of pages:", state=tkinter.DISABLED, name="npages_label"
        ).grid(row=7, column=0, sticky=tkinter.W, padx=(27, 0))
        tkinter.Spinbox(
            self,
            increment=1,
            from_=1,
            to=10000,
            width=6,
            textvariable=self.variables["pages"],
            state=tkinter.DISABLED,
            name="npages_spinbox",
        ).grid(row=7, column=1, sticky=tkinter.W)

    def on_radio(self, value):
        _, size, mult, npages = self.value
        self.set(value, size, mult, npages)

    def on_dropdown(self, value):
        mode, (custom_size, size), mult, npages = self.value
        if value == "custom":
            custom_size = True
        else:
            custom_size = False
            size = PAGE_SIZES[value]
        self.set(mode, (custom_size, size), mult, npages)

    def on_width(self, value):
        if getattr(self, "value", None) is None:
            return
        mode, (custom_size, (_, height)), mult, npages = self.value
        self.set(mode, (custom_size, (value, height)), mult, npages)

    def on_height(self, value):
        if getattr(self, "value", None) is None:
            return
        mode, (custom_size, (width, _)), mult, npages = self.value
        self.set(mode, (custom_size, (width, value)), mult, npages)

    def on_multiplier(self, value):
        if getattr(self, "value", None) is None:
            return
        mode, size, _, npages = self.value
        self.set(mode, size, value, npages)

    def on_pages(self, value):
        if getattr(self, "value", None) is None:
            return
        mode, size, mult, _ = self.value
        self.set(mode, size, mult, value)

    def set(self, mode, size, mult, npages):
        # before setting self.value, check if the effective value is different
        # from before or otherwise we do not need to execute the callback in
        # the end
        state_changed = True
        if getattr(self, "value", None) is not None:
            if mode == self.value[0] == "size":
                state_changed = self.value[1][1] != size[1]
            elif mode == self.value[0] == "mult":
                state_changed = self.value[2] != mult
            elif mode == self.value[0] == "npages":
                state_changed = self.value[3] != npages
        # execute callback if necessary
        if state_changed and self.callback is not None:
            mode, size, mult, npages = self.callback((mode, size, mult, npages))
        self.value = (mode, size, mult, npages)
        custom_size, (width, height) = size
        # cycle through all widgets and set the state accordingly
        for k, v in self.children.items():
            if k.endswith("_radio"):
                v.configure(state=tkinter.NORMAL)
                continue
            if not k.startswith(mode + "_"):
                v.configure(state=tkinter.DISABLED)
                continue
            if k in ["size_dropdown", "size_radio"]:
                v.configure(state=tkinter.NORMAL)
                continue
            if mode != "size":
                v.configure(state=tkinter.NORMAL)
                continue
            if custom_size:
                v.configure(state=tkinter.NORMAL)
                continue
            v.configure(state=tkinter.DISABLED)
        # only set variables that changed to not trigger multiple variable tracers
        if custom_size or mode != "size":
            if self.variables["dropdown"].get() != "custom":
                self.variables["dropdown"].set("custom")
        else:
            val = dict(zip(PAGE_SIZES.values(), PAGE_SIZES.keys()))[(width, height)]
            if self.variables["dropdown"].get() != val:
                self.variables["dropdown"].set(val)
        if self.variables["radio"].get() != mode:
            self.variables["radio"].set(mode)
        if self.variables["width"].get() != width:
            self.variables["width"].set(width)
        if self.variables["height"].get() != height:
            self.variables["height"].set(height)
        if self.variables["multiplier"].get() != mult:
            self.variables["multiplier"].set(mult)
        if self.variables["pages"].get() != npages:
            self.variables["pages"].set(npages)


def compute_layout(
    infile,
    outfile,
    mode,
    size=None,
    mult=None,
    npages=None,
    pagenr=0,
    pagesize=(210, 297),
    border=(0, 0, 0, 0),
    strategy="simple",
):
    plakativ = Plakativ(infile, pagenr)
    plakativ.compute_layout(mode, size, mult, npages, pagesize, border, strategy)
    plakativ.render(outfile)


def gui():
    root = tkinter.Tk()
    app = Application(master=root)
    app.mainloop()


def main():
    parser = argparse.ArgumentParser()
    gui_group = parser.add_mutually_exclusive_group(required=False)
    gui_group.add_argument(
        "--gui",
        dest="gui",
        action="store_true",
        help="run tkinter gui (default on Windows)",
    )
    gui_group.add_argument(
        "--nogui",
        dest="gui",
        action="store_false",
        help="don't run tkinter gui (default elsewhere)",
    )
    if platform.system() == "Windows":
        parser.set_defaults(gui=True)
    else:
        parser.set_defaults(gui=False)

    parser.add_argument(
        "--mode", choices=["size", "mult", "npages"], help="select poster size"
    )
    parser.add_argument("-o", "--output", help="output file")
    parser.add_argument("input", nargs="?", help="input file")

    args = parser.parse_args()

    if args.gui:
        gui()
        sys.exit(0)

    compute_layout(args.input, args.output, mode=args.mode, size=(297, 420))


if __name__ == "__main__":
    main()

__all__ = ["Plakativ", "compute_layout", "simple_cover", "complex_cover"]
