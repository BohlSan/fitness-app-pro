// Panel del trainer.
// Requiere: api.js, fechas-ui.js y entrenador-ui.js

requerirSesion();

const yo = obtenerUsuario();
if (!yo || yo.rol !== "PERSONAL_TRAINER") window.location.href = "/home.html";

const campoCodigo = document.getElementById("codigo");
const errorCodigo = document.getElementById("error-codigo");

function numero(valor, decimales = 0) {
  return Number(valor).toLocaleString("es-AR", { maximumFractionDigits: decimales });
}

// ---------- Código de enlace ----------
async function cargarCodigo() {
  const datos = await apiFetch("/trainer/codigo");
  campoCodigo.textContent = datos.codigo_enlace;
}

document.getElementById("copiar").addEventListener("click", async () => {
  errorCodigo.textContent = "";
  try {
    await navigator.clipboard.writeText(campoCodigo.textContent);
    errorCodigo.textContent = "Código copiado ✓";
  } catch (e) {
    errorCodigo.textContent = "No se pudo copiar. Seleccionalo y copialo a mano.";
  }
});

document.getElementById("regenerar").addEventListener("click", async () => {
  if (!window.confirm("El código actual dejará de funcionar. ¿Generar uno nuevo?")) return;
  errorCodigo.textContent = "";
  try {
    const datos = await apiFetch("/trainer/codigo/regenerar", { method: "POST" });
    campoCodigo.textContent = datos.codigo_enlace;
  } catch (e) {
    errorCodigo.textContent = e.message;
  }
});

// ---------- Solicitudes pendientes ----------
async function resolverSolicitud(vinculoId, accion) {
  try {
    await apiFetch(`/trainer/vinculos/${vinculoId}/${accion}`, { method: "POST" });
  } catch (e) {
    window.alert(e.message);
  }
  await recargar();
}

function tarjetaPendiente(solicitud) {
  return el(
    "div",
    { class: "solicitud" },
    el(
      "div",
      {},
      el("strong", { text: solicitud.cliente.nombre }),
      el("p", { class: "rutina-meta", text: solicitud.cliente.email })
    ),
    el(
      "div",
      { class: "acciones-fila" },
      el("button", {
        type: "button", class: "boton-chico", text: "Aceptar",
        onclick: () => resolverSolicitud(solicitud.vinculo_id, "aceptar"),
      }),
      el("button", {
        type: "button", class: "boton-chico peligro", text: "Rechazar",
        onclick: () => resolverSolicitud(solicitud.vinculo_id, "finalizar"),
      })
    )
  );
}

async function cargarPendientes() {
  const pendientes = await apiFetch("/trainer/clientes?estado=PENDIENTE");
  document.getElementById("bloque-pendientes").classList.toggle("oculto", pendientes.length === 0);
  document.getElementById("lista-pendientes").replaceChildren(...pendientes.map(tarjetaPendiente));
}

// ---------- Clientes activos ----------
function tarjetaCliente(cliente) {
  let ultimo = "Todavía no entrenó";
  if (cliente.ultimo_entrenamiento) {
    const dias = cliente.dias_sin_entrenar;
    const hace = dias === 0 ? "hoy" : dias === 1 ? "ayer" : `hace ${dias} días`;
    ultimo = `Último entrenamiento: ${formatoFechaCorta(cliente.ultimo_entrenamiento)} (${hace})`;
  }
  return el(
    "a",
    { class: "cliente-card", href: `/cliente.html?id=${cliente.cliente.id}` },
    el(
      "div",
      { class: "cliente-cabecera" },
      el("strong", { text: cliente.cliente.nombre }),
      el("span", { class: `cuota ${cliente.estado_cuota}`, text: ETIQUETAS_CUOTA[cliente.estado_cuota] })
    ),
    el("p", {
      class: "rutina-meta",
      text: cliente.objetivo ? ETIQUETAS_OBJETIVO[cliente.objetivo] : "Todavía no completó su perfil",
    }),
    el("p", { class: "rutina-meta", text: ultimo })
  );
}

async function cargarClientes() {
  const clientes = await apiFetch("/trainer/clientes?estado=ACTIVA");
  document.getElementById("estado-clientes").textContent = clientes.length
    ? ""
    : "Todavía no tenés clientes. Compartí tu código para que se vinculen.";
  document.getElementById("lista-clientes").replaceChildren(...clientes.map(tarjetaCliente));
}

// ---------- Actividad reciente (la alimenta el Observer) ----------
function itemActividad(novedad) {
  const detalle =
    `${formatoDuracionCorta(novedad.duracion_segundos)} · ${numero(novedad.volumen_kg)} kg · ` +
    formatoFechaCorta(novedad.fecha);
  return el(
    "a",
    { class: "actividad-item" + (novedad.leida ? "" : " nueva"), href: `/cliente.html?id=${novedad.cliente.id}` },
    `${novedad.cliente.nombre} terminó «${novedad.titulo}»`,
    el("small", { text: detalle })
  );
}

async function cargarActividad() {
  const novedades = await apiFetch("/trainer/actividad");
  document.getElementById("estado-actividad").textContent = novedades.length
    ? ""
    : "Cuando tus clientes terminen un entrenamiento, vas a verlo acá.";
  document.getElementById("lista-actividad").replaceChildren(...novedades.map(itemActividad));
}

document.getElementById("marcar-leidas").addEventListener("click", async () => {
  try {
    await apiFetch("/trainer/actividad/leidas", { method: "POST" });
    await cargarActividad();
  } catch (e) {
    document.getElementById("estado-actividad").textContent = e.message;
  }
});

// ---------- Inicio ----------
async function seguro(funcion) {
  try {
    await funcion();
  } catch (e) {
    console.error(e);
  }
}

async function recargar() {
  await Promise.all([seguro(cargarPendientes), seguro(cargarClientes), seguro(cargarActividad)]);
}

(async () => {
  await seguro(cargarCodigo);
  await recargar();
})();