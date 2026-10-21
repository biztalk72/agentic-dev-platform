# 컨텍스트 노트

## 2026-10-21 후속 과제 3건 (PR #1 머지 직후)

- **완료 조건 정의**. `plan()`이 빈 intent를 반환하고 `dashboard`의 `rendered` 로그가 있으면 task 완료로 판단해 `archive_task`를 호출한다. `prove_goal` 같은 명시적 노드 대신 "할 일이 더 없음"을 완료 신호로 택했다. MVP 범위에서 가장 작은 변경이기 때문이다.
- **flask 제거 근거**. `src/` 전체에서 flask/fastapi import가 0건. 코드는 표준 라이브러리만 사용한다. PRD의 "FastAPI"는 미래 API 레이어 계획으로 문구를 수정했고, 코드를 FastAPI로 바꾸지 않았다 (MVP는 CLI-first).
- **건드리지 않은 기존 quirk**. (1) ReviewerWorker는 데모 흐름에서 실행되지 않는다 — PRDWorker의 finding에 "PRD"가 포함되어 `has_finding and not has_prd` 조건이 성립하지 않음. (2) `has_log("dashboard","rendered")`는 task 단위가 아닌 전역 조회라 데모 재실행 시 dashboard가 다시 렌더되지 않음. 둘 다 동작에는 문제없어 범위 외로 남김.
- **테스트 DB 격리**. 테스트는 `tmp_path` SQLite를 쓴다. 루트의 `agentic.db`는 데모 생성물이며 커밋되어 있는 상태 그대로 둔다.
- **CI**. deploy-pages.yml의 기존 run 블록에 pytest 한 줄만 추가. 테스트 실패 시 배포가 중단된다.
