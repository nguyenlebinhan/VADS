from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import fitz


def minimal_pdf() -> bytes:
    return b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def minimal_docx() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
        )
    return buffer.getvalue()


def pdf_with_pages(page_texts: list[str | None]) -> bytes:
    document = fitz.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            y = 72
            for line in text.splitlines():
                page.insert_text((72, y), line, fontsize=11)
                y += 20
    result = document.tobytes()
    document.close()
    return result
