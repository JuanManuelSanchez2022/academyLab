"use strict";

const statusElement = document.getElementById("lab-service-status");
const openButton = document.getElementById("open-lab-btn");

async function requestJson(path, options) {
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Error HTTP ${response.status}`);
  }
  return payload;
}

async function refreshLabStatus() {
  try {
    const status = await requestJson("/api/lab/status", { cache: "no-store" });
    const lab = status.lab;
    statusElement.className = "service-status service-status--ok";
    statusElement.textContent = lab.running
      ? `Servidor activo · ${lab.active_sessions} pestaña(s) con sesión · cierre automático tras ${lab.idle_timeout_seconds} s sin actividad.`
      : "Servidor detenido · se iniciará automáticamente cuando ingreses.";
    openButton.disabled = false;
  } catch (error) {
    statusElement.className = "service-status service-status--error";
    statusElement.textContent = `No se pudo consultar el servicio: ${error.message}`;
    openButton.disabled = true;
  }
}

async function openLab() {
  openButton.disabled = true;
  statusElement.className = "service-status";
  statusElement.textContent = "Iniciando y verificando el servidor del laboratorio...";
  try {
    const result = await requestJson("/api/lab/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    statusElement.textContent = result.message;
    window.location.assign(result.url);
  } catch (error) {
    statusElement.className = "service-status service-status--error";
    statusElement.textContent = `No se pudo ingresar al laboratorio: ${error.message}`;
    openButton.disabled = false;
  }
}

openButton.addEventListener("click", openLab);
refreshLabStatus();
window.setInterval(refreshLabStatus, 10000);
