# 후속 과제 체크리스트 (2026-10-21)

- [x] 오케스트레이터 완료 감지: intent가 없고 dashboard 렌더 완료 시 `archive_task` 호출
- [x] requirements.txt 정리: 미사용 flask 제거, pytest 추가
- [x] PRD.md 기술스택 문구를 실제 코드(stdlib-only)와 일치
- [x] tests/ 추가: GraphStore(dedup·아카이브), HITLGate(승인·거부·타임아웃), Orchestrator(intent 순서·게이트 거부·E2E 완료)
- [x] CI(deploy-pages.yml)에 pytest 단계 추가
- [x] pytest 전체 통과(16 passed) + 데모 실행으로 task `completed` 확인
- [x] 커밋 분리(아카이브 수정 / 의존성·문서 / 테스트·CI) 후 push, PR #2 생성
