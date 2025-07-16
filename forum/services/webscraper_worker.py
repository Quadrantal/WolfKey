
import os
import sys
import django
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_forum.settings")
django.setup()

from forum.models import GradebookSnapshot
from forum.models import User
from django.utils.html import strip_tags

LOGIN_URL = "https://wpga.myschoolapp.com/"
USERNAME = "hugoc101923@wpga.ca" #TODO

def get_decrypted_wolfnet_password(user_email):
    user = User.objects.get(school_email=user_email)
    profile = user.userprofile
    return profile.get_decrypted_wolfnet_password()

def compare_assignments(old_assignments, new_assignments):
    changes = []
    old_map = {a["assignment_id"]: a for a in old_assignments}
    for new_a in new_assignments:
        aid = new_a["assignment_id"]
        old_a = old_map.get(aid)
        if not old_a:
            changes.append({"type": "new", "assignment": new_a})
            continue

        old_skills = {s["skill_id"]: s for s in old_a.get("skills", [])}
        for s in new_a["skills"]:
            old_s = old_skills.get(s["skill_id"])
            if not old_s or s["rating"] != old_s.get("rating") or s["rating_desc"] != old_s.get("rating_desc"):
                changes.append({"type": "skill_changed", "assignment": new_a, "skill": s})

        if new_a.get("points_earned") != old_a.get("points_earned") or new_a.get("max_points") != old_a.get("max_points"):
            changes.append({"type": "points_changed", "assignment": new_a})
        # Compare comments
        if new_a.get("comment") != old_a.get("comment"):
            changes.append({"type": "comment_changed", "assignment": new_a})
    return changes

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
        time.sleep(7)

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

        # Get cookies from Selenium to use in requests
        selenium_cookies = driver.get_cookies()
        cookies = {c['name']: c['value'] for c in selenium_cookies}

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": LOGIN_URL,
        }

        # For each sectionId, get markingPeriodId and then hydrategradebook JSON
        from forum.models import GradebookSnapshot, User
        user_obj = User.objects.get(school_email=USERNAME)
        for section_id in section_ids:
            # Get marking periods
            mp_url = f"https://wpga.myschoolapp.com/api/datadirect/GradeBookMarkingPeriodList?sectionId={section_id}"
            mp_resp = requests.get(mp_url, cookies=cookies, headers=headers)
            if mp_resp.status_code == 200:
                mp_json = mp_resp.json()
                for mp in mp_json:
                    marking_period_id = mp.get("MarkingPeriodId")
                    # Get hydrategradebook JSON
                    hydrate_url = (
                        f"https://wpga.myschoolapp.com/api/gradebook/hydrategradebook?"
                        f"sectionId={section_id}&markingPeriodId={marking_period_id}"
                        f"&sortAssignmentId=null&sortSkillPk=null&sortDesc=null&sortCumulative=null"
                        f"&studentUserId={student_id}&fromProgress=true"
                    )
                    hydrate_resp = requests.get(hydrate_url, cookies=cookies, headers=headers)
                    if hydrate_resp.status_code == 200:
                        hydrate_json = hydrate_resp.json()
                        print(f"HydrateGradebook for section {section_id}, marking period {marking_period_id}:")
                        # Extract relevant assignment info
                        assignments = []
                        roster = hydrate_json.get("Roster", [])
                        if roster:
                            for a in roster[0].get("AssignmentGrades", []):
                                assignments.append({
                                    "assignment_id": a.get("AssignmentId"),
                                    "name": a.get("AssignmentType", "").strip(),
                                    "points_earned": a.get("PointsEarned"),
                                    "max_points": a.get("MaxPoints"),
                                    "comment": a.get("Comment", "").strip(),
                                    "assignment_type": a.get("AssignmentType", "").strip(),
                                    "assignment_type_id": a.get("AssignmentTypeId"),
                                    "skills": [
                                        {
                                            "skill_id": s.get("SkillId"),
                                            "skill_name": s.get("SkillName"),
                                            "rating": s.get("Rating"),
                                            "rating_desc": s.get("RatingDesc")
                                        }
                                        for s in a.get("AssignmentSkillList", [])
                                    ]
                                })
                        print(assignments[-3:])
                        # Fetch AssignmentPerformanceStudent JSON for assignment names
                        aps_url = (
                            f"https://wpga.myschoolapp.com/api/gradebook/AssignmentPerformanceStudent?"
                            f"sectionId={section_id}&markingPeriodId={marking_period_id}&studentId={student_id}"
                        )
                        aps_resp = requests.get(aps_url, cookies=cookies, headers=headers)
                        assignment_names = {}
                        if aps_resp.status_code == 200:
                            aps_json = aps_resp.json()
                            for entry in aps_json:
                                aid = entry.get("AssignmentId")
                                short_desc = entry.get("AssignmentShortDescription")
                                if aid and short_desc:
                                    assignment_names[aid] = short_desc

                        # Compare with previous snapshot
                        snapshot_qs = GradebookSnapshot.objects.filter(
                            user=user_obj,
                            section_id=section_id,
                            marking_period_id=str(marking_period_id)
                        ).order_by('-timestamp')

                        if snapshot_qs.exists():
                            snapshot = snapshot_qs.first()
                            old_assignments = snapshot.json_data
                            changes = compare_assignments(old_assignments, assignments)
                            print(f"Changes for section {section_id}, marking period {marking_period_id}:")
                            from forum.services.notification_services import send_notification_service
                            for change in changes:
                                print(change)
                                # Send notification for new/changed grade
                                assignment = change["assignment"]
                                recipient = user_obj
                                sender = user_obj  # System or self
                                notification_type = "grade_update"
                                assignment_id = assignment.get("assignment_id")
                                assignment_name = strip_tags(assignment_names.get(assignment_id) or assignment.get("name") or assignment.get("assignment_type"))
                                # Determine grading system
                                skills = assignment.get("skills", [])
                                prof_skills = [s for s in skills if s.get("rating_desc", "")]
                                has_proficiency = bool(prof_skills)
                                if has_proficiency:
                                    # Use first non-empty proficiency
                                    prof_list = [f"{s.get('skill_name')}: {s.get('rating_desc')}" for s in prof_skills]
                                    grade_info = "\n".join(prof_list)
                                else:
                                    # Use percentage
                                    points_earned = assignment.get("points_earned")
                                    max_points = assignment.get("max_points")
                                    if points_earned is not None and max_points:
                                        try:
                                            percent = round((points_earned / max_points) * 100, 2)
                                        except Exception:
                                            percent = None
                                        grade_info = f"\n Grade: {points_earned}/{max_points} ({percent}%)" if percent is not None else f"Grade: {points_earned}/{max_points}"
                                    else:
                                        grade_info = "Grade information not available."

                                message = f"Your assignment '{assignment_name}' was graded or updated. \n{grade_info}"
                                if change["type"] == "new":
                                    message = f"New assignment '{assignment_name}' has been graded. \n{grade_info} \nComment: {assignment.get('comment')}"
                                elif change["type"] == "skill_changed":
                                    skill = change["skill"]
                                    message = f"Competency '{skill.get('skill_name')}' for assignment '{assignment_name}' was updated to '{skill.get('rating_desc')}'. {grade_info}"
                                elif change["type"] == "points_changed":
                                    message = f"Points for assignment '{assignment_name}' changed to {assignment.get('points_earned')}/{assignment.get('max_points')}. {grade_info}"
                                elif change["type"] == "comment_changed":
                                    message = f"Comment for assignment '{assignment_name}' was updated. {grade_info} \nComment: {assignment.get('comment')}"
                                email_subject = "WolfKey Grade Update"
                                email_message = f"Hello {recipient.get_full_name()},\n\n{message}\n\nBest regards,\nWolfKey Team"
                                print(email_message)
                                send_notification_service(
                                    recipient=recipient,
                                    sender=sender,
                                    notification_type=notification_type,
                                    message=message,
                                    email_subject=email_subject,
                                    email_message=email_message,
                                )
                            # Update snapshot
                            snapshot.json_data = assignments
                            snapshot.timestamp = django.utils.timezone.now()
                            snapshot.save()
                        else:
                            GradebookSnapshot.objects.create(
                                user=user_obj,
                                section_id=section_id,
                                marking_period_id=str(marking_period_id),
                                json_data=assignments
                            )
                    else:
                        print(f"Failed to get hydrategradebook for section {section_id}, marking period {marking_period_id}")
            else:
                print(f"Failed to get marking periods for section {section_id}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
