/**
 * Olivemount Homework Tracker - Complete Apps Script Engine
 * 1. refreshCurrentHomeworkSheet(): Clears sheet, formats headers, and writes current homework tasks.
 * 2. doGet(): Returns live task statuses for cross-device sync OR triggers GitHub Actions scraper workflow.
 * 3. doPost(): Updates Status and Timestamp in-place. NEVER adds duplicate rows!
 * 4. triggerGitHubScraper(): Dispatches the GitHub Actions Playwright scraper workflow on demand.
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

// Fallback initial task loader
function refreshCurrentHomeworkSheet() {
  var defaultTasks = [
    {
      date: "2026-10-30",
      student: "Sreedyuti Kalakbandi",
      grade: "Grade VI - A",
      subject: "MATHEMATICS",
      task: "Perimeter and area pg 138 figure it out 3rd problem. Cut the tangram at the end of the text book. Cut the triangles and quadrilaterals seperately. Bring A4 sheet and glue."
    },
    {
      date: "2026-10-30",
      student: "Sreedyuti Kalakbandi",
      grade: "Grade VI - A",
      subject: "SOCIAL SCIENCE",
      task: "Dear Students, A written quiz will be conducted on Monday, 2 November 2026, on the topic 'E-Waste Management.' Kindly prepare well. All the best!"
    }
  ];
  return refreshSheetWithTasks(defaultTasks, "2026-10-30");
}

function refreshSheetWithTasks(tasks, defaultDate) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.clear(); // Clear all old rows
  
  // Clean headers
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
      t.date || defaultDate || new Date().toISOString().split("T")[0],
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
  // If run manually from Apps Script editor via Run button
  if (!e || !e.postData || !e.postData.contents) {
    var count = refreshCurrentHomeworkSheet();
    return ContentService.createTextOutput(JSON.stringify({ success: true, count: count }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var data = JSON.parse(e.postData.contents);
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  // Called by daily scraper script to refresh current active tasks
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
      matchedRowIndex = i + 1; // 1-based row index in sheet
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
