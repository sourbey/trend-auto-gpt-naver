import os
import sys
import subprocess

# 필요한 패키지들을 자동 설치하는 함수
def install_package(package_name):
    try:
        __import__(package_name)
    except ImportError:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# 모든 필요한 패키지 설치 확인
packages = [
    "python-dotenv",
    "pytrends", 
    "beautifulsoup4",
    "requests",
    "openai",
    "notion-client"
]

for package in packages:
    if package == "python-dotenv":
        try:
            from dotenv import load_dotenv
        except ImportError:
            install_package(package)
            from dotenv import load_dotenv
    elif package == "pytrends":
        try:
            from pytrends.request import TrendReq
        except ImportError:
            install_package(package)
            from pytrends.request import TrendReq
    elif package == "beautifulsoup4":
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            install_package(package)
            from bs4 import BeautifulSoup
    elif package == "requests":
        try:
            import requests
        except ImportError:
            install_package(package)
            import requests
    elif package == "openai":
        try:
            import openai
        except ImportError:
            install_package(package)
            import openai
    elif package == "notion-client":
        try:
            from notion_client import Client
        except ImportError:
            install_package(package)
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
import requests
from bs4 import BeautifulSoup

# 1. 구글 트렌드 키워드 추출 (웹 스크레이핑 버전)
def get_trending_keywords():
    try:
        # 구글 트렌드 '일별' 인기 급상승 검색어 페이지 URL
        url = "https://trends.google.com/trends/trendingsearches/daily?geo=KR"
        
        # 'User-Agent' 헤더를 추가하여 브라우저인 것처럼 요청
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status() # 오류 발생 시 예외를 일으킴

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Google Trends 페이지의 구조를 분석하여 키워드가 담긴 CSS 선택자를 찾음
        # 현재 구조는 list-item-title 클래스 내에 키워드가 있음
        keyword_elements = soup.select("div.list-item-title")
        
        if not keyword_elements:
            print("키워드를 찾을 수 없습니다. Google Trends 페이지 구조가 변경되었을 수 있습니다.")
            raise ValueError("No keywords found")

        # 상위 5개 키워드를 텍스트만 추출하여 리스트로 만듦
        keywords = [elem.get_text(strip=True) for elem in keyword_elements[:5]]
        
        print(f"성공적으로 트렌드 키워드를 가져왔습니다: {keywords}")
        return keywords

    except Exception as e:
        # 에러 발생 시 기존처럼 대체 키워드 사용
        print(f"Google Trends 스크레이핑 오류: {e}")
        print("대체 키워드를 사용합니다.")
        return ["인공지능", "투자", "부동산", "취업", "여행"]

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
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # gpt-4 → gpt-3.5-turbo로 변경
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
