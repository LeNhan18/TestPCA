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
    }


def join_tokens(tokens: Iterable[str], stopwords: Set[str]) -> str:
    kept = [t for t in tokens if t and t not in stopwords and len(t) >= 2]
    return " ".join(kept)

