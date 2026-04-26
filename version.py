"""
version.py
무매 V4 버전 관리
"""

VERSION = "4.1.0"
VERSION_NAME = "무매 V4.1.0 완전판"
BUILD_DATE = "2026-04-26"

def get_version():
    return f"{VERSION_NAME} (빌드: {BUILD_DATE})"
