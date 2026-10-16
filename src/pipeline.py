import json
from config import GEMINI_KEY, RESEND_KEY, RECIPIENT_EMAIL, load_channels, load_portfolio
from youtube import fetch_youtube_transcripts
from dataroma import fetch_dataroma_moves
from ai_service import AIService
from mailer import Mailer

def run_pipeline():
    channels = load_channels()
    portfolio_str = load_portfolio()
    yt_data = fetch_youtube_transcripts(channels)
    dataroma_data = fetch_dataroma_moves()

    system_instruction = (
        "You are an executive intelligence analyst. Strip clickbait. "
        "Filter for durable tech architecture and verifiable economic moats."
    )

    prompt = f"""
    Create a clean, 5-minute morning intelligence brief.
    ### INPUT 1: PORTFOLIO
    {portfolio_str}
    ### INPUT 2: 13F ACTIVITY
    {dataroma_data}
    ### INPUT 3: YOUTUBE
    {json.dumps(yt_data)}
    
    Format in Markdown:
    1. **AI & Tech Architecture Radar (Max 3 Bullets)**
    2. **Portfolio Guard**
    3. **Screened Ideas (Markdown Table)**
    4. **Morningstar Candidates**
    """

    ai = AIService(api_key=GEMINI_KEY)
    analysis = ai.generate_briefing(prompt, system_instruction)

    mailer = Mailer(api_key=RESEND_KEY)
    mailer.send_digest(recipient_email=RECIPIENT_EMAIL, markdown_content=analysis)
    print("Pipeline run completed.")

if __name__ == "__main__":
    run_pipeline()
