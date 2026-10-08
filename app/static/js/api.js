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
  if (status === 422) return "Revisá los datos ingresados.";
  if (datos && typeof datos.detail === "string") return datos.detail;
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
    // Sesión vencida: volver al login
    if (respuesta.status === 401 && token) {
      cerrarSesion();
    }
    throw new Error(mensajeDeError(respuesta.status, datos));
  }
  return datos;
}