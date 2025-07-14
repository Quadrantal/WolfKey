
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

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#site-logo img")))
        logo_img = driver.find_element(By.CSS_SELECTOR, "#site-logo img")
        logo_src = logo_img.get_attribute("src")
        print("School image link:", logo_src)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
