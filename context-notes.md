# 컨텍스트 노트

## 2026-10-21 후속 과제 3건 (PR #1 머지 직후)

- **완료 조건 정의**. `plan()`이 빈 intent를 반환하고 `dashboard`의 `rendered` 로그가 있으면 task 완료로 판단해 `archive_task`를 호출한다. `prove_goal` 같은 명시적 노드 대신 "할 일이 더 없음"을 완료 신호로 택했다. MVP 범위에서 가장 작은 변경이기 때문이다.
- **flask 제거 근거**. `src/` 전체에서 flask/fastapi import가 0건. 코드는 표준 라이브러리만 사용한다. PRD의 "FastAPI"는 미래 API 레이어 계획으로 문구를 수정했고, 코드를 FastAPI로 바꾸지 않았다 (MVP는 CLI-first).
- **건드리지 않은 기존 quirk**. (1) ReviewerWorker는 데모 흐름에서 실행되지 않는다 — PRDWorker의 finding에 "PRD"가 포함되어 `has_finding and not has_prd` 조건이 성립하지 않음. (2) `has_log("dashboard","rendered")`는 task 단위가 아닌 전역 조회라 데모 재실행 시 dashboard가 다시 렌더되지 않음. 둘 다 동작에는 문제없어 범위 외로 남김.

## 2026-10-22 quirk 2건 해소 (PR #2 머지 직후)

- **plan() 플로우 재정렬**. PRD §5 의도대로 collector → analyst → prd → reviewer → dashboard 순서로 변경. 상태 판별은 finding 내용의 마커 문자열로 한다 — `analyst:` 접두사(분석), `PRD drafted` 포함(PRD), `lineage-check:` 접두사(리뷰). 워커 출력 문자열이 계약이 되므로 워커 메시지 형식을 바꾸면 plan()도 같이 바꿔야 한다. MVP 규모에서 노드 스키마 확장 대신 택한 최소 변경이다.
- **dashboard 렌더 per-task 스코프**. DashboardWorker가 로그 detail에 `task_id`를 포함하고, `has_log`가 선택적 `task_id` 인자로 `json_extract(detail_json,'$.task_id')` 조회를 지원한다. 기존 호출부(인자 2개)는 그대로 동작한다.
- **검증**. pytest 18건 통과. 기존 agentic.db를 재사용한 데모 실행에서 5개 워커 전부 실행 + task `completed` 확인 (per-task 수정 전에는 dashboard가 생략되어 완료 불가였을 시나리오).
- **테스트 DB 격리**. 테스트는 `tmp_path` SQLite를 쓴다. 루트의 `agentic.db`는 데모 생성물이며 커밋되어 있는 상태 그대로 둔다.
- **CI**. deploy-pages.yml의 기존 run 블록에 pytest 한 줄만 추가. 테스트 실패 시 배포가 중단된다.
