"""
設定ファイル
"""
import os
from dotenv import load_dotenv

load_dotenv()

# YouTube Data API v3 のAPIキー
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# 検索設定
DEFAULT_MAX_RESULTS = 50  # 一度に取得する動画数
TRENDING_PERIOD_DAYS = 14  # 急成長を判定する期間（日数）
