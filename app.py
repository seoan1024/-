# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

app = Flask(__name__)

# 🚨🚨🚨 드디어 찾은 정확한 API 주소! 🚨🚨🚨
BASE_URL = "https://imok-m.goesw.kr/schul/module/outsideApi/selectSchulApiEventViewAjax.do"

@app.route('/api/school_calendar', methods=['GET'])
def get_school_calendar():
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = request.args.get('year', type=int, default=current_year)
    month = request.args.get('month', type=int, default=current_month)

    # 파라미터는 기존과 동일하게 'year', 'month'일 가능성이 높습니다.
    # 개발자 도구의 Network 탭 -> 해당 요청 -> 'Payload' 탭 -> 'Form Data'에서 최종 확인이 가장 정확합니다.
    params = {
        'year': str(year),
        'month': str(month).zfill(2), # 월은 두 자리로 맞춰줍니다 (예: 07, 08)
        # 혹시 'schulCode', 'calType', 'm' 등 다른 파라미터가 있다면 여기에 추가
    }

    # 헤더는 이전 시도와 동일하게 브라우저처럼 보이도록 설정합니다.
    # 'Referer'는 이목중 학사일정 메인 페이지로 설정하는 것이 안전합니다.
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
        # 이 요청은 POST 방식으로 전송될 가능성이 높습니다. (개발자 도구에서 확인 필요)
        response = requests.post(BASE_URL, data=params, headers=headers)
        
        response.raise_for_status() # HTTP 에러(4xx, 5xx)가 발생하면 예외 발생

        # 응답이 HTML임을 스크린샷에서 확인했으니, 텍스트로 바로 받아서 BeautifulSoup으로 파싱합니다.
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 🚨🚨🚨 달력 테이블 찾기! <table class="sche_board">가 맞는지 'XHR 응답'에서 재확인 필수! 🚨🚨🚨
        # (이전 스크린샷에서도 이 클래스명을 확인했습니다.)
        calendar_table = soup.find('table', class_='sche_board')

        if not calendar_table:
            print(f"Error: Could not find calendar table (class='sche_board') in XHR response HTML for year={year}, month={month}.")
            return jsonify({"error": "Failed to find the calendar table. Check the HTML structure of the XHR response or the class name."}), 500

        academic_events = []
        date_cells = calendar_table.find_all('td', class_='sch_td')

        for cell in date_cells:
            day_p_tag = cell.find('p', class_='day')
            day_text = day_p_tag.get_text(strip=True) if day_p_tag else ''

            if not day_text: # 날짜가 없으면 (빈 칸) 건너뛰기
                continue
            
            full_date_str = f"{year}-{month:02d}-{int(day_text):02d}"

            events_in_day = []
            sch_list = cell.find('ul', class_='sch_list')
            if sch_list:
                for event_li in sch_list.find_all('li'):
                    event_text = event_li.get_text(strip=True)
                    if event_text:
                        events_in_day.append(event_text)
            
            academic_events.append({
                "date": full_date_str,
                "day": int(day_text),
                "events": events_in_day
            })
            
        return jsonify(academic_events)

    except requests.exceptions.RequestException as e:
        print(f"Request Error accessing API endpoint: {e}")
        return jsonify({"error": f"Failed to fetch content from the API URL. Details: {e}. Please ensure all request headers and parameters are correct."}), 500
    except Exception as e:
        print(f"An unexpected error occurred during parsing or other steps: {e}")
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
