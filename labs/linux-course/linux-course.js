"use strict";

const modulesContainer = document.getElementById("linux-modules");

function appendText(parent, tagName, text) {
  const element = document.createElement(tagName);
  element.textContent = text;
  parent.append(element);
  return element;
}

function renderModule(module) {
  const article = document.createElement("article");
  article.className = "linux-module";
  appendText(article, "h3", `${module.number}. ${module.title}`);
  appendText(article, "p", module.explanation);

  const concepts = document.createElement("ul");
  module.concepts.forEach((concept) => appendText(concepts, "li", concept));
  article.append(concepts);

  module.exercises.forEach((exercise) => {
    const section = document.createElement("section");
    section.className = "linux-module__exercise";
    appendText(section, "strong", exercise.title);
    appendText(section, "p", exercise.task);
    appendText(section, "p", "Comandos de referencia (material; no se ejecutan):");
    const commandList = document.createElement("ul");
    exercise.commands.forEach((command) => {
      const item = document.createElement("li");
      const code = document.createElement("code");
      code.textContent = command;
      item.append(code);
      commandList.append(item);
    });
    section.append(commandList);
    appendText(section, "p", `Resultado esperado: ${exercise.expected}`);
    appendText(section, "p", `Verificación prevista: ${exercise.verification}`);
    article.append(section);
  });
  return article;
}

if (Array.isArray(window.LINUX_COURSE_MODULES)) {
  modulesContainer.replaceChildren(...window.LINUX_COURSE_MODULES.map(renderModule));
} else {
  appendText(modulesContainer, "p", "No se pudo cargar el temario preparado.");
}
