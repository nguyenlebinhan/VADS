"""Generate the two DOCX fixtures used by the Postman regulatory-change demo."""

from pathlib import Path

from docx import Document

VERSIONS = {
    2024: (
        "Điều 10. Quy định phê duyệt",
        "Khoản 2. Hạn mức và thẩm quyền",
        "Ngưỡng phê duyệt: 500 triệu đồng.",
        "Thời hạn báo cáo: 30 ngày.",
        "Đơn vị phê duyệt: UBND tỉnh.",
    ),
    2026: (
        "Điều 12. Quy định phê duyệt",
        "Khoản 3. Hạn mức và thẩm quyền",
        "Ngưỡng phê duyệt: 800 triệu đồng.",
        "Thời hạn báo cáo: 30 ngày.",
        "Đơn vị phê duyệt: Sở Tài chính.",
    ),
}


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / "docs" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    for year, paragraphs in VERSIONS.items():
        document = Document()
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
        output_path = output_dir / f"quy-dinh-tham-dinh-{year}.docx"
        document.save(output_path)
        print(output_path)


if __name__ == "__main__":
    main()
