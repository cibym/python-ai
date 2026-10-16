import os
import json
import csv
import time
import requests
import feedparser
import markdown
import resend
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

# 1. Environment Secrets
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
RESEND_KEY = os.environ.get("RESEND_API_KEY")
RECIPIENT_EMAIL = os.environ.get("MY_EMAIL")

if not all([GEMINI_KEY, RESEND_KEY, RECIPIENT_EMAIL]):
    raise ValueError("Missing one or more environment variables: GEMINI_API_KEY, RESEND_API_KEY, MY_EMAIL")

client = genai.Client(api_key=GEMINI_KEY)
resend.api_key = RESEND_KEY

def load_config():
    with open("config/channels.json", "r") as f:
        channels = json.load(f)

    portfolio_items = []
    if os.path.exists("config/portfolio.csv"):
        with open("config/portfolio.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                portfolio_items.append(f"{row['ticker']} ({row['name']})")

    return channels, ", ".join(portfolio_items)

def fetch_youtube_transcripts(channels):
    extracted = []
    target_languages = ['en', 'en-US', 'en-GB', 'no', 'nb', 'nn', 'de', 'es', 'fr']
    
    for ch in channels:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}"
        feed = feedparser.parse(feed_url)
        
        channel_videos_found = 0
        for entry in feed.entries[:6]:
            if channel_videos_found >= 2:
                break
                
            video_id = entry.get("yt_videoid")
            if not video_id:
                continue

            try:
                # get_transcript supports specifying language priority
                chunks = YouTubeTranscriptApi.get_transcript(video_id, languages=target_languages)
                full_text = " ".join([c["text"] for c in chunks if "text" in c])

                if len(full_text.strip()) > 100:
                    extracted.append({
                        "channel": ch.get("name", "Unknown Channel"),
                        "category": ch.get("category", "General"),
                        "title": entry.title,
                        "link": entry.link,
                        "transcript": full_text[:12000]
                    })
                    channel_videos_found += 1
                    print(f"✓ Extracted: [{ch.get('name')}] {entry.title[:45]}")
            except Exception as e:
                # Continue gracefully if no captions exist in targeted languages
                continue

    print(f"\nTotal video transcripts passed to Gemini: {len(extracted)}")
    return extracted

def fetch_dataroma_moves():
    """Scrapes top recent buys and sells from superinvestor 13F filings."""
    url = "https://www.dataroma.com/m/allact.php?typ=a"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "grid"})
        rows = []
        if table:
            for tr in table.find_all("tr")[1:12]:
                cols = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(cols) >= 4:
                    rows.append(f"{cols[0]} | Stock: {cols[1]} | Action: {cols[2]} | Shares/Pct: {cols[3]}")
        return "\n".join(rows)
    except Exception as e:
        return f"Dataroma scrape bypassed: {e}"

def generate_with_fallback(prompt, system_instruction):
    """
    Cycles through valid model names with exponential backoff on 503 high-demand errors.
    """
    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]
    config = types.GenerateContentConfig(system_instruction=system_instruction)

    for model_name in candidate_models:
        for attempt in range(3):
            try:
                print(f"Generating brief using {model_name} (attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                return response
            except ServerError as e:
                wait_time = (attempt + 1) * 10
                print(f"Server demand spike (503) on {model_name}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            except ClientError as e:
                print(f"ClientError on {model_name} (status {getattr(e, 'code', 'unknown')}). Skipping model...")
                break
            except Exception as e:
                print(f"Error on {model_name}: {e}. Retrying in 5s...")
                time.sleep(5)

    raise RuntimeError("All configured Gemini models failed. Verify API key and model access in AI Studio.")

def run_analysis_and_send():
    channels, portfolio_str = load_config()
    yt_data = fetch_youtube_transcripts(channels)
    dataroma_data = fetch_dataroma_moves()

    system_instruction = (
        "You are an executive intelligence analyst for a Senior Java/AI Engineer managing a long-term "
        "wealth portfolio. Strip all clickbait, hype, promotional sponsors, and speculative price predictions. "
        "Filter for durable tech architecture and verifiable economic moats."
    )

    prompt = f"""
    Create a clean, 5-minute morning intelligence brief using the following inputs:

    ### INPUT 1: USER'S NORDNET PORTFOLIO HOLDINGS
    {portfolio_str if portfolio_str else "No holdings specified."}

    ### INPUT 2: RECENT 13F SUPERINVESTOR ACTIVITY (DATAROMA)
    {dataroma_data}

    ### INPUT 3: YOUTUBE TRANSCRIPTS (TECH & FINANCE)
    {json.dumps(yt_data)}

    Structure the response strictly in Markdown with these 4 sections:
    1. **AI & Tech Architecture Radar (Max 3 Bullets):** Concrete engineering/framework insights (Spring AI, RAG patterns, latency, model benchmarks).
    2. **Nordnet Portfolio Guard:** If any of the user's current holdings face material moat threats, regulatory disruption, or heavy institutional selling, flag it here. If everything looks stable, output exactly: `Status: Nominal — No Action Required.`
    3. **Screened Ideas & Institutional Cross-Check (Markdown Table):**
       - Columns: Ticker | Catalyst / Thesis | Downside Risk | Dataroma Smart Money Status
    4. **Morningstar Verification Candidates:**
       - Name at most 1–2 candidates possessing Wide/Narrow moats worth manually checking on Morningstar for a Price/Fair Value discount. If none qualify, write `None today — stick to core ETF contributions.`
    """

    response = generate_with_fallback(prompt, system_instruction)

    # Convert Markdown to HTML
    html_content = markdown.markdown(response.text, extensions=['tables'])

    styled_email = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 680px; margin: 0 auto; padding: 24px 16px; background-color: #f8fafc; }}
        .card {{ background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        h1 {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
        h2, h3 {{ font-size: 16px; font-weight: 600; color: #1e293b; margin-top: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
        th {{ background-color: #f1f5f9; font-weight: 600; }}
        ul {{ padding-left: 18px; }}
        li {{ margin-bottom: 6px; font-size: 14px; }}
        p {{ font-size: 14px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h1>☕ Daily Tech & Market Pulse</h1>
        {html_content}
      </div>
    </body>
    </html>
    """

    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": RECIPIENT_EMAIL,
        "subject": "☕ Daily Market & Tech Pulse",
        "html": styled_email
    })
    print("Morning briefing successfully generated and emailed.")

if __name__ == "__main__":
    run_analysis_and_send()
