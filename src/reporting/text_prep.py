from __future__ import annotations

import re
from typing import Iterable, List, Set


_WORD_RE = re.compile(r"[0-9A-Za-zÀ-ỹ]+", re.UNICODE)


def basic_vi_tokenize(text: str) -> List[str]:
    """
    Tokenize tiếng Việt theo kiểu đơn giản (regex word).
    Mục tiêu: đủ tốt cho TF-IDF/keywords trong bài test, không phụ thuộc NLP nặng.
    """
    if not text:
        return []
    return [t.lower() for t in _WORD_RE.findall(text)]


def load_stopwords_vi() -> Set[str]:
    # Danh sách tối thiểu để giảm nhiễu trong tiêu đề/snippet
    return {
        "và",
        "là",
        "của",
        "cho",
        "với",
        "một",
        "những",
        "các",
        "được",
        "trong",
        "khi",
        "đến",
        "từ",
        "theo",
        "về",
        "này",
        "đó",
        "ra",
        "sẽ",
        "đang",
        "bị",
        "có",
        "không",
        "như",
        "tại",
        "lại",
        "còn",
        "cũng",
        "hơn",
        "thì",
        "vì",
        "để",
        "nên",
        "do",
        "trên",
        "dưới",
        "giữa",
        "mới",
        "nhất",
        "lần",
        "ngày",
        "tuần",
        "năm",
        "tháng",
        "giờ",
        "vn",
        "việt",
        "nam",
        "việc",
        "thông",
        # mảnh HTML entity hay gặp khi RSS bị escape
        "amp",
        "quot",
        "apos",
        "nbsp",
        "lt",
        "gt",
        "agrave",
        "aacute",
        "acirc",
        "atilde",
        "egrave",
        "eacute",
        "ecirc",
        "igrave",
        "iacute",
        "ocirc",
        "ograve",
        "oacute",
        "otilde",
        "uacute",
        "ugrave",
        "yacute",
        "039",
    }


def join_tokens(tokens: Iterable[str], stopwords: Set[str]) -> str:
    kept: List[str] = []
    for t in tokens:
        if not t:
            continue
        if t in stopwords:
            continue
        if len(t) < 2:
            continue
        # loại token toàn chữ-số kiểu "2026", "5g" vẫn giữ, nhưng loại token toàn số
        if t.isdigit():
            continue
        kept.append(t)
    return " ".join(kept)

