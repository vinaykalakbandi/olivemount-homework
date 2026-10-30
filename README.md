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
 * Olivemount Homework Tracker - Fixed In-Place Two-Way Sync Engine
 * 1. refreshCurrentHomeworkSheet(): Clears sheet, formats headers, and writes current homework tasks.
 * 2. doGet(): Returns live task statuses for cross-device sync.
 * 3. doPost(): Updates Status and Timestamp in-place. NEVER adds new rows!
 */

// Helper to sanitize strings (supports Telugu Unicode, removes punctuation)
function cleanString(str) {
  if (!str) return "";
  return String(str)
    .toLowerCase()
    .replace(/[^\w\s\u0C00-\u0C7F]/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Run this once in Apps Script to populate/refresh today's homework
function refreshCurrentHomeworkSheet() {
  var defaultTasks = [
    {
      date: "2026-10-29",
      student: "Sreedyuti Kalakbandi",
      grade: "Grade VI - A",
      subject: "INFORMATION & COMMUNICATION TECHNOLOGY",
      task: "Practise all the HTML tags explained in class."
    },
    {
      date: "2026-10-29",
      student: "Sreedyuti Kalakbandi",
      grade: "Grade VI - A",
      subject: "R1 - ENGLISH",
      task: "CB- pg no: 89 Life Skills Qn 1 (to be written in the CW) GENTLE REMINDER: Start preparing for the Speaking Activity- Topic is give in the WB pg no: 69"
    },
    {
      date: "2026-10-29",
      student: "Sreekriti Kalakbandi",
      grade: "Grade I - A",
      subject: "General",
      task: "Hindi - Class work- Workbook Page number 6,7 done."
    },
    {
      date: "2026-10-29",
      student: "Sreekriti Kalakbandi",
      grade: "Grade I - A",
      subject: "MATHEMATICS",
      task: "complete tb Pg no 79. last two bits"
    },
    {
      date: "2026-10-29",
      student: "Sreekriti Kalakbandi",
      grade: "Grade I - A",
      subject: "R1 - ENGLISH",
      task: "Frame two sentences for the word explore in the notebook and complete tb Pg no 94 bit A"
    },
    {
      date: "2026-10-29",
      student: "Sreekriti Kalakbandi",
      grade: "Grade I - A",
      subject: "R2 - TELUGU/HINDI",
      task: "ట ఠ డ ఢ ణ practice letters in Notebook"
    }
  ];
  return refreshSheetWithTasks(defaultTasks);
}

function refreshSheetWithTasks(tasks, defaultDate) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.clear(); // Clear all old rows
  
  // Set up clean header
  var headers = ["Date", "Student", "Grade", "Subject", "Homework Task", "Status", "Completed At"];
  sheet.appendRow(headers);
  
  var headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight("bold");
  headerRange.setBackground("#EDE9FE"); // Soft pastel purple header
  headerRange.setFontColor("#3730A3");
  sheet.setFrozenRows(1);
  
  var rowsToAdd = [];
  for (var i = 0; i < tasks.length; i++) {
    var t = tasks[i];
    rowsToAdd.push([
      t.date || defaultDate || "2026-10-29",
      t.student,
      t.grade || "",
      t.subject || "",
      t.task,
      t.status || "Pending",
      t.timestamp || ""
    ]);
  }
  
  if (rowsToAdd.length > 0) {
    sheet.getRange(2, 1, rowsToAdd.length, headers.length).setValues(rowsToAdd);
    sheet.getRange(2, 6, rowsToAdd.length, 1).setHorizontalAlignment("center");
  }
  
  for (var col = 1; col <= headers.length; col++) {
    sheet.autoResizeColumn(col);
  }
  
  return rowsToAdd.length;
}

// 1. GET: Returns current completion statuses for cross-device sync
function doGet(e) {
  var params = e ? e.parameter : {};
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var rows = sheet.getDataRange().getValues();
  
  if (rows.length <= 1) {
    refreshCurrentHomeworkSheet();
    rows = sheet.getDataRange().getValues();
  }
  
  var statusMap = {};
  
  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    var student = String(r[1] || "").trim();
    var task = String(r[4] || "").trim();
    var status = String(r[5] || "").trim();
    var timestamp = String(r[6] || "").trim();
    
    if (!student || !task) continue;
    
    var key = cleanString(student) + "::" + cleanString(task);
    statusMap[key] = {
      student: student,
      task: task,
      status: status || "Pending",
      timestamp: timestamp
    };
  }
  
  var callback = params.callback;
  var jsonString = JSON.stringify({ success: true, tasks: statusMap });
  
  if (callback) {
    return ContentService.createTextOutput(callback + "(" + jsonString + ");")
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  
  return ContentService.createTextOutput(jsonString)
    .setMimeType(ContentService.MimeType.JSON);
}

// 2. POST: In-place update ONLY. Never adds new rows!
function doPost(e) {
  // If run manually from Apps Script editor via Run button
  if (!e || !e.postData || !e.postData.contents) {
    var count = refreshCurrentHomeworkSheet();
    return ContentService.createTextOutput(JSON.stringify({ success: true, count: count }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var data = JSON.parse(e.postData.contents);
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  if (data.action === "refreshSheet" && data.tasks) {
    var count = refreshSheetWithTasks(data.tasks, data.date);
    return ContentService.createTextOutput(JSON.stringify({ success: true, count: count }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  
  var rows = sheet.getDataRange().getValues();
  var targetStudent = cleanString(data.student);
  var targetTask = cleanString(data.task);
  
  var matchedRowIndex = -1;
  
  for (var i = 1; i < rows.length; i++) {
    var studentInSheet = cleanString(rows[i][1]);
    var taskInSheet = cleanString(rows[i][4]);
    
    var isStudentMatch = (studentInSheet === targetStudent || studentInSheet.indexOf(targetStudent) !== -1 || targetStudent.indexOf(studentInSheet) !== -1);
    var isTaskMatch = (taskInSheet === targetTask || taskInSheet.indexOf(targetTask) !== -1 || targetTask.indexOf(taskInSheet) !== -1);
    
    if (isStudentMatch && isTaskMatch) {
      matchedRowIndex = i + 1; // 1-based index in sheet
      break;
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
  
  // NEVER ADD NEW ROWS!
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
