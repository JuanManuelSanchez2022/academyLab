"use strict";

const profileGrid = document.getElementById("profile-grid");
const availabilityLabels = {
  available: "Disponible",
  in_development: "En desarrollo",
  pending_environment: "Pendiente de entorno",
  blocked_prerequisites: "Bloqueado por requisitos previos",
  planned: "Planificado",
};

function appendText(parent, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function renderProfile(profile) {
  const card = document.createElement("article");
  card.className = `course-card${profile.id === "cloud-production-support" ? " course-card--featured" : ""}`;

  const top = document.createElement("div");
  top.className = "course-card__top";
  appendText(top, "span", profile.id === "cloud-production-support" ? "OPS" : "RUTA", "course-icon");
  appendText(top, "span", availabilityLabels[profile.availability] || "Estado no definido", `status-badge${profile.availability === "in_development" ? " status-badge--preparing" : ""}`);
  card.append(top);

  appendText(card, "p", "PERFIL PROFESIONAL", "course-card__eyebrow");
  appendText(card, "h3", profile.title);
  appendText(card, "p", profile.description, "course-card__description");

  if (profile.route_id) {
    const link = document.createElement("a");
    link.className = "button button--primary course-card__action";
    link.href = `/profiles/${encodeURIComponent(profile.id)}/`;
    link.textContent = "Explorar niveles →";
    card.append(link);
  } else {
    const button = document.createElement("button");
    button.className = "button button--disabled course-card__action";
    button.type = "button";
    button.disabled = true;
    button.textContent = "Ruta aún no disponible";
    card.append(button);
  }
  return card;
}

async function loadProfiles() {
  try {
    const response = await fetch("/catalog/learning_catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Error HTTP ${response.status}`);
    const catalog = await response.json();
    if (!Array.isArray(catalog.profiles)) throw new Error("El catálogo no contiene perfiles válidos.");
    profileGrid.replaceChildren(...catalog.profiles.map(renderProfile));
  } catch (error) {
    appendText(profileGrid, "p", `No se pudieron cargar los perfiles: ${error.message}`, "empty");
  }
}

loadProfiles();
