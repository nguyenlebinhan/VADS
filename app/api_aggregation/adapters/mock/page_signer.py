from urllib.parse import quote


class MockPageImageUrlSigner:
    def sign_page_image(self, object_key: str, *, expires_seconds: int = 900) -> str:
        return f"/mock-page-images/{quote(object_key, safe='')}?expires={expires_seconds}"
