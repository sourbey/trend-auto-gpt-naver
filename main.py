# 환경변수 디버깅
print("🔍 환경변수 디버깅:")
print(f"NAVER_CLIENT_ID 존재 여부: {os.getenv('NAVER_CLIENT_ID') is not None}")
print(f"NAVER_CLIENT_SECRET 존재 여부: {os.getenv('NAVER_CLIENT_SECRET') is not None}")
print(f"OPENAI_API_KEY 존재 여부: {os.getenv('OPENAI_API_KEY') is not None}")
print(f"NOTION_TOKEN 존재 여부: {os.getenv('NOTION_TOKEN') is not None}")
print(f"NOTION_DATABASE_ID 존재 여부: {os.getenv('NOTION_DATABASE_ID') is not None}")

# 모든 환경변수 출력 (값은 숨김)
all_env = dict(os.environ)
naver_vars = {k: v for k, v in all_env.items() if 'NAVER' in k}
print(f"네이버 관련 환경변수: {list(naver_vars.keys())}")

import subprocess
import sys

# 패키지 자동 설치
def install_if_missing(package):
    try:
        __import__(package.replace("-", "_"))
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# 필요한 패키지들 설치
packages = ["requests", "python-dotenv", "beautifulsoup4", "openai", "notion-client"]
for pkg in packages:
    install_if_missing(pkg)

import os
import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import openai
from notion_client import Client

# 환경변수 불러오기
#load_dotenv()

# API 키 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID")

# 필수 환경변수 확인
required_vars = {
    "NAVER_CLIENT_ID": NAVER_CLIENT_ID,
    "NAVER_CLIENT_SECRET": NAVER_CLIENT_SECRET,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "NOTION_TOKEN": NOTION_TOKEN,
    "NOTION_DATABASE_ID": NOTION_DB_ID
}

missing_vars = [key for key, value in required_vars.items() if not value]
if missing_vars:
    print(f"❌ 필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
    sys.exit(1)

# 클라이언트 초기화
openai.api_key = OPENAI_API_KEY
notion = Client(auth=NOTION_TOKEN)

print("✅ 모든 환경변수가 정상적으로 로드되었습니다.")

# 1. 네이버 데이터랩 API로 실시간 트렌드 키워드 가져오기
def get_trending_keywords():
    try:
        url = "https://openapi.naver.com/v1/datalab/search"
        headers = {
            'X-Naver-Client-Id': NAVER_CLIENT_ID,
            'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
            'Content-Type': 'application/json'
        }
        
        # 현재 날짜 기준으로 최근 30일간 데이터 요청
        end_date = datetime.date.today().strftime('%Y-%m-%d')
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 인기 검색 카테고리들
        categories = ["인공지능", "투자", "부동산", "취업", "여행"]
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date",
            "keywordGroups": [
                {
                    "groupName": category,
                    "keywords": [category]
                } for category in categories
            ]
        }
        
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            data = response.json()
            # 검색량이 높은 순으로 정렬
            keywords = [group['title'] for group in data['results']]
            print(f"✅ 네이버 데이터랩에서 키워드 수집 완료: {keywords}")
            return keywords[:5]  # 상위 5개만 반환
        else:
            print(f"❌ 네이버 데이터랩 API 오류: {response.status_code}")
            raise Exception("API 호출 실패")
            
    except Exception as e:
        print(f"❌ 네이버 데이터랩 오류: {e}")
        # 백업 키워드 사용
        backup_keywords = ["인공지능", "투자", "부동산", "취업", "여행"]
        print(f"🔄 백업 키워드 사용: {backup_keywords}")
        return backup_keywords

# 2. 구글에서 키워드 관련 정보 수집
def collect_google_data(keyword):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        # 구글 검색
        search_url = f"https://www.google.com/search?q={keyword}"
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 검색 결과 타이틀 수집
        titles = []
        for result in soup.find_all('h3', limit=5):
            if result.text:
                titles.append(result.text)
        
        # 구글 뉴스 검색
        news_url = f"https://www.google.com/search?q={keyword}&tbm=nws"
        news_response = requests.get(news_url, headers=headers)
        news_soup = BeautifulSoup(news_response.text, 'html.parser')
        
        # 뉴스 제목 수집
        news_titles = []
        for news in news_soup.find_all('h3', limit=3):
            if news.text:
                news_titles.append(news.text)
        
        collected_data = {
            'search_results': titles,
            'news_results': news_titles
        }
        
        print(f"✅ '{keyword}' 구글 데이터 수집 완료")
        return collected_data
        
    except Exception as e:
        print(f"❌ '{keyword}' 구글 데이터 수집 실패: {e}")
        return {'search_results': [], 'news_results': []}

# 3. GPT로 데이터 분석
def analyze_with_gpt(keyword, google_data):
    try:
        search_text = " / ".join(google_data['search_results'])
        news_text = " / ".join(google_data['news_results'])
        
        prompt = f"""
다음은 '{keyword}' 키워드에 대한 구글 검색 및 뉴스 데이터입니다:

검색 결과: {search_text}
뉴스 결과: {news_text}

위 데이터를 분석하여 다음 형식으로 답변해주세요:
니즈: [이 트렌드가 반영하는 소비자 니즈나 심리적 욕구]
요약: [마케팅 인사이트 1-2줄 요약]
전망: [향후 트렌드 전망]
"""
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 트렌드 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ '{keyword}' GPT 분석 완료")
        return result
        
    except Exception as e:
        print(f"❌ '{keyword}' GPT 분석 실패: {e}")
        return f"니즈: 분석 실패\n요약: {keyword}에 대한 분석을 완료하지 못했습니다.\n전망: 추후 재분석 필요"

# 4. 노션에 결과 업로드
def upload_to_notion(keyword, analysis_result):
    try:
        today = datetime.date.today().isoformat()
        
        # 분석 결과 파싱
        lines = analysis_result.split('\n')
        parsed_data = {"키워드": keyword, "날짜": today}
        
        for line in lines:
            if line.startswith("니즈:"):
                parsed_data["니즈"] = line.replace("니즈:", "").strip()
            elif line.startswith("요약:"):
                parsed_data["요약"] = line.replace("요약:", "").strip()
            elif line.startswith("전망:"):
                parsed_data["전망"] = line.replace("전망:", "").strip()
        
        # 노션 페이지 생성
        notion.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "키워드": {"title": [{"text": {"content": parsed_data["키워드"]}}]},
                "날짜": {"date": {"start": parsed_data["날짜"]}},
                "니즈": {"rich_text": [{"text": {"content": parsed_data.get("니즈", "")}}]},
                "요약": {"rich_text": [{"text": {"content": parsed_data.get("요약", "")}}]},
                "전망": {"rich_text": [{"text": {"content": parsed_data.get("전망", "")}}]},
            },
        )
        
        print(f"✅ '{keyword}' 노션 업로드 완료")
        
    except Exception as e:
        print(f"❌ '{keyword}' 노션 업로드 실패: {e}")

# 5. 전체 프로세스 실행
def main():
    print("🚀 트렌드 분석 시작...")
    
    # 1. 트렌드 키워드 수집
    keywords = get_trending_keywords()
    
    # 2. 각 키워드별 분석
    for keyword in keywords:
        print(f"\n📊 '{keyword}' 분석 중...")
        
        # 구글 데이터 수집
        google_data = collect_google_data(keyword)
        
        # GPT 분석
        analysis = analyze_with_gpt(keyword, google_data)
        
        # 노션 업로드
        upload_to_notion(keyword, analysis)
        
        print(f"✅ '{keyword}' 분석 완료")
    
    print("\n🎉 모든 트렌드 분석이 완료되었습니다!")

if __name__ == "__main__":
    main()
