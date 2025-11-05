#!/usr/bin/env python3
"""
다중 요청 패턴 우선순위 수정 스크립트

더 구체적인 패턴(키워드 많음)이 먼저 매칭되도록 우선순위 재조정
"""

import yaml
from pathlib import Path

# YAML 파일 경로
yaml_path = Path("configs/multi_request_patterns.yaml")

# YAML 로드
with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# 패턴 분류
patterns = data['patterns']
two_tool_patterns = []
three_tool_patterns = []
four_tool_patterns = []

for pattern in patterns:
    tool_count = len(pattern['tools'])
    if tool_count == 2:
        two_tool_patterns.append(pattern)
    elif tool_count == 3:
        three_tool_patterns.append(pattern)
    elif tool_count == 4:
        four_tool_patterns.append(pattern)

print(f"2-Tool 패턴: {len(two_tool_patterns)}개")
print(f"3-Tool 패턴: {len(three_tool_patterns)}개")
print(f"4-Tool 패턴: {len(four_tool_patterns)}개")

# 우선순위 재조정
# 4-Tool: 110-120 (최고 우선순위)
# 3-Tool: 100-109 (높은 우선순위)
# 2-Tool: 60-99 (일반 우선순위)

for pattern in four_tool_patterns:
    # 기존 priority 유지하되 +20
    old_priority = pattern.get('priority', 70)
    pattern['priority'] = old_priority + 30  # 4-tool은 30 증가

for pattern in three_tool_patterns:
    # 기존 priority 유지하되 +10
    old_priority = pattern.get('priority', 70)
    pattern['priority'] = old_priority + 10  # 3-tool은 10 증가

# 2-tool은 그대로 유지

# 재결합
data['patterns'] = four_tool_patterns + three_tool_patterns + two_tool_patterns

# 저장
with open(yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

print("\n우선순위 업데이트 완료!")
print(f"4-Tool 범위: {min([p['priority'] for p in four_tool_patterns])} - {max([p['priority'] for p in four_tool_patterns])}")
print(f"3-Tool 범위: {min([p['priority'] for p in three_tool_patterns])} - {max([p['priority'] for p in three_tool_patterns])}")
print(f"2-Tool 범위: {min([p['priority'] for p in two_tool_patterns])} - {max([p['priority'] for p in two_tool_patterns])}")
