# src/prompts/loader.py
"""
프롬프트 JSON 파일 로더 모듈

프로젝트 최상위 prompts/ 폴더의 JSON 파일을 로드하여
각 모듈에서 사용할 수 있도록 제공
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any


# ==================== 프로젝트 루트 경로 ==================== #
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


# ==================== 프롬프트 로더 함수 ==================== #
def load_prompt_file(filename: str) -> Dict[str, Any]:
    """
    프롬프트 JSON 파일 로드

    Args:
        filename: JSON 파일명 (예: "routing_prompts.json")

    Returns:
        파싱된 JSON 딕셔너리

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 경우
        json.JSONDecodeError: JSON 파싱 오류
    """
    filepath = PROMPTS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 라우팅 프롬프트 ==================== #
def load_routing_prompts() -> Dict[str, Any]:
    """
    라우팅 프롬프트 로드

    Returns:
        {
            "routing_prompt": str,
            "few_shot_examples": List[Dict]
        }
    """
    return load_prompt_file("routing_prompts.json")


def get_routing_prompt() -> str:
    """라우팅 프롬프트 텍스트 반환"""
    data = load_routing_prompts()
    return data.get("prompt_template", data.get("routing_prompt", ""))


def get_few_shot_examples() -> List[Dict[str, str]]:
    """Few-shot 예시 리스트 반환"""
    data = load_routing_prompts()
    return data["few_shot_examples"]


# ==================== 난이도 매핑 ==================== #
# 기존 easy/hard를 새로운 4단계 난이도로 매핑
DIFFICULTY_MAPPING = {
    "easy": "beginner",      # easy -> beginner (초급자)
    "hard": "intermediate"   # hard -> intermediate (중급자)
}


def map_difficulty(difficulty: str) -> str:
    """
    기존 난이도를 새로운 난이도로 매핑

    Args:
        difficulty: 기존 난이도 (easy/hard) 또는 새 난이도 (elementary/beginner/intermediate/advanced)

    Returns:
        매핑된 난이도
    """
    # 이미 새 난이도 형식이면 그대로 반환
    if difficulty in ["elementary", "beginner", "intermediate", "advanced"]:
        return difficulty

    # 기존 난이도를 새 난이도로 매핑
    return DIFFICULTY_MAPPING.get(difficulty, "beginner")  # 기본값: beginner


# ==================== 도구별 프롬프트 ==================== #
def load_tool_prompts() -> Dict[str, Any]:
    """
    도구별 프롬프트 로드

    Returns:
        {
            "general_prompts": {...},
            "web_search_prompts": {...},
            "summarize_prompts": {...},
            "glossary_prompts": {...},
            "search_paper_prompts": {...},
            "save_file_prompts": {...}
        }
    """
    return load_prompt_file("tool_prompts.json")


def get_tool_prompt(tool_name: str, difficulty: str = "easy") -> str:
    """
    특정 도구의 시스템 프롬프트 반환

    Args:
        tool_name: 도구 이름 (예: "general_answer", "web_search", "general")
        difficulty: 난이도 ("easy"/"hard" 또는 "elementary"/"beginner"/"intermediate"/"advanced")

    Returns:
        시스템 프롬프트 문자열

    Example:
        >>> get_tool_prompt("general_answer", "easy")
        "당신은 친절한 AI 어시스턴트입니다..."
        >>> get_tool_prompt("general", "beginner")
        "당신은 초보자에게 친절하게 설명하는 AI 어시스턴트입니다..."
    """
    data = load_tool_prompts()

    # 난이도 매핑 (easy/hard -> beginner/intermediate)
    mapped_difficulty = map_difficulty(difficulty)

    # tool_name에 "_prompts" 접미사 처리
    # "general_answer" -> "general_prompts"
    # "general" -> "general_prompts"
    if tool_name.endswith("_answer"):
        # "general_answer" -> "general"
        tool_base = tool_name.replace("_answer", "")
    else:
        tool_base = tool_name

    prompt_key = f"{tool_base}_prompts"

    if prompt_key not in data:
        raise KeyError(f"도구 프롬프트를 찾을 수 없습니다: {tool_name} (키: {prompt_key})")

    # 새 구조: data[prompt_key]["easy"]["beginner"]["system_prompt"]
    # easy/hard 레벨 결정
    complexity_level = "easy" if mapped_difficulty in ["elementary", "beginner"] else "hard"

    if complexity_level not in data[prompt_key]:
        raise KeyError(f"복잡도 레벨을 찾을 수 없습니다: {complexity_level}")

    if mapped_difficulty not in data[prompt_key][complexity_level]:
        raise KeyError(f"난이도를 찾을 수 없습니다: {mapped_difficulty} (복잡도: {complexity_level})")

    return data[prompt_key][complexity_level][mapped_difficulty]["system_prompt"]


def get_summarize_title_extraction_prompt() -> str:
    """논문 제목 추출 프롬프트 반환"""
    data = load_tool_prompts()
    return data["summarize_prompts"]["title_extraction"]["template"]


def get_summarize_template(difficulty: str = "easy") -> str:
    """
    논문 요약 템플릿 반환

    Args:
        difficulty: 난이도 ("easy"/"hard" 또는 "elementary"/"beginner"/"intermediate"/"advanced")

    Returns:
        요약 템플릿 문자열
    """
    data = load_tool_prompts()
    mapped_difficulty = map_difficulty(difficulty)
    complexity_level = "easy" if mapped_difficulty in ["elementary", "beginner"] else "hard"

    return data["summarize_prompts"][complexity_level][mapped_difficulty]["summary_template"]


def get_web_search_user_prompt_template(difficulty: str = "easy") -> str:
    """
    웹 검색 사용자 프롬프트 템플릿 반환

    Args:
        difficulty: 난이도 ("easy"/"hard" 또는 "elementary"/"beginner"/"intermediate"/"advanced")

    Returns:
        사용자 프롬프트 템플릿 문자열
    """
    data = load_tool_prompts()
    mapped_difficulty = map_difficulty(difficulty)
    complexity_level = "easy" if mapped_difficulty in ["elementary", "beginner"] else "hard"

    return data["web_search_prompts"][complexity_level][mapped_difficulty]["user_prompt_template"]


# ==================== 평가 프롬프트 ==================== #
def load_evaluation_prompts() -> Dict[str, Any]:
    """
    평가 프롬프트 로드

    Returns:
        {
            "evaluation_prompt": {...},
            "evaluation_criteria": {...},
            "evaluation_examples": [...]
        }
    """
    return load_prompt_file("evaluation_prompts.json")


def get_evaluation_prompt_template() -> str:
    """평가 프롬프트 템플릿 반환"""
    data = load_evaluation_prompts()
    return data["evaluation_prompt"]["template"]


def get_evaluation_input_variables() -> List[str]:
    """평가 프롬프트 입력 변수 리스트 반환"""
    data = load_evaluation_prompts()
    return data["evaluation_prompt"]["input_variables"]


# ==================== 질문 생성 프롬프트 ==================== #
def load_question_generation_prompts() -> Dict[str, Any]:
    """
    질문 생성 프롬프트 로드

    Returns:
        {
            "question_generation_prompt": {...},
            "question_templates": {...},
            "tool_based_templates": {...},
            "generation_examples": [...]
        }
    """
    return load_prompt_file("question_generation_prompts.json")


def get_question_generation_template() -> str:
    """질문 생성 프롬프트 템플릿 반환"""
    data = load_question_generation_prompts()
    return data["question_generation_prompt"]["template"]


def get_question_templates(difficulty: str = "easy") -> List[str]:
    """난이도별 질문 템플릿 리스트 반환"""
    data = load_question_generation_prompts()
    return data["question_templates"][difficulty]


# ==================== Golden Dataset ==================== #
def load_golden_dataset() -> Dict[str, Any]:
    """
    Golden Dataset 로드

    Returns:
        {
            "golden_dataset": [...],
            "dataset_metadata": {...}
        }
    """
    return load_prompt_file("golden_dataset.json")


def get_golden_questions() -> List[Dict[str, Any]]:
    """Golden Dataset 질문 리스트 반환"""
    data = load_golden_dataset()
    return data["golden_dataset"]


def get_golden_questions_by_tool(tool_name: str) -> List[Dict[str, Any]]:
    """특정 도구의 Golden Dataset 질문만 반환"""
    questions = get_golden_questions()
    return [q for q in questions if q["expected_tool"] == tool_name]


def get_golden_questions_by_difficulty(difficulty: str) -> List[Dict[str, Any]]:
    """특정 난이도의 Golden Dataset 질문만 반환"""
    questions = get_golden_questions()
    return [q for q in questions if q["difficulty"] == difficulty]


# ==================== Export 목록 ==================== #
__all__ = [
    # 라우팅
    'load_routing_prompts',
    'get_routing_prompt',
    'get_few_shot_examples',

    # 도구별
    'load_tool_prompts',
    'get_tool_prompt',
    'get_summarize_title_extraction_prompt',
    'get_summarize_template',
    'get_web_search_user_prompt_template',

    # 평가
    'load_evaluation_prompts',
    'get_evaluation_prompt_template',
    'get_evaluation_input_variables',

    # 질문 생성
    'load_question_generation_prompts',
    'get_question_generation_template',
    'get_question_templates',

    # Golden Dataset
    'load_golden_dataset',
    'get_golden_questions',
    'get_golden_questions_by_tool',
    'get_golden_questions_by_difficulty',
]
