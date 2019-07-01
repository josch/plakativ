import pytest
import plakativ
import tempfile
import fitz
import fitz.utils
import os
import pdfrw


def mm_to_pt(length):
    return (72.0 * length) / 25.4


@pytest.fixture(scope="module")
def infile_a4_portrait():
    doc = fitz.open()
    width = mm_to_pt(210)
    height = mm_to_pt(297)
    page = doc.newPage(pno=-1, width=width, height=height)
    img = page.newShape()

    red = fitz.utils.getColor("red")
    green = fitz.utils.getColor("green")
    blue = fitz.utils.getColor("blue")
    orange = fitz.utils.getColor("orange")

    img.insertText(fitz.Point(97, 620), "A", fontsize=600, color=blue)
    img.commit()
    img.drawLine(fitz.Point(0, 0), fitz.Point(width, height))
    img.finish(color=red)
    img.drawLine(fitz.Point(0, height), fitz.Point(width, 0))
    img.finish(color=green)
    img.drawRect(fitz.Rect(fitz.Point(0, 0), fitz.Point(width, height)))
    img.finish(color=orange)
    img.commit()

    fd, tmpfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    doc.save(tmpfile, pretty=True, expand=255)
    yield tmpfile
    os.unlink(tmpfile)


@pytest.fixture(scope="module")
def infile_a4_landscape():
    doc = fitz.open()
    width = mm_to_pt(297)
    height = mm_to_pt(210)
    page = doc.newPage(pno=-1, width=width, height=height)
    img = page.newShape()

    red = fitz.utils.getColor("red")
    green = fitz.utils.getColor("green")
    blue = fitz.utils.getColor("blue")
    orange = fitz.utils.getColor("orange")

    img.insertText(fitz.Point(97, 620), "A", fontsize=600, color=blue)
    img.commit()
    img.drawLine(fitz.Point(0, 0), fitz.Point(width, height))
    img.finish(color=red)
    img.drawLine(fitz.Point(0, height), fitz.Point(width, 0))
    img.finish(color=green)
    img.drawRect(fitz.Rect(fitz.Point(0, 0), fitz.Point(width, height)))
    img.finish(color=orange)
    img.commit()

    fd, tmpfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    doc.save(tmpfile, pretty=True, expand=255)
    yield tmpfile
    os.unlink(tmpfile)


def test_foo_a3_portrait(infile_a4_portrait):
    fd, outfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    plakativ.compute_layout(infile_a4_portrait, outfile, mode="size", size=(297, 420))

    reader = pdfrw.PdfReader(outfile)
    os.unlink(outfile)

    pages = reader.Root.Pages.Kids
    assert len(pages) == 4
    assert pages[0].Resources.XObject.fzFrm0.BBox == [
        "0",
        "380.8549",
        "337.72779",
        "841.8898",
    ]
    assert pages[1].Resources.XObject.fzFrm0.BBox == [
        "257.5478",
        "380.8549",
        "595.2756",
        "841.8898",
    ]
    assert pages[2].Resources.XObject.fzFrm0.BBox == [
        "0",
        "0",
        "337.72779",
        "461.03489",
    ]
    assert pages[3].Resources.XObject.fzFrm0.BBox == [
        "257.5478",
        "0",
        "595.2756",
        "461.03489",
    ]
    assert pages[0].Resources.XObject.fzFrm0.Matrix == [
        "1.4141413",
        "0",
        "0",
        "1.4141413",
        "117.68077",
        "-538.5826",
    ]
    assert pages[1].Resources.XObject.fzFrm0.Matrix == [
        "1.4141413",
        "0",
        "0",
        "1.4141413",
        "-364.20893",
        "-538.5826",
    ]
    assert pages[2].Resources.XObject.fzFrm0.Matrix == [
        "1.4141413",
        "0",
        "0",
        "1.4141413",
        "117.68077",
        "189.9213",
    ]
    assert pages[3].Resources.XObject.fzFrm0.Matrix == [
        "1.4141413",
        "0",
        "0",
        "1.4141413",
        "-364.20893",
        "189.9213",
    ]


def test_foo_a3_landscape(infile_a4_landscape):
    fd, outfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    plakativ.compute_layout(infile_a4_landscape, outfile, mode="size", size=(420, 296))

    reader = pdfrw.PdfReader(outfile)
    os.unlink(outfile)

    pages = reader.Root.Pages.Kids
    assert len(pages) == 4
    assert pages[0].Resources.XObject.fzFrm0.BBox == [
        "0",
        "257.41648",
        "461.1662",
        "595.2756",
    ]
    assert pages[1].Resources.XObject.fzFrm0.BBox == [
        "380.72358",
        "257.41648",
        "841.8898",
        "595.2756",
    ]
    assert pages[2].Resources.XObject.fzFrm0.BBox == ["0", "0", "461.1662", "337.8591"]
    assert pages[3].Resources.XObject.fzFrm0.BBox == [
        "380.72358",
        "0",
        "841.8898",
        "337.8591",
    ]
    assert pages[0].Resources.XObject.fzFrm0.Matrix == [
        "1.4095239",
        "0",
        "0",
        "1.4095239",
        "191.86499",
        "-362.83467",
    ]
    assert pages[1].Resources.XObject.fzFrm0.Matrix == [
        "1.4095239",
        "0",
        "0",
        "1.4095239",
        "-536.6389",
        "-362.83467",
    ]
    assert pages[2].Resources.XObject.fzFrm0.Matrix == [
        "1.4095239",
        "0",
        "0",
        "1.4095239",
        "191.86499",
        "119.055118",
    ]
    assert pages[3].Resources.XObject.fzFrm0.Matrix == [
        "1.4095239",
        "0",
        "0",
        "1.4095239",
        "-536.6389",
        "119.055118",
    ]
