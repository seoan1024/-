# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta # timedelta 임포트 추가
import os
import re
import json

app = Flask(__name__)

# 정확한 API 주소
BASE_URL = "https://imok-m.goesw.kr/schul/module/outsideApi/selectSchulApiEventViewAjax.do"

@app.route('/api/school_calendar', methods=['GET'])
def get_school_calendar():
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = request.args.get('year', type=int, default=current_year)
    month = request.args.get('month', type=int, default=current_month)

    # 해당 월의 1일과 마지막 날로 설정
    start_dt_str = f"{year}-{month:02d}-01"
    
    # 마지막 날짜 계산: 다음 달 1일에서 하루를 빼면 이번 달 마지막 날이 됩니다.
    # 12월의 경우 다음 해 1월 1일에서 하루를 뺍니다.
    if month == 12:
        last_day_of_month = (datetime(year + 1, 1, 1) - timedelta(days=1)).day
    else:
        last_day_of_month = (datetime(year, month + 1, 1) - timedelta(days=1)).day
        
    end_dt_str = f"{year}-{month:02d}-{last_day_of_month:02d}"

    params = {
        'mlsvViewType': 'json', # 응답 스크립트에서 확인된 파라미터
        'startDt': start_dt_str,
        'endDt': end_dt_str,
        'eventSeCode': '', # 스크립트에서 기본값으로 사용될 가능성 있는 빈 문자열
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
        'Referer': 'https://imok-m.goesw.kr/subList/30000016611', # 학사일정 메인 페이지 주소
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', # POST 요청 시 필요
        'X-Requested-With': 'XMLHttpRequest', # AJAX 요청임을 알림
        # 'Cookie' 헤더가 Network 탭에서 확인된다면 여기에 추가해야 합니다.
    }

    try:
        response = requests.post(BASE_URL, data=params, headers=headers)
        response.raise_for_status() # HTTP 에러(4xx, 5xx)가 발생하면 예외 발생

        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # 🚨🚨🚨 JavaScript 코드에서 var eventListData = [...] 부분을 추출합니다! 🚨🚨🚨
        event_list_data_str = None
        for script_tag in soup.find_all('script'):
            # script_tag.string 대신 get_text() 사용 (더 안정적)
            script_text = script_tag.get_text(strip=True) # strip=True로 공백 제거
            
            if 'var eventListData =' in script_text:
                # 정규 표현식을 사용하여 'var eventListData = ' 다음의 JSON 배열 부분을 찾습니다.
                # 공백과 줄바꿈에 더 유연하게 대응하기 위해 \s*를 사용합니다.
                match = re.search(r'var eventListData\s*=\s*(\[.*?\]);', script_text, re.DOTALL)
                if match:
                    event_list_data_str = match.group(1)
                    break
        
        if not event_list_data_str:
            print(f"Error: Could not find 'var eventListData' in the script tags for year={year}, month={month}.")
            return jsonify({"error": "Failed to find event data in the script. The website HTML structure might have changed."}), 500

        # 추출한 JSON 문자열을 파이썬 리스트로 변환합니다.
        event_data_list = json.loads(event_list_data_str)

        academic_events_dict = {} # 날짜별로 이벤트를 묶기 위한 딕셔너리
        for event in event_data_list:
            event_date_str = event.get('start') # 'start' 키가 날짜 정보
            event_title = event.get('title') # 'title' 키가 이벤트 제목

            if event_date_str and event_title:
                # 날짜를 파싱하여 연, 월, 일을 추출합니다.
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    event_day = event_date.day
                    
                    # 해당 날짜의 이벤트 리스트를 가져오거나 새로 생성합니다.
                    if event_date_str not in academic_events_dict:
                        academic_events_dict[event_date_str] = {
                            "date": event_date_str,
                            "day": event_day,
                            "events": []
                        }
                    academic_events_dict[event_date_str]["events"].append(event_title)
                    
                except ValueError:
                    print(f"Warning: Invalid date format for event: {event_date_str}")
                    continue # 날짜 형식이 잘못되면 건너뜁니다.
        
        # 딕셔너리의 값을 리스트로 변환하고, 날짜 순으로 정렬합니다.
        academic_events = list(academic_events_dict.values())
        academic_events.sort(key=lambda x: x['date'])
        
        return jsonify(academic_events)

    except requests.exceptions.RequestException as e:
        print(f"Request Error accessing API endpoint: {e}")
        return jsonify({"error": f"Failed to fetch content from the API URL. Details: {e}. Please ensure all request headers and parameters are correct."}), 500
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e} - Raw string (first 200 chars): {event_list_data_str[:200] if event_list_data_str else 'N/A'}")
        return jsonify({"error": f"Failed to parse JSON data from script. Details: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
