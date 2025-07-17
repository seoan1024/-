# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
import os
import json # JSON 데이터 처리에만 사용합니다.

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
    if month == 12:
        last_day_of_month = (datetime(year + 1, 1, 1) - timedelta(days=1)).day
    else:
        last_day_of_month = (datetime(year, month + 1, 1) - timedelta(days=1)).day
        
    end_dt_str = f"{year}-{month:02d}-{last_day_of_month:02d}"

    # 이 파라미터들이 `image_e5ee78.png` 로그에도 영향을 미쳤을 수 있습니다.
    # 스크립트에서 확인된 파라미터를 정확히 사용합니다.
    params = {
        'mlsvViewType': 'json', # JSON 응답을 유도하는 파라미터
        'startDt': start_dt_str,
        'endDt': end_dt_str,
        'eventSeCode': '', # 스크립트에서 사용된 것으로 추정되는 빈 문자열
    }

    # 헤더는 여전히 브라우저처럼 보이도록 설정합니다.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
        'Referer': 'https://imok-m.goesw.kr/subList/30000016611', # 학사일정 메인 페이지 주소
        'Accept': 'application/json, text/javascript, */*; q=0.01', # JSON 응답을 받는다고 명시
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
    }

    try:
        response = requests.post(BASE_URL, data=params, headers=headers)
        response.raise_for_status() # HTTP 에러(4xx, 5xx)가 발생하면 예외 발생

        # 🚨🚨🚨 HTML 파싱 대신 JSON으로 바로 파싱합니다! 🚨🚨🚨
        data = response.json() 
        
        # `image_e5ee78.png` 로그에서 확인된 JSON 구조에 따라 데이터를 추출합니다.
        # {"head":{"result":"success"},"body":{"eventListJson":[...]}}
        event_data_list = data.get('body', {}).get('eventListJson', [])

        if not event_data_list:
            print(f"Error: 'eventListJson' not found or empty in JSON response for year={year}, month={month}. Response: {data}")
            return jsonify({"error": "Failed to find event data in the JSON response. The API structure might have changed or no events for this month."}), 500

        academic_events_dict = {} # 날짜별로 이벤트를 묶기 위한 딕셔너리
        for event in event_data_list:
            event_date_str = event.get('start') # 'start' 키가 날짜 정보
            event_title = event.get('title') # 'title' 키가 이벤트 제목

            if event_date_str and event_title:
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    event_day = event_date.day
                    
                    if event_date_str not in academic_events_dict:
                        academic_events_dict[event_date_str] = {
                            "date": event_date_str,
                            "day": event_day,
                            "events": []
                        }
                    academic_events_dict[event_date_str]["events"].append(event_title)
                    
                except ValueError:
                    print(f"Warning: Invalid date format for event: {event_date_str}")
                    continue
        
        # 딕셔너리의 값을 리스트로 변환하고, 날짜 순으로 정렬합니다.
        academic_events = list(academic_events_dict.values())
        academic_events.sort(key=lambda x: x['date'])
        
        return jsonify(academic_events)

    except requests.exceptions.RequestException as e:
        print(f"Request Error accessing API endpoint: {e}")
        return jsonify({"error": f"Failed to fetch content from the API URL. Details: {e}. Please ensure all request headers and parameters are correct."}), 500
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e} - Raw response (first 200 chars): {response.text[:200] if response.text else 'N/A'}")
        return jsonify({"error": f"Failed to parse JSON data from response. Details: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
