import logging
import re

from fastapi import APIRouter, HTTPException

from app.models import ScoreRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["score"])


@router.post("/score-article")
async def score_article(request: ScoreRequest):
    try:
        return calculate_article_score(request.article_text, request.target_keyword)
    except Exception:
        logger.error("Unhandled error in score_article")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        ) from None


def calculate_article_score(text: str, target_keyword: str = "") -> dict[str, int | float]:
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    reading_time = max(1, word_count // 200)
    headings = len(re.findall(r"^#{2,3}\s+", text, re.MULTILINE))
    kw_density = 0.0
    if target_keyword and word_count > 0:
        kw_count = len(re.findall(r"\b" + re.escape(target_keyword.lower()) + r"\b", text.lower()))
        kw_density = (kw_count / word_count) * 100

    sentences = max(1, len(re.split(r"[.!?]+", text)) - 1)
    syllables = sum(count_syllables(word) for word in words)

    fk_score = 0.0
    if word_count > 0:
        fk_score = 206.835 - 1.015 * (word_count / sentences) - 84.6 * (syllables / word_count)

    score = 50
    if word_count > 500:
        score += 10
    if word_count > 1000:
        score += 10
    if headings > 3:
        score += 10
    if 0.5 <= kw_density <= 2.5:
        score += 10
    if fk_score > 40:
        score += 10

    suggestions = build_suggestions(text, word_count, headings, kw_density, fk_score, target_keyword)

    return {
        "word_count": word_count,
        "reading_time": reading_time,
        "headings": headings,
        "keyword_density": round(kw_density, 2),
        "readability_score": round(fk_score, 1),
        "overall_score": min(100, max(0, score)),
        "suggestions": suggestions,
    }


def build_suggestions(
    text: str,
    word_count: int,
    headings: int,
    kw_density: float,
    fk_score: float,
    target_keyword: str,
) -> list[str]:
    """Actionable, machine-checked tips tied to the actual metrics."""
    tips: list[str] = []

    if word_count < 500:
        tips.append(f"the article is short ({word_count} words). aim for 800 to 1200 for a full treatment.")
    if headings <= 3:
        tips.append(f"only {headings} headings found. subheadings help scanning, add a few more.")
    if paragraphs := [p for p in (s.strip() for s in text.split("\n\n")) if p]:
        long_paras = sum(1 for p in paragraphs if len(re.findall(r"\b\w+\b", p)) > 90)
        if long_paras:
            tips.append(f"{long_paras} paragraph(s) run past 90 words. split the heavy ones.")
    if fk_score and fk_score < 40:
        tips.append("sentences skew long or dense for general readers. break up the worst offenders.")
    if not re.search(r"^#\s+", text, re.MULTILINE):
        tips.append("no H1 heading. give the article one clear top heading.")
    if target_keyword:
        if kw_density < 0.5:
            tips.append(f"'{target_keyword}' barely appears. work it into two or three natural spots.")
        elif kw_density > 2.5:
            tips.append(f"'{target_keyword}' density is {kw_density:.1f}%, too high. swap some mentions for synonyms.")
    if not re.search(r"[?!.]\s*$", text.rstrip(), re.MULTILINE):
        pass  # trailing text without punctuation is rare; skip nitpicks
    if len(tips) == 0:
        tips.append("looks solid. nothing mechanical to fix.")
    return tips


def count_syllables(word: str) -> int:
    if not word:
        return 0

    lowered = word.lower()
    count = 1 if lowered[0] in "aeiouy" else 0
    for index in range(1, len(lowered)):
        if lowered[index] in "aeiouy" and lowered[index - 1] not in "aeiouy":
            count += 1
    if lowered.endswith("e"):
        count -= 1
    return max(1, count)
