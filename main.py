import os
import sys
import json
import time
import datetime
import requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import openai
from notion_client import Client

# 환경변수 로드
load_dotenv()

# API 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET") 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID")

# 클라이언트 초기화
openai.api_key = OPENAI_API_KEY
notion = Client(auth=NOTION_TOKEN)

class TrendAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_naver_trending_keywords(self) -> List[str]:
        """네이버 데이터랩 API로 실시간 트렌드 키워드 수집"""
        try:
            # 네이버 데이터랩 실시간 급상승 검색어 API
            url = "https://openapi.naver.com/v1/datalab/search"
            
            headers = {
                'X-Naver-Client-Id': NAVER_CLIENT_ID,
                'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
                'Content-Type': 'application/json'
            }
            
            # 최근 7일간 인기 검색어 요청
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=7)
            
            body = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "timeUnit": "date",
                "keywordGroups": [
                    {"groupName": "트렌드", "keywords": ["트렌드"]}
                ]
            }
            
            response = self.session.post(url, headers=headers, data=json.dumps(body))
            
            if response.status_code == 200:
                # API 응답에서 키워드 추출 로직
                # 실제로는 더 복잡한 파싱이 필요할 수 있음
                print("네이버 데이터랩 API 호출 성공")
                
                # 대안: 네이버 실시간 검색어 페이지 크롤링
                return self.crawl_naver_realtime_keywords()
            else:
                print(f"API 호출 실패: {response.status_code}")
                return self.get_fallback_keywords()
                
        except Exception as e:
            print(f"네이버 API 오류: {e}")
            return self.get_fallback_keywords()
    
    def crawl_naver_realtime_keywords(self) -> List[str]:
        """네이버 실시간 검색어 크롤링 (대안)"""
        try:
            # 네이버 데이터랩 키워드 페이지
            url = "https://datalab.naver.com/keyword/realtimeList.naver?where=main"
            
            response = self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 실시간 검색어 추출 (CSS 선택자는 페이지 구조에 따라 조정 필요)
            keywords = []
            keyword_elements = soup.select('.keyword_rank li .title')
            
            if keyword_elements:
                keywords = [elem.get_text(strip=True) for elem in keyword_elements[:10]]
            
            if keywords:
                print(f"네이버 실시간 키워드 수집 성공: {keywords[:5]}")
                return keywords[:5]
            else:
                return self.get_fallback_keywords()
                
        except Exception as e:
            print(f"네이버 크롤링 오류: {e}")
            return self.get_fallback_keywords()
    
    def get_fallback_keywords(self) -> List[str]:
        """백업 키워드 (API 실패시 사용)"""
        fallback = [
            "인공지능 ChatGPT", 
            "부동산 투자", 
            "취업 준비", 
            "건강 관리",
            "여행 계획"
        ]
        print(f"백업 키워드 사용: {fallback}")
        return fallback
    
    def search_google_content(self, keyword: str) -> Dict[str, Any]:
        """구글에서 키워드 관련 정보 검색"""
        try:
            # 구글 검색 URL 구성
            search_url = f"https://www.google.com/search?q={keyword}&num=10&hl=ko"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
            }
            
            response = self.session.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 검색 결과 추출
            results = []
            search_results = soup.select('div.g')
            
            for result in search_results[:5]:
                title_elem = result.select_one('h3')
                snippet_elem = result.select_one('.VwiC3b, .s3v9rd')
                link_elem = result.select_one('a')
                
                if title_elem and snippet_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'snippet': snippet_elem.get_text(strip=True),
                        'link': link_elem.get('href') if link_elem else ''
                    })
            
            # 연관 검색어 추출
            related_searches = []
            related_elements = soup.select('.s75CSd .sATSHe')
            for elem in related_elements[:5]:
                related_searches.append(elem.get_text(strip=True))
            
            return {
                'keyword': keyword,
                'results': results,
                'related_searches': related_searches,
                'total_results': len(results)
            }
            
        except Exception as e:
            print(f"구글 검색 오류 ({keyword}): {e}")
            return {
                'keyword': keyword,
                'results': [],
                'related_searches': [],
                'total_results': 0
            }
    
    def analyze_with_gpt(self, keyword: str, search_data: Dict[str, Any]) -> Dict[str, str]:
        """GPT로 트렌드 분석"""
        try:
            # 검색 결과를 문자열로 정리
            content_summary = ""
            for result in search_data['results']:
                content_summary += f"제목: {result['title']}\n내용: {result['snippet']}\n\n"
            
            related_info = ", ".join(search_data['related_searches'])
            
            # GPT 프롬프트 구성
            prompt = f"""
다음은 '{keyword}' 키워드에 대한 최신 검색 정보입니다:

=== 검색 결과 ===
{content_summary}

=== 연관 검색어 ===
{related_info}

위 정보를 바탕으로 다음을 분석해주세요:

1. **트렌드 배경**: 이 키워드가 왜 인기를 끌고 있는지
2. **소비자 니즈**: 사람들이 이 키워드를 통해 얻으려는 정보나 해결하려는 문제
3. **마케팅 인사이트**: 비즈니스나 마케팅 관점에서의 활용 방안
4. **향후 전망**: 이 트렌드의 지속성과 발전 방향

각 항목을 2-3줄로 간결하게 정리해주세요.
"""

            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 트렌드 분석 전문가입니다. 데이터를 바탕으로 명확하고 실용적인 인사이트를 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content.strip()
            
            # 분석 결과 파싱
            analysis_dict = {
                'keyword': keyword,
                'full_analysis': analysis,
                'trend_background': '',
                'consumer_needs': '',
                'marketing_insights': '',
                'future_outlook': ''
            }
            
            # 간단한 파싱 (실제로는 더 정교한 파싱 필요)
            lines = analysis.split('\n')
            current_section = ''
            
            for line in lines:
                line = line.strip()
                if '트렌드 배경' in line:
                    current_section = 'trend_background'
                elif '소비자 니즈' in line:
                    current_section = 'consumer_needs'
                elif '마케팅 인사이트' in line:
                    current_section = 'marketing_insights'
                elif '향후 전망' in line:
                    current_section = 'future_outlook'
                elif line and current_section:
                    analysis_dict[current_section] += line + ' '
            
            print(f"GPT 분석 완료: {keyword}")
            return analysis_dict
            
        except Exception as e:
            print(f"GPT 분석 오류 ({keyword}): {e}")
            return {
                'keyword': keyword,
                'full_analysis': f'{keyword}에 대한 분석을 완료할 수 없습니다.',
                'trend_background': '분석 불가',
                'consumer_needs': '분석 불가',
                'marketing_insights': '분석 불가',
                'future_outlook': '분석 불가'
            }
    
    def upload_to_notion(self, analysis: Dict[str, str], search_data: Dict[str, Any]) -> bool:
        """노션 데이터베이스에 분석 결과 업로드"""
        try:
            today = datetime.date.today().isoformat()
            
            # 노션 페이지 속성 구성
            properties = {
                "키워드": {"title": [{"text": {"content": analysis['keyword']}}]},
                "분석일자": {"date": {"start": today}},
                "트렌드 배경": {
                    "rich_text": [{"text": {"content": analysis.get('trend_background', '')}}]
                },
                "소비자 니즈": {
                    "rich_text": [{"text": {"content": analysis.get('consumer_needs', '')}}]
                },
                "마케팅 인사이트": {
                    "rich_text": [{"text": {"content": analysis.get('marketing_insights', '')}}]
                },
                "향후 전망": {
                    "rich_text": [{"text": {"content": analysis.get('future_outlook', '')}}]
                },
                "검색 결과 수": {"number": search_data['total_results']},
                "상태": {"select": {"name": "완료"}}
            }
            
            # 페이지 콘텐츠 (상세 분석)
            children = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "상세 분석"}}]
                    }
                },
                {
                    "object": "block", 
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": analysis['full_analysis']}}]
                    }
                }
            ]
            
            # 검색 결과 추가
            if search_data['results']:
                children.append({
                    "object": "block",
                    "type": "heading_3", 
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "주요 검색 결과"}}]
                    }
                })
                
                for result in search_data['results'][:3]:
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": f"• {result['title']}: {result['snippet'][:100]}..."}}
                            ]
                        }
                    })
            
            # 노션 페이지 생성
            response = notion.pages.create(
                parent={"database_id": NOTION_DB_ID},
                properties=properties,
                children=children
            )
            
            print(f"노션 업로드 완료: {analysis['keyword']}")
            return True
            
        except Exception as e:
            print(f"노션 업로드 오류 ({analysis['keyword']}): {e}")
            return False
    
    def run_analysis(self):
        """전체 분석 프로세스 실행"""
        print("🚀 트렌드 분석 시스템 시작")
        print("=" * 50)
        
        # 1. 트렌드 키워드 수집
        print("📊 실시간 트렌드 키워드 수집 중...")
        keywords = self.get_naver_trending_keywords()
        
        if not keywords:
            print("❌ 키워드 수집 실패")
            return
        
        print(f"✅ 수집된 키워드: {keywords}")
        
        # 2. 각 키워드 분석
        success_count = 0
        for i, keyword in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] '{keyword}' 분석 중...")
            
            # 구글 검색
            print("🔍 구글 검색 중...")
            search_data = self.search_google_content(keyword)
            
            if search_data['total_results'] == 0:
                print(f"⚠️ '{keyword}' 검색 결과 없음")
                continue
            
            # GPT 분석
            print("🤖 GPT 분석 중...")
            analysis = self.analyze_with_gpt(keyword, search_data)
            
            # 노션 업로드
            print("📝 노션 업로드 중...")
            if self.upload_to_notion(analysis, search_data):
                success_count += 1
                print(f"✅ '{keyword}' 분석 완료")
            else:
                print(f"❌ '{keyword}' 업로드 실패")
            
            # API 호출 간격 조절
            time.sleep(2)
        
        print("\n" + "=" * 50)
        print(f"🎉 분석 완료: {success_count}/{len(keywords)}개 성공")
        print("📊 노션 데이터베이스에서 결과를 확인하세요!")

def main():
    """메인 실행 함수"""
    # 환경변수 검증
    required_vars = [
        'NAVER_CLIENT_ID', 'NAVER_CLIENT_SECRET', 
        'OPENAI_API_KEY', 'NOTION_TOKEN', 'NOTION_DATABASE_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ 필수 환경변수가 설정되지 않았습니다: {missing_vars}")
        print("💡 .env 파일을 확인하세요!")
        return
    
    # 트렌드 분석 실행
    analyzer = TrendAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
