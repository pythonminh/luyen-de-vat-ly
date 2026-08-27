#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phân loại dạng bài tập cho ngân hàng câu hỏi Vật lý."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_INDEX_PATH = ROOT_DIR / "ngan-hang" / "muc_luc.json"
DEFAULT_CONFIG_PATH = ROOT_DIR / "bai_tap_phan_loai.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "ngan-hang" / "Vật lý" / "bai_tap_phan_loai_metadata.json"

QUESTION_SPLIT_RE = re.compile(r"%\s*=====\s*Câu\s+\d+\s*=====")
QUESTION_ID_RE = re.compile(r"%\s*ID:\s*([A-Za-z0-9\-]+)")
LEVEL_RE = re.compile(r"%\s*Mức:\s*([A-Za-z0-9]+)")
DANGBT_RE = re.compile(r"\\dangbt\{([^}]*)\}")
QUESTION_TEXT_RE = re.compile(
    r"\\begin\{(?:ex|bt)\}(.*?)(?=\\choiceTF|\\choice\b|\\shortans|\\loigiai\{|\\end\{(?:ex|bt)\})",
    re.DOTALL,
)

QUESTION_TYPE_PATTERNS = {
    "DS": re.compile(r"\\choiceTF"),
    "TN": re.compile(r"\\choice\b"),
    "TLN": re.compile(r"\\shortans"),
    "TL": re.compile(r"\\begin\{bt\}"),
}

QUESTION_TYPE_NAMES = {
    "DS": "Đúng/Sai",
    "TN": "Trắc nghiệm",
    "TL": "Tự luận",
    "TLN": "Tự luận ngắn",
}

LEVEL_TO_COMPLEXITY = {
    "NB": "dễ",
    "TH": "trung bình",
    "VD": "khó",
    "VDC": "khó",
}

COMPLEXITY_WEIGHTS = {
    "dễ": 1,
    "trung bình": 2,
    "khó": 3,
}

RESPONSE_FORMAT_CODES = {"multiple_choice", "short_answer_essay"}


@dataclass(frozen=True)
class ExerciseTypeRule:
    code: str
    name: str
    dimension: str
    description: str
    keywords: List[str]
    patterns: List[str]
    match_raw_block: bool = False


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = text.lower()
    return bool(re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", normalized_text))


def infer_question_type(block: str, qid: Optional[str]) -> Optional[str]:
    if qid:
        for qtype in ("TLN", "TL", "DS", "TN"):
            if qid.endswith(f"-{qtype}"):
                return qtype
    for qtype, pattern in QUESTION_TYPE_PATTERNS.items():
        if pattern.search(block):
            return qtype
    return None


def extract_question_text(block: str) -> str:
    match = QUESTION_TEXT_RE.search(block)
    if not match:
        return ""
    text = match.group(1)
    text = re.sub(r"%.*", "", text)
    return normalize_whitespace(text)


def map_complexity(level: Optional[str]) -> str:
    return LEVEL_TO_COMPLEXITY.get(level or "", "trung bình")


def summarize_complexity(counter: Mapping[str, int]) -> str:
    total = sum(counter.values())
    if total == 0:
        return "trung bình"
    weighted = sum(COMPLEXITY_WEIGHTS.get(name, 0) * count for name, count in counter.items()) / total
    # 1.75 và 2.4 là các ngưỡng trung gian giữa ba mức trọng số 1-2-3:
    # dưới 1.75 nghiêng rõ về "dễ", từ 1.75 đến dưới 2.4 xem là "trung bình",
    # còn từ 2.4 trở lên nghiêng về "khó".
    if weighted < 1.75:
        return "dễ"
    if weighted < 2.4:
        return "trung bình"
    return "khó"


class PhysicsExerciseClassifier:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.rules = self._load_rules(config_path)

    @staticmethod
    def _load_rules(config_path: Path) -> List[ExerciseTypeRule]:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return [
            ExerciseTypeRule(
                code=item["code"],
                name=item["name"],
                dimension=item["dimension"],
                description=item["description"],
                keywords=item.get("keywords", []),
                patterns=item.get("patterns", []),
                match_raw_block=item.get("match_raw_block", False),
            )
            for item in data["exercise_types"]
        ]

    def classify_question_block(self, block: str, lesson_name: str = "") -> Optional[Dict]:
        qid_match = QUESTION_ID_RE.search(block)
        qid = qid_match.group(1) if qid_match else None
        if not qid:
            return None

        level_match = LEVEL_RE.search(block)
        level = level_match.group(1) if level_match else None

        dangbt_match = DANGBT_RE.search(block)
        raw_label = normalize_whitespace(dangbt_match.group(1)) if dangbt_match else ""

        question_text = extract_question_text(block)
        question_type = infer_question_type(block, qid)
        exercise_types = self._detect_exercise_types(
            block=block,
            question_text=question_text,
            raw_label=raw_label,
            question_type=question_type,
            level=level,
            lesson_name=lesson_name,
        )

        return {
            "id": qid,
            "question_type": question_type,
            "question_type_name": QUESTION_TYPE_NAMES.get(question_type or "", "Không xác định"),
            "difficulty_level": level,
            "complexity": map_complexity(level),
            "raw_label": raw_label or "Chưa có dạng",
            "question_preview": question_text[:240],
            "exercise_types": exercise_types,
        }

    def _detect_exercise_types(
        self,
        *,
        block: str,
        question_text: str,
        raw_label: str,
        question_type: Optional[str],
        level: Optional[str],
        lesson_name: str,
    ) -> List[str]:
        normalized = normalize_whitespace(" ".join(part for part in (lesson_name, raw_label, question_text) if part)).lower()
        matched: List[str] = []
        application_rule = next((rule for rule in self.rules if rule.code == "application"), None)

        for rule in self.rules:
            if rule.code == "application":
                continue
            if self._matches_rule(rule, block, normalized, question_type, level):
                matched.append(rule.code)

        if application_rule and self._should_mark_application(
            normalized=normalized,
            level=level,
            matched=matched,
            rule=application_rule,
        ):
            matched.append(application_rule.code)

        if not matched:
            fallback = "short_answer_essay" if question_type in {"TL", "TLN"} else "multiple_choice"
            matched.append(fallback)

        return sorted(set(matched), key=self._rule_order)

    def _matches_rule(
        self,
        rule: ExerciseTypeRule,
        block: str,
        normalized: str,
        question_type: Optional[str],
        level: Optional[str],
    ) -> bool:
        if rule.code == "multiple_choice":
            return question_type in {"DS", "TN"} or bool(re.search(r"\\choiceTF|\\choice\b", block))

        if rule.code == "short_answer_essay":
            return question_type in {"TL", "TLN"} or bool(re.search(r"\\shortans|\\begin\{bt\}", block))

        for keyword in rule.keywords:
            if contains_keyword(normalized, keyword):
                return True

        for pattern in rule.patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
            if rule.match_raw_block and re.search(pattern, block):
                return True

        return False

    def _should_mark_application(
        self,
        *,
        normalized: str,
        level: Optional[str],
        matched: List[str],
        rule: ExerciseTypeRule,
    ) -> bool:
        if self._matches_rule(rule, "", normalized, None, level):
            return True
        return level in {"VD", "VDC"} and any(code not in RESPONSE_FORMAT_CODES for code in matched)

    def _rule_order(self, code: str) -> int:
        return next((index for index, rule in enumerate(self.rules) if rule.code == code), len(self.rules))

    def classify_lesson(self, lesson_entry: Dict, repo_root: Path) -> Dict:
        relative_path = Path(lesson_entry["path"])
        if relative_path.parts and relative_path.parts[0] == "ngan-hang":
            relative_parts = relative_path.parts[1:]
            if not relative_parts:
                raise ValueError(f"Đường dẫn bài học không hợp lệ: {lesson_entry['path']}")
            relative_path = Path(*relative_parts)
        tex_path = repo_root / "ngan-hang" / relative_path
        if not tex_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file TeX cho bài học: {tex_path}")
        content = tex_path.read_text(encoding="utf-8")
        blocks = QUESTION_SPLIT_RE.split(content)[1:]

        questions = []
        type_counter: Counter = Counter()
        complexity_counter: Counter = Counter()
        raw_label_counter: Counter = Counter()
        skipped_blocks_without_id = 0

        for block in blocks:
            question = self.classify_question_block(block, lesson_name=lesson_entry["BaiHoc"])
            if not question:
                skipped_blocks_without_id += 1
                continue
            questions.append(question)
            type_counter.update(question["exercise_types"])
            complexity_counter.update([question["complexity"]])
            raw_label_counter.update([question["raw_label"]])

        total_questions = len(questions)
        counts_by_type = {rule.code: type_counter.get(rule.code, 0) for rule in self.rules}
        ratios_by_type = {
            code: round((count / total_questions), 4) if total_questions else 0.0
            for code, count in counts_by_type.items()
        }

        return {
            "Mon": lesson_entry["Mon"],
            "Lop": lesson_entry["Lop"],
            "Chuong": lesson_entry["Chuong"],
            "BaiHoc": lesson_entry["BaiHoc"],
            "path": f"ngan-hang/{relative_path.as_posix()}",
            "github": lesson_entry.get("github", ""),
            "total_questions": total_questions,
            "exercise_types": [rule.code for rule in self.rules if counts_by_type[rule.code] > 0],
            "counts_by_type": counts_by_type,
            "ratios_by_type": ratios_by_type,
            "counts_by_complexity": {
                "dễ": complexity_counter.get("dễ", 0),
                "trung bình": complexity_counter.get("trung bình", 0),
                "khó": complexity_counter.get("khó", 0),
            },
            "overall_complexity": summarize_complexity(complexity_counter),
            "skipped_blocks_without_id": skipped_blocks_without_id,
            "raw_labels": dict(raw_label_counter.most_common()),
            "questions": questions,
        }

    def build_metadata(self, repo_root: Path, index_path: Path) -> Dict:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        physics_lessons = [lesson for lesson in index_data["lessons"] if lesson.get("Mon") == "Vật lý"]

        lessons = []
        missing_lesson_files = []

        for lesson in physics_lessons:
            try:
                lessons.append(self.classify_lesson(lesson, repo_root))
            except FileNotFoundError as exc:
                missing_lesson_files.append(
                    {
                        "BaiHoc": lesson.get("BaiHoc", ""),
                        "path": lesson.get("path", ""),
                        "error": str(exc),
                    }
                )

        summary_type_counter = Counter()
        summary_complexity_counter = Counter()
        total_questions = 0
        total_skipped_blocks = 0

        for lesson in lessons:
            total_questions += lesson["total_questions"]
            summary_type_counter.update({key: value for key, value in lesson["counts_by_type"].items() if value})
            summary_complexity_counter.update(
                {key: value for key, value in lesson["counts_by_complexity"].items() if value}
            )
            total_skipped_blocks += lesson["skipped_blocks_without_id"]

        return {
            "schema": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "ngan-hang/Vật lý",
            "config_file": self.config_path.name,
            "summary": {
                "lesson_count": len(lessons),
                "question_count": total_questions,
                "counts_by_type": {
                    rule.code: summary_type_counter.get(rule.code, 0) for rule in self.rules
                },
                "counts_by_complexity": {
                    "dễ": summary_complexity_counter.get("dễ", 0),
                    "trung bình": summary_complexity_counter.get("trung bình", 0),
                    "khó": summary_complexity_counter.get("khó", 0),
                },
                "skipped_blocks_without_id": total_skipped_blocks,
                "missing_lesson_files": len(missing_lesson_files),
            },
            "exercise_type_definitions": [
                {
                    "code": rule.code,
                    "name": rule.name,
                    "dimension": rule.dimension,
                    "description": rule.description,
                }
                for rule in self.rules
            ],
            "warnings": {
                "missing_lesson_files": missing_lesson_files,
            },
            "lessons": lessons,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phân loại dạng bài tập cho ngân hàng Vật lý")
    parser.add_argument("--repo-root", default=str(ROOT_DIR), help="Đường dẫn tuyệt đối tới root của repository")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="Đường dẫn file mục lục JSON")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Đường dẫn file cấu hình schema JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Đường dẫn file JSON đầu ra")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    index_path = Path(args.index).resolve()
    config_path = Path(args.config).resolve()
    output_path = Path(args.output).resolve()

    classifier = PhysicsExerciseClassifier(config_path=config_path)
    metadata = classifier.build_metadata(repo_root=repo_root, index_path=index_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Đã phân loại {metadata['summary']['lesson_count']} bài Vật lý.")
    print(f"Tổng số câu hỏi: {metadata['summary']['question_count']}.")
    print(f"Số block thiếu ID: {metadata['summary']['skipped_blocks_without_id']}.")
    if metadata["summary"]["missing_lesson_files"]:
        print(f"Có {metadata['summary']['missing_lesson_files']} bài thiếu file TeX.")
    print(f"File đầu ra: {output_path}")


if __name__ == "__main__":
    main()
