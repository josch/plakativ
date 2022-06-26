import pytest
import plakativ
import tempfile
import fitz
import fitz.utils
import os
import math


def mm_to_pt(length):
    return (72.0 * length) / 25.4


def _create_pdf(width, height):
    return tmpfile


@pytest.fixture(scope="module")
def infile_a4_portrait():
    tmpfile = _create_pdf(mm_to_pt(210), mm_to_pt(297))
    yield tmpfile
    os.unlink(tmpfile)


@pytest.fixture(scope="module")
def infile_custom_portrait():
    tmpfile = _create_pdf(mm_to_pt(200), mm_to_pt(400))
    yield tmpfile
    os.unlink(tmpfile)


@pytest.fixture(scope="module")
def infile_a4_landscape():
    tmpfile = _create_pdf(mm_to_pt(297), mm_to_pt(210))
    yield tmpfile
    os.unlink(tmpfile)


@pytest.fixture(scope="module")
def infile_custom_landscape():
    tmpfile = _create_pdf(mm_to_pt(400), mm_to_pt(200))
    yield tmpfile
    os.unlink(tmpfile)


@pytest.fixture(scope="module")
def infile_custom_square():
    tmpfile = _create_pdf(mm_to_pt(300), mm_to_pt(300))
    yield tmpfile
    os.unlink(tmpfile)


_formats = {
    "dina4_portrait": (210, 297),
    "dina4_landscape": (297, 210),
    "dina3_portrait": (297, 420),
    "dina3_landscape": (420, 297),
    "dina2_portrait": (420, 594),
}


@pytest.mark.parametrize(
    "postersize,input_pagesize,output_pagesize,strategy,expected",
    [
        (
            _formats["dina3_portrait"],
            _formats["dina4_portrait"],
            _formats["dina4_portrait"],
            "simple",
            [
                (
                    ["0", "380.8549", "337.72779", "841.8898"],
                    ["1.4141413", "0", "0", "1.4141413", "117.68077", "-538.5826"],
                ),
                (
                    ["257.5478", "380.8549", "595.2756", "841.8898"],
                    ["1.4141413", "0", "0", "1.4141413", "-364.20893", "-538.5826"],
                ),
                (
                    ["0", "0", "337.72779", "461.03489"],
                    ["1.4141413", "0", "0", "1.4141413", "117.68077", "189.9213"],
                ),
                (
                    ["257.5478", "0", "595.2756", "461.03489"],
                    ["1.4141413", "0", "0", "1.4141413", "-364.20893", "189.9213"],
                ),
            ],
        ),
        (
            _formats["dina3_landscape"],
            _formats["dina4_landscape"],
            _formats["dina4_portrait"],
            "simple",
            [
                (
                    ["0", "257.5478", "461.03489", "595.2756"],
                    ["1.4141413", "0", "0", "1.4141413", "189.9213", "-364.20893"],
                ),
                (
                    ["380.8549", "257.5478", "841.8898", "595.2756"],
                    ["1.4141413", "0", "0", "1.4141413", "-538.5826", "-364.20893"],
                ),
                (
                    ["0", "0", "461.03489", "337.72779"],
                    ["1.4141413", "0", "0", "1.4141413", "189.9213", "117.68074"],
                ),
                (
                    ["380.8549", "0", "841.8898", "337.72779"],
                    ["1.4141413", "0", "0", "1.4141413", "-538.5826", "117.68074"],
                ),
            ],
        ),
        (
            _formats["dina2_portrait"],
            _formats["dina4_landscape"],
            _formats["dina4_portrait"],
            "complex",
            [
                (
                    ["0", "202.67716", "269.29136", "595.2756"],
                    ["1.9999999", "0", "0", "1.9999999", "56.692934", "-405.35429"],
                ),
                (
                    ["212.59844", "202.67716", "510.23625", "595.2756"],
                    ["1.9999999", "0", "0", "1.9999999", "-425.1968", "-405.35429"],
                ),
                (
                    ["449.29136", "325.98423", "841.8898", "595.2756"],
                    ["1.9999998", "0", "0", "1.9999998", "-898.58267", "-651.9683"],
                ),
                (
                    ["331.65354", "0", "629.2913", "392.59846"],
                    ["1.9999999", "0", "0", "1.9999999", "-663.307", "56.692934"],
                ),
                (
                    ["572.59848", "0", "841.8898", "392.59846"],
                    ["1.9999999", "0", "0", "1.9999999", "-1145.1968", "56.692934"],
                ),
                (
                    ["0", "0", "392.59843", "269.29136"],
                    ["2", "0", "0", "2", "56.692934", "56.69287"],
                ),
            ],
        ),
    ],
)
def test_cases(postersize, input_pagesize, output_pagesize, strategy, expected):
    width = mm_to_pt(input_pagesize[0])
    height = mm_to_pt(input_pagesize[1])

    doc = fitz.open()
    page = doc.new_page(pno=-1, width=width, height=height)
    img = page.new_shape()

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

    fd, infile = tempfile.mkstemp(
        prefix="plakativ", suffix="%f_%f.pdf" % (width, height)
    )
    os.close(fd)
    doc.save(infile, pretty=True, expand=255)
    doc.close()

    fd, outfile = tempfile.mkstemp(prefix="plakativ")
    os.close(fd)
    plakativ.compute_layout(
        infile,
        outfile,
        mode="size",
        size=postersize,
        pagesize=output_pagesize,
        border=(20, 20, 20, 20),
        strategy=strategy,
    )
    os.unlink(infile)

    doc = fitz.open(outfile)

    for pnum, (bbox, matrix) in zip(range(doc.page_count), expected):
        xreflist = doc._getPageInfo(pnum, 3)
        assert len(xreflist) >= 1
        xref, name, _, _ = xreflist[0]
        assert name == "fzFrm0"
        # doc.xrefObject() will return something like:
        #      <<
        #        /Type /XObject
        #        /Subtype /Form
        #        /BBox [ 185.47917 262.17189 445.79167 595 ]
        #        /Matrix [ 2.286773 0 0 2.286773 -424.1487 -599.5276 ]
        #        /Resources <<
        #          /XObject <<
        #            /fullpage 7 0 R
        #          >>
        #        >>
        #        /Length 12
        #      >>
        keyvals = dict(
            tuple(line.strip().split(maxsplit=1))
            for line in doc.xref_object(xref).splitlines()
            if " " in line.strip()
        )
        assert "/BBox" in keyvals
        newbbox = keyvals["/BBox"].strip(" []").split()
        for v1, v2 in zip(bbox, newbbox):
            assert math.isclose(float(v1), float(v2), abs_tol=0.00001)
        assert "/Matrix" in keyvals
        newmatrix = keyvals["/Matrix"].strip(" []").split()
        for v1, v2 in zip(matrix, newmatrix):
            assert math.isclose(float(v1), float(v2), abs_tol=0.00001)
    doc.close()
    os.unlink(outfile)
