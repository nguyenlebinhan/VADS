import re


class LexicalRerankerProvider:
    def score(
        self,
        query: str,
        documents: list[str],
        *,
        model_alias: str,
    ) -> list[float]:
        del model_alias
        query_terms = set(re.findall(r"\w+", query.casefold(), flags=re.UNICODE))
        return [
            len(query_terms & set(re.findall(r"\w+", document.casefold(), flags=re.UNICODE)))
            / (len(query_terms) or 1)
            for document in documents
        ]

    def health_check(self) -> bool:
        return True


class FailingRerankerProvider:
    def score(
        self,
        query: str,
        documents: list[str],
        *,
        model_alias: str,
    ) -> list[float]:
        del query, documents, model_alias
        raise RuntimeError("reranker unavailable")

    def health_check(self) -> bool:
        return False
