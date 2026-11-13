import unicodedata


def normalize_model(value: str | None) -> str:
    return "".join(unicodedata.normalize("NFKC", value or "").strip().upper().split())


def normalize_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())
