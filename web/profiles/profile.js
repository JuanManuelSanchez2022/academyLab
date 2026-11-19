"use strict";

const levelGrid = document.getElementById("level-grid");
const levelPaths = {
  basic: "Básico",
  intermediate: "Intermedio",
  advanced: "Avanzado",
};

function appendText(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function renderLevel(level, route) {
  const card = document.createElement("article");
  card.className = "course-card level-card";
  appendText(card, "p", `NIVEL ${String(level.order).padStart(2, "0")}`, "course-card__eyebrow");
  appendText(card, "h3", level.title);
  appendText(card, "p", level.description, "course-card__description");
  appendText(card, "p", `Competencias esperadas: ${level.competency_summary}`, "level-card__outcome");

  const count = route.levels.find((entry) => entry.level_id === level.id)?.course_ids.length || 0;
  appendText(card, "p", `${count} cursos en la ruta · contenidos sujetos a disponibilidad`, "level-card__meta");

  const link = document.createElement("a");
  link.className = "button button--primary course-card__action";
  link.href = `/routes/${encodeURIComponent(route.id)}/${encodeURIComponent(level.id)}/`;
  link.textContent = "Ver cursos del nivel →";
  card.append(link);
  return card;
}

async function loadLevels() {
  try {
    const response = await fetch("/catalog/learning_catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Error HTTP ${response.status}`);
    const catalog = await response.json();
    const profileId = "cloud-production-support";
    const profile = catalog.profiles.find((item) => item.id === profileId);
    const route = catalog.routes.find((item) => item.id === profile?.route_id);
    if (!route) throw new Error("No se encontró la ruta del perfil seleccionado.");
    levelGrid.replaceChildren(...catalog.levels.map((level) => renderLevel(level, route)));
  } catch (error) {
    appendText(levelGrid, "p", `No se pudieron cargar los niveles: ${error.message}`, "empty");
  }
}

loadLevels();
