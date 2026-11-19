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

// Navegación visual compartida.
// No interviene en permisos ni en llamadas al backend.
function montarNavegacion() {
  const paginasProtegidas = new Set([
    "/home.html", "/entrenar.html", "/entrenamiento.html", "/historial.html",
    "/progreso.html", "/ejercicios.html", "/rutina.html", "/trainer.html",
    "/cliente.html", "/configuracion.html",
  ]);

  if (!paginasProtegidas.has(window.location.pathname) || !obtenerToken()) {
    return;
  }

  const contenido = document.querySelector("main.pagina, main.pantalla");

  if (!contenido || document.querySelector(".app-sidebar")) {
    return;
  }

  const usuario = obtenerUsuario() || {};

  const enlaces = [
    { href: "/home.html", texto: "Inicio", icono: "⌂" },
    { href: "/entrenar.html", texto: "Entrenar", icono: "▶" },
    { href: "/historial.html", texto: "Historial", icono: "▦" },
    { href: "/ejercicios.html", texto: "Ejercicios", icono: "✣" },
  ];

  if (usuario.rol === "PERSONAL_TRAINER") {
    enlaces.push({
      href: "/trainer.html",
      texto: "Mis clientes",
      icono: "♙"
    });
  } else {
    enlaces.splice(3, 0, {
      href: "/progreso.html",
      texto: "Progreso",
      icono: "↗"
    });
  }

  enlaces.push({
    href: "/configuracion.html",
    texto: "Configuración",
    icono: "⚙"
  });

  const sidebar = document.createElement("aside");
  sidebar.className = "app-sidebar";
  sidebar.setAttribute("aria-label", "Navegación principal");

  sidebar.innerHTML = `
    <a class="app-brand" href="/home.html">
      <span class="app-brand-mark" aria-hidden="true">✳</span>
      <span>HIT<small>PERFORMANCE</small></span>
    </a>
    <nav class="app-nav" aria-label="Secciones"></nav>
    <div class="app-sidebar-footer">
      <span class="app-sidebar-user"></span>
      <button class="app-sidebar-logout" type="button">
        ↗ Cerrar sesión
      </button>
    </div>`;

  const nav = sidebar.querySelector(".app-nav");

  enlaces.forEach(({ href, texto, icono }) => {
    const enlace = document.createElement("a");

    enlace.href = href;
    enlace.className =
      window.location.pathname === href ? "activo" : "";

    if (
      href === "/trainer.html" &&
      window.location.pathname === "/cliente.html"
    ) {
      enlace.classList.add("activo");
    }

    const iconoNodo = document.createElement("span");
    iconoNodo.className = "app-nav-icon";
    iconoNodo.setAttribute("aria-hidden", "true");
    iconoNodo.textContent = icono;

    const textoNodo = document.createElement("span");
    textoNodo.textContent = texto;

    enlace.append(iconoNodo, textoNodo);
    nav.appendChild(enlace);
  });

  sidebar.querySelector(".app-sidebar-user").textContent =
    usuario.nombre || "Mi cuenta";

  sidebar
    .querySelector(".app-sidebar-logout")
    .addEventListener("click", cerrarSesion);

  const principal = document.createElement("div");
  principal.className = "app-main";

  document.body.classList.add("app-shell");

  document.body.insertBefore(sidebar, contenido);
  document.body.insertBefore(principal, contenido);

  principal.appendChild(contenido);
}

montarNavegacion();

const ETIQUETAS_OBJETIVO = {
  PERDER_PESO: "Perder peso",
  GANAR_MASA_MUSCULAR: "Ganar masa muscular",
  MANTENER_PESO: "Mantener peso",
  MEJORAR_RENDIMIENTO: "Mejorar rendimiento",
};