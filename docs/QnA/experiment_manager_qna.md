# ExperimentManager Q&A

## 문서 정보
- **작성일**: 2025-11-04
- **작성자**: 최현화[팀장]
- **목적**: ExperimentManager 시스템 관련 자주 묻는 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [폴더 시스템](#2-폴더-시스템)
3. [로깅 시스템](#3-로깅-시스템)
4. [메타데이터 관리](#4-메타데이터-관리)
5. [데이터베이스 기록](#5-데이터베이스-기록)
6. [사용 예시](#6-사용-예시)
7. [트러블슈팅](#7-트러블슈팅)
8. [고급 활용](#8-고급-활용)

---

## 1. 기본 개념

### Q1-1. ExperimentManager란?

**A:** **모든 챗봇 실행을 체계적으로 추적하고 관리하는 중앙 시스템**입니다.

**주요 역할:**
1. **Session ID 자동 부여**: 당일 기준 순차적 ID 생성 (session_001, 002...)
2. **폴더 구조 자동 생성**: 6개 필수 폴더 + debug 폴더(필요시 생성)
3. **설정 스냅샷**: configs 폴더를 실험 폴더에 복사하여 설정 보존
4. **Logger 통합**: 메인 Logger 및 도구별 Logger 제공
5. **메타데이터 관리**: `metadata.json`으로 실험 정보 추적
6. **DB 쿼리 기록**: SQL 쿼리 및 pgvector 검색 기록
7. **프롬프트 저장**: 시스템/사용자 프롬프트 저장
8. **평가 지표 저장**: RAG, Agent, 비용, 응답 시간 등 평가 데이터 저장

**사용 위치:**
- Streamlit UI (`ui/components/chat_interface.py`)
- Agent 노드 (`src/agent/nodes.py`)
- 도구 실행 (`src/tools/*.py`)
- 평가 시스템 (`src/evaluation/evaluator.py`)

---

### Q1-2. Session ID는 무엇인가요?

**A:** **하루 동안 실행된 챗봇 세션을 식별하는 고유 번호**입니다.

**명명 규칙:**
```
experiments/
└── 20251104/                           # 날짜 (YYYYMMDD)
    ├── 20251104_103015_session_001/    # 첫 번째 세션
    ├── 20251104_110530_session_002/    # 두 번째 세션
    ├── 20251104_143022_session_003/    # 세 번째 세션
    ...
```

**Session ID 부여 로직:**
1. **날짜 폴더 확인**: `experiments/20251104/` 존재 여부
2. **기존 세션 탐색**: `*_session_*` 패턴 찾기
3. **최대 ID 찾기**: 가장 큰 session ID 추출
4. **+1 증가**: `max_id + 1`

**특징:**
- **당일 기준**: 다음 날이 되면 다시 session_001부터 시작
- **자동 증가**: 수동으로 번호 지정 불필요
- **중복 방지**: 동시 실행 시에도 고유 ID 보장

**코드:**
```python
def _get_next_session_id(self, date: str) -> int:
    date_dir = Path(f"experiments/{date}")

    if not date_dir.exists():
        return 1

    existing_sessions = list(date_dir.glob(f"{date}_*_session_*"))
    if not existing_sessions:
        return 1

    max_id = 0
    for session_dir in existing_sessions:
        session_id_str = session_dir.name.split('_')[-1]
        session_id = int(session_id_str)
        max_id = max(max_id, session_id)

    return max_id + 1
```

---

### Q1-3. 실험 폴더는 언제 생성되나요?

**A:** **ExperimentManager 인스턴스 생성 시 자동으로 생성**됩니다.

**생성 시점:**
```python
# Streamlit UI에서
exp_manager = ExperimentManager()  # 여기서 폴더 생성

# 생성되는 폴더 구조
experiments/
└── 20251104/
    └── 20251104_103015_session_001/
        ├── metadata.json
        ├── chatbot.log
        ├── configs/            # 설정 파일 스냅샷 (자동 복사)
        │   ├── db_config.yaml
        │   └── model_config.yaml
        ├── tools/              # 도구별 로그
        ├── database/           # DB 쿼리 로그
        ├── prompts/            # 프롬프트 저장
        ├── ui/                 # UI 관련 로그
        ├── outputs/            # 답변 및 파일 저장
        └── evaluation/         # 평가 결과 저장
```

**생성 순서:**
1. **날짜/시간 계산**: `20251104`, `103015`
2. **Session ID 부여**: `_get_next_session_id()` 호출
3. **메인 폴더 생성**: `experiments/20251104/20251104_103015_session_001/`
4. **서브 폴더 6개 생성**: tools, database, prompts, ui, outputs, evaluation
5. **설정 스냅샷**: configs 폴더에 db_config.yaml, model_config.yaml 복사
6. **metadata.json 초기화**: 기본 메타데이터 설정
7. **Logger 초기화**: `chatbot.log` 생성

**참고:**
- **debug 폴더**는 자동 생성되지 않으며, `save_debug_info()` 호출 시 필요할 때만 생성됩니다

---

### Q1-4. 왜 폴더 구조가 복잡한가요?

**A:** **체계적인 실험 추적과 재현성 확보**를 위해서입니다.

**장점:**

| 폴더 | 목적 | 재현성 기여도 |
|------|------|--------------|
| **tools/** | 도구별 실행 로그 분리 | ⭐⭐⭐ 도구 실행 과정 추적 |
| **database/** | SQL 쿼리 및 검색 기록 | ⭐⭐⭐ DB 동작 재현 |
| **prompts/** | 프롬프트 버전 관리 | ⭐⭐⭐ LLM 입력 재현 |
| **ui/** | UI 인터랙션 기록 | ⭐⭐ 사용자 동작 추적 |
| **outputs/** | 최종 결과물 저장 | ⭐⭐⭐ 답변 비교 |
| **evaluation/** | 평가 지표 저장 | ⭐⭐⭐ 성능 분석 |
| **debug/** | 에러 디버깅 정보 | ⭐⭐ 문제 해결 |

**비교 (단순 구조):**
```
# ❌ 단순 구조 (재현성 낮음)
experiments/
└── session_001.log

# ✅ 복잡 구조 (재현성 높음)
experiments/
└── 20251104_103015_session_001/
    ├── tools/
    ├── database/
    ├── prompts/
    ...
```

**재현 시나리오:**
```
질문: "6개월 전 실험에서 RAG 검색 결과가 왜 달랐을까?"

단순 구조:
→ session_001.log만 있음
→ 원인 파악 어려움

복잡 구조:
→ database/search_results.json: 검색 결과 확인
→ prompts/system_prompt.txt: 프롬프트 변경 여부 확인
→ tools/rag_paper.log: 상세 실행 과정 확인
→ evaluation/rag_metrics.json: 정량적 지표 비교
→ 원인: 프롬프트 변경으로 인한 검색 결과 차이
```

---

## 2. 폴더 시스템

### Q2-1. tools/ 폴더의 역할은?

**A:** **각 도구의 실행 과정을 독립적으로 기록**합니다.

**도구별 로그 파일:**
```
tools/
├── general.log        # 일반 답변 도구
├── search_paper.log   # RAG 검색 도구
├── web_search.log     # 웹 검색 도구
├── glossary.log       # 용어집 검색 도구
├── summarize.log      # 논문 요약 도구
├── text2sql.log       # Text-to-SQL 도구
└── save_file.log      # 파일 저장 도구
```

**로그 내용 예시 (search_paper.log):**
```
[2025-11-04 10:30:15] RAG 검색 노드 실행: Transformer 논문 설명해줘
[2025-11-04 10:30:15] 난이도: easy
[2025-11-04 10:30:15] 검색 모드: mmr
[2025-11-04 10:30:15] top_k: 5
[2025-11-04 10:30:16] pgvector 검색 완료: 5개 청크 검색
[2025-11-04 10:30:16] 검색 결과 paper_id: [101, 105, 112]
[2025-11-04 10:30:17] LLM 답변 생성 시작
[2025-11-04 10:30:19] 답변 생성 완료: 450 글자
```

**생성 방법:**
```python
# 도구에서 사용
tool_logger = exp_manager.get_tool_logger('search_paper')
tool_logger.write("RAG 검색 노드 실행")
tool_logger.write(f"난이도: {difficulty}")
tool_logger.close()
```

---

### Q2-2. database/ 폴더에는 무엇이 저장되나요?

**A:** **모든 DB 쿼리 및 검색 기록**이 저장됩니다.

**파일 목록:**

| 파일 | 내용 | 형식 |
|------|------|------|
| **queries.sql** | 실행된 SQL 쿼리 모음 | SQL |
| **pgvector_searches.json** | pgvector 검색 기록 | JSON |
| **search_results.json** | DB 검색 결과 | JSON |
| **db_performance.json** | 쿼리 실행 시간 등 | JSON |

**queries.sql 예시:**
```sql
-- 실행 시간: 2025-11-04 10:30:15
-- 도구: text2sql
-- 설명: 2024년 논문 개수 조회
-- 실행 소요: 45ms
-- 결과 개수: 1

SELECT COUNT(*) AS paper_count
FROM papers
WHERE EXTRACT(YEAR FROM publish_date) = 2024;

-- 실행 시간: 2025-11-04 10:31:20
-- 도구: glossary
-- 설명: 용어 검색 (Attention)
-- 실행 소요: 12ms
-- 결과 개수: 3

SELECT term, definition
FROM glossary
WHERE term ILIKE '%Attention%';
```

**pgvector_searches.json 예시:**
```json
[
  {
    "timestamp": "2025-11-04T10:30:16",
    "tool": "search_paper",
    "collection": "paper_chunks",
    "query_text": "Transformer 논문 설명해줘",
    "top_k": 5,
    "search_type": "mmr",
    "execution_time_ms": 150,
    "result_count": 5
  }
]
```

---

### Q2-3. prompts/ 폴더의 활용법은?

**A:** **LLM에 전달된 모든 프롬프트를 버전 관리**합니다.

**파일 목록:**

| 파일 | 내용 |
|------|------|
| **system_prompt.txt** | 시스템 프롬프트 (역할, 규칙) |
| **user_prompt.txt** | 사용자 프롬프트 (질문 + 컨텍스트) |
| **final_prompt.txt** | LLM에 전달된 최종 프롬프트 |
| **prompt_template.yaml** | 프롬프트 템플릿 정보 |

**system_prompt.txt 예시:**
```
당신은 AI/ML 논문 전문가입니다.

규칙:
- 초심자도 이해할 수 있게 쉽게 설명하세요.
- 전문 용어는 풀어서 설명하세요.
- 비유와 예시를 사용하세요.

===== 메타데이터 =====
difficulty: easy
tool: search_paper
model: solar-pro2
temperature: 0.7
```

**user_prompt.txt 예시:**
```
질문: Transformer 논문 설명해줘

검색된 논문 청크:
[청크 1] Attention is All You Need
저자: Vaswani et al.
내용: Transformer는 recurrence 없이 전적으로 attention...

[청크 2] ...
[청크 3] ...

===== 메타데이터 =====
results_count: 5
search_type: mmr
```

**활용:**
- **프롬프트 최적화**: 어떤 프롬프트가 좋은 답변을 생성했는지 분석
- **버그 재현**: 특정 답변의 프롬프트 재사용
- **A/B 테스트**: 프롬프트 변경 전후 비교

---

### Q2-4. outputs/ 폴더는 언제 사용하나요?

**A:** **사용자가 파일 저장을 요청할 때** 사용됩니다.

**저장 방법:**
```python
# save_file 도구에서
exp_manager.save_output("summary.md", content)

# 결과
outputs/
└── summary.md
```

**저장되는 파일 종류:**
- 논문 요약 (summary.md)
- RAG 검색 결과 (search_results.txt)
- Text-to-SQL 쿼리 결과 (query_result.md)
- 사용자 지정 파일 (user_requested_file.txt)

**metadata.json 연동:**
```json
{
  "outputs": [
    {
      "filename": "summary.md",
      "size_bytes": 1024,
      "created_at": "2025-11-04T10:35:20"
    }
  ]
}
```

---

### Q2-5. evaluation/ 폴더의 용도는?

**A:** **챗봇 성능을 정량적으로 평가한 지표를 저장**합니다.

**평가 지표 파일:**

| 파일 | 내용 |
|------|------|
| **rag_metrics.json** | Recall@K, MRR, NDCG 등 |
| **agent_accuracy.json** | 도구 선택 정확도 |
| **latency_report.json** | 응답 시간 분석 |
| **cost_analysis.json** | LLM 비용 분석 |
| **test_results.json** | 단위 테스트 결과 |

**rag_metrics.json 예시:**
```json
{
  "timestamp": "2025-11-04T10:30:20",
  "query": "Transformer 논문 설명해줘",
  "metrics": {
    "recall_at_3": 1.0,
    "recall_at_5": 1.0,
    "mrr": 0.5,
    "ndcg_at_5": 0.85,
    "search_time_ms": 150
  },
  "ground_truth": [101, 105],
  "retrieved": [101, 105, 112, 120, 125]
}
```

**cost_analysis.json 예시:**
```json
{
  "session_id": "001",
  "total_cost_usd": 0.015,
  "breakdown": {
    "router": 0.001,
    "search_paper": 0.012,
    "embedding": 0.002
  },
  "tokens": {
    "prompt": 1200,
    "completion": 800,
    "total": 2000
  }
}
```

---

## 3. 로깅 시스템

### Q3-1. 메인 Logger와 도구별 Logger의 차이는?

**A:**

| 구분 | 메인 Logger | 도구별 Logger |
|------|------------|--------------|
| **파일** | `chatbot.log` | `tools/{tool_name}.log` |
| **목적** | 전체 실행 흐름 추적 | 도구별 상세 실행 과정 |
| **생성 시점** | ExperimentManager 초기화 | `get_tool_logger()` 호출 시 |
| **사용 위치** | Agent, UI, 전역 | 각 도구 내부 |

**메인 Logger 예시 (chatbot.log):**
```
[2025-11-04 10:30:15] 세션 시작: session_001
[2025-11-04 10:30:15] 폴더 경로: experiments/20251104/20251104_103015_session_001
[2025-11-04 10:30:16] 사용자 질문: Transformer 논문 설명해줘
[2025-11-04 10:30:16] 난이도: easy
[2025-11-04 10:30:16] Router 실행 시작
[2025-11-04 10:30:17] 선택된 도구: search_paper
[2025-11-04 10:30:17] search_paper 도구 실행 시작
[2025-11-04 10:30:19] 답변 생성 완료
[2025-11-04 10:30:19] 응답 시간: 2500ms
```

**도구별 Logger 예시 (tools/search_paper.log):**
```
[2025-11-04 10:30:17] RAG 검색 노드 실행
[2025-11-04 10:30:17] 검색 모드: mmr, top_k: 5
[2025-11-04 10:30:17] 질문 임베딩 시작
[2025-11-04 10:30:18] 임베딩 완료: 150ms
[2025-11-04 10:30:18] pgvector 검색 시작
[2025-11-04 10:30:18] 검색 완료: 5개 청크
[2025-11-04 10:30:18] LLM 답변 생성 시작
[2025-11-04 10:30:19] 답변 생성 완료: 450 글자
```

---

### Q3-2. Logger는 어떻게 사용하나요?

**A:**

**메인 Logger:**
```python
from src.utils.experiment_manager import ExperimentManager

exp_manager = ExperimentManager()

# 메인 로그 기록
exp_manager.logger.write("사용자 질문 입력")
exp_manager.logger.write(f"난이도: {difficulty}")
exp_manager.logger.write("Router 실행 시작")
```

**도구별 Logger:**
```python
# 도구 내부에서
def search_paper_node(state, exp_manager=None):
    # 도구별 Logger 생성
    tool_logger = exp_manager.get_tool_logger('search_paper')

    tool_logger.write("RAG 검색 시작")
    tool_logger.write(f"검색 모드: {search_mode}")

    # 검색 수행...

    tool_logger.write("검색 완료")
    tool_logger.close()  # Logger 닫기 (선택)
```

**중요 사항:**
- `exp_manager.logger.write()`: 메인 로그
- `exp_manager.get_tool_logger('tool_name')`: 도구별 로그
- 도구별 Logger는 매번 새로 생성 (캐싱 안 됨)
- `close()` 호출은 선택 사항 (자동으로 닫힘)

---

### Q3-3. 로그 레벨은 지원하나요?

**A:** 현재는 **단일 레벨 (INFO)**만 지원합니다.

**현재:**
```python
logger.write("메시지")  # 항상 기록
```

**향후 확장 (DEBUG, INFO, WARNING, ERROR):**
```python
logger.debug("디버그 메시지")      # DEBUG 이상일 때만 기록
logger.info("정보 메시지")         # INFO 이상
logger.warning("경고 메시지")      # WARNING 이상
logger.error("에러 메시지")        # 항상 기록
```

**현재 해결 방법:**
```python
# 에러 로그 명시
if exp_manager:
    exp_manager.logger.write(f"❌ 에러 발생: {e}", print_error=True)

# 디버그 로그 (환경변수로 제어)
if os.getenv("DEBUG") == "1":
    exp_manager.logger.write(f"디버그: {debug_info}")
```

---

## 4. 메타데이터 관리

### Q4-1. metadata.json의 구조는?

**A:** **실험의 핵심 정보를 한 곳에 요약한 JSON 파일**입니다.

**기본 스키마:**
```json
{
  "session_id": "001",
  "start_time": "2025-11-04T10:30:15",
  "end_time": "2025-11-04T10:32:45",
  "difficulty": "easy",
  "tool_used": "search_paper",
  "user_query": "Transformer 논문 설명해줘",
  "success": true,
  "response_time_ms": 2500,
  "response_length": 450,
  "model": "solar-pro2",
  "temperature": 0.7,
  "tokens_used": {
    "prompt": 1200,
    "completion": 800,
    "total": 2000
  },
  "db_queries_count": 4,
  "db_total_time_ms": 120,
  "outputs": [
    {
      "filename": "summary.md",
      "size_bytes": 1024,
      "created_at": "2025-11-04T10:35:20"
    }
  ]
}
```

**필드 설명:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `session_id` | string | Session ID (예: "001") |
| `start_time` | string (ISO 8601) | 세션 시작 시간 |
| `end_time` | string (ISO 8601) | 세션 종료 시간 |
| `difficulty` | string | 난이도 (easy/hard) |
| `tool_used` | string | 사용된 도구명 |
| `user_query` | string | 사용자 질문 |
| `success` | boolean | 성공 여부 |
| `response_time_ms` | integer | 응답 시간 (밀리초) |
| `model` | string | 사용된 LLM 모델 |
| `tokens_used` | object | 토큰 사용량 |

---

### Q4-2. metadata.json은 언제 업데이트되나요?

**A:** **`update_metadata()` 메서드 호출 시** 업데이트됩니다.

**초기화 (ExperimentManager 생성 시):**
```python
self.metadata = {
    'session_id': "001",
    'start_time': datetime.now().isoformat(),
    'difficulty': None,
    'tool_used': None,
    'user_query': None,
    'success': None,
    'response_time_ms': None,
    'end_time': None
}
```

**업데이트 (실행 중):**
```python
# 사용자 질문 입력 시
exp_manager.update_metadata(
    user_query="Transformer 논문 설명해줘",
    difficulty="easy"
)

# 도구 선택 시
exp_manager.update_metadata(tool_used="search_paper")

# 답변 생성 완료 시
exp_manager.update_metadata(
    success=True,
    response_time_ms=2500,
    end_time=datetime.now().isoformat()
)
```

**파일 저장:**
```python
def update_metadata(self, **kwargs):
    self.metadata.update(kwargs)
    with open(self.metadata_file, 'w', encoding='utf-8') as f:
        json.dump(self.metadata, f, ensure_ascii=False, indent=2)
```

---

### Q4-3. metadata.json으로 통계를 내려면?

**A:** **모든 세션의 metadata.json을 수집하여 분석**합니다.

**스크립트 예시:**
```python
from pathlib import Path
import json
import pandas as pd

# 모든 metadata.json 수집
metadata_files = Path("experiments").rglob("metadata.json")

data = []
for file in metadata_files:
    with open(file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
        data.append(metadata)

# DataFrame 생성
df = pd.DataFrame(data)

# 통계 분석
print("도구별 사용 횟수:")
print(df['tool_used'].value_counts())

print("\n난이도별 평균 응답 시간:")
print(df.groupby('difficulty')['response_time_ms'].mean())

print("\n성공률:")
print(f"{df['success'].mean() * 100:.1f}%")
```

**분석 결과 예시:**
```
도구별 사용 횟수:
search_paper    45
general         30
web_search      15
glossary        10
...

난이도별 평균 응답 시간:
easy    2100ms
hard    3500ms

성공률:
95.5%
```

---

## 5. 데이터베이스 기록

### Q5-1. SQL 쿼리는 어떻게 기록하나요?

**A:** `log_sql_query()` 메서드를 사용합니다.

**사용 예시:**
```python
# text2sql 도구에서
exp_manager.log_sql_query(
    query="SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024",
    description="2024년 논문 개수 조회",
    tool="text2sql",
    execution_time_ms=45,
    result_count=1
)
```

**저장 위치:** `database/queries.sql`

**저장 형식:**
```sql
-- 실행 시간: 2025-11-04 10:30:15
-- 도구: text2sql
-- 설명: 2024년 논문 개수 조회
-- 실행 소요: 45ms
-- 결과 개수: 1

SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
```

---

### Q5-2. pgvector 검색은 어떻게 기록하나요?

**A:** `log_pgvector_search()` 메서드를 사용합니다.

**사용 예시:**
```python
# search_paper 도구에서
exp_manager.log_pgvector_search({
    'tool': 'search_paper',
    'collection': 'paper_chunks',
    'query_text': 'Transformer 논문 설명해줘',
    'top_k': 5,
    'search_type': 'mmr',
    'execution_time_ms': 150,
    'result_count': 5
})
```

**저장 위치:** `database/pgvector_searches.json`

**저장 형식:**
```json
[
  {
    "timestamp": "2025-11-04T10:30:16",
    "tool": "search_paper",
    "collection": "paper_chunks",
    "query_text": "Transformer 논문 설명해줘",
    "top_k": 5,
    "search_type": "mmr",
    "execution_time_ms": 150,
    "result_count": 5
  }
]
```

---

### Q5-3. DB 검색 결과는 어떻게 저장하나요?

**A:** `save_search_results()` 메서드를 사용합니다.

**사용 예시:**
```python
# search_paper 도구에서
exp_manager.save_search_results('search_paper', {
    'query': 'Transformer 논문',
    'results': [
        {
            'paper_id': 101,
            'title': 'Attention is All You Need',
            'score': 0.15,
            'content': '...'
        },
        {
            'paper_id': 105,
            'title': 'BERT',
            'score': 0.22,
            'content': '...'
        }
    ]
})
```

**저장 위치:** `database/search_results.json`

---

## 6. 사용 예시

### Q6-1. 기본 사용 흐름

**A:**

```python
from src.utils.experiment_manager import ExperimentManager

# 1. ExperimentManager 초기화
exp_manager = ExperimentManager()
exp_manager.logger.write("챗봇 세션 시작")

# 2. 사용자 질문 입력
user_query = "Transformer 논문 설명해줘"
difficulty = "easy"

exp_manager.update_metadata(
    user_query=user_query,
    difficulty=difficulty
)

# 3. 도구 실행 (search_paper 예시)
tool_logger = exp_manager.get_tool_logger('search_paper')
tool_logger.write(f"RAG 검색 시작: {user_query}")

# RAG 검색...
tool_logger.write("검색 완료: 5개 청크")
tool_logger.close()

# 4. DB 쿼리 기록
exp_manager.log_pgvector_search({
    'tool': 'search_paper',
    'query_text': user_query,
    'top_k': 5,
    'execution_time_ms': 150
})

# 5. 프롬프트 저장
exp_manager.save_system_prompt(system_prompt, {"difficulty": difficulty})
exp_manager.save_user_prompt(user_prompt, {"results_count": 5})

# 6. 최종 답변 저장
exp_manager.save_output("response.txt", final_answer)

# 7. 메타데이터 업데이트
exp_manager.update_metadata(
    tool_used="search_paper",
    success=True,
    response_time_ms=2500,
    end_time=datetime.now().isoformat()
)

exp_manager.logger.write("세션 종료")
```

---

### Q6-2. 에러 처리 예시

**A:**

```python
try:
    # 도구 실행
    result = execute_tool(user_query)

    exp_manager.update_metadata(
        success=True,
        tool_used="search_paper"
    )

except Exception as e:
    exp_manager.logger.write(f"에러 발생: {e}", print_error=True)

    exp_manager.update_metadata(
        success=False,
        error_message=str(e)
    )

    # 에러 트레이스 저장
    import traceback
    error_trace = traceback.format_exc()

    exp_manager.save_output("error_trace.log", error_trace)
```

---

### Q6-3. 평가 지표 저장 예시

**A:**

```python
# RAG 평가 지표 저장
exp_manager.save_rag_metrics({
    'query': user_query,
    'recall_at_3': 1.0,
    'recall_at_5': 1.0,
    'mrr': 0.5,
    'ndcg_at_5': 0.85,
    'search_time_ms': 150
})

# 비용 분석 저장
exp_manager.save_cost_analysis({
    'total_cost_usd': 0.015,
    'breakdown': {
        'router': 0.001,
        'search_paper': 0.012,
        'embedding': 0.002
    },
    'tokens': {
        'prompt': 1200,
        'completion': 800,
        'total': 2000
    }
})

# LLM-as-a-Judge 답변 평가 결과 저장
exp_manager.save_evaluation_result({
    'question': user_query,
    'answer': final_answer,
    'reference_docs': reference_docs,
    'difficulty': 'easy',
    'accuracy_score': 9,
    'relevance_score': 10,
    'difficulty_score': 8,
    'citation_score': 7,
    'total_score': 34,
    'comment': '답변이 정확하고 관련성이 높음'
})

# 전체 대화 내역 저장
exp_manager.save_conversation([
    {'role': 'user', 'content': '첫 번째 질문'},
    {'role': 'assistant', 'content': '첫 번째 답변', 'tool_choice': 'search_paper'},
    {'role': 'user', 'content': '두 번째 질문'},
    {'role': 'assistant', 'content': '두 번째 답변', 'tool_choice': 'glossary'}
])

# SQL 쿼리 로그 파일로 플러시
exp_manager.flush_queries_to_file()
```

---

## 7. 트러블슈팅

### Q7-1. 폴더가 생성되지 않아요

**원인:** 권한 문제 또는 경로 오류

**해결:**
```bash
# 권한 확인
ls -la experiments/

# 폴더 수동 생성
mkdir -p experiments/$(date +%Y%m%d)

# Python 테스트
python -c "from src.utils.experiment_manager import ExperimentManager; ExperimentManager()"
```

---

### Q7-2. Session ID가 중복돼요

**원인:** 동시에 여러 세션 실행

**해결:**
- Session ID 생성은 파일 시스템 기반이므로 동시 실행 시에도 고유 ID 보장
- 만약 중복이 발생하면 `_get_next_session_id()` 로직 확인

---

### Q7-3. metadata.json이 업데이트되지 않아요

**원인:** `update_metadata()` 호출 누락

**확인:**
```python
# metadata.json 확인
cat experiments/20251104/20251104_103015_session_001/metadata.json

# 수동 업데이트 테스트
exp_manager.update_metadata(test_field="test_value")
```

---

### Q7-4. 로그 파일이 너무 커요

**원인:** 장시간 실행 또는 과도한 로그 작성

**해결:**

**1. 로그 레벨 제어 (향후)**
```python
logger.set_level("WARNING")  # DEBUG, INFO 로그 생략
```

**2. 로그 로테이션 (현재 미지원, 향후 추가)**
```python
# 로그 파일 크기 제한
logger = Logger("chatbot.log", max_bytes=10*1024*1024)  # 10MB
```

**3. 로그 정리 스크립트**
```bash
# 30일 이상 된 실험 폴더 삭제
find experiments/ -type d -mtime +30 -exec rm -rf {} +
```

---

## 8. 고급 활용

### Q8-1. 실험 비교 스크립트

**A:**

```python
import json
from pathlib import Path
import pandas as pd

def compare_experiments(session_ids):
    """여러 세션 비교"""
    data = []

    for session_id in session_ids:
        # metadata.json 찾기
        metadata_path = list(Path("experiments").rglob(f"*session_{session_id:03d}/metadata.json"))[0]

        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            data.append(metadata)

    df = pd.DataFrame(data)
    print(df[['session_id', 'difficulty', 'tool_used', 'response_time_ms', 'success']])

# 사용
compare_experiments([1, 2, 3, 4, 5])
```

---

### Q8-2. 성능 대시보드

**A:**

```python
import streamlit as st
import json
from pathlib import Path

st.title("ExperimentManager 대시보드")

# 모든 metadata.json 수집
metadata_files = list(Path("experiments").rglob("metadata.json"))

total_sessions = len(metadata_files)
success_count = 0
total_time = 0

for file in metadata_files:
    with open(file, 'r') as f:
        metadata = json.load(f)
        if metadata.get('success'):
            success_count += 1
        total_time += metadata.get('response_time_ms', 0)

st.metric("총 세션 수", total_sessions)
st.metric("성공률", f"{success_count/total_sessions*100:.1f}%")
st.metric("평균 응답 시간", f"{total_time/total_sessions:.0f}ms")
```

---

### Q8-3. 자동 백업 스크립트

**A:**

```bash
#!/bin/bash
# backup_experiments.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="backups/experiments_$DATE.tar.gz"

# experiments 폴더 압축
tar -czf $BACKUP_DIR experiments/

# 7일 이상 된 백업 삭제
find backups/ -name "experiments_*.tar.gz" -mtime +7 -delete

echo "백업 완료: $BACKUP_DIR"
```

---

## 참고 자료

### 관련 문서
- [03_실험_관리_시스템.md](../modularization/03_실험_관리_시스템.md)
- [02_Logger_시스템.md](../modularization/02_Logger_시스템.md)

### 구현 파일
- `src/utils/experiment_manager.py` - ExperimentManager 클래스
- `src/utils/logger.py` - Logger 클래스

---

## 작성자
- **최현화[팀장]** (ExperimentManager 시스템 구현 및 문서화)
