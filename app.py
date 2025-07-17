# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service # 🚨🚨🚨 Service 객체를 다시 불러옵니다! 🚨🚨🚨
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import time
import os

app = Flask(__name__)

SCHOOL_CALENDAR_URL = "https://imok-m.goesw.kr/subList/30000016611"

@app.route('/api/school_calendar', methods=['GET'])
def get_school_calendar():
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = request.args.get('year', type=int, default=current_year)
    month = request.args.get('month', type=int, default=current_month)

    # Render 배포를 위한 Selenium 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36")
    
    # Render 환경에 설치된 Chrome 바이너리 경로 지정
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome-stable")

    # Render 환경에 설치된 ChromeDriver 경로 지정
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    
    driver = None
    try:
        # 🚨🚨🚨 WebDriver 초기화 방식을 Service 객체 사용으로 변경합니다! 🚨🚨🚨
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(SCHOOL_CALENDAR_URL)

        time.sleep(5) # 페이지 로딩을 기다려야 해요.

        # <iframe>으로 전환! (src 속성으로 찾기)
        # <iframe>의 src가 'calendar_2020.10.1.jsp'인 것을 확인했으니, 그 속성으로 찾아요.
        iframe_element = driver.find_element(By.CSS_SELECTOR, 'iframe[src*="calendar_2020.10.1.jsp"]')
        driver.switch_to.frame(iframe_element)

        # <iframe> 내부 HTML 가져와 BeautifulSoup으로 파싱!
        iframe_html = driver.page_source
        soup = BeautifulSoup(iframe_html, 'html.parser')

        # 달력 테이블 찾기 (클래스 이름 재확인)
        # <iframe> 내부에서 <table class="sche_board">를 찾아야 해요.
        calendar_table = soup.find('table', class_='sche_board')

        if not calendar_table:
            print("Error: Could not find calendar table (class='sche_board') within the iframe content.")
            return jsonify({"error": "Failed to find the calendar table. Check the iframe's HTML structure or class name."}), 500

        academic_events = []
        date_cells = calendar_table.find_all('td', class_='sch_td')

        for cell in date_cells:
            day_p_tag = cell.find('p', class_='day')
            day_text = day_p_tag.get_text(strip=True) if day_p_tag else ''

            if not day_text:
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

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)