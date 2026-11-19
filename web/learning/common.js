"use strict";

(function () {
  let sessionPromise;

  async function requestJson(path, options) {
    if (!sessionPromise) {
      sessionPromise = fetch("/api/learning/session", {
        cache: "no-store",
        credentials: "same-origin",
      }).then(async (response) => {
        let payload;
        try {
          payload = await response.json();
        } catch (error) {
          throw new Error(`Respuesta inválida al iniciar el perfil local (HTTP ${response.status}).`);
        }
        if (!response.ok || payload.ok === false) {
          throw new Error(payload.error || `Error HTTP ${response.status}`);
        }
      }).catch((error) => {
        sessionPromise = null;
        throw error;
      });
    }
    await sessionPromise;
    const response = await fetch(path, {
      ...options,
      credentials: "same-origin",
    });
    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new Error(`Respuesta inválida del servidor (HTTP ${response.status}).`);
    }
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || `Error HTTP ${response.status}`);
    }
    return payload;
  }

  function postJson(path, payload) {
    return requestJson(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
  }

  function shuffleOptions(options) {
    const shuffled = [...options];
    for (let index = shuffled.length - 1; index > 0; index -= 1) {
      const target = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[target]] = [shuffled[target], shuffled[index]];
    }
    return shuffled;
  }

  window.learningClient = { requestJson, postJson, shuffleOptions };
}());
