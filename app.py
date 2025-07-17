# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re # 정규 표현식을 사용하기 위해 re 모듈을 임포트합니다.
import json # JSON 문자열을 파싱하기 위해 json 모듈을 임포트합니다.

app = Flask(__name__)

# 정확한 API 주소
BASE_URL = "https://imok-m.goesw.kr/schul/module/outsideApi/selectSchulApiEventViewAjax.do"

@app.route('/api/school_calendar', methods=['GET'])
def get_school_calendar():
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = request.args.get('year', type=int, default=current_year)
    month = request.args.get('month', type=int, default=current_month)

    # 파라미터는 `moduleEventvViewCal.jsp` 스크립트에서 확인한 대로 `startDt`, `endDt`, `eventSeCode`가 필요합니다.
    # startDt와 endDt는 해당 월의 1일과 마지막 날로 설정합니다.
    start_dt_str = f"{year}-{month:02d}-01"
    
    # 해당 월의 마지막 날짜 계산
    last_day_of_month = (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day if month < 12 else (datetime(year + 1, 1, 1) - timedelta(days=1)).day
    end_dt_str = f"{year}-{month:02d}-{last_day_of_month:02d}"

    params = {
        'mlsvViewType': 'json', # 스크립트에서 mlsvViewType: 'json'으로 되어 있었음
        'startDt': start_dt_str,
        'endDt': end_dt_str,
        'eventSeCode': '', # 스크립트에서 $('#eventSeCode').val() 이었으나, 기본값은 빈 문자열로 추정
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
        script_tags = soup.find_all('script')
        event_list_data_str = None
        for script_tag in script_tags:
            script_text = script_tag.string # script_tag.string은 <script>...</script> 안의 텍스트를 가져옵니다.
            if script_text and 'var eventListData =' in script_text:
                # 정규 표현식을 사용하여 'var eventListData = ' 다음의 JSON 배열 부분을 찾습니다.
                match = re.search(r'var eventListData = (\[.*?\]);', script_text, re.DOTALL)
                if match:
                    event_list_data_str = match.group(1)
                    break
        
        if not event_list_data_str:
            print(f"Error: Could not find 'var eventListData' in the script tags for year={year}, month={month}.")
            return jsonify({"error": "Failed to find event data in the script. The website HTML structure might have changed."}), 500

        # 추출한 JSON 문자열을 파이썬 리스트로 변환합니다.
        event_data_list = json.loads(event_list_data_str)

        academic_events = []
        for event in event_data_list:
            event_date_str = event.get('start') # 'start' 키가 날짜 정보
            event_title = event.get('title') # 'title' 키가 이벤트 제목

            if event_date_str and event_title:
                # 날짜를 파싱하여 연, 월, 일을 추출합니다.
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    event_year = event_date.year
                    event_month = event_date.month
                    event_day = event_date.day
                except ValueError:
                    continue # 날짜 형식이 잘못되면 건너뜁니다.
                
                # 기존 데이터 구조에 맞게 변환합니다.
                # 날짜별로 이벤트를 묶으려면 별도의 로직이 필요하지만, 일단 JSON 리스트 그대로 반환하겠습니다.
                # 만약 날짜별로 묶고 싶다면, 딕셔너리에 날짜를 키로 사용하여 이벤트를 추가하는 로직을 구현해야 합니다.
                
                # 여기서는 원본 JSON 리스트의 각 항목을 그대로 반환하는 방식입니다.
                academic_events.append({
                    "date": event_date_str,
                    "day": event_day,
                    "events": [event_title] # 이벤트를 리스트 안에 넣습니다.
                    # 원본 JSON의 다른 필드도 포함하려면 여기에 추가:
                    # "eventSeCode": event.get('eventSeCode'),
                    # "eventSeq": event.get('eventSeq'),
                    # "className": event.get('className')
                })
        
        # 날짜 순으로 정렬 (선택 사항)
        academic_events.sort(key=lambda x: x['date'])
        
        return jsonify(academic_events)

    except requests.exceptions.RequestException as e:
        print(f"Request Error accessing API endpoint: {e}")
        return jsonify({"error": f"Failed to fetch content from the API URL. Details: {e}. Please ensure all request headers and parameters are correct."}), 500
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e} - Raw string: {event_list_data_str[:200]}...") # 에러 발생 시 원시 문자열 일부 출력
        return jsonify({"error": f"Failed to parse JSON data from script. Details: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

# 날짜 계산을 위한 timedelta 임포트
from datetime import timedelta
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
