"use strict";

const moduleContainer = document.getElementById("module-container");
const courseId = window.location.pathname.split("/").filter(Boolean)[1];
const levelId = new URLSearchParams(window.location.search).get("level");
let currentCourse;

const statusLabels = {
  available: "Disponible",
  pending_environment: "Pendiente de entorno",
  in_progress: "Iniciado",
  approved: "Aprobado",
  completed: "Completado",
  in_development: "En desarrollo",
};

function appendText(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function addList(parent, title, values) {
  const section = document.createElement("section");
  section.className = "lesson-block";
  appendText(section, "h3", title);
  const list = document.createElement("ul");
  values.forEach((value) => appendText(list, "li", value));
  section.append(list);
  parent.append(section);
}

function statusClass(status) {
  if (status === "available" || status === "approved" || status === "completed") {
    return "status-badge status-badge--available";
  }
  if (status === "pending_environment" || status === "in_development") {
    return "status-badge status-badge--preparing";
  }
  return "status-badge";
}

function addMessage(parent, text, state) {
  const box = document.createElement("p");
  box.className = `learning-feedback${state ? ` learning-feedback--${state}` : ""}`;
  box.setAttribute("role", "status");
  box.textContent = text;
  parent.replaceChildren(box);
}

function buildChoiceForm(activity, onSubmit) {
  const form = document.createElement("form");
  form.className = "learning-form";
  const fieldset = document.createElement("fieldset");
  appendText(fieldset, "legend", activity.prompt);
  window.learningClient.shuffleOptions(activity.options).forEach((option) => {
    const label = document.createElement("label");
    label.className = "learning-option";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "answer";
    input.value = option.id;
    label.append(input);
    appendText(label, "span", option.label);
    fieldset.append(label);
  });
  form.append(fieldset);
  const button = document.createElement("button");
  button.className = "button button--primary";
  button.type = "submit";
  button.textContent = "Verificar respuesta";
  form.append(button);
  const feedback = document.createElement("div");
  feedback.setAttribute("aria-live", "polite");
  form.append(feedback);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const selected = form.querySelector('input[name="answer"]:checked');
    onSubmit(selected ? selected.value : null, button, feedback);
  });
  return form;
}

function buildExerciseForm(module, exercise) {
  const section = document.createElement("section");
  section.className = "activity-card";
  section.dataset.moduleId = module.id;
  appendText(section, "p", exercise.title, "activity-card__label");
  appendText(section, "p", exercise.instructions);
  appendText(section, "p", exercise.prompt, "activity-card__prompt");
  const formHost = document.createElement("div");
  section.append(formHost);
  const form = exercise.type === "choice"
    ? buildChoiceForm(exercise, (answer, button, feedback) =>
      submitActivity("/api/learning/submit-exercise", {
        course_id: courseId,
        module_id: module.id,
        exercise_id: exercise.id,
        answer,
      }, button, feedback))
    : exercise.type === "incident_report"
      ? buildIncidentReportForm(module, exercise)
      : exercise.type === "linux_command"
        ? buildLinuxCommandForm(module, exercise)
      : buildInputExercise(module, exercise);
  formHost.append(form);
  return section;
}

function buildLinuxCommandForm(module, exercise) {
  const form = document.createElement("form");
  form.className = "learning-form";
  addList(form, "Comandos de la práctica", exercise.commands);
  const button = document.createElement("button");
  button.className = "button button--primary";
  button.type = "submit";
  button.textContent = "Ejecutar en Ubuntu";
  form.append(button);
  const feedback = document.createElement("div");
  feedback.setAttribute("aria-live", "polite");
  form.append(feedback);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitActivity("/api/learning/submit-exercise", {
      course_id: courseId,
      module_id: module.id,
      exercise_id: exercise.id,
    }, button, feedback);
  });
  return form;
}

function buildIncidentReportForm(module, exercise) {
  const form = document.createElement("form");
  form.className = "learning-form";
  form.dataset.exerciseId = exercise.id;
  const controls = new Map();
  exercise.fields.forEach((field) => {
    const label = document.createElement("label");
    label.className = "learning-field";
    appendText(label, "span", field.label);
    let control;
    if (field.type === "textarea") {
      control = document.createElement("textarea");
      control.rows = 5;
      control.maxLength = field.max_length;
      control.required = true;
    } else {
      control = document.createElement("select");
      control.required = true;
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Selecciona una opción...";
      placeholder.disabled = true;
      placeholder.selected = true;
      control.append(placeholder);
      field.options.forEach((option) => {
        const choice = document.createElement("option");
        choice.value = option.id;
        choice.textContent = option.label;
        control.append(choice);
      });
    }
    control.name = field.id;
    control.setAttribute("aria-label", field.label);
    label.append(control);
    form.append(label);
    controls.set(field.id, control);
  });
  const button = document.createElement("button");
  button.className = "button button--primary";
  button.type = "submit";
  button.textContent = "Verificar informe";
  form.append(button);
  const feedback = document.createElement("div");
  feedback.setAttribute("aria-live", "polite");
  form.append(feedback);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const answer = Object.fromEntries(
      [...controls].map(([fieldId, control]) => [fieldId, control.value.trim()])
    );
    submitActivity("/api/learning/submit-exercise", {
      course_id: courseId,
      module_id: module.id,
      exercise_id: exercise.id,
      answer,
    }, button, feedback);
  });
  return form;
}

function buildInputExercise(module, exercise) {
  const form = document.createElement("form");
  form.className = "learning-form";
  form.dataset.exerciseId = exercise.id;
  let input;
  if (exercise.type === "sql_query") {
    input = document.createElement("textarea");
    input.name = "query";
    input.rows = 4;
    input.maxLength = 4000;
    input.placeholder = "Escribe una consulta SELECT de solo lectura...";
    input.required = true;
    input.setAttribute("aria-label", "Consulta SQL");
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.name = "answer";
    input.maxLength = 100;
    input.autocomplete = "off";
    input.placeholder = exercise.type === "python_result" ? "Escribe tu resultado esperado" : "";
    input.required = true;
    input.setAttribute("aria-label", "Respuesta del ejercicio");
  }
  form.append(input);
  const button = document.createElement("button");
  button.className = "button button--primary";
  button.type = "submit";
  button.textContent = exercise.type === "python_result" ? "Ejecutar verificación Python" : "Ejecutar y verificar SQL";
  form.append(button);
  const feedback = document.createElement("div");
  feedback.setAttribute("aria-live", "polite");
  form.append(feedback);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const field = input.value.trim();
    submitActivity("/api/learning/submit-exercise", {
      course_id: courseId,
      module_id: module.id,
      exercise_id: exercise.id,
      [exercise.type === "sql_query" ? "query" : "answer"]: field,
    }, button, feedback);
  });
  return form;
}

async function submitActivity(path, payload, button, feedback) {
  const linuxRun = courseId === "linux" && Boolean(payload.exercise_id);
  if ((!payload.answer && !payload.query) && !linuxRun) {
    addMessage(feedback, "Completa la respuesta antes de verificarla.", "error");
    return;
  }
  button.disabled = true;
  addMessage(feedback, "Verificando el ejercicio...", "pending");
  try {
    const { result } = await window.learningClient.postJson(path, payload);
    renderActivityResult(feedback, result);
    renderProgress(result.progress);
  } catch (error) {
    addMessage(feedback, `No se pudo verificar: ${error.message}`, "error");
  } finally {
    button.disabled = false;
  }
}

function renderActivityResult(container, result) {
  container.replaceChildren();
  appendText(
    container,
    "p",
    `${result.passed ? "Aprobado" : "Requiere repaso"} · ${result.score_percent}% · intento ${result.attempt_number}`,
    result.passed ? "pass" : "fail"
  );
  appendText(container, "p", result.feedback || "Revisa la retroalimentación.");
  if (result.execution_result) {
    const output = document.createElement("pre");
    const execution = result.execution_result;
    output.textContent = [
      execution.runtime ? `Kernel Ubuntu: ${execution.runtime}` : "",
      execution.commands && execution.commands.length
        ? `Comandos: ${execution.commands.join(", ")}`
        : "",
      execution.stdout || "",
      execution.stderr ? `Error:\n${execution.stderr}` : "",
      execution.error || "",
    ].filter(Boolean).join("\n");
    container.append(output);
  }
  if (result.review_recommendations && result.review_recommendations.length) {
    appendText(container, "p", `Repaso recomendado: ${result.review_recommendations.join(", ")}`);
  }
}

function buildAssessment(module) {
  const section = document.createElement("section");
  section.className = "assessment-card";
  appendText(section, "h3", "Evaluación del módulo");
  appendText(section, "p", `Responde las ${module.assessment.questions.length} preguntas. Puntaje mínimo: ${currentCourse.minimum_score_percent}%. Los intentos son ilimitados y se conserva el historial.`);
  const form = document.createElement("form");
  form.className = "learning-form";
  form.dataset.moduleId = module.id;
  module.assessment.questions.forEach((question, index) => {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "assessment-question";
    appendText(fieldset, "legend", `${index + 1}. ${question.prompt}`);
    window.learningClient.shuffleOptions(question.options).forEach((option) => {
      const label = document.createElement("label");
      label.className = "learning-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = question.id;
      input.value = option.id;
      label.append(input);
      appendText(label, "span", option.label);
      fieldset.append(label);
    });
    form.append(fieldset);
  });
  const button = document.createElement("button");
  button.className = "button button--primary";
  button.type = "submit";
  button.disabled = true;
  button.textContent = "Completa y aprueba ambas prácticas";
  form.append(button);
  const practiceNotice = appendText(
    form,
    "p",
    "La evaluación se habilita al aprobar la práctica guiada y la independiente.",
    "availability-note"
  );
  practiceNotice.dataset.practiceNotice = "true";
  const result = document.createElement("div");
  result.setAttribute("aria-live", "polite");
  form.append(result);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const answers = {};
    module.assessment.questions.forEach((question) => {
      const selected = form.querySelector(`input[name="${CSS.escape(question.id)}"]:checked`);
      if (selected) answers[question.id] = selected.value;
    });
    button.disabled = true;
    addMessage(result, "Corrigiendo evaluación...", "pending");
    try {
      const response = await window.learningClient.postJson("/api/learning/submit-assessment", {
        course_id: courseId,
        module_id: module.id,
        assessment_id: module.assessment.id,
        answers,
      });
      renderAssessmentResult(result, response.result);
      renderProgress(response.result.progress);
    } catch (error) {
      addMessage(result, `No se pudo corregir: ${error.message}`, "error");
    } finally {
      button.disabled = false;
    }
  });
  section.append(form);
  return section;
}

function renderAssessmentResult(container, result) {
  container.replaceChildren();
  appendText(
    container,
    "p",
    `${result.passed ? "Aprobada" : "No aprobada"} · ${result.score_percent}% · ${result.correct_count}/${result.question_count} correctas · intento ${result.attempt_number}`,
    result.passed ? "pass" : "fail"
  );
  result.question_results.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = `question-feedback${item.correct ? " question-feedback--correct" : " question-feedback--incorrect"}`;
    appendText(row, "strong", `Pregunta ${index + 1}: ${item.correct ? "correcta" : "incorrecta"}`);
    appendText(row, "p", item.feedback);
    container.append(row);
  });
  if (result.review_recommendations.length) {
    appendText(container, "p", `Antes de repetir, repasa: ${result.review_recommendations.join(", ")}.`);
  }
  if (result.competency_eligible) {
    appendText(container, "p", "La evaluación y las prácticas cumplen los criterios registrados para la competencia.", "pass");
  }
}

function renderModule(module, progress) {
  const article = document.createElement("article");
  article.className = "learning-module";
  article.dataset.moduleId = module.id;
  appendText(article, "p", `MÓDULO · ${statusLabels[progress?.status] || "Sin iniciar"}`, "course-card__eyebrow");
  appendText(article, "h2", module.title);
  appendText(article, "p", `Objetivo: ${module.objective}`, "module-objective");
  const moduleNotice = appendText(
    article,
    "p",
    "Completa los módulos anteriores para habilitar estas actividades.",
    "availability-note"
  );
  moduleNotice.dataset.moduleAccessNotice = "true";
  moduleNotice.hidden = true;
  addList(article, "Conceptos", module.concepts);

  const explanation = document.createElement("section");
  explanation.className = "lesson-block";
  appendText(explanation, "h3", "Explicación");
  module.explanation.forEach((paragraph) => appendText(explanation, "p", paragraph));
  article.append(explanation);

  const example = document.createElement("section");
  example.className = "worked-example";
  appendText(example, "h3", module.worked_example.title);
  module.worked_example.steps.forEach((step, index) => appendText(example, "p", `${index + 1}. ${step}`));
  if (module.worked_example.query || module.worked_example.code) {
    const code = document.createElement("pre");
    code.textContent = module.worked_example.query || module.worked_example.code;
    example.append(code);
  }
  appendText(example, "p", module.worked_example.result);
  article.append(example);

  appendText(article, "h3", "Práctica guiada");
  article.append(buildExerciseForm(module, module.guided_practice));
  appendText(article, "h3", "Práctica independiente");
  article.append(buildExerciseForm(module, module.independent_practice));
  appendText(article, "p", `Verificación: ${module.verification}`, "availability-note");

  const errors = document.createElement("section");
  errors.className = "lesson-block";
  appendText(errors, "h3", "Errores frecuentes y troubleshooting");
  module.common_errors.forEach((item) => {
    const entry = document.createElement("div");
    entry.className = "troubleshooting-item";
    appendText(entry, "strong", item.error);
    appendText(entry, "p", `Por qué ocurre: ${item.cause}`);
    appendText(entry, "p", `Cómo resolverlo: ${item.recovery}`);
    errors.append(entry);
  });
  article.append(errors);
  article.append(buildAssessment(module));
  return article;
}

function renderProgress(progress) {
  if (!progress) return;
  const courseProgress = progress.courses.find((item) => item.course_id === courseId);
  const moduleRows = progress.modules.filter((item) => item.course_id === courseId);
  const approvedModules = moduleRows.filter((item) => item.status === "completed").length;
  const totalModules = currentCourse.modules.length;
  const percentage = totalModules ? Math.round((approvedModules / totalModules) * 100) : 0;
  const moduleStatus = new Map(moduleRows.map((item) => [item.module_id, item.status]));
  document.querySelectorAll(".learning-module").forEach((article) => {
    const status = moduleStatus.get(article.dataset.moduleId);
    const label = article.querySelector(".course-card__eyebrow");
    label.textContent = `MÓDULO · ${statusLabels[status] || "Sin iniciar"}`;
  });
  const bar = document.getElementById("course-progress-bar");
  bar.value = percentage;
  bar.textContent = `${percentage}%`;
  document.getElementById("course-progress-label").textContent =
    courseProgress ? statusLabels[courseProgress.status] || "Iniciado" : "Sin iniciar";
  let detail = `${approvedModules} de ${totalModules} módulos verificados. Los intentos anteriores se conservan.`;
  if (currentCourse.environment_required) {
    detail += " La competencia operativa no se aprueba sin Ubuntu verificado.";
  }
  document.getElementById("course-progress-detail").textContent = detail;
  updateModuleAccess(progress);
  updateAssessmentAccess(progress);
}

function updateModuleAccess(progress) {
  const environmentReady = !currentCourse.environment_required;
  const completedModules = new Set(
    progress.modules
      .filter((item) => item.course_id === courseId && item.status === "completed")
      .map((item) => item.module_id)
  );
  document.querySelectorAll(".learning-module").forEach((article) => {
    const moduleIndex = currentCourse.modules.findIndex(
      (item) => item.id === article.dataset.moduleId
    );
    const unlocked = environmentReady && moduleIndex >= 0 && currentCourse.modules
      .slice(0, moduleIndex)
      .every((item) => completedModules.has(item.id));
    article.querySelectorAll(".activity-card button").forEach((button) => {
      button.disabled = !unlocked;
    });
    const notice = article.querySelector('[data-module-access-notice="true"]');
    notice.textContent = environmentReady
      ? "Completa los módulos anteriores para habilitar estas actividades."
      : "Las actividades están bloqueadas hasta que Ubuntu/WSL 2 y sus herramientas se verifiquen.";
    notice.hidden = unlocked;
  });
}

function updateAssessmentAccess(progress) {
  const environmentReady = !currentCourse.environment_required;
  const completedModules = new Set(
    progress.modules
      .filter((item) => item.course_id === courseId && item.status === "completed")
      .map((item) => item.module_id)
  );
  const passedExercises = new Set(
    progress.exercises
      .filter((item) => item.course_id === courseId && item.passed)
      .map((item) => `${item.module_id}:${item.exercise_id}`)
  );
  document.querySelectorAll(".assessment-card form").forEach((form) => {
    const moduleIndex = currentCourse.modules.findIndex(
      (item) => item.id === form.dataset.moduleId
    );
    const module = currentCourse.modules[moduleIndex];
    if (!module || moduleIndex < 0) return;
    const previousModulesCompleted = currentCourse.modules
      .slice(0, moduleIndex)
      .every((item) => completedModules.has(item.id));
    const required = environmentReady && [
      module.guided_practice.id,
      module.independent_practice.id,
    ].every((exerciseId) => passedExercises.has(`${module.id}:${exerciseId}`))
      && previousModulesCompleted;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = !required;
    button.textContent = required
      ? "Enviar evaluación"
      : "Completa y aprueba ambas prácticas";
    const notice = form.querySelector('[data-practice-notice="true"]');
    notice.hidden = required;
  });
}

function showLoadError(message) {
  moduleContainer.replaceChildren();
  appendText(moduleContainer, "p", `No se pudo cargar el curso: ${message}`, "fail");
}

async function loadCourse() {
  if (levelId && levelId !== "basic") {
    showLoadError("Esta pantalla solo ofrece el nivel Básico.");
    return;
  }
  try {
    const { course } = await window.learningClient.requestJson(
      `/api/learning/course?course_id=${encodeURIComponent(courseId)}`
    );
    currentCourse = course;
    document.title = `${course.title} Básico | academyLab`;
    document.getElementById("course-title").textContent = course.title;
    document.getElementById("course-breadcrumb").textContent = course.title;
    document.getElementById("course-objective").textContent = course.modules[0].objective;
    const availability = document.getElementById("course-availability");
    availability.textContent = statusLabels[course.availability] || "Estado no definido";
    availability.className = statusClass(course.availability);
    if (course.environment_required) {
      const notice = document.getElementById("environment-notice");
      notice.hidden = false;
      notice.textContent =
        (course.environment_status && course.environment_status.reason) ||
        "Ubuntu/WSL 2 no está disponible. Las prácticas y evaluaciones Linux permanecen bloqueadas.";
    }
    if (course.project_id) document.getElementById("project-link-section").hidden = false;
    const started = await window.learningClient.postJson("/api/learning/start-course", {
      course_id: courseId,
    });
    const { progress } = await window.learningClient.requestJson(
      "/api/learning/progress"
    );
    renderProgress(progress || started.result);
    moduleContainer.replaceChildren(...course.modules.map((module) => {
      const moduleProgress = progress.modules.find(
        (item) => item.course_id === courseId && item.module_id === module.id
      );
      return renderModule(module, moduleProgress);
    }));
    renderProgress(progress || started.result);
  } catch (error) {
    showLoadError(error.message);
  }
}

loadCourse();
