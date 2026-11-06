// Ficha de un cliente (vista del trainer).
// Requiere: api.js, fechas-ui.js y entrenador-ui.js

requerirSesion();

const yo = obtenerUsuario();
if (!yo || yo.rol !== "PERSONAL_TRAINER") window.location.href = "/home.html";

const clienteId = new URLSearchParams(window.location.search).get("id");
if (!clienteId) window.location.href = "/trainer.html";

const BASE = `/trainer/clientes/${clienteId}`;
const LIMITE = 10;
let offset = 0;
let vinculoId = null;

function numero(valor, decimales = 0) {
  return Number(valor).toLocaleString("es-AR", { maximumFractionDigits: decimales });
}

function dato(valor, etiqueta) {
  return el("div", { class: "dato" }, el("strong", { text: valor }), el("span", { text: etiqueta }));
}

// ---------- Información básica ----------
async function cargarDetalle() {
  const cliente = await apiFetch(BASE);
  vinculoId = cliente.vinculo_id;

  document.getElementById("nombre-cliente").textContent = cliente.nombre;
  document.getElementById("meta-cliente").textContent =
    `${cliente.email} · cliente desde el ${formatoFechaCorta(cliente.inicio)}`;
  document.getElementById("ver-progreso").href = `/progreso.html?cliente=${clienteId}`;

  document.getElementById("datos-basicos").replaceChildren(
    dato(cliente.edad === null ? "—" : `${cliente.edad} años`, "Edad"),
    dato(cliente.altura_cm === null ? "—" : `${cliente.altura_cm} cm`, "Altura"),
    dato(cliente.peso_actual_kg === null ? "—" : `${numero(cliente.peso_actual_kg, 1)} kg`, "Peso actual"),
    dato(cliente.objetivo ? ETIQUETAS_OBJETIVO[cliente.objetivo] : "—", "Objetivo"),
    dato(cliente.dias_entrenamiento_semana === null ? "—" : String(cliente.dias_entrenamiento_semana), "Días por semana")
  );
  pintarCuota(cliente.estado_cuota);
}

async function cargarActividad() {
  const desde = new Date();
  desde.setDate(desde.getDate() - 29);
  const [resumen, racha] = await Promise.all([
    apiFetch(`${BASE}/estadisticas/resumen?desde=${aISO(desde)}`),
    apiFetch(`${BASE}/racha`).catch(() => null), // sin perfil no hay racha
  ]);
  document.getElementById("datos-actividad").replaceChildren(
    dato(String(resumen.cantidad_entrenamientos), "Entrenamientos"),
    dato(numero(resumen.frecuencia_semanal, 2), "Por semana"),
    dato(racha ? `${racha.racha_actual} días` : "—", "Racha actual"),
    dato(`${numero(resumen.volumen_total_kg)} kg`, "Volumen")
  );
}

// ---------- Cuota y pagos (RF-13) ----------
function pintarCuota(estado) {
  const chip = document.getElementById("estado-cuota");
  chip.className = `cuota ${estado}`;
  chip.textContent = ETIQUETAS_CUOTA[estado];
  document.getElementById("select-cuota").value = estado;
}

document.getElementById("select-cuota").addEventListener("change", async (evento) => {
  try {
    const cliente = await apiFetch(`${BASE}/cuota`, {
      method: "PUT",
      body: { estado_cuota: evento.target.value },
    });
    pintarCuota(cliente.estado_cuota);
  } catch (e) {
    document.getElementById("error-pago").textContent = e.message;
  }
});

async function cargarPagos() {
  const pagos = await apiFetch(`${BASE}/pagos`);
  const lista = document.getElementById("lista-pagos");
  if (!pagos.length) {
    lista.replaceChildren(el("li", { text: "Todavía no registraste pagos." }));
    return;
  }
  lista.replaceChildren(
    ...pagos.map((pago) =>
      el(
        "li",
        {},
        el("span", { text: `${formatoFechaCorta(pago.fecha)}${pago.concepto ? " · " + pago.concepto : ""}` }),
        el("strong", { text: `$ ${numero(pago.monto)}` })
      )
    )
  );
}

document.getElementById("form-pago").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const error = document.getElementById("error-pago");
  error.textContent = "";

  const monto = Number(document.getElementById("pago-monto").value);
  if (!Number.isInteger(monto) || monto < 1) {
    error.textContent = "Ingresá un monto entero mayor a cero.";
    return;
  }
  const boton = document.getElementById("pago-guardar");
  boton.disabled = true;
  try {
    await apiFetch(`${BASE}/pagos`, {
      method: "POST",
      body: {
        monto,
        fecha: document.getElementById("pago-fecha").value || null,
        concepto: document.getElementById("pago-concepto").value.trim() || null,
      },
    });
    document.getElementById("pago-monto").value = "";
    document.getElementById("pago-concepto").value = "";
    await Promise.all([cargarPagos(), cargarDetalle()]); // registrar un pago deja la cuota al día
  } catch (e) {
    error.textContent = e.message;
  } finally {
    boton.disabled = false;
  }
});

// ---------- Rutinas asignadas (RF-11) ----------
async function cargarAsignaciones() {
  const asignaciones = await apiFetch(`${BASE}/asignaciones`);
  const lista = document.getElementById("lista-asignaciones");
  if (!asignaciones.length) {
    lista.replaceChildren(el("li", { text: "Todavía no le asignaste rutinas." }));
    return;
  }
  lista.replaceChildren(
    ...asignaciones.map((asignacion) => {
      const activa = asignacion.estado === "ACTIVA";
      const acciones = [];
      if (activa && asignacion.rutina_id) {
        acciones.push(
          el("a", { class: "boton-chico", href: `/rutina.html?id=${asignacion.rutina_id}`, text: "Editar" })
        );
      }
      if (activa) {
        acciones.push(
          el("button", {
            type: "button", class: "boton-chico", text: "Finalizar",
            onclick: async () => {
              await apiFetch(`${BASE}/asignaciones/${asignacion.id}/finalizar`, { method: "POST" });
              await cargarAsignaciones();
            },
          })
        );
      }
      return el(
        "li",
        {},
        el(
          "div",
          {},
          el("strong", { text: asignacion.rutina_nombre }),
          el("p", {
            class: "rutina-meta",
            text: `Asignada el ${formatoFechaCorta(asignacion.fecha_asignacion)} · ${activa ? "Activa" : "Finalizada"}`,
          })
        ),
        el("div", { class: "acciones-fila" }, ...acciones)
      );
    })
  );
}

async function cargarRutinasPropias() {
  const rutinas = await apiFetch("/rutinas");
  const select = document.getElementById("select-rutina");
  select.replaceChildren(...rutinas.map((rutina) => el("option", { value: rutina.id, text: rutina.nombre })));
  document.getElementById("asignar").disabled = rutinas.length === 0;
  document.getElementById("aviso-rutinas").textContent = rutinas.length
    ? "Se le entrega una copia: cada cliente tiene su propia versión de la rutina."
    : "Primero armá una rutina desde «Entrenar» y después podés asignarla.";
}

document.getElementById("asignar").addEventListener("click", async () => {
  const error = document.getElementById("error-asignacion");
  error.textContent = "";
  const rutinaId = Number(document.getElementById("select-rutina").value);
  if (!rutinaId) return;
  try {
    await apiFetch(`${BASE}/asignaciones`, { method: "POST", body: { rutina_id: rutinaId } });
    await cargarAsignaciones();
  } catch (e) {
    error.textContent = e.message;
  }
});

// ---------- Historial de entrenamientos (RF-12) ----------
function tarjetaEntrenamiento(entrenamiento) {
  const datos = [
    `⏱ ${formatoDuracionCorta(entrenamiento.duracion_segundos)}`,
    `🏋️ ${numero(entrenamiento.volumen_total_kg)} kg`,
  ];
  if (entrenamiento.dificultad) datos.push(`💪 ${entrenamiento.dificultad}/5`);

  return el(
    "button",
    {
      type: "button",
      class: "entreno-card",
      style: "text-align: left; font: inherit; cursor: pointer",
      onclick: () => verEntrenamiento(entrenamiento.id),
    },
    el("span", { class: "entreno-fecha", text: formatoFechaLarga(entrenamiento.fecha) }),
    el("strong", { text: entrenamiento.titulo }),
    el("span", { class: "rutina-meta", text: datos.join(" · ") })
  );
}

async function cargarHistorial(reiniciar) {
  const lista = document.getElementById("lista-historial");
  const estado = document.getElementById("estado-historial");
  const botonMas = document.getElementById("mas");
  if (reiniciar) {
    offset = 0;
    lista.replaceChildren();
  }
  const entrenamientos = await apiFetch(`${BASE}/entrenamientos?limite=${LIMITE}&offset=${offset}`);
  entrenamientos.forEach((entrenamiento) => lista.append(tarjetaEntrenamiento(entrenamiento)));
  offset += entrenamientos.length;
  botonMas.classList.toggle("oculto", entrenamientos.length < LIMITE);
  estado.textContent = lista.children.length ? "" : "Todavía no hay entrenamientos.";
}

async function verEntrenamiento(id) {
  const entrenamiento = await apiFetch(`${BASE}/entrenamientos/${id}`);
  document.getElementById("detalle-titulo").textContent = entrenamiento.titulo;
  document.getElementById("detalle-cuerpo").replaceChildren(
    el("p", {
      class: "rutina-meta",
      text:
        `${capitalizar(formatoFechaLarga(entrenamiento.fecha))} · ` +
        `${formatoDuracionCorta(entrenamiento.duracion_segundos)} · ` +
        `${numero(entrenamiento.volumen_total_kg)} kg de volumen`,
    }),
    ...entrenamiento.ejercicios.map((item) =>
      el(
        "div",
        { class: "ej-tarjeta" },
        el("strong", { text: item.ejercicio.nombre }),
        el(
          "ul",
          { class: "series-detalle" },
          ...item.series.map((serie) =>
            el("li", {
              text: item.ejercicio.tipo_medicion === "TIEMPO"
                ? `Duración: ${formatoDuracionCorta(serie.duracion_segundos)}`
                : `Serie ${serie.numero}: ${serie.peso_kg ?? "—"} kg × ${serie.repeticiones}`,
            })
          )
        ),
        item.notas ? el("p", { class: "rutina-meta", text: `📝 ${item.notas}` }) : ""
      )
    )
  );
  document.getElementById("dialogo-entrenamiento").showModal();
}

document.getElementById("mas").addEventListener("click", () => cargarHistorial(false));
document.getElementById("cerrar-detalle").addEventListener("click", () =>
  document.getElementById("dialogo-entrenamiento").close()
);

// ---------- Relación ----------
document.getElementById("finalizar-relacion").addEventListener("click", async () => {
  if (!window.confirm("¿Finalizar la relación con este cliente? Dejás de ver su información y se cierran sus rutinas asignadas.")) return;
  try {
    await apiFetch(`/trainer/vinculos/${vinculoId}/finalizar`, { method: "POST" });
    window.location.href = "/trainer.html";
  } catch (e) {
    window.alert(e.message);
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

(async () => {
  document.getElementById("pago-fecha").value = aISO(new Date());
  document.getElementById("pago-fecha").max = aISO(new Date());

  try {
    await cargarDetalle();
  } catch (e) {
    // No es un cliente activo de este trainer
    window.location.href = "/trainer.html";
    return;
  }
  await Promise.all([
    seguro(cargarActividad),
    seguro(cargarPagos),
    seguro(cargarAsignaciones),
    seguro(cargarRutinasPropias),
    seguro(() => cargarHistorial(true)),
  ]);
})();