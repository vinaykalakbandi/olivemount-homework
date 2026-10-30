# 📚 Olivemount Multi-Student Daily Homework Dashboard

A lightweight, automated web dashboard that logs into **Olivemount MyClassBoard** every evening at **6:00 PM IST**, extracts daily homework and classwork updates for both **Sreedyuti (Grade VI)** and **Sreekriti (Grade I)**, publishes them to a single **GitHub Pages** website, and lets the children check off completed homework with real-time logging to a **Google Sheet**.

---

## 🚀 5-Minute Setup Guide

### 1. Create a New GitHub Repository
1. Log in to [GitHub](https://github.com) and click **New Repository**.
2. Name it `olivemount-homework`.
3. Set visibility to **Public** (recommended for free GitHub Pages).
4. Click **Create repository**.

### 2. Push These Project Files
Unzip the downloaded archive and push the files:
```bash
git init
git add .
git commit -m "feat: homework dashboard with interactive checkboxes"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/olivemount-homework.git
git push -u origin main
```

### 3. Add Encrypted Secrets for Both Students
In your GitHub repository:
1. Go to **Settings** → **Secrets and variables** → **Actions**.
2. Under **Repository secrets**, click **New repository secret** and add:
   - `MCB_USER_1`: `<Student 1 Portal ID>` *(Sreedyuti)*
   - `MCB_PASS_1`: `<Student 1 Portal Password>`
   - `MCB_USER_2`: `<Student 2 Portal ID>` *(Sreekriti)*
   - `MCB_PASS_2`: `<Student 2 Portal Password>`

### 4. Enable GitHub Pages & Permissions
1. Under **Settings** → **Actions** → **General**:
   - Set **Workflow permissions** to **Read and write permissions** → click **Save**.
2. Under **Settings** → **Pages**:
   - Set **Source** to **Deploy from a branch**.
   - Select **Branch**: `main` and **Folder**: `/docs`.
   - Click **Save**.

---

## 📊 How to Link Checkboxes to Your Google Sheet

When your child taps a checkbox on the dashboard, it immediately strikes through the task, changes the badge to "Completed ✨", and posts the completion timestamp to your Google Sheet!

### Step 1: Open Your Homework Tracker Sheet
Open your Google Sheet: [Olivemount Daily Homework Tracker](https://docs.google.com/spreadsheets/d/10xisBUoj1jUnTK1tIpmnk7XM5P_Qnw2MfkuGnGuO8VI/edit).

### Step 2: Open Apps Script
1. Inside the Google Sheet, click **Extensions** → **Apps Script**.
2. Replace whatever is in the editor with this two-way sync script:

```javascript
/**
 * Olivemount Homework Tracker - Ongoing Historical Log & Two-Way Sync Engine
 * 1. syncHomeworkTasks(): Appends new tasks without duplicates. NEVER deletes historical records!
 * 2. doGet(): Returns live task statuses for cross-device sync OR triggers GitHub Actions scraper workflow.
 * 3. doPost(): Updates Status and Timestamp in-place. NEVER duplicates rows!
 * 4. triggerGitHubScraper(): Dispatches the GitHub Actions Playwright scraper workflow on demand.
 */

// Helper to normalize dates (handles Date objects, ISO strings, etc.)
function normalizeDateString(val) {
  if (!val) return "";
  if (val instanceof Date) {
    var y = val.getFullYear();
    var m = ("0" + (val.getMonth() + 1)).slice(-2);
    var d = ("0" + val.getDate()).slice(-2);
    return y + "-" + m + "-" + d;
  }
  var str = String(val).trim();
  var match = str.match(/\d{4}-\d{2}-\d{2}/);
  if (match) return match[0];
  var parsed = new Date(str);
  if (!isNaN(parsed.getTime())) {
    var py = parsed.getFullYear();
    var pm = ("0" + (parsed.getMonth() + 1)).slice(-2);
    var pd = ("0" + parsed.getDate()).slice(-2);
    return py + "-" + pm + "-" + pd;
  }
  return str.toLowerCase();
}

// Helper to sanitize strings (supports Telugu Unicode, removes punctuation)
function cleanString(str) {
  if (!str) return "";
  return String(str)
    .toLowerCase()
    .replace(/[^\w\s\u0C00-\u0C7F]/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Appends new tasks to the ongoing log if not already present.
 * NEVER deletes or clears existing days!
 */
function syncHomeworkTasks(tasks, defaultDate) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var lastRow = sheet.getLastRow();
  var headers = ["Date", "Student", "Grade", "Subject", "Homework Task", "Status", "Completed At"];
  
  if (lastRow === 0) {
    sheet.appendRow(headers);
    var headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#EDE9FE");
    headerRange.setFontColor("#3730A3");
    sheet.setFrozenRows(1);
    lastRow = 1;
  }
  
  // Read existing rows to check for duplicates
  var existingData = (lastRow > 1) ? sheet.getRange(2, 1, lastRow - 1, headers.length).getValues() : [];
  var existingKeys = {};
  
  for (var i = 0; i < existingData.length; i++) {
    var r = existingData[i];
    var rDate = normalizeDateString(r[0]);
    var rStudent = cleanString(r[1]);
    var rTask = cleanString(r[4]);
    var key = rDate + "::" + rStudent + "::" + rTask;
    existingKeys[key] = true;
  }
  
  var rowsToAppend = [];
  for (var j = 0; j < tasks.length; j++) {
    var t = tasks[j];
    var taskDate = normalizeDateString(t.date || defaultDate || new Date());
    var taskStudent = cleanString(t.student);
    var taskText = cleanString(t.task);
    var taskKey = taskDate + "::" + taskStudent + "::" + taskText;
    
    // Only append if this exact task on this exact date does not already exist
    if (!existingKeys[taskKey]) {
      rowsToAppend.push([
        taskDate,
        t.student,
        t.grade || "",
        t.subject || "",
        t.task,
        t.status || "Pending",
        t.timestamp || ""
      ]);
      existingKeys[taskKey] = true;
    }
  }
  
  if (rowsToAppend.length > 0) {
    var startRow = sheet.getLastRow() + 1;
    sheet.getRange(startRow, 1, rowsToAppend.length, headers.length).setValues(rowsToAppend);
    sheet.getRange(startRow, 6, rowsToAppend.length, 1).setHorizontalAlignment("center");
    for (var col = 1; col <= headers.length; col++) {
      sheet.autoResizeColumn(col);
    }
  }
  
  return rowsToAppend.length;
}

// 1. GET: Returns current completion statuses for cross-device sync OR triggers scraper
function doGet(e) {
  var params = e ? e.parameter : {};
  var callback = params.callback;

  // On-Demand Scraper Trigger from Webpage Button
  if (params.action === "triggerSync") {
    var triggerResult = triggerGitHubScraper();
    var triggerJson = JSON.stringify(triggerResult);
    if (callback) {
      return ContentService.createTextOutput(callback + "(" + triggerJson + ");")
        .setMimeType(ContentService.MimeType.JAVASCRIPT);
    }
    return ContentService.createTextOutput(triggerJson)
      .setMimeType(ContentService.MimeType.JSON);
  }

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var rows = sheet.getDataRange().getValues();
  var targetDate = normalizeDateString(params.date || "");
  var statusMap = {};
  
  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    var rowDate = normalizeDateString(r[0]);
    var student = String(r[1] || "").trim();
    var task = String(r[4] || "").trim();
    var status = String(r[5] || "").trim();
    var timestamp = String(r[6] || "").trim();
    
    if (!student || !task) continue;
    if (targetDate && rowDate !== targetDate) continue;
    
    var key = cleanString(student) + "::" + cleanString(task);
    statusMap[key] = {
      date: rowDate,
      student: student,
      task: task,
      status: status || "Pending",
      timestamp: timestamp
    };
  }
  
  // If target date yielded no rows, fall back to returning recent rows
  if (targetDate && Object.keys(statusMap).length === 0) {
    for (var i = 1; i < rows.length; i++) {
      var r = rows[i];
      var student = String(r[1] || "").trim();
      var task = String(r[4] || "").trim();
      var status = String(r[5] || "").trim();
      var timestamp = String(r[6] || "").trim();
      if (!student || !task) continue;
      var key = cleanString(student) + "::" + cleanString(task);
      statusMap[key] = {
        date: normalizeDateString(r[0]),
        student: student,
        task: task,
        status: status || "Pending",
        timestamp: timestamp
      };
    }
  }
  
  var jsonString = JSON.stringify({ success: true, tasks: statusMap });
  
  if (callback) {
    return ContentService.createTextOutput(callback + "(" + jsonString + ");")
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  
  return ContentService.createTextOutput(jsonString)
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Dispatches the GitHub Actions daily homework sync scraper workflow.
 * Set GH_TOKEN in Project Settings > Script Properties > GH_TOKEN
 */
function triggerGitHubScraper() {
  var cache = CacheService.getScriptCache();
  if (cache.get("SCRAPER_COOLDOWN")) {
    return {
      success: false,
      message: "A sync was already started in the last 2 minutes. Please wait for it to finish!"
    };
  }
  cache.put("SCRAPER_COOLDOWN", "true", 120);

  var token = PropertiesService.getScriptProperties().getProperty("GH_TOKEN") || "PASTE_YOUR_GITHUB_TOKEN_HERE";
  var url = "https://api.github.com/repos/vinaykalakbandi/olivemount-homework/actions/workflows/update_homework.yml/dispatches";
  
  var options = {
    method: "post",
    headers: {
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github+json",
      "User-Agent": "Olivemount-Homework-Dashboard"
    },
    payload: JSON.stringify({ ref: "main" }),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    if (code === 204 || code === 200) {
      return { success: true, message: "Scraper workflow dispatched successfully!" };
    } else {
      return { success: false, message: "GitHub API returned " + code + ": " + response.getContentText() };
    }
  } catch (err) {
    return { success: false, message: "Request error: " + err.toString() };
  }
}

// 2. POST: In-place update ONLY. Never adds duplicate rows!
function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput(JSON.stringify({ success: true, message: "No post data received" }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var data = JSON.parse(e.postData.contents);
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  // Scraper append / sync request
  if ((data.action === "syncTasks" || data.action === "refreshSheet") && data.tasks) {
    var count = syncHomeworkTasks(data.tasks, data.date);
    return ContentService.createTextOutput(JSON.stringify({ success: true, addedCount: count }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  
  // Checkbox toggle: In-place update ONLY
  var rows = sheet.getDataRange().getValues();
  var targetDate = normalizeDateString(data.date || "");
  var targetStudent = cleanString(data.student);
  var targetTask = cleanString(data.task);
  
  var matchedRowIndex = -1;
  
  // Search from bottom up (newest entries first)
  for (var i = rows.length - 1; i >= 1; i--) {
    var rowDate = normalizeDateString(rows[i][0]);
    var studentInSheet = cleanString(rows[i][1]);
    var taskInSheet = cleanString(rows[i][4]);
    
    var isStudentMatch = (studentInSheet === targetStudent || studentInSheet.indexOf(targetStudent) !== -1 || targetStudent.indexOf(studentInSheet) !== -1);
    var isTaskMatch = (taskInSheet === targetTask || taskInSheet.indexOf(targetTask) !== -1 || targetTask.indexOf(taskInSheet) !== -1);
    var isDateMatch = (!targetDate || rowDate === targetDate);
    
    if (isStudentMatch && isTaskMatch && isDateMatch) {
      matchedRowIndex = i + 1; // 1-based row index in sheet
      break;
    }
  }
  
  // Fallback match without date if date format differed
  if (matchedRowIndex === -1) {
    for (var i = rows.length - 1; i >= 1; i--) {
      var studentInSheet = cleanString(rows[i][1]);
      var taskInSheet = cleanString(rows[i][4]);
      if ((studentInSheet === targetStudent || studentInSheet.indexOf(targetStudent) !== -1 || targetStudent.indexOf(studentInSheet) !== -1) &&
          (taskInSheet === targetTask || taskInSheet.indexOf(targetTask) !== -1 || targetTask.indexOf(taskInSheet) !== -1)) {
        matchedRowIndex = i + 1;
        break;
      }
    }
  }
  
  if (matchedRowIndex > 0) {
    var newStatus = (data.status === "Done") ? "Done" : "Pending";
    var timestamp = (newStatus === "Done") ? (data.timestamp || "") : "";
    
    sheet.getRange(matchedRowIndex, 6).setValue(newStatus); // Column F: Status
    sheet.getRange(matchedRowIndex, 7).setValue(timestamp); // Column G: Completed At
    
    return ContentService.createTextOutput(JSON.stringify({ success: true, updatedRow: matchedRowIndex, status: newStatus }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  
  return ContentService.createTextOutput(JSON.stringify({ success: false, message: "Row not found. No rows added." }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

3. Click **Deploy** (blue button top right) → **New deployment**.
4. Click the gear icon next to "Select type" → choose **Web app**.
5. Set:
   - **Execute as:** `Me`
   - **Who has access:** `Anyone` (this lets the web dashboard send checkbox clicks securely)
6. Click **Deploy** and copy the **Web app URL**.

### Step 3: Connect It on the Dashboard
1. Open your live GitHub Pages dashboard (or the preview).
2. At the bottom, click **⚙️ Settings / Sheet Webhook**.
3. Paste your Web app URL and click **OK**.

That's it! Every time a child checks off a homework item, it instantly updates the status and appends a row with the exact completion time to your Google Sheet.
