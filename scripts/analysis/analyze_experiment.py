"""
실험 로그 분석 스크립트
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

def parse_chatbot_log(log_path: Path) -> List[Dict]:
    """chatbot.log 파일 파싱"""
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()

    questions = []
    current_question = None

    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 질문 시작 감지
        if '라우터 노드 실행:' in line:
            if current_question:
                questions.append(current_question)

            q_text = line.split('라우터 노드 실행:')[1].strip()
            current_question = {
                'question': q_text,
                'tool_choice': None,
                'tool_status': None,
                'fallback_events': [],
                'pipeline': [],
                'errors': [],
                'start_line': i
            }

        if not current_question:
            continue

        # 도구 선택
        if '최종 선택 도구:' in line:
            current_question['tool_choice'] = line.split(':')[1].strip()

        # 다중 요청 감지
        if '다중 요청 감지:' in line:
            tools = re.search(r'→ \[(.*?)\]', line)
            if tools:
                current_question['pipeline'] = eval(f"[{tools.group(1)}]")

        # 도구 실행 성공/실패
        if '도구 실행 성공:' in line:
            current_question['tool_status'] = 'success'
        elif '도구 실행 실패 감지:' in line or '도구 실행 오류:' in line:
            current_question['tool_status'] = 'failed'

        # Fallback 이벤트
        if 'Fallback Router 실행' in line:
            current_question['fallback_events'].append({
                'line': i,
                'type': 'fallback_router'
            })
        elif '파이프라인 도구 대체:' in line:
            match = re.search(r'대체: (\w+) → (\w+)', line)
            if match:
                current_question['fallback_events'].append({
                    'type': 'tool_replacement',
                    'from': match.group(1),
                    'to': match.group(2)
                })

        # 에러 감지
        if 'Error code:' in line or '실행 오류:' in line:
            current_question['errors'].append(line.strip())

    if current_question:
        questions.append(current_question)

    return questions

def analyze_tool_accuracy(questions: List[Dict], test_questions: List[Dict]) -> Dict:
    """도구 선택 정확도 분석"""
    total = len(questions)
    correct = 0
    mismatches = []

    for i, (q, expected) in enumerate(zip(questions, test_questions)):
        expected_tool = expected.get('expected_tool')
        actual_tool = q['tool_choice']

        if expected_tool == actual_tool:
            correct += 1
        else:
            mismatches.append({
                'index': i + 1,
                'question': q['question'][:50] + '...',
                'expected': expected_tool,
                'actual': actual_tool
            })

    return {
        'total': total,
        'correct': correct,
        'accuracy': correct / total if total > 0 else 0,
        'mismatches': mismatches
    }

def analyze_fallback_system(questions: List[Dict]) -> Dict:
    """Fallback 시스템 작동 분석"""
    total_fallback_events = 0
    fallback_questions = []

    for i, q in enumerate(questions):
        if q['fallback_events']:
            total_fallback_events += len(q['fallback_events'])
            fallback_questions.append({
                'index': i + 1,
                'question': q['question'][:50] + '...',
                'events': q['fallback_events']
            })

    return {
        'total_events': total_fallback_events,
        'questions_with_fallback': len(fallback_questions),
        'details': fallback_questions
    }

def analyze_pipeline_execution(questions: List[Dict]) -> Dict:
    """파이프라인 실행 분석"""
    pipeline_questions = [q for q in questions if len(q['pipeline']) > 1]

    successful = 0
    failed = 0
    details = []

    for q in pipeline_questions:
        status = 'success' if q['tool_status'] == 'success' else 'failed'
        if status == 'success':
            successful += 1
        else:
            failed += 1

        details.append({
            'question': q['question'][:50] + '...',
            'pipeline': q['pipeline'],
            'status': status,
            'has_fallback': len(q['fallback_events']) > 0
        })

    return {
        'total': len(pipeline_questions),
        'successful': successful,
        'failed': failed,
        'details': details
    }

def analyze_errors(questions: List[Dict]) -> Dict:
    """에러 분석"""
    error_types = defaultdict(int)
    error_questions = []

    for i, q in enumerate(questions):
        if q['errors']:
            for error in q['errors']:
                # Error code 추출
                if 'Error code: 429' in error:
                    error_types['API_QUOTA_EXCEEDED'] += 1
                elif 'Error code: 500' in error:
                    error_types['INTERNAL_SERVER_ERROR'] += 1
                elif 'Error code:' in error:
                    error_types['OTHER_API_ERROR'] += 1
                else:
                    error_types['UNKNOWN'] += 1

            error_questions.append({
                'index': i + 1,
                'question': q['question'][:50] + '...',
                'errors': q['errors'][:2]  # 처음 2개만
            })

    return {
        'error_types': dict(error_types),
        'total_errors': sum(error_types.values()),
        'questions_with_errors': len(error_questions),
        'details': error_questions
    }

def generate_report(log_dir: Path, output_dir: Path):
    """분석 보고서 생성"""
    log_path = log_dir / 'chatbot.log'

    if not log_path.exists():
        print(f"로그 파일 없음: {log_path}")
        return

    # 로그 파싱
    questions = parse_chatbot_log(log_path)

    # 테스트 질문 로드 (전문가 모드)
    test_questions_path = Path('docs/scenarios/test_questions_expert.md')
    # TODO: 실제 테스트 질문 파싱 필요

    # 분석 수행
    fallback_analysis = analyze_fallback_system(questions)
    pipeline_analysis = analyze_pipeline_execution(questions)
    error_analysis = analyze_errors(questions)

    # 결과 저장
    analysis_result = {
        'experiment_id': log_dir.name,
        'total_questions': len(questions),
        'fallback_analysis': fallback_analysis,
        'pipeline_analysis': pipeline_analysis,
        'error_analysis': error_analysis,
        'generated_at': datetime.now().isoformat()
    }

    output_path = output_dir / 'analysis_result.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print(f"분석 완료: {output_path}")
    return analysis_result

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_experiment.py <log_dir>")
        sys.exit(1)

    log_dir = Path(sys.argv[1])
    output_dir = Path('docs/experiments') / datetime.now().strftime('%Y%m%d')

    result = generate_report(log_dir, output_dir)
    print(f"\n분석 결과:")
    print(f"- 총 질문 수: {result['total_questions']}")
    print(f"- Fallback 이벤트: {result['fallback_analysis']['total_events']}회")
    print(f"- 파이프라인 질문: {result['pipeline_analysis']['total']}")
    print(f"- 에러 발생: {result['error_analysis']['total_errors']}회")
