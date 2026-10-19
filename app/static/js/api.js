const TOKEN_KEY = "fitness_token";
const USER_KEY = "fitness_user";

function guardarSesion(auth) {
  localStorage.setItem(TOKEN_KEY, auth.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(auth.usuario));
}

function obtenerToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function obtenerUsuario() {
  const crudo = localStorage.getItem(USER_KEY);
  return crudo ? JSON.parse(crudo) : null;
}

function cerrarSesion() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.location.href = "/index.html";
}

function requerirSesion() {
  if (!obtenerToken()) {
    window.location.href = "/login.html";
  }
}

function mensajeDeError(status, datos) {
  if (datos && typeof datos.detail === "string") return datos.detail;
  if (status === 422) return "Revisá los datos ingresados.";
  return "Ocurrió un error. Intentá de nuevo.";
}

async function apiFetch(ruta, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = obtenerToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const respuesta = await fetch(ruta, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let datos = null;
  try {
    datos = await respuesta.json();
  } catch (_) {
    // respuesta sin cuerpo JSON
  }

  if (!respuesta.ok) {
    // Sesión vencida: volver al inicio
    if (respuesta.status === 401 && token) {
      cerrarSesion();
    }
    const error = new Error(mensajeDeError(respuesta.status, datos));
    error.status = respuesta.status;
    throw error;
  }
  return datos;
}

// Único lugar que decide a dónde va una persona recién autenticada:
// - Personal Trainer: Home
// - Usuario particular con perfil completo: Home
// - Usuario particular sin perfil: formulario
async function irAlDestino(usuario) {
  if (!usuario || usuario.rol !== "USUARIO") {
    window.location.href = "/home.html";
    return;
  }
  try {
    await apiFetch("/perfil");
    window.location.href = "/home.html";
  } catch (e) {
    if (e.status === 404) {
      window.location.href = "/formulario.html";
      return;
    }
    throw e;
  }
}

const ETIQUETAS_OBJETIVO = {
  PERDER_PESO: "Perder peso",
  GANAR_MASA_MUSCULAR: "Ganar masa muscular",
  MANTENER_PESO: "Mantener peso",
  MEJORAR_RENDIMIENTO: "Mejorar rendimiento",
};