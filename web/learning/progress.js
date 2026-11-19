"use strict";

const courseList = document.getElementById("course-progress-list");
const competencyList = document.getElementById("competency-list");
const attemptList = document.getElementById("attempt-list");
const evidenceList = document.getElementById("evidence-list");
const statusLabels = {
  in_progress: "En curso",
  approved: "Aprobado",
  completed: "Completado",
  pending_environment: "Pendiente de entorno",
  passed: "Aprobado",
  needs_review: "Requiere repaso",
  blocked_environment: "Bloqueado por entorno",
};

function appendText(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function renderCourses(progress, catalog) {
  courseList.replaceChildren();
  if (!progress.courses.length) {
    appendText(courseList, "p", "Todavía no hay cursos iniciados.", "empty");
    return;
  }
  progress.courses.forEach((courseProgress) => {
    const course = catalog.courses.find((item) => item.id === courseProgress.course_id);
    const card = document.createElement("article");
    card.className = "progress-course-card";
    appendText(card, "h3", course ? course.title : courseProgress.course_id);
    appendText(card, "p", `Estado: ${statusLabels[courseProgress.status] || courseProgress.status}`);
    const modules = progress.modules.filter((item) => item.course_id === courseProgress.course_id);
    const completed = modules.filter((item) => item.status === "completed").length;
    if (modules.length) {
      appendText(card, "p", `Módulos verificados: ${completed}/${modules.length}`);
    } else {
      const projectAttempt = progress.attempts.find(
        (item) => item.course_id === courseProgress.course_id && item.activity_type === "project"
      );
      appendText(
        card,
        "p",
        projectAttempt
          ? `Proyecto integrador: ${statusLabels[projectAttempt.status] || projectAttempt.status} · ${projectAttempt.score_percent}%`
          : "Proyecto integrador: aún no iniciado."
      );
    }
    modules.forEach((module) => {
      const moduleMeta = catalog.modules.find((item) => item.id === module.module_id);
      appendText(card, "p", `${moduleMeta?.title || module.module_id}: ${statusLabels[module.status] || module.status}`);
    });
    if (courseProgress.blocked_reason) {
      appendText(card, "p", `Bloqueo: ${courseProgress.blocked_reason}`, "availability-note");
    }
    if (course) {
      const link = document.createElement("a");
      link.href = course.id === "production-support"
        ? "/courses/production-support/?level=basic"
        : `/courses/${encodeURIComponent(course.id)}/?level=basic`;
      link.textContent = "Continuar curso";
      card.append(link);
    }
    courseList.append(card);
  });
}

function renderCompetencies(progress, catalog) {
  competencyList.replaceChildren();
  if (!progress.competencies.length) {
    appendText(competencyList, "p", "Aún no hay competencias aprobadas. Los cursos con requisitos de entorno no se aprobarán hasta que se verifiquen.", "empty");
    return;
  }
  progress.competencies.forEach((award) => {
    const competency = catalog.competencies.find((item) => item.id === award.competency_id);
    const card = document.createElement("article");
    card.className = "progress-course-card";
    appendText(card, "h3", competency ? competency.title : award.competency_id);
    appendText(card, "p", `Aprobada: ${formatDate(award.awarded_at)}`);
    appendText(card, "p", `Curso: ${award.course_id} · intento ${award.attempt_id}`);
    competencyList.append(card);
  });
}

function renderAttempts(progress, catalog) {
  attemptList.replaceChildren();
  if (!progress.attempts.length) {
    appendText(attemptList, "p", "Todavía no hay intentos guardados.", "empty");
    return;
  }
  progress.attempts.forEach((attempt) => {
    const card = document.createElement("details");
    card.className = "attempt-card";
    const summary = document.createElement("summary");
    const course = catalog.courses.find((item) => item.id === attempt.course_id);
    summary.textContent =
      `${course ? course.title : attempt.course_id} · ${attempt.activity_type} · intento ${attempt.attempt_number} · ${attempt.score_percent}% · ${statusLabels[attempt.status] || attempt.status} · ${formatDate(attempt.created_at)}`;
    card.append(summary);
    const answers = document.createElement("section");
    appendText(answers, "h4", "Respuestas enviadas");
    const answerOutput = document.createElement("pre");
    try {
      answerOutput.textContent = JSON.stringify(JSON.parse(attempt.answers_json), null, 2);
    } catch (error) {
      answerOutput.textContent = "No se pudieron leer las respuestas guardadas.";
    }
    answers.append(answerOutput);
    appendText(answers, "h4", "Resultado y retroalimentación");
    const resultOutput = document.createElement("pre");
    try {
      resultOutput.textContent = JSON.stringify(JSON.parse(attempt.result_json), null, 2);
    } catch (error) {
      resultOutput.textContent = "No se pudo leer el resultado guardado.";
    }
    answers.append(resultOutput);
    card.append(answers);
    attemptList.append(card);
  });
}

function renderEvidence(progress, catalog) {
  evidenceList.replaceChildren();
  if (!progress.evidence.length) {
    appendText(evidenceList, "p", "No hay evidencias generadas todavía.", "empty");
    return;
  }
  progress.evidence.forEach((item) => {
    const card = document.createElement("article");
    card.className = "attempt-card";
    const course = catalog.courses.find((entry) => entry.id === item.course_id);
    appendText(card, "h3", item.kind);
    appendText(card, "p", item.summary);
    appendText(card, "p", `${course ? course.title : item.course_id} · ${formatDate(item.created_at)} · intento ${item.attempt_id}`);
    evidenceList.append(card);
  });
}

async function loadProgress() {
  document.getElementById("learner-notice").textContent =
    "Perfil local administrado por el servidor; el progreso se guarda en SQLite en este equipo.";
  const errorBox = document.getElementById("progress-error");
  errorBox.replaceChildren();
  try {
    const [{ progress }, catalog] = await Promise.all([
      window.learningClient.requestJson(
        "/api/learning/progress"
      ),
      window.learningClient.requestJson("/catalog/learning_catalog.json"),
    ]);
    renderCourses(progress, catalog);
    renderCompetencies(progress, catalog);
    renderAttempts(progress, catalog);
    renderEvidence(progress, catalog);
  } catch (error) {
    appendText(errorBox, "p", `No se pudo consultar el progreso: ${error.message}`, "fail");
  }
}

document.getElementById("refresh-progress").addEventListener("click", loadProgress);
loadProgress();
