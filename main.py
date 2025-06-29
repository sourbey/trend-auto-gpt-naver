import os
from dotenv import load_dotenv
from pytrends.request import TrendReq
from bs4 import BeautifulSoup
import requests
import openai
from notion_client import Client
import datetime

# 환경변수 불러오기
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID")

openai.api_key = OPENAI_API_KEY
notion = Client(auth=NOTION_TOKEN)

# 1. 구글 트렌드 키워드 추출
def get_trending_keywords():
    pytrends = TrendReq(hl='ko', tz=540)
    pytrends.build_payload(kw_list=[""], cat=0, timeframe='now 1-d', geo='KR')
    trending_searches = pytrends.trending_searches(pn='south_korea')
    return trending_searches[0:5][0].tolist()

# 2. 네이버 블로그 VIEW 탭에서 내용 수집
def crawl_naver_blog(keyword):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://search.naver.com/search.naver?where=view&query={keyword}"
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select(".title_link")
    summaries = [item.get_text() for item in items[:3]]
    return " / ".join(summaries)

# 3. GPT로 요약 및 니즈 분류
def analyze_with_gpt(keyword, blog_summary):
    prompt = f"""
다음은 '{keyword}' 관련 블로그 내용 요약이야:
\"{blog_summary}\"

위 내용을 기반으로
1. 이 트렌드가 어떤 '소비자 니즈' 또는 '심리적 욕구'를 반영하는지 분석하고,
2. 마케팅 인사이트 1~2줄로 요약해줘.
결과는 '니즈: ..., 요약: ...' 형식으로 줘.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "트렌드 분석 전문가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# 4. 노션 DB에 업로드
def upload_to_notion(keyword, result):
    today = datetime.date.today().isoformat()
    parsed = {"키워드": keyword, "날짜": today}
    for line in result.split("\n"):
        if "니즈:" in line:
            parsed["니즈"] = line.replace("니즈:", "").strip()
        elif "요약:" in line:
            parsed["요약"] = line.replace("요약:", "").strip()

    notion.pages.create(
        parent={"database_id": NOTION_DB_ID},
        properties={
            "키워드": {"title": [{"text": {"content": parsed["키워드"]}}]},
            "날짜": {"date": {"start": parsed["날짜"]}},
            "니즈": {"rich_text": [{"text": {"content": parsed.get("니즈", "")}}]},
            "요약": {"rich_text": [{"text": {"content": parsed.get("요약", "")}}]},
        },
    )

# 전체 자동 실행
def main():
    keywords = get_trending_keywords()
    for kw in keywords:
        blog = crawl_naver_blog(kw)
        result = analyze_with_gpt(kw, blog)
        upload_to_notion(kw, result)

if __name__ == "__main__":
    main()
