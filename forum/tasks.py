from celery import shared_task
from forum.models import User, GradebookSnapshot
import logging
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from django.utils.html import strip_tags
from django.http import HttpRequest
import django

logger = logging.getLogger(__name__)

# Grade checking functions
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
        if new_a.get("comment") != old_a.get("comment"):
            changes.append({"type": "comment_changed", "assignment": new_a})
    return changes

def login_to_wolfnet(user_email, driver, wait):
    """Log into WolfNet and return the authenticated driver"""
    LOGIN_URL = "https://wpga.myschoolapp.com/"
    
    PASSWORD = get_decrypted_wolfnet_password(user_email)
    if not PASSWORD:
        logger.error(f"No Wolfnet password found for {user_email}. Cannot login.")
        return False
    
    try:
        logger.info(f"Navigating to login page for {user_email}")
        driver.get(LOGIN_URL)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#Username")))
        username_input = driver.find_element(By.CSS_SELECTOR, "#Username")
        username_input.send_keys(user_email)
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
        logger.info(f"Successfully logged in for {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to login for {user_email}: {str(e)}")
        return False

def check_user_grades_core(user_email):
    """Core grade checking logic using Selenium"""
    logger.info(f"Starting grade check for user: {user_email}")
    LOGIN_URL = "https://wpga.myschoolapp.com/"
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # Use the new login function
        if not login_to_wolfnet(user_email, driver, wait):
            return

        # Wait for courses to load
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".collapse")))
        course_divs = driver.find_elements(By.CSS_SELECTOR, ".collapse")
        section_ids = []
        section_id_to_course_name = {}
        for div in course_divs:
            div_id = div.get_attribute("id")
            # Only process divs whose IDs match 'course' followed by digits (e.g., 'course114310942')
            if div_id and re.match(r"^course\d+$", div_id):
                sid = div_id.replace("course", "")
                section_ids.append(sid)
                try:
                    parent = div.find_element(By.XPATH, "..")
                    a_tag = parent.find_element(By.TAG_NAME, "a")
                    h3 = a_tag.find_element(By.TAG_NAME, "h3")
                    course_name = h3.text.strip()
                except Exception:
                    course_name = "Unknown Course"
                section_id_to_course_name[sid] = course_name

        logger.info(f"Section IDs for {user_email}: {section_ids}")

        # Get studentId from #profile-link
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#profile-link")))
        profile_link = driver.find_element(By.CSS_SELECTOR, "#profile-link")
        href = profile_link.get_attribute("href")
        m = re.search(r"profile/(\d+)/contactcard", href)
        student_id = m.group(1) if m else None
        logger.info(f"Student ID for {user_email}: {student_id}")

        # Get cookies from Selenium to use in requests
        selenium_cookies = driver.get_cookies()
        cookies = {c['name']: c['value'] for c in selenium_cookies}

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://wpga.myschoolapp.com/",
        }

        # For each sectionId, get markingPeriodId and then hydrategradebook JSON
        user_obj = User.objects.get(school_email=user_email)

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
                        # logger.info(f"Recent assignments for {user_email}: {assignments[-1:] if assignments else 'None'}")
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
                            logger.info(f"Changes for {user_email} - section {section_id}, marking period {marking_period_id}: {len(changes)} changes found")
                            
                            for change in changes:
                                logger.info(f"Processing change for {user_email}: {change}")
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
                                    prof_list = [f"<strong>{s.get('skill_name')}:</strong> {s.get('rating_desc')}" for s in prof_skills]
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
                                        grade_info = f"\n <strong>Grade:</strong> {points_earned}/{max_points} ({percent}%)" if percent is not None else f"Grade: {points_earned}/{max_points}"
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
                                
                                # Get course name for this section
                                course_name = section_id_to_course_name.get(str(section_id), "Unknown Course")
                                email_subject = f"WolfKey Grade Update: {course_name}"
                                # HTML email body
                                email_message = f"""
                                    <html>
                                    <body>
                                        <h2>Course: {course_name}</h2>
                                        <p>Hello {recipient.get_full_name()},</p>
                                        <p>{message.replace(chr(10), '<br>')}</p>
                                        <br>
                                        <p>Best regards,<br>WolfKey Team</p>
                                    </body>
                                    </html>
                                """
                                logger.info(f"Sending grade update notification to {recipient.personal_email}: {message}")
                                # Use the new email task for sending emails
                                send_email_notification.delay(
                                    recipient.personal_email,
                                    email_subject,
                                    email_message
                                )
                                # Send in-app notification without email
                                from forum.services.notification_services import send_notification_service
                                send_notification_service(
                                    recipient=recipient,
                                    sender=sender,
                                    notification_type=notification_type,
                                    message=message,
                                    # Remove email parameters to avoid duplicate emails
                                )
                            
                            # Update snapshot
                            snapshot.json_data = assignments
                            snapshot.timestamp = django.utils.timezone.now()
                            snapshot.save()
                            logger.info(f"Updated snapshot for {user_email} - section {section_id}, marking period {marking_period_id}")
                        else:
                            GradebookSnapshot.objects.create(
                                user=user_obj,
                                section_id=section_id,
                                marking_period_id=str(marking_period_id),
                                json_data=assignments
                            )
                            logger.info(f"Created new snapshot for {user_email} - section {section_id}, marking period {marking_period_id}")
                    else:
                        logger.error(f"Failed to get hydrategradebook for {user_email} - section {section_id}, marking period {marking_period_id}")
            else:
                logger.error(f"Failed to get marking periods for {user_email} - section {section_id}")
    finally:
        driver.quit()
        logger.info(f"Grade check completed for {user_email}")

@shared_task
def check_single_user_grades(user_email):
    """
    Check grades for a single user
    """
    try:
        return check_user_grades_core(user_email)
    except Exception as e:
        logger.error(f"Error checking grades for {user_email}: {str(e)}")
        raise

@shared_task
def check_all_user_grades():
    """
    Schedule grade checking for all users in parallel
    """
    users = User.objects.all()
    logger.info(f"Starting grade check for {users.count()} users")
    
    # Create a task for each user
    job_ids = []
    for user in users:
        if user.school_email:  # Only check users with school emails
            job = check_single_user_grades.delay(user.school_email)
            job_ids.append(job.id)
    
    logger.info(f"Scheduled {len(job_ids)} grade checking tasks")
    return {"scheduled_tasks": len(job_ids), "task_ids": job_ids}

@shared_task
def send_email_notification(recipient_email, subject, message):
    """
    Send email notification - separate task for email queue
    """
    from django.core.mail import send_mail
    from django.conf import settings
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
            html_message=message
        )
        logger.info(f"Email sent successfully to {recipient_email}")
        return f"Email sent to {recipient_email}"
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        raise

@shared_task
def auto_complete_courses(user_email):
    """
    Auto-complete courses from WolfNet schedule for a user
    """
    logger.info(f"Starting auto-complete courses for user: {user_email}")
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # Use the login function
        if not login_to_wolfnet(user_email, driver, wait):
            return {"success": False, "error": "Failed to login to WolfNet"}

        # Wait for the page to load and find the first .subnav-multicol element
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".subnav-multicol")))
        subnav_elements = driver.find_elements(By.CSS_SELECTOR, ".subnav-multicol")
        
        if not subnav_elements:
            logger.error(f"No .subnav-multicol elements found for {user_email}")
            return {"success": False, "error": "No course navigation found"}
        
        # Take the first .subnav-multicol element
        subnav = subnav_elements[0]
        
        # Find all span.multi.title elements in the subnav
        title_spans = subnav.find_elements(By.CSS_SELECTOR, "span.multi.title")
        logger.info(f"Found {len(title_spans)} span.multi.title elements")

        courses_data = {}
        for title_span in title_spans:
            try:
                # Try multiple ways to get the text
                text_direct = title_span.text.strip()
                text_inner = title_span.get_attribute('innerText').strip() if title_span.get_attribute('innerText') else ''
                text_content = title_span.get_attribute('textContent').strip() if title_span.get_attribute('textContent') else ''
                logger.info(f"Title span outer HTML: {title_span.get_attribute('outerHTML')}")
                logger.info(f"Title span .text: '{text_direct}' | innerText: '{text_inner}' | textContent: '{text_content}'")

                # Use the first non-empty value
                course_text = text_direct or text_inner or text_content

                # Only process if it matches the block course pattern
                if " (" in course_text and course_text.endswith(")"):
                    block_match = re.search(r'\(([^)]+)\)$', course_text)
                    logger.info(block_match)
                    if block_match:
                        block = block_match.group(1)
                        course_name_part = course_text.split(" (", 1)[0]
                        if " - " in course_name_part:
                            course_name = course_name_part.split(" - ", 1)[0].strip()
                        else:
                            course_name = course_name_part.strip()
                        logger.info(block)
                        logger.info(course_name)
                        if re.match(r'^[12][A-E]|Flex\d*$', block):
                            if block.startswith("Flex"):
                                continue  # Skip flex blocks
                            courses_data[block] = {
                                "name": course_name,
                                "block": block,
                                "raw_text": course_text
                            }
                            logger.info(f"Found course for {user_email}: {course_name} in block {block}")
            except Exception as e:
                logger.warning(f"Error parsing span.multi.title for {user_email}: {str(e)}")
                continue
        logger.info(f"Found {len(courses_data)} courses for {user_email}: {courses_data}")
        
        # Now search for each course in our database using course_search
        matched_courses = {}
        
        for block, course_info in courses_data.items():
            course_name = course_info["name"]
            
            # Create a mock request object for course_search
            mock_request = type('MockRequest', (), {
                'GET': {'q': course_name},
                'method': 'GET'
            })()
            
            try:
                # Import course_search function locally to avoid circular imports
                from forum.services.course_services import course_search
                
                # Use the course_search function to find matching courses
                search_response = course_search(mock_request)
                search_data = search_response.content.decode('utf-8')
                import json
                courses = json.loads(search_data)
                
                if courses:
                    # Take the first (best) match
                    best_match = courses[0]
                    matched_courses[block] = {
                        "id": best_match["id"],
                        "name": best_match["name"],
                        "category": best_match["category"],
                        "experienced_count": best_match["experienced_count"]
                    }
                    logger.info(f"Matched {course_name} to {best_match['name']} for block {block}")
                else:
                    logger.warning(f"No match found for course: {course_name} in block {block}")
                    
            except Exception as e:
                logger.error(f"Error searching for course {course_name}: {str(e)}")
                continue
        
        return {
            "success": True, 
            "courses": matched_courses,
            "raw_data": courses_data
        }
        
    except Exception as e:
        logger.error(f"Error in auto_complete_courses for {user_email}: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        driver.quit()
        logger.info(f"Auto-complete courses completed for {user_email}")
