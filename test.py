import pytest
import plakativ
import tempfile
import fitz
import fitz.utils
import os
import pdfrw


@pytest.fixture(scope="module")
def infile():
    doc = fitz.open()
    page = doc.newPage(pno=-1, width=595, height=842)
    img = page.newShape()

    red = fitz.utils.getColor("red")
    green = fitz.utils.getColor("green")
    blue = fitz.utils.getColor("blue")
    orange = fitz.utils.getColor("orange")

    img.insertText(fitz.Point(97, 620), "A", fontsize=600, color=blue)
    img.commit()
    img.drawLine(fitz.Point(0, 0), fitz.Point(595, 842))
    img.finish(color=red)
    img.drawLine(fitz.Point(0, 842), fitz.Point(595, 0))
    img.finish(color=green)
    img.drawRect(fitz.Rect(fitz.Point(0, 0), fitz.Point(595, 842)))
    img.finish(color=orange)
    img.commit()

    fd, tmpfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    doc.save(tmpfile, pretty=True, expand=255)
    yield tmpfile
    os.unlink(tmpfile)


def test_foo(infile):
    print("blob")
    fd, outfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    plakativ.compute_layout(infile, outfile, mode="size", size=(297, 420))

    reader = pdfrw.PdfReader(outfile)
    pages = reader.Root.Pages.Kids
    assert len(pages) == 4
    assert pages[0].Resources.XObject.fzFrm0.BBox == [
        "0",
        "380.6912",
        "337.75163",
        "842",
    ]
    assert pages[1].Resources.XObject.fzFrm0.BBox == [
        "257.524",
        "380.6912",
        "595",
        "842",
    ]
    assert pages[2].Resources.XObject.fzFrm0.BBox == [
        "0",
        "0",
        "337.75163",
        "460.91883",
    ]
    assert pages[3].Resources.XObject.fzFrm0.BBox == [
        "257.524",
        "0",
        "595",
        "460.91883",
    ]
    assert pages[0].Resources.XObject.fzFrm0.Matrix == [
        "1.4133016",
        "0",
        "0",
        "1.4133016",
        "117.930667",
        "-538.03146",
    ]
    assert pages[1].Resources.XObject.fzFrm0.Matrix == [
        "1.4133017",
        "0",
        "0",
        "1.4133017",
        "-363.76438",
        "-538.0315",
    ]
    assert pages[2].Resources.XObject.fzFrm0.Matrix == [
        "1.4133016",
        "0",
        "0",
        "1.4133016",
        "117.930667",
        "190.19687",
    ]
    assert pages[3].Resources.XObject.fzFrm0.Matrix == [
        "1.4144558",
        "0",
        "0",
        "1.4144558",
        "-364.25627",
        "189.93088",
    ]
    os.unlink(outfile)
