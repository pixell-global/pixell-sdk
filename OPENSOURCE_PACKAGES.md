# Pixell Agent Kit - Open Source Packages

## Core Dependencies (Production)

| 오픈소스 이름 | 활용 내용 | 라이선스 | 링크 |
|--------------|----------|---------|------|
| **click** | CLI 프레임워크 - pixell 명령줄 인터페이스 구현 (build, init, deploy 등 모든 명령어) | BSD-3-Clause | https://github.com/pallets/click |
| **pydantic** | 데이터 검증 및 설정 관리 - agent.yaml 매니페스트 검증, UI 스펙 검증, 프로토콜 메시지 검증 | MIT | https://github.com/pydantic/pydantic |
| **pyyaml** | YAML 파서 - agent.yaml 및 pak.yaml 파일 읽기/쓰기 | MIT | https://github.com/yaml/pyyaml |
| **jsonschema** | JSON 스키마 검증 - 프로토콜 엔벨로프 검증 (ui.event, action.result, ui.patch) | MIT | https://github.com/python-jsonschema/jsonschema |
| **fastapi** | 웹 프레임워크 - 개발 서버 REST API 지원, 에이전트 엔드포인트 마운팅 | MIT | https://github.com/tiangolo/fastapi |
| **uvicorn** | ASGI 서버 - FastAPI 개발 서버 실행, 로컬 에이전트 서빙 및 핫 리로드 | BSD-3-Clause | https://github.com/encode/uvicorn |
| **watchdog** | 파일 시스템 모니터링 - 개발 서버 핫 리로드 기능, 코드 변경 감지 | Apache-2.0 | https://github.com/gorakhargosh/watchdog |
| **python-dotenv** | 환경변수 관리 - .env 파일에서 환경변수 로드, 시크릿 설정 읽기 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| **tabulate** | 테이블 출력 포맷팅 - `pixell list` 명령어 에이전트 목록 표시, 시크릿 테이블 포맷 | MIT | https://github.com/astanin/python-tabulate |
| **jinja2** | 템플릿 엔진 - setup.py 파일 생성, 프로젝트 스캐폴딩 (`pixell init`) | BSD-3-Clause | https://github.com/pallets/jinja |
| **requests** | HTTP 클라이언트 - Pixell Agent Cloud API 호출, APKG 업로드, 배포 상태 확인, 시크릿 관리 | Apache-2.0 | https://github.com/psf/requests |

## Build System Dependencies

| 오픈소스 이름 | 활용 내용 | 라이선스 | 링크 |
|--------------|----------|---------|------|
| **setuptools** | 패키지 빌드 및 배포 - pixell-kit 패키지 빌드, 에이전트 패키지용 setup.py 자동 생성 | MIT | https://github.com/pypa/setuptools |
| **wheel** | Python 패키지 배포 포맷 - wheel 배포판 생성, 빠른 설치 지원 | MIT | https://github.com/pypa/wheel |

## Development Dependencies (Optional)

| 오픈소스 이름 | 활용 내용 | 라이선스 | 링크 |
|--------------|----------|---------|------|
| **pytest** | 테스트 프레임워크 - 단위 테스트 및 통합 테스트 실행 | MIT | https://github.com/pytest-dev/pytest |
| **pytest-cov** | 테스트 커버리지 플러그인 - 코드 커버리지 측정 및 리포트 생성 | MIT | https://github.com/pytest-dev/pytest-cov |
| **pytest-asyncio** | 비동기 테스트 지원 - async/await 코드 테스트 (배포, 서버 테스트) | Apache-2.0 | https://github.com/pytest-dev/pytest-asyncio |
| **black** | 코드 포맷터 - Python 코드 자동 포맷팅 (100자 라인 길이) | MIT | https://github.com/psf/black |
| **mypy** | 정적 타입 체커 - Python 코드 타입 검사, 런타임 이전 에러 감지 | MIT | https://github.com/python/mypy |
| **ruff** | 고속 Python 린터 - 코드 린팅 및 스타일 검사 (Rust 기반) | MIT | https://github.com/astral-sh/ruff |
| **build** | 패키지 빌드 프론트엔드 - PEP 517/518 호환 빌드 도구 | MIT | https://github.com/pypa/build |
| **twine** | PyPI 업로더 - pixell-kit을 PyPI에 배포 | Apache-2.0 | https://github.com/pypa/twine |
| **types-PyYAML** | PyYAML 타입 스텁 - mypy를 사용한 YAML 코드 타입 검사 | Apache-2.0 | https://github.com/python/typeshed |

## Optional Dependencies (Signing)

| 오픈소스 이름 | 활용 내용 | 라이선스 | 링크 |
|--------------|----------|---------|------|
| **python-gnupg** | GnuPG Python 래퍼 - APKG 패키지 암호화 서명 및 검증 (보안 기능) | BSD-3-Clause | https://github.com/vsajip/python-gnupg |

---

## Summary

### Package Count by Category

| 카테고리 | 패키지 수 | 목적 |
|---------|----------|------|
| CLI & UX | 2 | 명령줄 인터페이스 및 사용자 경험 |
| Web & API | 4 | 웹 서버, API, HTTP 통신 |
| Data Validation | 2 | 데이터 검증 및 스키마 검사 |
| File Formats | 2 | 파일 형식 파싱 (YAML, .env) |
| Templating | 1 | 코드 생성 및 템플릿 |
| Build System | 2 | 패키지 빌드 및 배포 |
| Development | 8 | 테스트, 포맷팅, 린팅, 타입 검사 |
| Security | 1 | 패키지 서명 및 보안 |
| **Total** | **23** | 전체 의존성 |

### License Distribution

| 라이선스 | 패키지 수 | 패키지 목록 |
|---------|----------|-----------|
| MIT | 14 | pydantic, pyyaml, jsonschema, fastapi, tabulate, setuptools, wheel, pytest, pytest-cov, black, mypy, ruff, build |
| BSD-3-Clause | 4 | click, uvicorn, python-dotenv, jinja2, python-gnupg |
| Apache-2.0 | 5 | watchdog, requests, pytest-asyncio, twine, types-PyYAML |

### All Dependencies Are Open Source

✅ 모든 의존성은 오픈소스이며 상업적 사용이 가능한 허용적(permissive) 라이선스를 사용합니다.

✅ MIT, BSD, Apache 라이선스는 상업적 프로젝트에서 자유롭게 사용 가능합니다.

✅ Pixell Agent Kit (AGPL-3.0)은 이러한 오픈소스 도구들을 기반으로 구축되었습니다.

---

## Installation Commands

### Core Dependencies Only
```bash
pip install pixell-kit
```

### With Development Tools
```bash
pip install pixell-kit[dev]
```

### With Package Signing Support
```bash
pip install pixell-kit[signing]
```

### All Optional Dependencies
```bash
pip install pixell-kit[dev,signing]
```

---

## Version Requirements

모든 패키지는 최소 버전 요구사항을 명시하여 호환성을 보장합니다:

- **Python**: >=3.11 (Python 3.11 이상 필수)
- **Core packages**: 명시된 최소 버전 이상 사용 권장
- **Dev packages**: 최신 버전 사용 권장

---

*Last updated: 2025-01-04*
*Source: pyproject.toml, requirements.txt*
