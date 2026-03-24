/**
 * Podium Task Creator — Gmail Add-on
 *
 * Creates tasks in Podium directly from Gmail.
 * Requires: N8N_WEBHOOK_URL, N8N_PROJECTS_WEBHOOK_URL, and PODIUM_API_KEY
 * set in Script Properties.
 *
 * Setup:
 * 1. Open script.google.com, create a new project
 * 2. Paste this code into Code.gs
 * 3. Copy appsscript.json into the manifest (View > Show manifest file)
 * 4. Set Script Properties (Project Settings > Script Properties):
 *    - N8N_WEBHOOK_URL: your n8n webhook URL for task creation
 *    - N8N_PROJECTS_WEBHOOK_URL: your n8n webhook URL for listing projects
 *    - PODIUM_API_KEY: your Podium API key (pod_...)
 * 5. Deploy > Test deployments > Gmail Add-on
 */

var PROPS = PropertiesService.getScriptProperties();

function getConfig() {
  return {
    webhookUrl: PROPS.getProperty("N8N_WEBHOOK_URL"),
    projectsWebhookUrl: PROPS.getProperty("N8N_PROJECTS_WEBHOOK_URL"),
    apiKey: PROPS.getProperty("PODIUM_API_KEY"),
  };
}

/**
 * Triggered when a Gmail message is opened. Shows the task creation card.
 */
function onGmailMessage(e) {
  var message = getCurrentMessage(e);
  var subject = message ? message.getSubject() : "";
  var body = message ? message.getPlainBody() : "";
  // Truncate body to first 500 chars for description
  if (body.length > 500) {
    body = body.substring(0, 500) + "...";
  }

  return buildTaskCard(subject, body);
}

function getCurrentMessage(e) {
  if (!e || !e.gmail || !e.gmail.messageId) return null;
  return GmailApp.getMessageById(e.gmail.messageId);
}

/**
 * Build the sidebar card UI.
 */
function buildTaskCard(defaultTitle, defaultDescription) {
  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle("Create Podium Task")
      .setSubtitle("From this email")
  );

  var section = CardService.newCardSection();

  // Project dropdown — populated from API
  var projectDropdown = CardService.newSelectionInput()
    .setType(CardService.SelectionInputType.DROPDOWN)
    .setTitle("Project")
    .setFieldName("project_id");

  var projects = fetchProjects();
  for (var i = 0; i < projects.length; i++) {
    var p = projects[i];
    var label = (p.job_code || p.project_number) + " — " + p.name;
    projectDropdown.addItem(label, p.id, i === 0);
  }
  section.addWidget(projectDropdown);

  // Title
  section.addWidget(
    CardService.newTextInput()
      .setFieldName("title")
      .setTitle("Task Title")
      .setValue(defaultTitle || "")
  );

  // Description
  section.addWidget(
    CardService.newTextInput()
      .setFieldName("description")
      .setTitle("Description")
      .setMultiline(true)
      .setValue(defaultDescription || "")
  );

  // Due date
  section.addWidget(
    CardService.newDatePicker()
      .setFieldName("due_date")
      .setTitle("Due Date")
  );

  // Submit button
  section.addWidget(
    CardService.newTextButton()
      .setText("Create Task")
      .setOnClickAction(
        CardService.newAction().setFunctionName("onCreateTask")
      )
      .setTextButtonStyle(CardService.TextButtonStyle.FILLED)
  );

  card.addSection(section);
  return card.build();
}

/**
 * Handle the Create Task button click.
 */
function onCreateTask(e) {
  var formInputs = e.commonEventObject.formInputs;
  var projectId = formInputs.project_id.stringInputs.value[0];
  var title = formInputs.title.stringInputs.value[0];
  var description =
    formInputs.description && formInputs.description.stringInputs
      ? formInputs.description.stringInputs.value[0]
      : "";
  var dueDate =
    formInputs.due_date && formInputs.due_date.dateInput
      ? formInputs.due_date.dateInput.msSinceEpoch
      : null;

  if (!title) {
    return notify("Please enter a task title.");
  }

  var config = getConfig();
  if (!config.webhookUrl || !config.apiKey || !config.projectsWebhookUrl) {
    return notify("Add-on not configured. Set N8N_WEBHOOK_URL, N8N_PROJECTS_WEBHOOK_URL, and PODIUM_API_KEY in Script Properties.");
  }

  var payload = {
    project_id: projectId,
    title: title,
    description: description,
    status: "todo",
    api_key: config.apiKey,
  };

  if (dueDate) {
    var d = new Date(dueDate);
    payload.due_date =
      d.getFullYear() +
      "-" +
      String(d.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(d.getDate()).padStart(2, "0");
  }

  try {
    var response = UrlFetchApp.fetch(config.webhookUrl, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    });

    var code = response.getResponseCode();
    if (code >= 200 && code < 300) {
      return notify("Task created in Podium!");
    } else {
      Logger.log("Error: " + response.getContentText());
      return notify("Failed to create task (HTTP " + code + "). Check logs.");
    }
  } catch (err) {
    Logger.log("Exception: " + err);
    return notify("Error: " + err.message);
  }
}

/**
 * Fetch active projects from Podium via n8n relay.
 */
function fetchProjects() {
  var config = getConfig();
  if (!config.projectsWebhookUrl || !config.apiKey) return [];

  var projectsUrl = config.projectsWebhookUrl;

  try {
    var response = UrlFetchApp.fetch(projectsUrl, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ api_key: config.apiKey }),
      muteHttpExceptions: true,
    });

    if (response.getResponseCode() === 200) {
      return JSON.parse(response.getContentText());
    }
  } catch (err) {
    Logger.log("Failed to fetch projects: " + err);
  }
  return [];
}

/**
 * Show a notification card.
 */
function notify(message) {
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText(message))
    .build();
}
