#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
파이프라인 테스트 스크립트

다중 요청 처리가 정상적으로 작동하는지 테스트
"""

from datetime import datetime
from src.agent.graph import create_agent_graph, initialize_fallback_state
from src.utils.logger import Logger
from src.utils.experiments import ExperimentManager

def test_multi_request():
    """다중 요청 테스트"""
    # ExperimentManager 초기화
    today = datetime.now().strftime("%Y%m%d")
    exp_manager = ExperimentManager(base_dir=f"experiments/{today}")
    logger = exp_manager.logger

    # Agent 그래프 생성
    agent_executor = create_agent_graph(exp_manager=exp_manager)

    # 다중 요청 질문 (찾 + 요약 패턴)
    question = "Attention Mechanism 논문을 찾아서 요약해줘"
    difficulty = "easy"

    logger.write("=" * 80)
    logger.write("다중 요청 파이프라인 테스트 시작")
    logger.write(f"질문: {question}")
    logger.write(f"난이도: {difficulty}")
    logger.write("=" * 80)

    # Agent 실행
    try:
        # 초기 상태 생성
        initial_state = {
            "question": question,
            "difficulty": difficulty,
            "messages": []
        }

        # Fallback 상태 초기화
        initial_state = initialize_fallback_state(initial_state, exp_manager)

        # Agent 실행
        result = agent_executor.invoke(initial_state)

        # 결과 확인
        logger.write("\n" + "=" * 80)
        logger.write("실행 결과:")
        logger.write("=" * 80)
        logger.write(f"도구 선택: {result.get('tool_choice', 'N/A')}")
        logger.write(f"도구 상태: {result.get('tool_status', 'N/A')}")
        logger.write(f"파이프라인: {result.get('tool_pipeline', [])}")
        logger.write(f"파이프라인 인덱스: {result.get('pipeline_index', 0)}")

        # 타임라인 확인
        timeline = result.get("tool_timeline", [])
        logger.write(f"\n실행 타임라인 ({len(timeline)}개 이벤트):")
        for event in timeline:
            logger.write(f"  - {event.get('event')}: {event.get('tool', 'N/A')} (status: {event.get('status', 'N/A')})")

        # 최종 답변
        logger.write("\n최종 답변 (200자까지):")
        final_answer = result.get("final_answer", "답변 없음")
        logger.write(final_answer[:200] + "...")

        logger.write("\n" + "=" * 80)
        logger.write("테스트 완료")
        logger.write("=" * 80)

        return result

    except Exception as e:
        logger.write(f"오류 발생: {e}", print_error=True)
        import traceback
        logger.write(traceback.format_exc(), print_error=True)
        return None


if __name__ == "__main__":
    test_multi_request()
