"""Gemini AI news summarizer with investment relevance scoring."""
import os
import json
import logging
from typing import Optional
import google.generativeai as genai

from app.services.rss_collector import RSSArticle

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

SUMMARIZE_PROMPT = """
You are a financial news analyst. Summarize the following news article and rate its investment relevance.

Title: {title}
Content: {content}

Respond ONLY with a valid JSON object:
{{
  "summary": "<2-3 sentence summary in Korean>",
  "investment_score": <integer 1-10>,
  "sentiment": "positive" | "negative" | "neutral",
  "key_sectors": ["<sector1>", "<sector2>"],
  "keywords": ["<kw1>", "<kw2>", "<kw3>"]
}}
"""


class NewsSummarizer:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model = genai.GenerativeModel(model_name)

    async def summarize(self, article: RSSArticle) -> Optional[dict]:
        """Summarize article and assign investment relevance score."""
        content = article.summary or article.title
        prompt = SUMMARIZE_PROMPT.format(title=article.title, content=content[:2000])
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            return json.loads(text)
        except Exception as exc:
            logger.error("Summarization failed for '%s': %s", article.title, exc)
            return {
                "summary": article.summary[:300] if article.summary else article.title,
                "investment_score": 5,
                "sentiment": "neutral",
                "key_sectors": [],
                "keywords": [],
            }

    async def summarize_batch(self, articles: list[RSSArticle]) -> list[dict]:
        """Summarize a list of articles sequentially to respect rate limits."""
        import asyncio
        results = []
        for article in articles:
            result = await self.summarize(article)
            results.append(result)
            await asyncio.sleep(0.5)  # avoid rate limit
        return results


news_summarizer = NewsSummarizer()
