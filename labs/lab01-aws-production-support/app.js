"use strict";

const elements = {
  status: document.getElementById("status"),
  events: document.getElementById("events"),
  uniqueOps: document.getElementById("unique-ops"),
  invalidLines: document.getElementById("invalid-lines"),
  errors: document.getElementById("errors"),
  testsStatus: document.getElementById("tests-status"),
  fileSelect: document.getElementById("file-select"),
  analyzeButton: document.getElementById("analyze-btn"),
  refreshButton: document.getElementById("refresh-evidence-btn"),
  runTestsButton: document.getElementById("run-tests-btn"),
  analyzeResult: document.getElementById("analyze-result"),
  testsResult: document.getElementById("tests-result"),
  evidenceContent: document.getElementById("evidence-content"),
  sessionStatus: document.getElementById("lab-session-status"),
  continueButton: document.getElementById("continue-practicing-btn"),
  stopButton: document.getElementById("stop-lab-btn"),
};
const PLATFORM_ORIGIN = "http://127.0.0.1:8765";
const HEARTBEAT_INTERVAL_MS = 20000;
const sessionId = new URLSearchParams(window.location.search).get("session");
const tabId = createId();
let sessionActive = Boolean(sessionId);
let leaving = false;

function createId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  window.crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || `Error HTTP ${response.status}`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

function setMessage(container, message, state) {
  container.replaceChildren();
  const paragraph = document.createElement("p");
  paragraph.className = state || "";
  paragraph.textContent = message;
  container.append(paragraph);
}

function setSummary(data) {
  elements.events.textContent = data.total_eventos_parseados ?? "-";
  elements.uniqueOps.textContent = data.operaciones_unicas ?? "-";
  elements.invalidLines.textContent = data.lineas_no_parseadas ?? "-";
  elements.errors.textContent = Object.keys(data.operaciones_error || {}).length;
}

function showAnalysis(result) {
  elements.analyzeResult.replaceChildren();
  const state = document.createElement("p");
  state.className = result.ok ? "pass" : "fail";
  state.textContent = result.ok
    ? `Análisis terminado correctamente: ${result.file}`
    : `El análisis falló: ${result.error || result.stderr || "error de ejecución"}`;
  elements.analyzeResult.append(state);
  if (result.stdout) {
    const output = document.createElement("pre");
    output.textContent = result.stdout;
    elements.analyzeResult.append(output);
  }
  if (result.stderr) {
    const error = document.createElement("pre");
    error.textContent = result.stderr;
    elements.analyzeResult.append(error);
  }
  if (result.data) {
    setSummary(result.data);
    showEvidence(result.data);
  }
}

function showEvidence(data) {
  const output = document.createElement("pre");
  output.textContent = JSON.stringify(data, null, 2);
  elements.evidenceContent.replaceChildren(output);
}

async function loadHealth() {
  try {
    await requestJson("/api/health");
    elements.status.textContent = "En línea";
    elements.status.className = "ok";
  } catch (error) {
    elements.status.textContent = `Error: ${error.message}`;
    elements.status.className = "bad";
  }
}

async function loadFiles() {
  try {
    const { files } = await requestJson("/api/files");
    const previous = elements.fileSelect.value;
    elements.fileSelect.replaceChildren();
    files.filter((file) => file.name.toLowerCase().endsWith(".log")).forEach((file) => {
      const option = document.createElement("option");
      option.value = file.name;
      option.textContent = `${file.name} (${file.size} bytes)`;
      elements.fileSelect.append(option);
    });
    if (files.some((file) => file.name === previous)) {
      elements.fileSelect.value = previous;
    }
    elements.analyzeButton.disabled = elements.fileSelect.options.length === 0;
    if (elements.fileSelect.options.length === 0) {
      setMessage(elements.analyzeResult, "No hay archivos .log disponibles en data/test.", "warn");
    }
  } catch (error) {
    setMessage(elements.analyzeResult, `No se pudo cargar la lista de archivos: ${error.message}`, "fail");
  }
}

async function loadEvidence() {
  try {
    const { data } = await requestJson("/api/evidence");
    showEvidence(data);
    setSummary(data);
  } catch (error) {
    setMessage(elements.evidenceContent, `Evidencia no disponible: ${error.message}`, "empty");
  }
}

async function analyzeSelectedFile() {
  const file = elements.fileSelect.value;
  if (!file) {
    setMessage(elements.analyzeResult, "Seleccione un archivo .log.", "fail");
    return;
  }
  elements.analyzeButton.disabled = true;
  setMessage(elements.analyzeResult, `Analizando ${file}...`, "warn");
  try {
    const result = await requestJson("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file }),
    });
    showAnalysis(result);
    await loadEvidence();
  } catch (error) {
    if (error.payload && error.payload.ok === false) {
      showAnalysis(error.payload);
    } else {
      setMessage(elements.analyzeResult, `El análisis falló: ${error.message}`, "fail");
    }
  } finally {
    elements.analyzeButton.disabled = elements.fileSelect.options.length === 0;
  }
}

function showTests(result) {
  elements.testsResult.replaceChildren();
  const summary = document.createElement("p");
  summary.className = result.ok ? "pass" : "fail";
  summary.textContent = result.ok
    ? `Pruebas terminadas: ${result.passed}/${result.total} PASS; ${result.failed} FAIL.`
    : `Las pruebas fallaron: ${result.passed}/${result.total} PASS; ${result.failed} FAIL. ${result.error || ""}`;
  elements.testsResult.append(summary);
  elements.testsStatus.textContent = `${result.passed}/${result.total} PASS`;
  elements.testsStatus.className = result.ok ? "ok" : "bad";
  if (result.results && result.results.length) {
    const table = document.createElement("table");
    const head = document.createElement("tr");
    ["Resultado", "Prueba", "Detalle"].forEach((label) => {
      const cell = document.createElement("th");
      cell.textContent = label;
      head.append(cell);
    });
    table.append(head);
    result.results.forEach((test) => {
      const row = document.createElement("tr");
      [test.status, test.name, test.detail].forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (index === 0) cell.className = value === "PASS" ? "pass" : "fail";
        row.append(cell);
      });
      table.append(row);
    });
    elements.testsResult.append(table);
  }
  if (result.stdout) {
    const output = document.createElement("pre");
    output.textContent = result.stdout;
    elements.testsResult.append(output);
  }
  if (result.stderr) {
    const error = document.createElement("pre");
    error.textContent = result.stderr;
    elements.testsResult.append(error);
  }
}

async function runTests() {
  elements.runTestsButton.disabled = true;
  setMessage(elements.testsResult, "Ejecutando las pruebas automatizadas...", "warn");
  elements.testsStatus.textContent = "En curso...";
  try {
    showTests(await requestJson("/api/tests", { method: "POST" }));
    await loadEvidence();
  } catch (error) {
    elements.testsStatus.textContent = "Fallaron";
    elements.testsStatus.className = "bad";
    if (error.payload && error.payload.results) {
      showTests(error.payload);
    } else {
      setMessage(elements.testsResult, `No se pudieron ejecutar las pruebas: ${error.message}`, "fail");
    }
  } finally {
    elements.runTestsButton.disabled = false;
  }
}

async function postSessionAction(action) {
  const response = await fetch(`${PLATFORM_ORIGIN}/api/lab/${action}`, {
    method: "POST",
    headers: { "Content-Type": "text/plain;charset=UTF-8" },
    body: JSON.stringify({ session_id: sessionId, tab_id: tabId }),
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || payload.message || `Error HTTP ${response.status}`);
  }
  return payload;
}

async function heartbeat() {
  if (!sessionActive || leaving) return;
  try {
    const session = await postSessionAction("heartbeat");
    const timeout = session.idle_timeout_seconds;
    const timeoutText = timeout % 60 === 0
      ? `${timeout / 60} ${timeout === 60 ? "minuto" : "minutos"}`
      : `${timeout} segundos`;
    elements.sessionStatus.textContent = `Sesión activa. Si se cierra el navegador sin avisar, el laboratorio se detendrá tras ${timeoutText} sin actividad.`;
    elements.sessionStatus.className = "session-status session-status--active";
  } catch (error) {
    elements.sessionStatus.textContent = `No se pudo renovar la sesión: ${error.message}.`;
    elements.sessionStatus.className = "session-status session-status--error";
  }
}

async function leaveLab() {
  if (!sessionActive || leaving) return;
  leaving = true;
  elements.stopButton.disabled = true;
  elements.continueButton.disabled = true;
  elements.sessionStatus.textContent = "Cerrando esta sesión del laboratorio...";
  try {
    const result = await postSessionAction("leave");
    sessionActive = false;
    elements.sessionStatus.textContent = result.message;
    elements.sessionStatus.className = "session-status session-status--active";
    window.setTimeout(() => {
      window.location.assign(`${PLATFORM_ORIGIN}/`);
    }, 1200);
  } catch (error) {
    leaving = false;
    elements.stopButton.disabled = false;
    elements.continueButton.disabled = false;
    elements.sessionStatus.textContent = `No se pudo cerrar el laboratorio: ${error.message}.`;
    elements.sessionStatus.className = "session-status session-status--error";
  }
}

function installSessionSupervisor() {
  if (!sessionId) {
    elements.sessionStatus.textContent = "Esta página no tiene una sesión administrada. Inicia el laboratorio desde academyLab.";
    elements.sessionStatus.className = "session-status session-status--error";
    elements.stopButton.disabled = true;
    elements.continueButton.disabled = true;
    window.setTimeout(() => {
      window.location.assign(`${PLATFORM_ORIGIN}/courses/aws-production-support/`);
    }, 2500);
    return;
  }

  elements.continueButton.addEventListener("click", () => {
    elements.sessionStatus.textContent = "Puedes continuar practicando. Esta sesión permanece activa mientras esta pestaña envíe su señal periódica.";
    elements.sessionStatus.className = "session-status session-status--active";
  });
  elements.stopButton.addEventListener("click", leaveLab);
  heartbeat();
  window.setInterval(heartbeat, HEARTBEAT_INTERVAL_MS);

  window.addEventListener("pagehide", () => {
    if (!sessionActive || leaving || !navigator.sendBeacon) return;
    const body = new Blob(
      [JSON.stringify({ session_id: sessionId, tab_id: tabId })],
      { type: "text/plain;charset=UTF-8" },
    );
    navigator.sendBeacon(`${PLATFORM_ORIGIN}/api/lab/leave`, body);
  });
}

elements.analyzeButton.addEventListener("click", analyzeSelectedFile);
elements.refreshButton.addEventListener("click", loadEvidence);
elements.runTestsButton.addEventListener("click", runTests);

loadHealth();
loadFiles();
loadEvidence();
installSessionSupervisor();
window.setInterval(() => {
  loadHealth();
  loadFiles();
}, 30000);
