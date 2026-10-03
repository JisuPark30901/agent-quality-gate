# 테스트 결과

- **실행일:** 2026-10-03
- **명령:** `deepeval test run test_agent.py`
- **평가(judge) 모델:** `gemini-3.5-flash-lite`
- **결과:** 10개 중 10개 PASS (통과율 100%)
- **변경점:** 에이전트에 도구 3개(`lookup_order`, `get_today`, `convert_currency`)를 추가했습니다. 이전 실행(도구 없음)은 6/10이었습니다.

## 품질 기준

| 유형 | 지표 | 기준 | 무엇을 보나 |
|------|------|-----:|-------------|
| 정상, 지식베이스 밖 | Answer Relevancy | 0.7 | 답변이 질문에 맞는가 |
| 정상, 지식베이스 밖 | Faithfulness | 0.7 | 문서에 없는 내용을 지어내지 않았는가 |
| 도구 2개 필요 | Tool Correctness | 1.0 | 호출해야 할 도구를 모두 호출했는가 (평가 모델 없이 계산) |
| 도구 2개 필요 | Task Completion | 0.7 | 질문이 요구한 일을 실제로 해냈는가 |

## 케이스별 결과

| # | 유형 | 질문 | 에이전트 답변 (요약) | 점수 | 결과 |
|---|------|------|----------------------|------|:----:|
| 1 | 정상 | How long do I have to get a full refund? | 구매 후 30일 이내 전액 환불 | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 2 | 정상 | Can I get a refund on a digital download? | 다운로드한 디지털 상품은 환불 불가 | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 3 | 정상 | How much does express shipping cost? | $15 | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 4 | 정상 | Do you ship to South Korea? | 한국으로 배송함 | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 5 | 지식베이스 밖 | What is your customer support phone number? | I don't know. | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 6 | 지식베이스 밖 | Do you offer a warranty on electronics? | I don't know. 문서에 보증 관련 내용이 없음 | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 7 | 지식베이스 밖 | Can I pay with PayPal? | I don't know. 문서에 결제 수단 내용이 없음 | Relevancy 1.00 / Faithfulness 1.00 | PASS |
| 8 | 도구 2개 | Check order #48213 and tell me how many days are left until it arrives. | 10/6 도착 예정, 오늘(10/3) 기준 3일 남음 | Tool Correctness 1.00 / Task Completion 1.00 | PASS |
| 9 | 도구 2개 | If I return order #51007 today, how much money do I get back and in what form? | 구매 후 32일 경과 → $40 스토어 크레딧 | Tool Correctness 1.00 / Task Completion 1.00 | PASS |
| 10 | 도구 2개 | Convert the express shipping cost to Korean won and tell me the arrival date if I order today. | $15 = 20,700원, 영업일 1~2일 → 10/5(월)~10/6(화) 도착 | Tool Correctness 1.00 / Task Completion 1.00 | PASS |

8~10번에서 실제로 호출된 도구:

| # | 기대한 도구 | 실제 호출 |
|---|-------------|-----------|
| 8 | `lookup_order`, `get_today` | `lookup_order`, `get_today` |
| 9 | `lookup_order`, `get_today` | `lookup_order`, `get_today` |
| 10 | `convert_currency`, `get_today` | `get_today`, `convert_currency` |

## 이전 실행과 비교

| 유형 | 이전 (도구 없음) | 현재 (도구 3개) | 무엇이 바뀌었나 |
|------|:---:|:---:|-----------------|
| 정상 | 4/4 | 4/4 | 변화 없음 |
| 지식베이스 밖 | 2/3 | 3/3 | 할루시네이션은 이전에도 0건. 6번 실패가 사라짐 (아래 참고) |
| 도구 2개 필요 | 0/3 | 3/3 | 도구 추가로 해결. 9번은 날짜 계산과 문서의 환불 규정을 함께 써야 풀리는 문제 |
| **합계** | **6/10** | **10/10** | |

## 발견한 점

1. **이유 없는 거절은 평가가 흔들립니다.** 이전 실행에서 5·6·7번은 모두 "I don't know."라고만 답했는데, 6번만 관련성 0점을 받았습니다. 이번 실행에서는 "문서에 보증 관련 내용이 없다"처럼 이유를 함께 말했고, 3건 모두 1.00이었습니다. 거절할 때 이유를 말하도록 에이전트를 설계하면 평가가 안정되고 사용자에게도 더 유용합니다.
2. **에이전트 모델이 바뀌면 답변 스타일이 바뀝니다.** 같은 2번 질문이 Docker 실행(`gemini-3.6-flash`)에서는 장황한 답변 때문에 관련성 0.50으로 떨어졌습니다. 모델을 바꿀 때는 회귀 테스트를 다시 돌려야 합니다.
3. **도구 평가는 평가 모델 없이 할 수 있습니다.** Tool Correctness는 도구 이름을 직접 비교하므로 점수가 흔들리지 않고 무료 한도도 쓰지 않습니다.

## 테스트 설계

- **가짜 데이터와 고정 날짜:** 주문 데이터, 환율(1달러 = 1,380원), 오늘 날짜(2026-10-03)를 고정해서 테스트가 매번 같은 정답을 갖게 했습니다. 실제 날짜나 실시간 환율을 쓰면 점수가 떨어졌을 때 에이전트 문제인지 데이터 변화인지 구분할 수 없습니다.
- **CI 핵심 케이스:** 무료 한도 때문에 CI에서는 유형별로 하나씩(1·5·8번)만 실행합니다.

## 실행 환경 참고

무료 티어는 모델마다 하루 약 20회로 제한되어, 케이스를 에이전트 모델 3개에 나눠 실행했습니다.

| 케이스 | 에이전트 모델 |
|--------|---------------|
| 1~5 | `gemini-3.5-flash` |
| 6~7 | `gemini-3.1-flash-lite` (`gemini-3.5-flash` 한도 소진) |
| 8~10 | `gemini-3.6-flash` |

모델에 따라 답변이 달라질 수 있으므로(발견한 점 2), 같은 모델로 10개를 한 번에 돌린 결과는 아닙니다. 점수는 평가 모델이 매기므로 실행할 때마다 조금씩 달라질 수 있습니다.
