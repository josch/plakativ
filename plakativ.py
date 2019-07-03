#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import OrderedDict
import math
import fitz
import tkinter
import tkinter.filedialog
import sys
import argparse
import os.path
import platform

VERSION = "0.1"

PAGE_SIZES = OrderedDict(
    [
        ("custom", (None, None)),
        ("A0 (84.1 cm × 118.9 cm)", (841, 1189)),
        ("A1 (59.4 cm × 84.1 cm)", (594, 841)),
        ("A2 (42.0 cm × 59.4 cm)", (420, 594)),
        ("A3 (29.7 cm × 42.0 cm)", (297, 420)),
        ("A4 (21.0 cm × 29.7 cm)", (210, 297)),
        ("A5 (14.8 cm × 21.0 cm)", (148, 210)),
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


class Plakativ:
    def __init__(self, infile, pagenr=1):
        self.doc = fitz.open(infile)
        self.pagenr = pagenr

        self.border_left = 20
        self.border_right = 20
        self.border_top = 20
        self.border_bottom = 20

    def set_input_pagenr(self, pagenr):
        if pagenr < 1 or pagenr >= len(self.doc):
            raise PageNrOutOfRangeException()

        self.pagenr = pagenr

    def get_input_page_size(self):
        width = self.doc[self.pagenr - 1].getDisplayList().rect.width
        height = self.doc[self.pagenr - 1].getDisplayList().rect.height
        return (width, height)

    def get_image(self, zoom):
        mat_0 = fitz.Matrix(zoom, zoom)
        pix = (
            self.doc[self.pagenr - 1]
            .getDisplayList()
            .getPixmap(matrix=mat_0, alpha=False)
        )
        return pix.getImageData("ppm")

    def compute_layout(
        self, mode, size=None, mult=None, npages=None, border=(0, 0, 0, 0)
    ):
        border_top, border_right, border_bottom, border_left = border

        self.layout = {
            "output_pagesize": PAGE_SIZES["A4 (21.0 cm × 29.7 cm)"],
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
        inpage_width = pt_to_mm(self.doc[self.pagenr - 1].getDisplayList().rect.width)
        inpage_height = pt_to_mm(self.doc[self.pagenr - 1].getDisplayList().rect.height)

        if mode in ["size", "mult"]:
            if mode == "size":
                # fit the input page size into the selected postersize
                poster_width = size[0]
                poster_height = (poster_width * inpage_height) / inpage_width
                if poster_height > size[1]:
                    poster_height = size[1]
                    poster_width = (poster_height * inpage_width) / inpage_height
            elif mode == "mult":
                area = inpage_width * inpage_height * mult
                poster_width = math.sqrt(area * inpage_width / inpage_height)
                poster_height = math.sqrt(area * inpage_height / inpage_width)
            else:
                raise Exception("unsupported mode: %s" % mode)

            pages_x_portrait = math.ceil(poster_width / printable_width)
            pages_y_portrait = math.ceil(poster_height / printable_height)

            pages_x_landscape = math.ceil(poster_width / printable_height)
            pages_y_landscape = math.ceil(poster_height / printable_width)

            portrait = True
            if (
                pages_x_portrait * pages_y_portrait
                > pages_x_landscape * pages_y_landscape
            ):
                portrait = False

            if portrait:
                pages_x = pages_x_portrait
                pages_y = pages_y_portrait
            else:
                pages_x = pages_x_landscape
                pages_y = pages_y_landscape
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
                        best = (x, y, True, poster_width, poster_height)

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
                        best = (x, y, False, poster_width, poster_height)

            pages_x, pages_y, portrait, poster_width, poster_height = best
        else:
            raise Exception("unsupported mode: %s" % mode)

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

        # size of output poster is always proportional to size of input page
        self.layout["postersize"] = poster_width, poster_height

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

        # positions are relative to upper left corner of poster
        self.layout["positions"] = []
        for y in range(pages_y):
            for x in range(pages_x):
                if portrait:
                    posx = x * printable_width
                    posy = y * printable_height
                else:
                    posx = x * printable_height
                    posy = y * printable_width
                self.layout["positions"].append((posx, posy, portrait))

        if mode == "size":
            mult = (poster_width * poster_height) / (inpage_width * inpage_height)
            npages = pages_x * pages_y
        elif mode == "mult":
            size = poster_width, poster_height
            npages = pages_x * pages_y
        elif mode == "npages":
            size = poster_width, poster_height
            mult = (poster_width * poster_height) / (inpage_width * inpage_height)
        else:
            raise Exception("unsupported mode: %s" % mode)

        return size, mult, npages

    def render(self, outfile):
        if not hasattr(self, "layout"):
            raise LayoutNotComputedException()

        inpage_width = pt_to_mm(self.doc[self.pagenr - 1].getDisplayList().rect.width)

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

            target_x = x - self.layout["posterpos"][0]
            target_y = y - self.layout["posterpos"][1]
            target_xoffset = 0
            target_yoffset = 0
            if portrait:
                target_width = self.layout["output_pagesize"][0]
                target_height = self.layout["output_pagesize"][1]
            else:
                target_width = self.layout["output_pagesize"][1]
                target_height = self.layout["output_pagesize"][0]
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
                self.pagenr - 1,  # input page number
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
        menu = self.__menu = tkinter.Menu(self, name="menu", tearoff=0)
        self.menuname = menu._w
        # 'command' is the only supported keyword
        callback = kwargs.get("command")
        if "command" in kwargs:
            del kwargs["command"]
        if kwargs:
            raise tkinter.TclError("unknown option -" + list(kwargs.keys())[0])
        menu.add_command(label=value, command=tkinter._setit(variable, value, callback))
        for v in values:
            menu.add_command(label=v, command=tkinter._setit(variable, v, callback))
        self["menu"] = menu

    def __getitem__(self, name):
        if name == "menu":
            return self.__menu
        return tkinter.Widget.__getitem__(self, name)

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

        # tkinter does not allow scrollbars for frames
        frame1 = VerticalScrolledFrame(self)
        frame1.pack(side=tkinter.TOP, expand=tkinter.TRUE, fill=tkinter.Y)

        top_frame = tkinter.Frame(frame1.interior)
        top_frame.pack(fill=tkinter.X)

        open_button = tkinter.Button(
            top_frame, text="Open PDF", command=self.on_open_button
        )
        open_button.pack(side=tkinter.LEFT, expand=tkinter.TRUE, fill=tkinter.X)
        help_button = tkinter.Button(top_frame, text="Help", state=tkinter.DISABLED)
        help_button.pack(side=tkinter.RIGHT, expand=tkinter.TRUE, fill=tkinter.X)

        input_group = tkinter.LabelFrame(frame1.interior, text="Input properties")
        input_group.pack(fill=tkinter.X)

        label_input_width = tkinter.Label(input_group, text="Width:")
        label_input_width.grid(row=0, column=0, sticky=tkinter.W)
        label_input_height = tkinter.Label(input_group, text="Height:")
        label_input_height.grid(row=1, column=0, sticky=tkinter.W)
        label_input_npages = tkinter.Label(input_group, text="# of pages:")
        label_input_npages.grid(row=2, column=0, sticky=tkinter.W)
        label_input_range = tkinter.Label(input_group, text="Page range:")
        label_input_range.grid(row=3, column=0, sticky=tkinter.W)
        self.input_range = tkinter.StringVar()
        self.input_range.set("1")
        input_range_entry = tkinter.Entry(
            input_group, textvariable=self.input_range, width=6, state=tkinter.DISABLED
        )
        input_range_entry.grid(row=3, column=1, sticky=tkinter.W)

        pagesize_group = tkinter.LabelFrame(
            frame1.interior, text="Size of output pages"
        )
        pagesize_group.pack(fill=tkinter.X)

        pagesize_fixed = tkinter.StringVar()
        if not hasattr(self, "plakativ"):
            pagesize_fixed.set("")
        else:
            pagesize_fixed.set(
                dict(zip(PAGE_SIZES.values(), PAGE_SIZES.keys()))[
                    self.plakativ.pagesize
                ]
            )
        pagesize_options = OptionMenu(
            pagesize_group,
            pagesize_fixed,
            *PAGE_SIZES.keys(),
            command=self.on_select_pagesize,
            state=tkinter.DISABLED if not hasattr(self, "plakativ") else tkinter.NORMAL
        )
        pagesize_options.grid(row=1, column=0, columnspan=3, sticky=tkinter.W)

        label_pagesize_width = tkinter.Label(
            pagesize_group, text="Width:", state=tkinter.DISABLED
        )
        label_pagesize_width.grid(row=2, column=0, sticky=tkinter.W)
        pagesize_width = tkinter.Spinbox(
            pagesize_group,
            format="%.2f",
            increment=0.01,
            from_=0,
            to=100,
            width=5,
            state=tkinter.DISABLED,
        )
        pagesize_width.grid(row=2, column=1, sticky=tkinter.W)
        label_pagesize_width_mm = tkinter.Label(
            pagesize_group, text="mm", state=tkinter.DISABLED
        )
        label_pagesize_width_mm.grid(row=2, column=2, sticky=tkinter.W)

        label_pagesize_height = tkinter.Label(
            pagesize_group, text="Height:", state=tkinter.DISABLED
        )
        label_pagesize_height.grid(row=3, column=0, sticky=tkinter.W)
        pagesize_height = tkinter.Spinbox(
            pagesize_group,
            format="%.2f",
            increment=0.01,
            from_=0,
            to=100,
            width=5,
            state=tkinter.DISABLED,
        )
        pagesize_height.grid(row=3, column=1, sticky=tkinter.W)
        label_pagesize_height_mm = tkinter.Label(
            pagesize_group, text="mm", state=tkinter.DISABLED
        )
        label_pagesize_height_mm.grid(row=3, column=2, sticky=tkinter.W)

        self.border = BorderWidget(frame1.interior)
        self.border.pack(fill=tkinter.X)
        self.border.set(20.0, 20.0, 20.0, 20.0)
        if hasattr(self, "plakativ"):
            self.postersize.callback = self.on_border

        self.postersize = PostersizeWidget(frame1.interior)
        self.postersize.pack(fill=tkinter.X)
        self.postersize.set("size", (False, (594, 841)), 1.0, 1)
        if hasattr(self, "plakativ"):
            self.postersize.callback = self.on_postersize

        layouter_group = tkinter.LabelFrame(frame1.interior, text="Layouter")
        layouter_group.pack(fill=tkinter.X)

        self.layouter = tkinter.IntVar()
        self.layouter.set(1)
        layouter1 = tkinter.Radiobutton(
            layouter_group, text="Simple", variable=self.layouter, value=1
        )
        layouter1.pack(anchor=tkinter.W)
        layouter2 = tkinter.Radiobutton(
            layouter_group,
            text="Advanced",
            variable=self.layouter,
            value=2,
            state=tkinter.DISABLED,
        )
        layouter2.pack(anchor=tkinter.W)
        layouter3 = tkinter.Radiobutton(
            layouter_group,
            text="Complex",
            variable=self.layouter,
            value=3,
            state=tkinter.DISABLED,
        )
        layouter3.pack(anchor=tkinter.W)

        output_group = tkinter.LabelFrame(frame1.interior, text="Output options")
        output_group.pack(fill=tkinter.X)

        tkinter.Checkbutton(
            output_group, text="Print cutting guides", state=tkinter.DISABLED
        ).pack(anchor=tkinter.W)
        tkinter.Checkbutton(
            output_group, text="Print poster border", state=tkinter.DISABLED
        ).pack(anchor=tkinter.W)

        bottom_frame = tkinter.Frame(frame1.interior)
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

    def on_postersize(self, value):
        mode, (custom_size, size), mult, npages = value
        border = self.border.value
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, border
        )
        self.draw()
        return (mode, (custom_size, size), mult, npages)

    def on_border(self, value):
        mode, (custom_size, size), mult, npages = self.postersize.value
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, value
        )
        self.postersize.set(mode, (custom_size, size), mult, npages)
        self.draw()

    def on_select_pagesize(self, value):
        self.posterizer.pagesize = PAGE_SIZES[value]
        self.posterizer.compute_layout()
        self.draw()

    def on_resize(self, event):
        self.canvas_size = (event.width, event.height)
        self.draw()

    def draw(self):
        # clean canvas
        self.canvas.delete(tkinter.ALL)

        if not hasattr(self, "plakativ"):
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

        # draw rectangles
        for (x, y, portrait) in self.plakativ.layout["positions"]:
            x0 = (
                x * zoom_1
                + (
                    self.canvas_size[0]
                    - zoom_1 * self.plakativ.layout["overallsize"][0]
                )
                / 2
            )
            y0 = (
                y * zoom_1
                + (
                    self.canvas_size[1]
                    - zoom_1 * self.plakativ.layout["overallsize"][1]
                )
                / 2
            )
            if portrait:
                x1 = x0 + self.plakativ.layout["output_pagesize"][0] * zoom_1
                y1 = y0 + self.plakativ.layout["output_pagesize"][1] * zoom_1
            else:
                x1 = x0 + self.plakativ.layout["output_pagesize"][1] * zoom_1
                y1 = y0 + self.plakativ.layout["output_pagesize"][0] * zoom_1
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="red")
            if portrait:
                top = self.plakativ.layout["border_top"]
                right = self.plakativ.layout["border_right"]
                bottom = self.plakativ.layout["border_bottom"]
                left = self.plakativ.layout["border_left"]
            else:
                top = self.plakativ.layout["border_left"]
                right = self.plakativ.layout["border_top"]
                bottom = self.plakativ.layout["border_right"]
                left = self.plakativ.layout["border_bottom"]
            self.canvas.create_rectangle(
                x0 + zoom_1 * left,
                y0 + zoom_1 * top,
                x1 - zoom_1 * right,
                y1 - zoom_1 * bottom,
                outline="blue",
            )

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
        border = self.border.value
        size, mult, npages = self.plakativ.compute_layout(
            mode, size, mult, npages, border
        )
        # update postersize widget
        self.postersize.set(mode, (custom_size, size), mult, npages)
        # draw preview in canvas
        self.draw()
        # enable save button
        self.save_button.configure(state=tkinter.NORMAL)
        # set callback function
        self.postersize.callback = self.on_postersize
        self.border.callback = self.on_border

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


class BorderWidget(tkinter.LabelFrame):
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
            name="size_dropdown"
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
            text="Factor of input page size",
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
    infile, outfile, mode, size=None, mult=None, npages=None, border=(0, 0, 0, 0)
):
    plakativ = Plakativ(infile)
    plakativ.compute_layout(mode, size, mult, npages, border)
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
        exit(0)

    compute_layout(args.input, args.output, mode=args.mode, size=(297, 420))


if __name__ == "__main__":
    main()

__all__ = ["Plakativ", "compute_layout"]
