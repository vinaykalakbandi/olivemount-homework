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
// 1. GET: Returns current completion statuses for cross-device sync
function doGet(e) {
  var params = e ? e.parameter : {};
  var targetDate = params.date || "";
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var rows = sheet.getDataRange().getValues();
  
  var statusMap = {};
  
  // Columns: Date (0), Student (1), Grade (2), Subject (3), Task (4), Status (5), Timestamp (6)
  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    var rowDate = String(r[0] || "").trim();
    var student = String(r[1] || "").trim();
    var task = String(r[4] || "").trim();
    var status = String(r[5] || "").trim();
    var timestamp = String(r[6] || "").trim();
    
    if (!student || !task) continue;
    
    var dateMatches = (!targetDate || rowDate === targetDate || rowDate.indexOf(targetDate) !== -1 || targetDate.indexOf(rowDate) !== -1);
    if (dateMatches) {
      var key = (student + "::" + task).toLowerCase();
      statusMap[key] = {
        student: student,
        task: task,
        status: status,
        timestamp: timestamp
      };
    }
  }
  
  var callback = params.callback;
  var jsonString = JSON.stringify({ success: true, tasks: statusMap });
  
  // JSONP support for universal cross-origin device support
  if (callback) {
    return ContentService.createTextOutput(callback + "(" + jsonString + ");")
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  
  return ContentService.createTextOutput(jsonString)
    .setMimeType(ContentService.MimeType.JSON);
}

// 2. POST: Updates existing row in-place (no duplicates!) or appends new row
function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var rows = sheet.getDataRange().getValues();
  
  var targetDate = String(data.date || "").trim();
  var targetStudent = String(data.student || "").trim().toLowerCase();
  var targetTask = String(data.task || "").trim().toLowerCase();
  
  var matchedRowIndex = -1;
  
  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    var rowDate = String(r[0] || "").trim();
    var student = String(r[1] || "").trim().toLowerCase();
    var task = String(r[4] || "").trim().toLowerCase();
    
    var dateMatches = (!targetDate || rowDate === targetDate || rowDate.indexOf(targetDate) !== -1 || targetDate.indexOf(rowDate) !== -1);
    if (dateMatches && student === targetStudent && task === targetTask) {
      matchedRowIndex = i + 1; // 1-based index
      break;
    }
  }
  
  if (matchedRowIndex > 0) {
    // Update existing row in place: Status (Col 6), Timestamp (Col 7)
    sheet.getRange(matchedRowIndex, 6).setValue(data.status);
    sheet.getRange(matchedRowIndex, 7).setValue(data.timestamp);
  } else {
    // Append new row if not present
    sheet.appendRow([
      data.date,
      data.student,
      data.grade,
      data.subject,
      data.task,
      data.status,
      data.timestamp
    ]);
  }
  
  return ContentService.createTextOutput(JSON.stringify({ success: true, updatedRow: matchedRowIndex }))
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
