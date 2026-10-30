import os
import sys
import json
import re
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

IST = pytz.timezone("Asia/Kolkata")

def get_student_credentials():
    students = []
    
    # Student 1 (Middle School)
    u1 = os.environ.get("MCB_USER_1") or os.environ.get("MCB_USERNAME")
    p1 = os.environ.get("MCB_PASS_1") or os.environ.get("MCB_PASSWORD")
    if u1 and p1:
        students.append({
            "key": "sreedyuti",
            "id": u1,
            "password": p1,
            "name": "Sreedyuti Kalakbandi",
            "grade": "Grade VI - A",
            "category": "Middle School",
            "icon": "🎒",
            "avatar": "images/sreedyuti.jpg",
            "theme": "purple"
        })
    else:
        print("Notice: MCB_USER_1 and/or MCB_PASS_1 environment variables not set.")
        
    # Student 2 (Primary School)
    u2 = os.environ.get("MCB_USER_2")
    p2 = os.environ.get("MCB_PASS_2")
    if u2 and p2:
        students.append({
            "key": "sreekriti",
            "id": u2,
            "password": p2,
            "name": "Sreekriti Kalakbandi",
            "grade": "Grade I - A",
            "category": "Primary School",
            "icon": "🎨",
            "avatar": "images/sreekriti.jpg",
            "theme": "pink"
        })
    else:
        print("Notice: MCB_USER_2 and/or MCB_PASS_2 environment variables not set.")
        
    return students

def parse_diary_soup(soup):
    today_div = soup.select_one("#divtodaydiary")
    if not today_div:
        today_div = soup
        
    diary_div = today_div.select_one("#diaryDiv") or today_div
    
    entries = []
    current_subject = "General"
    
    for el in diary_div.find_all(["div", "span", "h5", "h6"]):
        classes = el.get("class") or []
        
        # Check if subject header
        if "col-lg-12" in classes and not any(c in classes for c in ["form-group", "text-right", "card-body", "p-2"]):
            txt = el.get_text(strip=True)
            if txt and not any(k in txt.lower() for k in ["submit now", "created at", "classwork", "homework", "date :", "oops"]):
                if len(txt) < 60 and (txt.isupper() or "&" in txt or "-" in txt):
                    current_subject = txt
                    
        # Check if entry card
        if "card" in classes and not any(c in classes for c in ["dropdowntxt", "border-radius-10"]):
            card_text = el.get_text(separator=" ", strip=True)
            if not any(k in card_text.lower() for k in ["classwork", "homework", "notes", "revision"]):
                continue
                
            badge_el = el.select_one(".badge-warning, .badge-danger, .badge")
            entry_type = badge_el.get_text(strip=True) if badge_el else ("Homework" if "homework" in card_text.lower() else "Classwork")
            
            # Normalize type
            if "home" in entry_type.lower():
                entry_type = "Homework"
            else:
                entry_type = "Classwork"
                
            # Teacher
            teacher_el = el.select_one("span[style*='darkgray']")
            teacher = teacher_el.get_text(strip=True) if teacher_el else ""
            
            # Summary / Description
            summery_el = el.select_one(".summery-class")
            topic = ""
            desc = ""
            created_at = ""
            
            if summery_el:
                topic_el = summery_el.select_one("label, h6, strong, b")
                if topic_el:
                    topic = topic_el.get_text(strip=True)
                    
                raw_text = summery_el.get_text(separator="\n", strip=True)
                
                # Extract Created at: ...
                created_match = re.search(r"Created at:\s*([0-9]{1,2}:[0-9]{2}\s*(?:AM|PM|am|pm))", raw_text)
                if created_match:
                    created_at = created_match.group(1).strip()
                    raw_text = raw_text.replace(created_match.group(0), "").strip()
                    
                # Clean up lines
                lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
                clean_lines = []
                for line in lines:
                    if topic and line == topic:
                        continue
                    clean_lines.append(line)
                    
                desc = "\n".join(clean_lines).strip()
            else:
                desc = card_text
                
            entries.append({
                "subject": current_subject,
                "type": entry_type,
                "teacher": teacher,
                "topic": topic,
                "description": desc,
                "created_at": created_at
            })
            
    return entries

def scrape_student(page, student_info):
    print(f"Logging in for {student_info['name']} ({student_info['id']})...")
    
    try:
        page.goto("https://omgs.myclassboard.com/", timeout=60000, wait_until="networkidle")
    except Exception as e:
        print(f"Initial navigation notice: {e}")
        
    try:
        page.wait_for_selector("#Username, input[name*='User']", timeout=15000)
        user_input = page.locator("#Username, input[name*='User']").first
        pass_input = page.locator("#Password, input[name*='Pass']").first
        login_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Log In'), button:has-text('Login')").first

        user_input.fill(student_info['id'])
        pass_input.fill(student_info['password'])
        login_btn.click()
        page.wait_for_load_state("domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Login form interaction error: {e}")

    # Navigate to Diary / Homework Calendar view
    diary_url = "https://omgs.myclassboard.com/StudentERP/ERPURLRedirection?urlres=/StudentERP/StaffDiaryToStudent_CalenderView/"
    print(f"Navigating to Diary Calendar view for {student_info['name']}...")
    try:
        page.goto(diary_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
    except Exception as e:
        print(f"Calendar navigation error: {e}")

    content = page.content()
    soup = BeautifulSoup(content, "html.parser")
    entries = parse_diary_soup(soup)
    print(f"Parsed {len(entries)} diary entries for {student_info['name']}.")

    # Clear cookies/session for the next student
    page.context.clear_cookies()

    return {
        "key": student_info["key"],
        "name": student_info["name"],
        "grade": student_info["grade"],
        "category": student_info["category"],
        "icon": student_info["icon"],
        "avatar": student_info.get("avatar", ""),
        "theme": student_info["theme"],
        "entries": entries
    }

def main():
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%A, %B %d, %Y")
    updated_str = now_ist.strftime("%d %b %Y, %I:%M %p IST")

    students = get_student_credentials()
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for st in students:
            try:
                data = scrape_student(page, st)
                results.append(data)
            except Exception as ex:
                print(f"Error scraping {st['name']}: {ex}")
                results.append({
                    "key": st["key"],
                    "name": st["name"],
                    "grade": st["grade"],
                    "category": st["category"],
                    "icon": st["icon"],
                    "avatar": st.get("avatar", ""),
                    "theme": st["theme"],
                    "entries": []
                })

        browser.close()

    payload = {
        "date": today_str,
        "date_iso": now_ist.strftime("%Y-%m-%d"),
        "last_updated": updated_str,
        "students": results
    }

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/homework.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Scraping completed. Wrote {len(results)} students data to docs/data/homework.json.")

    # Auto-refresh Google Sheet with today's homework elements
    webhook_url = os.environ.get("SHEET_WEBHOOK_URL") or "https://script.google.com/macros/s/AKfycbzKKXyacPIxIPuvNvp7cAglDDuD9YmSIaJQ0PZ2X6dFEUSoghixnjkJOhf-q0nrXwSpoA/exec"
    hw_tasks = []
    for st in results:
        for entry in st.get("entries", []):
            if entry.get("type") == "Homework":
                hw_tasks.append({
                    "date": payload.get("date_iso", ""),
                    "student": st["name"],
                    "grade": st["grade"],
                    "subject": entry["subject"],
                    "task": entry["description"].replace("\n", " ").strip(),
                    "status": "Pending",
                    "timestamp": ""
                })
    if hw_tasks and webhook_url:
        import urllib.request
        try:
            print(f"Refreshing Google Sheet with {len(hw_tasks)} current homework tasks...")
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps({"action": "refreshSheet", "date": payload.get("date_iso", ""), "tasks": hw_tasks}).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                print("Google Sheet sync response:", resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Notice during Google Sheet auto-sync: {e}")

if __name__ == "__main__":
    main()
