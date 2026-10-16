import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

TARGET_LANGUAGES = ['en', 'en-US', 'en-GB', 'no', 'nb', 'nn', 'de', 'es', 'fr']

def fetch_youtube_transcripts(channels: list, max_videos_per_channel: int = 2) -> list:
    extracted = []
    for ch in channels:
        channel_id = ch.get("channel_id")
        if not channel_id:
            continue

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)
        videos_found = 0

        for entry in feed.entries[:6]:
            if videos_found >= max_videos_per_channel:
                break
            video_id = entry.get("yt_videoid")
            if not video_id:
                continue
            try:
                chunks = YouTubeTranscriptApi.get_transcript(video_id, languages=TARGET_LANGUAGES)
                full_text = " ".join([c["text"] for c in chunks if "text" in c])
                if len(full_text.strip()) > 100:
                    extracted.append({
                        "channel": ch.get("name", "Unknown"),
                        "title": getattr(entry, "title", "Untitled"),
                        "transcript": full_text[:12000]
                    })
                    videos_found += 1
            except Exception:
                continue
    return extracted
