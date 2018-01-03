from __future__ import print_function
from wand.image import Image
import io
import PyPDF2
import os


def pdf_page_to_png(src_pdf, pagenum, resolution=72):
    """
    Returns specified PDF page as wand.image.Image png.
    :param PyPDF2.PdfFileReader src_pdf: PDF from which to take pages.
    :param int pagenum: Page number to take.
    :param int resolution: Resolution for resulting png in DPI.
    """
    dst_pdf = PyPDF2.PdfFileWriter()
    dst_pdf.addPage(src_pdf.getPage(pagenum))

    pdf_bytes = io.BytesIO()
    dst_pdf.write(pdf_bytes)
    pdf_bytes.seek(0)

    img = Image(file=pdf_bytes, resolution=resolution)
    img.convert("png")

    return img


def extract_pdf_pages_as_images(pdf_path, destination_folder):
    """
    Exports PDF file pages to specified folder as PNG images
    :param pdf_path: Path to pdf file
    :param destination_folder: Path to folder to store page images
    :return: an iterator over ``(page_id, file_path)`` tuples
    :rtype: ``iterator``
    """
    with open(pdf_path, "rb") as f:
        src_pdf = PyPDF2.PdfFileReader(f)
        for page in range(src_pdf.numPages):
            img = pdf_page_to_png(src_pdf, pagenum=page)
            img_path = os.path.join(destination_folder, '{}.png'.format(page))
            img.save(filename=img_path)
            yield (page, img_path)