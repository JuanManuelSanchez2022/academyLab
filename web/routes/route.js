"use strict";

const routeCourses = document.getElementById("route-courses");
const capstoneContent = document.getElementById("capstone-content");
const levelNavigation = document.getElementById("level-navigation");
const availabilityLabels = {
  available: "Disponible",
  in_development: "En desarrollo",
  pending_environment: "Pendiente de entorno",
  blocked_prerequisites: "Bloqueado por requisitos previos",
};
const progressStatusLabels = {
  in_progress: "En curso",
  approved: "Aprobado",
  pending_environment: "Pendiente de entorno",
  blocked_environment: "Bloqueado por entorno",
  blocked_prerequisites: "Bloqueado por competencia Linux",
};
const pathParts = window.location.pathname.split("/").filter(Boolean);
const routeId = pathParts[1];
const levelId = pathParts[2];

function appendText(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function appendList(parent, title, values) {
  const section = document.createElement("section");
  section.className = "route-detail";
  appendText(section, "h4", title);
  const list = document.createElement("ul");
  values.forEach((value) => appendText(list, "li", value));
  section.append(list);
  parent.append(section);
}

function statusClass(status) {
  if (status === "available") return "status-badge status-badge--available";
  if (status === "in_development" || status === "pending_environment") {
    return "status-badge status-badge--preparing";
  }
  return "status-badge";
}

function renderCourse(course, level, levelTitle, catalog, recommendedOrder) {
  const levelContent = course.contents_by_level[level.id];
  if (!levelContent) throw new Error(`El curso ${course.id} no tiene contenido de catálogo para este nivel.`);

  const card = document.createElement("article");
  card.className = "route-course-card";
  const heading = document.createElement("div");
  heading.className = "route-course-card__heading";
  const copy = document.createElement("div");
  appendText(copy, "p", `${levelTitle.toUpperCase()} · ORDEN RECOMENDADO ${String(recommendedOrder).padStart(2, "0")}`, "course-card__eyebrow");
  appendText(copy, "h3", course.title);
  heading.append(copy);
  appendText(heading, "span", availabilityLabels[levelContent.availability] || "Estado no definido", statusClass(levelContent.availability));
  card.append(heading);

  appendText(card, "p", course.objective, "route-course-card__objective");
  appendList(card, "Contenidos previstos", levelContent.contents);
  appendList(
    card,
    "Requisitos previos",
    levelContent.prerequisites.length
      ? levelContent.prerequisites.map((id) => catalog.competencies.find((item) => item.id === id)?.title || id)
      : ["Sin requisitos previos dentro de esta ruta."]
  );
  appendText(card, "p", levelContent.availability_note, "availability-note");

  if (level.id === "basic" && ["available", "pending_environment"].includes(levelContent.availability)) {
    const courseLink = document.createElement("a");
    courseLink.className = "button button--primary course-entry-link";
    courseLink.href = `/courses/${encodeURIComponent(course.id)}/?level=basic`;
    courseLink.textContent = levelContent.availability === "pending_environment"
      ? "Ver curso · entorno pendiente →"
      : "Ingresar al curso Básico →";
    card.append(courseLink);
  }

  const tracking = document.createElement("div");
  tracking.className = "course-tracking";
  const progress = appendText(tracking, "p", "Progreso: consultando...");
  progress.className = "course-progress-summary";
  const evaluation = appendText(tracking, "p", "Evaluación: consultando...");
  evaluation.className = "course-evaluation-summary";
  card.append(tracking);
  card.dataset.courseId = course.id;

  const resources = (course.resources || []).filter((resource) =>
    resource.availability === "available" &&
    (!resource.level_ids || resource.level_ids.includes(level.id))
  );
  resources.forEach((resource) => {
    const resourceCard = document.createElement("div");
    resourceCard.className = "available-resource";
    appendText(resourceCard, "p", `Recurso operativo · ${availabilityLabels[resource.availability]}`, "eyebrow");
    appendText(resourceCard, "p", resource.description);
    const link = document.createElement("a");
    link.className = "button button--primary";
    link.href = resource.url;
    link.textContent = `Abrir ${resource.title} →`;
    resourceCard.append(link);
    card.append(resourceCard);
  });
  return card;
}

function renderLevelNavigation(levels) {
  const fragment = document.createDocumentFragment();
  levels.forEach((level) => {
    const link = document.createElement("a");
    link.className = `level-navigation__link${level.id === levelId ? " level-navigation__link--active" : ""}`;
    link.href = `/routes/${encodeURIComponent(routeId)}/${encodeURIComponent(level.id)}/`;
    if (level.id === levelId) link.setAttribute("aria-current", "page");
    link.textContent = level.title;
    fragment.append(link);
  });
  levelNavigation.replaceChildren(fragment);
}

function renderCapstone(capstone, catalog) {
  capstoneContent.replaceChildren();
  appendText(capstoneContent, "h3", capstone.title);
  appendText(capstoneContent, "p", capstone.objective);
  appendText(
    capstoneContent,
    "p",
    `Estado: ${availabilityLabels[capstone.availability] || "En desarrollo"}. Consulta el alcance y los criterios verificables del proyecto.`,
    "availability-note"
  );
  appendList(capstoneContent, "Criterios de aceptación previstos", capstone.acceptance_criteria);
  if (capstone.prerequisites && capstone.prerequisites.length) {
    appendList(
      capstoneContent,
      "Competencias requeridas antes del envío",
      capstone.prerequisites.map((id) => catalog.competencies.find((item) => item.id === id)?.title || id)
    );
  }
  appendText(
    capstoneContent,
    "p",
    `Criterio general propuesto: puntaje mínimo ${catalog.evaluation_model.minimum_score_percent}%, además de cumplir los criterios de aceptación.`
  );
  if (capstone.id === "support-basic-integrator") {
    const link = document.createElement("a");
    link.className = "button button--primary";
    link.href = "/projects/support-basic/";
    link.textContent = "Abrir proyecto y verificar criterios disponibles →";
    capstoneContent.append(link);
  }
}

function renderLevelProgress(routeLevel, catalog, progress) {
  const summary = document.getElementById("level-progress-summary");
  const progressBar = document.getElementById("level-progress-bar");
  const note = document.getElementById("level-progress-note");
  const courses = routeLevel.course_ids
    .map((courseId) => catalog.courses.find((item) => item.id === courseId))
    .filter(Boolean);
  const availableCourses = courses.filter(
    (course) => course.contents_by_level[levelId]?.availability === "available"
  );
  const approvedCourses = availableCourses.filter((course) =>
    progress.courses.some(
      (item) => item.course_id === course.id && item.status === "approved"
    )
  );
  const percent = availableCourses.length
    ? Math.round((approvedCourses.length / availableCourses.length) * 100)
    : 0;
  const pendingEnvironment = courses
    .filter((course) => course.contents_by_level[levelId]?.availability === "pending_environment")
    .map((course) => course.title);
  const blockedCourses = courses
    .filter((course) => course.contents_by_level[levelId]?.availability === "blocked_prerequisites")
    .map((course) => course.title);
  const projectAttempt = progress.attempts.find(
    (attempt) => attempt.course_id === "production-support" && attempt.activity_type === "project"
  );

  summary.textContent = availableCourses.length
    ? `${approvedCourses.length}/${availableCourses.length} cursos disponibles aprobados · ${percent}%`
    : "Sin cursos disponibles";
  progressBar.value = percent;
  note.textContent = [
    pendingEnvironment.length
      ? `Pendiente de entorno: ${pendingEnvironment.join(", ")}; no se incluye en el porcentaje.`
      : "",
    blockedCourses.length
      ? `Bloqueado por requisitos previos: ${blockedCourses.join(", ")}.`
      : "",
    routeLevel.capstone
      ? `Evaluación final: ${projectAttempt
        ? `${progressStatusLabels[projectAttempt.status] || projectAttempt.status} · ${projectAttempt.score_percent}%.`
        : "pendiente; aún no hay intentos guardados."}`
      : "",
  ].filter(Boolean).join(" ");
}

async function loadLearnerProgress(catalog, routeLevel) {
  const courseCards = [...routeCourses.querySelectorAll("[data-course-id]")];
  try {
    const { progress } = await window.learningClient.requestJson("/api/learning/progress");
    renderLevelProgress(routeLevel, catalog, progress);
    const moduleCourse = new Map(
      catalog.modules.map((module) => [module.id, module.course_id])
    );
    const evaluationModule = new Map(
      catalog.evaluations.map((evaluation) => [evaluation.id, evaluation.module_id])
    );
    courseCards.forEach((card) => {
      const courseId = card.dataset.courseId;
      const course = catalog.courses.find((item) => item.id === courseId);
      const courseProgress = progress.courses.find((item) => item.course_id === courseId);
      const moduleIds = (course.contents_by_level[levelId]?.module_ids || []);
      const completed = progress.modules.filter(
        (item) => moduleIds.includes(item.module_id) && item.status === "completed"
      ).length;
      const pendingEnvironment = progress.modules.some(
        (item) => moduleIds.includes(item.module_id) && item.status === "pending_environment"
      );
      const progressText = courseProgress
        ? `${progressStatusLabels[courseProgress.status] || courseProgress.status} · ${completed}/${moduleIds.length} módulos verificados${pendingEnvironment ? " · entorno pendiente" : ""}`
        : "Sin iniciar · 0 módulos verificados";
      card.querySelector(".course-progress-summary").textContent = `Progreso: ${progressText}.`;

      const evaluationIds = catalog.evaluations
        .filter((evaluation) => evaluationModule.get(evaluation.id) &&
          moduleCourse.get(evaluationModule.get(evaluation.id)) === courseId)
        .map((evaluation) => evaluation.id);
      const attempts = progress.attempts.filter(
        (attempt) => attempt.course_id === courseId &&
          attempt.activity_type === "assessment" &&
          evaluationIds.includes(attempt.activity_id)
      );
      const latest = attempts[0];
      let evaluationText = latest
        ? `Evaluación: ${latest.passed ? "aprobada" : "pendiente"} · último intento ${latest.score_percent}%.`
        : "Evaluación: pendiente · aún no hay intentos.";
      if (courseId === "production-support") {
        const projectAttempt = progress.attempts.find(
          (attempt) => attempt.course_id === courseId && attempt.activity_type === "project"
        );
        if (projectAttempt) {
          evaluationText += ` Proyecto: ${progressStatusLabels[projectAttempt.status] || projectAttempt.status} · ${projectAttempt.score_percent}%.`;
        }
      }
      card.querySelector(".course-evaluation-summary").textContent = evaluationText;
    });
  } catch (error) {
    document.getElementById("level-progress-summary").textContent = "Progreso no disponible";
    document.getElementById("level-progress-note").textContent =
      `No se pudo consultar el avance local: ${error.message}`;
    courseCards.forEach((card) => {
      card.querySelector(".course-progress-summary").textContent =
        `Progreso: no disponible (${error.message}).`;
      card.querySelector(".course-evaluation-summary").textContent =
        "Evaluación: no se pudo consultar el historial local.";
    });
  }
}

async function loadRoute() {
  try {
    const response = await fetch("/catalog/learning_catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Error HTTP ${response.status}`);
    const catalog = await response.json();
    const route = catalog.routes.find((item) => item.id === routeId);
    const level = catalog.levels.find((item) => item.id === levelId);
    const routeLevel = route?.levels.find((item) => item.level_id === levelId);
    if (!route || !level || !routeLevel) throw new Error("La ruta o el nivel solicitado no existe.");

    document.title = `${level.title} · Cloud / Production Support | academyLab`;
    document.getElementById("route-title").textContent = `Nivel ${level.title}`;
    document.getElementById("level-breadcrumb").textContent = level.title;
    document.getElementById("route-description").textContent =
      `${level.description} ${level.competency_summary}`;
    renderLevelNavigation(catalog.levels);

    const coursesById = new Map(catalog.courses.map((course) => [course.id, course]));
    const selectedCourses = routeLevel.course_ids.map((id, index) => {
      const course = coursesById.get(id);
      if (!course) throw new Error(`El curso ${id} no está definido en el catálogo.`);
      return renderCourse(course, level, level.title, catalog, index + 1);
    });
    routeCourses.replaceChildren(...selectedCourses);
    renderCapstone(routeLevel.capstone, catalog);
    await loadLearnerProgress(catalog, routeLevel);
  } catch (error) {
    routeCourses.replaceChildren();
    appendText(routeCourses, "p", `No se pudo cargar esta ruta: ${error.message}`, "empty");
    capstoneContent.replaceChildren();
    appendText(capstoneContent, "p", "No se pudo cargar el proyecto integrador.", "empty");
  }
}

loadRoute();
