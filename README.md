# Agent Quality Gate

LLM 에이전트의 응답 품질과 도구 호출을 자동으로 평가하고, 기준에 못 미치면 CI에서 배포를 막는 품질 게이트 예제입니다.

[![quality-gate](https://github.com/JisuPark30901/kt-agent-quality-gate/actions/workflows/quality-gate.yml/badge.svg)](https://github.com/JisuPark30901/kt-agent-quality-gate/actions/workflows/quality-gate.yml)

**결과 요약:** 테스트 10개 중 10개 PASS. 도구 추가 전 6/10에서 개선했습니다. 자세한 내용은 [RESULTS.md](RESULTS.md)에 있습니다.

## 무엇을 검증하나

평가 대상은 쇼핑몰 고객 문의에 답하는 Q&A 에이전트(Gemini)입니다.

- **문서 기반 답변:** `docs/`의 환불·배송 정책 문서에서만 답합니다.
- **도구 3개:** 주문 조회(`lookup_order`), 오늘 날짜(`get_today`), 환율 변환(`convert_currency`)

에이전트가 제대로 동작하려면 세 가지가 필요합니다.

1. 문서에 있는 질문에는 정확하게 답한다.
2. 문서에 없는 질문에는 지어내지 않고 모른다고 답한다 (할루시네이션 방지).
3. 여러 도구를 조합해야 하는 질문에서 필요한 도구를 모두 호출하고, 결과를 맞게 조합한다.

## 테스트 계획

| 유형 | 케이스 수 | 목적 | 예시 |
|------|:---:|------|------|
| 정상 | 4 | 문서 기반 정답률 | "How much does express shipping cost?" |
| 지식베이스 밖 | 3 | 할루시네이션 유도 | "Can I pay with PayPal?" (문서에 없음) |
| 도구 2개 필요 | 3 | 도구 선택과 조합 | "If I return order #51007 today, how much do I get back?" (주문 조회 + 날짜 + 환불 규정) |

## 품질 기준

| 유형 | 지표 | 통과 기준 | 평가 방식 |
|------|------|:---:|-----------|
| 정상, 지식베이스 밖 | Answer Relevancy | ≥ 0.7 | LLM 평가 모델 |
| 정상, 지식베이스 밖 | Faithfulness | ≥ 0.7 | LLM 평가 모델 |
| 도구 2개 필요 | Tool Correctness | = 1.0 | 기대 도구와 실제 호출을 직접 비교 (평가 모델 없음) |
| 도구 2개 필요 | Task Completion | ≥ 0.7 | LLM 평가 모델 |

케이스 하나라도 기준 미달이면 테스트가 실패하고, CI job도 실패합니다.

## 설계 결정

- **유형마다 지표를 다르게 썼습니다.** 도구 케이스의 답은 문서가 아니라 도구 결과에서 나오므로 Faithfulness로는 평가할 수 없습니다. 그래서 도구 호출 자체(Tool Correctness)와 과제 완수(Task Completion)를 봅니다.
- **도구 평가는 평가 모델 없이 계산합니다.** LLM 평가 모델은 같은 답에도 다른 점수를 줄 수 있습니다(RESULTS.md 발견한 점 1). Tool Correctness는 이름을 직접 비교하므로 흔들리지 않습니다.
- **테스트 데이터를 고정했습니다.** 주문 데이터, 환율, 오늘 날짜(`AGENT_TODAY=2026-10-03`)를 고정해 매번 같은 정답을 갖게 했습니다. 그래야 점수가 떨어졌을 때 에이전트 문제인지 데이터 변화인지 구분할 수 있습니다.
- **무료 티어에 맞췄습니다.** Gemini 무료 티어는 모델당 분당 5회, 하루 약 20회입니다. 그래서 평가 호출 사이에 간격을 두고, 에이전트와 평가 모델을 분리하고, CI에서는 유형별 핵심 케이스 1개씩(3개)만 실행합니다.

## Quality Gate (CI)

`.github/workflows/quality-gate.yml`은 push와 pull request마다 다음을 실행합니다.

1. 의존성 설치
2. `ruff check .` (lint)
3. `deepeval test run test_agent.py -m core` (핵심 케이스 3개)

- **실패 조건:** 지표가 기준에 못 미치면 deepeval이 0이 아닌 종료 코드를 반환하고, job이 실패합니다.
- **API 키:** GitHub Secrets의 `GOOGLE_API_KEY`에서 읽습니다.
- **모델 교체:** 무료 한도가 차면 **Settings → Variables**의 `GEMINI_MODEL`, `JUDGE_MODEL`만 바꾸면 됩니다. 코드는 고치지 않아도 됩니다.

## 실행 방법

### 로컬

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
echo "GOOGLE_API_KEY=<your key>" > .env

source .venv/bin/activate
python agent.py "Check order #48213 and tell me how many days are left until it arrives."
deepeval test run test_agent.py            # 전체 10개
deepeval test run test_agent.py -m core    # 핵심 3개
```

### Docker

```bash
docker build -t agent-quality-gate .
docker run --rm --env-file .env agent-quality-gate -m core
```

## 파일 구성

| 파일 | 역할 |
|------|------|
| `agent.py` | 에이전트: 문서 검색, Gemini 호출, 도구 호출 기록 |
| `tools.py` | 도구 3개와 고정된 테스트 데이터 |
| `docs/` | 지식베이스 (환불·배송 정책) |
| `test_agent.py` | 테스트 케이스 10개, 지표, 평가 모델 설정 |
| `RESULTS.md` | 케이스별 결과, 실패 원인 분석, 이전 실행과 비교 |
| `Dockerfile` | 컨테이너에서 테스트 실행 |
| `.github/workflows/quality-gate.yml` | CI 품질 게이트 |

## 한계와 다음 단계

- **규모:** 문서 2개, 테스트 10개의 작은 예제입니다. 실제 서비스 수준의 테스트셋이 필요합니다.
- **검색:** 키워드 매칭 검색입니다. 임베딩 기반 검색으로 바꾸고 검색 품질(Contextual Recall 등)도 평가해야 합니다.
- **반복 실행:** 무료 한도 때문에 같은 테스트를 여러 번 돌려 점수 편차를 재지 못했습니다. 평가 모델이 흔들리는 정도를 수치로 측정하는 것이 다음 과제입니다.
- **추적:** Langfuse나 OpenTelemetry로 에이전트 실행 과정을 추적하면 실패 원인 분석이 빨라집니다.
- **벤치마크:** GAIA 같은 공개 에이전트 벤치마크로 범용 능력도 평가해 볼 계획입니다.
