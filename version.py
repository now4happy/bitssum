"""
version.py
무매 V4 버전 관리
"""

VERSION = "4.1.1"
VERSION_NAME = "무매 V4.1.1 완전판"
BUILD_DATE = "2026-04-27"

CHANGELOG = """
V4.1.1 (2026-04-27)
- FIX: /register 명령어 충돌 문제 해결
- FIX: CommandHandler 제거하여 텍스트 핸들러로 통합
- 모든 /register 명령어 정상 작동 보장

V4.1.0 (2026-04-26)
- 버전 관리 시스템 도입
- /balance 명령어 추가
- 좀비봇 지원
- 시드머니 관리 개선
"""

def get_version():
    return f"{VERSION_NAME} (빌드: {BUILD_DATE})"
