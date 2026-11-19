"use strict";

const form = document.getElementById("project-form");
const resultBox = document.getElementById("project-result");
const submitButton = document.getElementById("submit-project");

function appendText(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function showMessage(text, state) {
  resultBox.replaceChildren();
  appendText(resultBox, "p", text, state ? `learning-feedback learning-feedback--${state}` : "");
}

function populateSelect(selectId, field) {
  const select = document.getElementById(selectId);
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Selecciona una opción...";
  placeholder.selected = true;
  placeholder.disabled = true;
  select.required = true;
  select.append(placeholder);
  window.learningClient.shuffleOptions(field.options).forEach((option) => {
    const element = document.createElement("option");
    element.value = option.id;
    element.textContent = option.label;
    select.append(element);
  });
}

function populateChoices(elementId, title, options, name) {
  const fieldset = document.getElementById(elementId);
  fieldset.querySelector("legend").textContent = title;
  window.learningClient.shuffleOptions(options).forEach((option) => {
    const label = document.createElement("label");
    label.className = "learning-option";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = name;
    input.value = option.id;
    input.required = true;
    label.append(input);
    appendText(label, "span", option.label);
    fieldset.append(label);
  });
}

async function loadFixture(path, targetId) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`No se pudo cargar ${path} (HTTP ${response.status}).`);
  document.getElementById(targetId).textContent = await response.text();
}

function showProjectResult(result) {
  resultBox.replaceChildren();
  const statusText = result.status === "approved"
    ? "Proyecto aprobado: todos los criterios, incluido Linux real, fueron verificados."
    : result.status === "blocked_environment"
      ? "Verificación completa de criterios disponibles; aprobación bloqueada por Ubuntu real."
      : result.status === "blocked_prerequisites"
        ? "Aprobación bloqueada: falta completar Linux Básico con evidencia real."
        : "Intento guardado. Revisa los criterios que requieren corrección.";
  const resultClass = result.status === "approved"
    ? "learning-feedback learning-feedback--success"
    : result.status === "blocked_environment" || result.status === "blocked_prerequisites"
      ? "learning-feedback learning-feedback--pending"
      : "learning-feedback learning-feedback--error";
  appendText(
    resultBox,
    "p",
    `${statusText} Puntaje observado: ${result.score_percent}% · intento ${result.attempt_number}.`,
    resultClass
  );
  appendText(resultBox, "p", `ID de intento: ${result.attempt_id}`);

  const criteria = document.createElement("ul");
  criteria.className = "criterion-results";
  result.criteria.forEach((criterion) => {
    const row = document.createElement("li");
    row.className = criterion.passed ? "criterion-results__pass" : "criterion-results__fail";
    appendText(row, "strong", `${criterion.passed ? "PASS" : criterion.id === "linux" ? "PENDIENTE" : "FAIL"} · ${criterion.id}`);
    appendText(row, "p", criterion.feedback);
    criteria.append(row);
  });
  resultBox.append(criteria);
  if (result.python_result) {
    appendText(resultBox, "h3", "Resultado real del procesador Python");
    const output = document.createElement("pre");
    output.textContent = JSON.stringify(result.python_result, null, 2);
    resultBox.append(output);
  }
  if (result.sql_result) {
    appendText(resultBox, "h3", "Resultado SQL");
    const output = document.createElement("pre");
    output.textContent = JSON.stringify(result.sql_result, null, 2);
    resultBox.append(output);
  } else if (result.sql_error) {
    appendText(resultBox, "p", `SQL: ${result.sql_error}`, "fail");
  }
  if (result.linux_analysis) {
    appendText(resultBox, "h3", "Verificación real del log en Ubuntu");
    const output = document.createElement("pre");
    output.textContent = [
      result.linux_analysis.runtime
        ? `Kernel Ubuntu: ${result.linux_analysis.runtime}`
        : "",
      result.linux_analysis.commands && result.linux_analysis.commands.length
        ? `Comandos: ${result.linux_analysis.commands.join(", ")}`
        : "",
      result.linux_analysis.stdout || "",
      result.linux_analysis.stderr
        ? `Error:\n${result.linux_analysis.stderr}`
        : "",
      result.linux_analysis.error || "",
    ].filter(Boolean).join("\n");
    resultBox.append(output);
  }
  if (result.progress) {
    appendText(resultBox, "p", "El intento quedó disponible en Mi progreso.");
  }
}

async function loadProject() {
  try {
    const [{ project }, { progress }] = await Promise.all([
      window.learningClient.requestJson("/api/learning/project"),
      window.learningClient.requestJson("/api/learning/progress"),
      loadFixture("/course-data/basic_capstone_events.log", "event-fixture"),
      loadFixture("/course-data/basic_capstone_operations.csv", "operations-fixture"),
    ]);
    document.title = `${project.title} | academyLab`;
    document.getElementById("project-title").textContent = project.title;
    document.getElementById("project-objective").textContent = project.objective;
    document.getElementById("project-scenario").textContent = project.scenario;
    document.getElementById("environment-requirement").textContent = project.environment_requirement;
    document.getElementById("environment-notice").textContent = project.linux_notice;
    document.getElementById("primary-id-label").textContent =
      project.report_fields.find((field) => field.id === "primary_id").label;

    const tasks = document.getElementById("project-tasks");
    project.tasks.forEach((task) => appendText(tasks, "li", task));
    const acceptance = document.getElementById("acceptance-criteria");
    project.acceptance_criteria.forEach((criterion) => {
      const item = document.createElement("li");
      item.textContent = `${criterion.label}${criterion.automatic ? " · verificación automática" : " · requiere entorno real"}`;
      acceptance.append(item);
    });

    populateChoices("network-options", project.network_question, project.network_options, "network-answer");
    populateChoices("aws-options", project.aws_question, project.aws_options, "aws-answer");
    populateSelect("cause-status", project.report_fields.find((field) => field.id === "cause_status"));
    populateSelect("next-step", project.report_fields.find((field) => field.id === "next_step"));
    populateSelect("impact-statement", project.report_fields.find((field) => field.id === "impact_statement"));
    const earned = new Set(progress.competencies.map((item) => item.competency_id));
    const missing = project.prerequisites
      .filter((item) => !earned.has(item.id))
      .map((item) => item.title);
    submitButton.disabled = missing.length > 0;
    document.getElementById("project-status").textContent = missing.length
      ? `Bloqueado por requisitos previos: ${missing.join(", ")}.`
      : project.availability === "pending_environment"
        ? "Disponible para verificación parcial · aprobación final pendiente del entorno Ubuntu"
        : "Disponible";
    if (missing.length) {
      showMessage("Completa y aprueba las competencias previas antes de enviar el proyecto.", "pending");
    }
  } catch (error) {
    showMessage(`No se pudo cargar el proyecto: ${error.message}`, "error");
    submitButton.disabled = true;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const selectedRadio = (name) => form.querySelector(`input[name="${name}"]:checked`)?.value;
  const splitIds = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
  const answers = {
    error_ids: splitIds(document.getElementById("error-ids").value),
    pending_ids: splitIds(document.getElementById("pending-ids").value),
    sql_query: document.getElementById("project-sql").value,
    python_error_amount: document.getElementById("python-error-amount").value,
    network_answer: selectedRadio("network-answer"),
    aws_answer: selectedRadio("aws-answer"),
    report: {
      primary_id: document.getElementById("primary-id").value,
      cause_status: document.getElementById("cause-status").value,
      next_step: document.getElementById("next-step").value,
      impact_statement: document.getElementById("impact-statement").value,
      summary: document.getElementById("incident-summary").value,
    },
  };
  submitButton.disabled = true;
  showMessage("Ejecutando verificaciones y guardando el intento...", "pending");
  try {
    const response = await window.learningClient.postJson("/api/learning/submit-project", {
      answers,
    });
    showProjectResult(response.result);
  } catch (error) {
    showMessage(`No se pudo verificar el proyecto: ${error.message}`, "error");
  } finally {
    submitButton.disabled = false;
  }
});

loadProject();
