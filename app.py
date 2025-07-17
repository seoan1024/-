# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template # render_template 임포트 추가
import requests
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)

# 정확한 API 주소
BASE_URL = "https://imok-m.goesw.kr/schul/module/outsideApi/selectSchulApiEventViewAjax.do"

# 🚨🚨🚨 새로 추가하는 HTML 템플릿 라우트 🚨🚨🚨
@app.route('/')
def index():
    return render_template('calendar.html') # templates 폴더의 calendar.html 파일을 렌더링

@app.route('/api/school_calendar', methods=['GET'])
def get_school_calendar():
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = request.args.get('year', type=int, default=current_year)
    month = request.args.get('month', type=int, default=current_month)

    # 해당 월의 1일과 마지막 날로 설정
    start_dt_str = f"{year}-{month:02d}-01"

    if month == 12:
        last_day_of_month = (datetime(year + 1, 1, 1) - timedelta(days=1)).day
    else:
        last_day_of_month = (datetime(year, month + 1, 1) - timedelta(days=1)).day

    end_dt_str = f"{year}-{month:02d}-{last_day_of_month:02d}"

    params = {
        'mlsvViewType': 'json',
        'startDt': start_dt_str,
        'endDt': end_dt_str,
        'eventSeCode': '',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
        'Referer': 'https://imok-m.goesw.kr/subList/30000016611',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
    }

    try:
        response = requests.post(BASE_URL, data=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        event_data_list = data.get('body', {}).get('eventListJson', [])

        if not event_data_list:
            print(f"Error: 'eventListJson' not found or empty in JSON response for year={year}, month={month}. Response: {data}")
            return jsonify({"error": "Failed to find event data in the JSON response. The API structure might have changed or no events for this month."}), 500

        academic_events_dict = {}
        for event in event_data_list:
            event_date_str = event.get('start')
            event_title = event.get('title')

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
