"""
YouTubeで急成長している動画を検索するシステム
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import googleapiclient.discovery
from googleapiclient.errors import HttpError
import config


class YouTubeTrendingFinder:
    """YouTubeで急成長している動画を検索するクラス"""
    
    def __init__(self, api_key: str):
        """
        初期化
        
        Args:
            api_key: YouTube Data API v3のAPIキー
        """
        self.api_key = api_key
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=api_key
        )
        self.trending_period = timedelta(days=config.TRENDING_PERIOD_DAYS)
    
    def search_videos(self, keyword: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> List[Dict]:
        """
        キーワードで動画を検索
        
        Args:
            keyword: 検索キーワード
            max_results: 取得する動画の最大数
            
        Returns:
            動画情報のリスト
        """
        try:
            # 検索リクエスト
            published_after = (datetime.now(timezone.utc) - self.trending_period).isoformat().replace("+00:00", "Z")
            search_response = self.youtube.search().list(
                q=keyword,
                part="id,snippet",
                type="video",
                maxResults=max_results,
                order="relevance",  # 関連度順
                publishedAfter=published_after
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            
            if not video_ids:
                return []
            
            # 動画の詳細情報を取得（再生回数など）
            videos_response = self.youtube.videos().list(
                part="statistics,snippet,contentDetails",
                id=",".join(video_ids)
            ).execute()
            
            videos = []
            for video in videos_response.get("items", []):
                video_info = {
                    "video_id": video["id"],
                    "title": video["snippet"]["title"],
                    "channel_title": video["snippet"]["channelTitle"],
                    "published_at": video["snippet"]["publishedAt"],
                    "view_count": int(video["statistics"].get("viewCount", 0)),
                    "like_count": int(video["statistics"].get("likeCount", 0)),
                    "duration": video["contentDetails"]["duration"],
                    "url": f"https://www.youtube.com/watch?v={video['id']}"
                }
                videos.append(video_info)
            
            return videos
            
        except HttpError as e:
            print(f"YouTube APIエラーが発生しました: {e}")
            return []
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return []
    
    def calculate_trending_score(self, video: Dict) -> float:
        """
        動画の急成長スコアを計算
        
        Args:
            video: 動画情報の辞書
            
        Returns:
            急成長スコア（高いほど急成長している）
        """
        published_at = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_since_published = (now - published_at).total_seconds() / 86400  # 日数に変換
        
        # 公開から0日未満の場合はスキップ
        if days_since_published < 0:
            return 0
        
        # 公開から2週間を超えている場合は除外
        if days_since_published > config.TRENDING_PERIOD_DAYS:
            return 0
        
        view_count = video["view_count"]
        
        # 1日あたりの再生回数でスコアを計算
        # より最近公開された動画ほど、同じ再生回数でも高いスコアになる
        if days_since_published < 1:
            days_since_published = 1  # 0除算を防ぐ
        
        views_per_day = view_count / days_since_published
        
        # スコア計算：1日あたりの再生回数 × 公開からの日数の逆数（新しいほど高得点）
        # さらに総再生回数も考慮
        trending_score = views_per_day * (1 + view_count / 10000)
        
        return trending_score
    
    def find_trending_videos(self, keyword: str, max_results: int = config.DEFAULT_MAX_RESULTS, 
                             min_trending_score: float = 1000) -> List[Dict]:
        """
        急成長している動画を検索してソート
        
        Args:
            keyword: 検索キーワード
            max_results: 取得する動画の最大数
            min_trending_score: 最小の急成長スコア（フィルタリング用）
            
        Returns:
            急成長スコアでソートされた動画リスト
        """
        videos = self.search_videos(keyword, max_results)
        
        # 各動画に急成長スコアを追加
        for video in videos:
            video["trending_score"] = self.calculate_trending_score(video)
        
        # 急成長スコアでソート（降順）
        trending_videos = sorted(
            [v for v in videos if v["trending_score"] >= min_trending_score],
            key=lambda x: x["trending_score"],
            reverse=True
        )
        
        return trending_videos


def format_duration(duration_str: str) -> str:
    """
    ISO 8601形式の期間を読みやすい形式に変換
    
    Args:
        duration_str: ISO 8601形式の期間文字列（例: PT1H2M10S）
        
    Returns:
        読みやすい形式（例: 1時間2分10秒）
    """
    import re
    
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return duration_str
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}時間")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if seconds > 0:
        parts.append(f"{seconds}秒")
    
    return "".join(parts) if parts else "0秒"


def display_results(videos: List[Dict]):
    """
    検索結果を表示
    
    Args:
        videos: 動画情報のリスト
    """
    if not videos:
        print("\n急成長している動画が見つかりませんでした。")
        return
    
    print(f"\n{'='*80}")
    print(f"急成長している動画: {len(videos)}件")
    print(f"{'='*80}\n")
    
    for i, video in enumerate(videos, 1):
        published_at = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
        days_ago = (datetime.now(published_at.tzinfo) - published_at).days
        
        print(f"{i}. {video['title']}")
        print(f"   チャンネル: {video['channel_title']}")
        print(f"   再生回数: {video['view_count']:,}回")
        print(f"   いいね数: {video['like_count']:,}回")
        print(f"   公開日: {published_at.strftime('%Y年%m月%d日')} ({days_ago}日前)")
        print(f"   動画時間: {format_duration(video['duration'])}")
        print(f"   急成長スコア: {video['trending_score']:.2f}")
        print(f"   URL: {video['url']}")
        print()


def main():
    """メイン関数"""
    api_key = config.YOUTUBE_API_KEY
    
    if not api_key:
        print("エラー: YouTube APIキーが設定されていません。")
        print(".envファイルにYOUTUBE_API_KEYを設定してください。")
        return
    
    finder = YouTubeTrendingFinder(api_key)
    
    print("YouTube急成長動画検索システム")
    print("=" * 50)
    
    keyword = input("\n検索キーワードを入力してください: ").strip()
    
    if not keyword:
        print("キーワードが入力されていません。")
        return
    
    print(f"\n「{keyword}」で検索中...")
    
    trending_videos = finder.find_trending_videos(keyword)
    
    display_results(trending_videos)


if __name__ == "__main__":
    main()
