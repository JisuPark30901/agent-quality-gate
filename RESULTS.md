# 테스트 결과

- **실행 시각:** 2026-10-03
- **명령:** `deepeval test run test_agent.py`
- **에이전트 모델:** `gemini-3.7-flash` (9번만 `gemini-3.6-flash`, 아래 참고)
- **평가(judge) 모델:** `gemini-3.5-flash-lite`
- **통과 기준:** Answer Relevancy, Faithfulness 모두 0.7 이상
- **결과:** 10개 중 6개 PASS, 4개 FAIL (통과율 60%)

## 케이스별 결과

| # | 유형 | 질문 | 에이전트 답변 | Answer Relevancy | Faithfulness | 결과 | 실패 원인 |
|---|------|------|---------------|-----------------:|-------------:|:----:|-----------|
| 1 | 정상 | How long do I have to get a full refund? | You have within 30 days of purchase to request a full refund. | 1.00 | 1.00 | PASS | |
| 2 | 정상 | Can I get a refund on a digital download? | Digital downloads are non-refundable once the file has been downloaded. | 1.00 | 1.00 | PASS | |
| 3 | 정상 | How much does express shipping cost? | Express shipping costs $15. | 1.00 | 1.00 | PASS | |
| 4 | 정상 | Do you ship to South Korea? | Yes, we ship to South Korea. | 1.00 | 1.00 | PASS | |
| 5 | 지식베이스 밖 | What is your customer support phone number? | I don't know. | 1.00 | 1.00 | PASS | |
| 6 | 지식베이스 밖 | Do you offer a warranty on electronics? | I don't know. | 0.00 | 1.00 | FAIL | **평가 모델의 판정이 일관되지 않음.** 답변은 5·7번과 똑같은 "I don't know."로 올바르게 거절했지만, 이 케이스에서만 관련성 0점을 받음. 에이전트 결함이 아니라 지표 문제 |
| 7 | 지식베이스 밖 | Can I pay with PayPal? | I don't know. | 1.00 | 1.00 | PASS | |
| 8 | 도구 2개 필요 | Check the status of order #48213 and tell me its delivery date. | I don't know. | 0.00 | 1.00 | FAIL | **에이전트에 도구가 없음.** 주문 조회와 배송일 계산이 필요하지만 에이전트는 문서 검색만 함. 지어내지는 않았지만(Faithfulness 1.0), 왜 못 하는지 설명하지 않고 "I don't know."로만 답해 관련성 0점 |
| 9 | 도구 2개 필요 | I paid $40 for an item on September 1. If I return it today, how much do I get back and in what form? | I don't know. The provided context does not mention today's date, so it is not possible to determine if the return is within 30 days… | 1.00 | 0.67 | FAIL | **날짜 도구가 없음.** 오늘 날짜를 몰라 30일 경과 여부(→ $40 store credit)를 판단하지 못함. 문서에 없는 판단을 섞어 설명하다 Faithfulness가 기준 미달 |
| 10 | 도구 2개 필요 | Convert the express shipping cost to Korean won at today's rate and tell me the arrival date if I order now. | I don't know. | 0.00 | 1.00 | FAIL | **환율·날짜 도구가 없고, 아는 부분도 답하지 않음.** 문서에 있는 "$15, 1~2 영업일"조차 말하지 않고 전부 거절함. 부분 답변을 못 하는 것은 에이전트(프롬프트) 개선 대상 |

## 유형별 요약

| 유형 | PASS | FAIL | 해석 |
|------|-----:|-----:|------|
| 정상 | 4 | 0 | 문서로 답할 수 있는 질문은 모두 정확함 |
| 지식베이스 밖 (할루시네이션 유도) | 2 | 1 | **할루시네이션 0건.** 3건 모두 올바르게 거절함(Faithfulness 1.0). 실패 1건은 평가 모델의 판정 흔들림 |
| 도구 2개 필요 | 0 | 3 | 에이전트에 도구가 없어 예상대로 실패. 지어내지는 않음 |

## 개선 제안

1. **도구 추가:** 주문 조회, 오늘 날짜, 환율 도구를 붙이면 8~10번을 해결할 수 있습니다.
2. **부분 답변 허용:** 시스템 프롬프트를 바꿔 "아는 부분은 답하고, 모르는 부분은 왜 모르는지 설명"하게 하면 10번처럼 전부 거절하는 일이 줄어듭니다.
3. **거절 케이스용 지표:** Answer Relevancy는 올바른 거절에도 0점을 줄 수 있습니다(6번). 지식베이스 밖 질문은 "모른다고 답했는가"를 직접 확인하는 지표(예: deepeval `GEval`)로 평가하는 편이 정확합니다.

## 참고

- **9번 재실행:** 첫 실행에서 9번은 에이전트 모델 `gemini-3.7-flash`의 하루 무료 한도(20회)를 넘어 `429 RESOURCE_EXHAUSTED`로 평가되지 못했습니다. 그래서 9번만 `GEMINI_MODEL=gemini-3.6-flash`로 다시 실행했고, 위 표에는 그 결과를 넣었습니다.
- **Docker 실행 확인:** 컨테이너 안에서 핵심 케이스 3개(1·2·5번, 에이전트 `gemini-3.6-flash`)를 돌린 결과 2개 PASS, 1개 FAIL이었습니다. 2번이 Answer Relevancy 0.50으로 떨어졌는데, 답변이 "Based on the provided policy, …"로 장황해지며 관련 없는 문장이 섞였기 때문입니다. 같은 질문이 `gemini-3.7-flash`에서는 1.00이었으므로, 에이전트 모델에 따라 결과가 달라집니다.
- 점수는 평가 모델이 매기므로 실행할 때마다 달라질 수 있습니다.
