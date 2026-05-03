"""
version.py
무매 (무한매수법) V5.0
"""

VERSION = "5.0.0"
VERSION_NAME = "무매 V5.0"
BUILD_DATE = "2026-05-03"

CHANGELOG = """
V5.0.0 (2026-05-03) - 새 출발
- 완전히 새로운 코드베이스
- 첫 매수 시장가 자동 진입
- 소수점 10자리 수량 처리
- 시드머니 50만원 ~ 5천만원
- BTC/ETH 전용
- 불필요한 요소 제거 (RP 등)
- 간소화된 UI
- 백테스팅 검증 완료 (+7.15% 수익)
"""

def get_version():
    return f"{VERSION_NAME} (빌드: {BUILD_DATE})"

def get_changelog():
    return CHANGELOG
