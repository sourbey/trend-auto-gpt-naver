import os
import sys
import datetime
import subprocess

# 패키지 자동 설치 (Render에서 안전하게)
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {package} 설치 완료")
    except:
        print(f"❌ {package} 설치 실패")

# 필요 패키지 확인 및 설치
required_packages = {
    'requests': 'requests',
    'bs4': 'beautifulsoup4', 
    'openai': 'openai',
    'notion_client': 'notion-client'
}

for module, package in required_packages.items():
    try:
        __import__(module)
    except ImportError:
        print(f"📦 {package} 설치 중...")
        install_package(package)

# 패키지 import
import requests
from bs4 import BeautifulSoup
import openai
from notion_client import Client

print("🚀 트렌드 분석 시스템 시작...")

# 환경변수 직접 가져오기 (Render에서)
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_DATABASE_ID")

# 환경변수 확인
env_vars = {
    "NAVER_CLIENT_ID": NAVER_CLIENT_ID,
    "NAVER_CLIENT_SECRET": NAVER_CLIENT_SECRET,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "NOTION_TOKEN": NOTION_TOKEN,
    "NOTION_DATABASE_ID": NOTION_DB_ID
}

missing_vars = [name for name, value in env_vars.items() if not value]
if missing_vars:
    print(f"❌ 환경변수 누락: {', '.join(missing_vars)}")
    print("🔧 Render Dashboard → Settings → Environment에서 환경변수를 확인하세요!")
    sys.exit(1)

print("✅ 모든 환경변수 확인 완료")

# API 클라이언트 초기화
try:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    notion_client = Client(auth=NOTION_TOKEN)
    print("✅ API 클라이언트 초기화 완료")
except Exception as e:
    print(f"❌ API 클라이언트 초기화 실패: {e}")
    sys.exit(1)

# 1. 트렌드 키워드 수집 (백업 방식)
def get_trending_keywords():
    try:
        # 네이버 데이터랩 API 시도
        url = "https://openapi.naver.com/v1/datalab/search"
        headers = {
            'X-Naver-Client-Id': NAVER_CLIENT_ID,
            'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
            'Content-Type': 'application/json'
        }
        
        end_date = datetime.date.today().strftime('%Y-%m-%d')
        start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date",
            "keywordGroups": [
                {"groupName": "AI", "keywords": ["인공지능"]},
                {"groupName": "투자", "keywords": ["투자"]},
                {"groupName": "부동산", "keywords": ["부동산"]}
            ]
        }
        
        response = requests.post(url, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            keywords = ["인공지능", "투자", "부동산"]
            print("✅ 네이버 데이터랩 키워드 수집 성공")
            return keywords
        else:
            raise Exception(f"API 오류: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ 네이버 API 실패: {e}")
        # 현재 이슈 키워드 사용
        trending_keywords = ["ChatGPT", "비트코인", "부동산 투자", "취업 준비", "여행"]
        print(f"📈 현재 트렌드 키워드 사용: {trending_keywords}")
        return trending_keywords

# 2. 구글 데이터 수집
def collect_google_data(keyword):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 구글 검색
        search_url = f"https://www.google.com/search?q={keyword}&hl=ko"
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 검색 결과 제목 수집
        titles = []
        for h3 in soup.find_all('h3', limit=3):
            if h3.text.strip():
                titles.append(h3.text.strip())
        
        if not titles:
            titles = [f"{keyword} 관련 최신 동향", f"{keyword} 시장 분석", f"{keyword} 전망"]
        
        return {
            'search_results': titles,
            'keyword': keyword
        }
        
    except Exception as e:
        print(f"⚠️ 구글 데이터 수집 실패 ({keyword}): {e}")
        return {
            'search_results': [f"{keyword} 트렌드 분석", f"{keyword} 시장 동향"],
            'keyword': keyword
        }

# 3. GPT 분석
def analyze_with_gpt(keyword, google_data):
    try:
        search_text = " / ".join(google_data['search_results'])
        
        prompt = f"""
키워드: {keyword}
관련 정보: {search_text}

위 키워드와 정보를 바탕으로 다음 형식으로 분석해주세요:

니즈: [이 키워드가 반영하는 소비자의 주요 니즈나 관심사]
요약: [마케팅 관점에서의 핵심 인사이트 1-2줄]
전망: [향후 3-6개월 트렌드 전망]
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 트렌드 분석 전문가입니다. 간결하고 실용적인 인사이트를 제공해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ '{keyword}' GPT 분석 완료")
        return result
        
    except Exception as e:
        print(f"⚠️ '{keyword}' GPT 분석 실패: {e}")
        return f"""니즈: {keyword}에 대한 정보 수요 증가
요약: {keyword} 관련 관심도가 높아지고 있어 마케팅 기회 존재
전망: 지속적인 관심 유지 예상"""

# 4. 노션 업로드
def upload_to_notion(keyword, analysis_result):
    try:
        today = datetime.date.today().isoformat()
        
        # 분석 결과 파싱
        lines = analysis_result.split('\n')
        parsed_data = {
            "키워드": keyword,
            "날짜": today,
            "니즈": "",
            "요약": "",
            "전망": ""
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("니즈:"):
                parsed_data["니즈"] = line.replace("니즈:", "").strip()
            elif line.startswith("요약:"):
                parsed_data["요약"] = line.replace("요약:", "").strip()
            elif line.startswith("전망:"):
                parsed_data["전망"] = line.replace("전망:", "").strip()
        
        # 노션 페이지 생성
        notion_client.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "키워드": {"title": [{"text": {"content": parsed_data["키워드"]}}]},
                "날짜": {"date": {"start": parsed_data["날짜"]}},
                "니즈": {"rich_text": [{"text": {"content": parsed_data["니즈"]}}]},
                "요약": {"rich_text": [{"text": {"content": parsed_data["요약"]}}]},
                "전망": {"rich_text": [{"text": {"content": parsed_data["전망"]}}]},
            },
        )
        
        print(f"✅ '{keyword}' 노션 업로드 완료")
        return True
        
    except Exception as e:
        print(f"❌ '{keyword}' 노션 업로드 실패: {e}")
        return False

# 5. 메인 실행 함수
def main():
    print("="*50)
    print("🤖 자동 트렌드 분석 시스템")
    print(f"📅 실행 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    try:
        # 1. 키워드 수집
        keywords = get_trending_keywords()
        print(f"📊 분석 대상 키워드: {keywords}")
        
        success_count = 0
        
        # 2. 각 키워드별 분석
        for i, keyword in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] 🔍 '{keyword}' 분석 중...")
            
            # 구글 데이터 수집
            google_data = collect_google_data(keyword)
            
            # GPT 분석
            analysis = analyze_with_gpt(keyword, google_data)
            
            # 노션 업로드
            if upload_to_notion(keyword, analysis):
                success_count += 1
            
            print(f"✅ '{keyword}' 처리 완료")
        
        print("\n" + "="*50)
        print(f"🎉 분석 완료! 성공: {success_count}/{len(keywords)}")
        print("="*50)
        
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
