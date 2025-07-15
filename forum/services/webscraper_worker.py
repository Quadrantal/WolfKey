
import os
import sys
import django
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_forum.settings")
django.setup()

from forum.models import User

LOGIN_URL = "https://wpga.myschoolapp.com/"
USERNAME = "hugoc101923@wpga.ca" #TODO

def get_decrypted_wolfnet_password(user_email):
    user = User.objects.get(school_email=user_email)
    profile = user.userprofile
    return profile.get_decrypted_wolfnet_password()

def main():
    PASSWORD = get_decrypted_wolfnet_password(USERNAME)
    chrome_options = Options()
    # chrome_options.add_argument("--headless") CHANGE IN PROD
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(LOGIN_URL)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#Username")))
        username_input = driver.find_element(By.CSS_SELECTOR, "#Username")
        username_input.send_keys(USERNAME)
        next_btn = driver.find_element(By.CSS_SELECTOR, "#nextBtn")
        next_btn.click()

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#i0118")))
        password_input = driver.find_element(By.CSS_SELECTOR, "#i0118")
        password_input.send_keys(PASSWORD)
        submit_btn = driver.find_element(By.ID, "idSIButton9")
        submit_btn.click()

        # Handle 'Stay signed in?' prompt if it appears
        try:
            stay_signed_in_btn = wait.until(
                EC.presence_of_element_located((By.ID, "idBtn_Back"))
            )
            stay_signed_in_btn.click()
        except Exception:
            pass  # If not present, continue
        time.sleep(8)

        # Wait for courses to load
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".collapse")))
        course_divs = driver.find_elements(By.CSS_SELECTOR, ".collapse")
        section_ids = []
        for div in course_divs:
            div_id = div.get_attribute("id")
            if div_id and div_id.startswith("course"):
                section_ids.append(div_id.replace("course", ""))

        print("Section IDs: ", section_ids)

        # Get studentId from #profile-link
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#profile-link")))
        profile_link = driver.find_element(By.CSS_SELECTOR, "#profile-link")
        href = profile_link.get_attribute("href")
        import re
        m = re.search(r"profile/(\d+)/contactcard", href)
        student_id = m.group(1) if m else None
        print("Student ID:", student_id)

        # Wait for page/session to fully load

        import requests
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

        # Get cookies from Selenium to use in requests
        selenium_cookies = driver.get_cookies()
        cookies = {c['name']: c['value'] for c in selenium_cookies}

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": LOGIN_URL,
        }

        # For each sectionId, get markingPeriodId and then grades
        for section_id in section_ids:
            # Get marking periods
            mp_url = f"https://wpga.myschoolapp.com/api/datadirect/GradeBookMarkingPeriodList?sectionId={section_id}"
            mp_resp = requests.get(mp_url, cookies=cookies, headers=headers)
            if mp_resp.status_code == 200:
                mp_json = mp_resp.json()
                for mp in mp_json:
                    marking_period_id = mp.get("MarkingPeriodId")
                    # Get grades JSON
                    grades_url = f"https://wpga.myschoolapp.com/api/gradebook/AssignmentPerformanceStudent?sectionId={section_id}&markingPeriodId={marking_period_id}&studentId={student_id}"
                    grades_resp = requests.get(grades_url, cookies=cookies, headers=headers)
                    if grades_resp.status_code == 200:
                        print(f"Grades for section {section_id}, marking period {marking_period_id}:")
                        print(grades_resp.json())
                    else:
                        print(f"Failed to get grades for section {section_id}, marking period {marking_period_id}")
            else:
                print(f"Failed to get marking periods for section {section_id}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
