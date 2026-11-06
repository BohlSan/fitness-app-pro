// Historial de entrenamientos con calendario.
// Requiere: api.js y fechas-ui.js

requerirSesion();

const CARITAS_CANSANCIO = ["😄", "🙂", "😐", "😓", "😫"];
const CARITAS_ANIMO = ["😞", "🙁", "😐", "🙂", "😄"];
const LIMITE = 20;

const tituloMes = document.getElementById("titulo-mes");
const grilla = document.getElementById("grilla");
const lista = document.getElementById("lista");
const estado = document.getElementById("estado");
const filtroActivo = document.getElementById("filtro-activo");
const botonMas = document.getElementById("mas");
const errorPeriodo = document.getElementById("error-periodo");
const detallePlanificado = document.getElementById("detalle-planificado");
const campoDesde = document.getElementById("desde");
const campoHasta = document.getElementById("hasta");

const inicial = new Date();
let mesVisible = { anio: inicial.getFullYear(), mes: inicial.getMonth() + 1 };
let filtro = { desde: null, hasta: null, etiqueta: "" };
let diasConEntreno = new Map();
let diasPlanificados = new Map();
let fechaSeleccionada = aISO(inicial);
let offset = 0;
let numeroPeticion = 0;

// ---------- Utilidades de DOM ----------
function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  Object.entries(atributos).forEach(([clave, valor]) => {
    if (valor === null || valor === undefined || valor === false) return;
    if (clave === "class") nodo.className = valor;
    else if (clave === "text") nodo.textContent = valor;
    else if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
    else nodo.setAttribute(clave, valor === true ? "" : valor);
  });
  hijos.forEach((hijo) => nodo.append(hijo));
  return nodo;
}

// ---------- Filtros ----------
function filtroDia(iso) {
  return { desde: iso, hasta: iso, etiqueta: capitalizar(formatoFechaLarga(iso)) };
}

function filtroMes(anio, mes) {
  const ultimoDia = new Date(anio, mes, 0).getDate();
  return {
    desde: `${anio}-${pad2(mes)}-01`,
    hasta: `${anio}-${pad2(mes)}-${pad2(ultimoDia)}`,
    etiqueta: `${capitalizar(nombreMes(mes - 1))} ${anio}`,
  };
}

function filtroSemana(fecha) {
  // Las semanas van de lunes a domingo
  const lunes = new Date(fecha);
  lunes.setDate(lunes.getDate() - ((lunes.getDay() + 6) % 7));
  const domingo = new Date(lunes);
  domingo.setDate(lunes.getDate() + 6);

  const mismoMes = lunes.getMonth() === domingo.getMonth();
  const etiqueta = mismoMes
    ? `Semana del ${lunes.getDate()} al ${domingo.getDate()} de ${nombreMes(lunes.getMonth())}`
    : `Semana del ${lunes.getDate()} de ${nombreMes(lunes.getMonth())} al ${domingo.getDate()} de ${nombreMes(domingo.getMonth())}`;
  return { desde: aISO(lunes), hasta: aISO(domingo), etiqueta };
}

function aplicarFiltro(nuevo) {
  filtro = nuevo;
  if (nuevo.desde && nuevo.hasta && nuevo.desde === nuevo.hasta) {
    fechaSeleccionada = nuevo.desde;
  }
  filtroActivo.textContent = filtro.etiqueta;
  pintarCalendario();
  pintarDetallePlanificado(fechaSeleccionada);
  cargarLista(true);
}

// ---------- Calendario ----------
async function cargarCalendario() {
  const query = `anio=${mesVisible.anio}&mes=${mesVisible.mes}`;
  const [entrenamientos, planificados] = await Promise.all([
    apiFetch(`/entrenamientos/calendario?${query}`),
    apiFetch(`/entrenamientos/calendario/planificados?${query}`),
  ]);
  diasConEntreno = new Map(entrenamientos.map((dia) => [dia.fecha, dia]));
  diasPlanificados = new Map(planificados.map((dia) => [dia.fecha, dia]));
  pintarCalendario();
  pintarDetallePlanificado(fechaSeleccionada);
}

async function mostrarMes(anio, mes) {
  mesVisible = { anio, mes };
  const mesDeSeleccion = fechaSeleccionada.slice(0, 7);
  const mesNuevo = `${anio}-${pad2(mes)}`;
  if (mesDeSeleccion !== mesNuevo) fechaSeleccionada = `${mesNuevo}-01`;
  await cargarCalendario();
}

function pintarDetallePlanificado(iso) {
  if (!detallePlanificado) return;
  const programacion = diasPlanificados.get(iso);
  const encabezado = el("strong", { text: `Rutinas previstas · ${capitalizar(formatoFechaLarga(iso))}` });
  if (!programacion || !programacion.rutinas.length) {
    detallePlanificado.replaceChildren(
      encabezado,
      el("p", { text: "No hay rutinas planificadas para esta fecha." })
    );
    return;
  }
  detallePlanificado.replaceChildren(
    encabezado,
    el(
      "ul",
      {},
      ...programacion.rutinas.map((rutina) =>
        el("li", { text: `${rutina.rutina_nombre} · ${rutina.dia_nombre}` })
      )
    )
  );
}

function mesDesplazado(delta) {
  const fecha = new Date(mesVisible.anio, mesVisible.mes - 1 + delta, 1);
  return { anio: fecha.getFullYear(), mes: fecha.getMonth() + 1 };
}

function pintarCalendario() {
  tituloMes.textContent = `${capitalizar(nombreMes(mesVisible.mes - 1))} ${mesVisible.anio}`;

  const primero = new Date(mesVisible.anio, mesVisible.mes - 1, 1);
  const huecos = (primero.getDay() + 6) % 7; // la semana empieza el lunes
  const cantidadDias = new Date(mesVisible.anio, mesVisible.mes, 0).getDate();
  const hoyISO = aISO(new Date());

  const celdas = [];
  for (let i = 0; i < huecos; i++) celdas.push(el("span", { class: "dia vacio" }));

  for (let dia = 1; dia <= cantidadDias; dia++) {
    const iso = `${mesVisible.anio}-${pad2(mesVisible.mes)}-${pad2(dia)}`;
    const info = diasConEntreno.get(iso);
    const planificado = diasPlanificados.get(iso);

    const clases = ["dia"];
    if (info) {
      clases.push("con-entreno");
      if (info.dificultad_max) clases.push(`nivel-${info.dificultad_max}`);
    }
    if (planificado) clases.push("planificado");
    if (iso === hoyISO) clases.push("hoy");
    if (fechaSeleccionada === iso) clases.push("seleccionado");

    const datosAria = [];
    if (info) datosAria.push(`${info.cantidad} entrenamiento${info.cantidad === 1 ? "" : "s"}`);
    if (planificado) datosAria.push(`${planificado.rutinas.length} rutina${planificado.rutinas.length === 1 ? "" : "s"} prevista${planificado.rutinas.length === 1 ? "" : "s"}`);
    const etiquetaAria = [formatoFechaLarga(iso), ...datosAria].join(": ");

    const marcas = [];
    if (info) marcas.push(el("span", { class: "marca", text: info.dificultad_max ? "💪" : "✅" }));
    if (planificado) marcas.push(el("span", { class: "marca planificado-marca", text: "📅" }));

    celdas.push(
      el(
        "button",
        {
          type: "button",
          class: clases.join(" "),
          "aria-label": etiquetaAria,
          "aria-current": iso === hoyISO ? "date" : null,
          onclick: () => {
            fechaSeleccionada = iso;
            aplicarFiltro(filtroDia(iso));
          },
        },
        el("span", { class: "num", text: String(dia) }),
        ...(iso === hoyISO ? [el("small", { class: "etiqueta-hoy", text: "HOY" })] : []),
        ...(marcas.length ? [el("span", { class: "marcas-dia" }, ...marcas)] : []),
        info && info.dificultad_max ? el("small", { class: "nivel-numero", text: String(info.dificultad_max) }) : "",
        planificado && planificado.rutinas.length > 1
          ? el("small", { class: "cantidad-planificada", text: `${planificado.rutinas.length}` })
          : ""
      )
    );
  }
  grilla.replaceChildren(...celdas);
}

// ---------- Lista ----------
function tarjeta(entrenamiento) {
  const datos = [el("span", { text: `⏱ ${formatoDuracionCorta(entrenamiento.duracion_segundos)}` })];
  if (entrenamiento.dificultad) {
    datos.push(el("span", { title: "Dificultad", text: `💪 ${entrenamiento.dificultad}/5` }));
  }
  if (entrenamiento.cansancio) {
    datos.push(el("span", { title: "Cansancio", text: CARITAS_CANSANCIO[entrenamiento.cansancio - 1] }));
  }
  if (entrenamiento.animo) {
    datos.push(el("span", { title: "Estado de ánimo", text: CARITAS_ANIMO[entrenamiento.animo - 1] }));
  }
  datos.push(el("span", { text: `🏋️ ${entrenamiento.volumen_total_kg} kg` }));
  if (entrenamiento.agua_ml) datos.push(el("span", { text: `💧 ${entrenamiento.agua_ml} ml` }));

  const nombres = entrenamiento.ejercicios.map((item) => item.ejercicio.nombre);
  const visibles = nombres.slice(0, 4).join(" · ");
  const resto = nombres.length > 4 ? ` · +${nombres.length - 4} más` : "";

  return el(
    "a",
    { class: "entreno-card", href: `/entrenamiento.html?id=${entrenamiento.id}` },
    el("span", { class: "entreno-fecha", text: formatoFechaLarga(entrenamiento.fecha) }),
    el("h2", { class: "entreno-titulo", text: entrenamiento.titulo }),
    el("div", { class: "entreno-datos" }, ...datos),
    el("p", { class: "entreno-ejercicios", text: visibles + resto })
  );
}

async function cargarLista(reiniciar) {
  const miPeticion = ++numeroPeticion;
  if (reiniciar) {
    offset = 0;
    lista.replaceChildren();
    botonMas.classList.add("oculto");
  }
  estado.textContent = "Cargando…";

  const params = new URLSearchParams({ limite: LIMITE, offset: offset });
  if (filtro.desde) params.set("desde", filtro.desde);
  if (filtro.hasta) params.set("hasta", filtro.hasta);

  try {
    const entrenamientos = await apiFetch(`/entrenamientos?${params.toString()}`);
    if (miPeticion !== numeroPeticion) return; // llegó una búsqueda más nueva
    entrenamientos.forEach((entrenamiento) => lista.append(tarjeta(entrenamiento)));
    offset += entrenamientos.length;
    botonMas.classList.toggle("oculto", entrenamientos.length < LIMITE);
    estado.textContent = lista.children.length ? "" : "No hay entrenamientos en este período.";
  } catch (e) {
    if (miPeticion === numeroPeticion) estado.textContent = e.message;
  }
}

// ---------- Eventos ----------
document.getElementById("mes-anterior").addEventListener("click", async () => {
  const { anio, mes } = mesDesplazado(-1);
  await mostrarMes(anio, mes);
  aplicarFiltro(filtroMes(anio, mes));
});

document.getElementById("mes-siguiente").addEventListener("click", async () => {
  const { anio, mes } = mesDesplazado(1);
  await mostrarMes(anio, mes);
  aplicarFiltro(filtroMes(anio, mes));
});

document.getElementById("filtros-rapidos").addEventListener("click", async (evento) => {
  const boton = evento.target.closest("[data-filtro]");
  if (!boton) return;
  const ahora = new Date();
  const accion = boton.dataset.filtro;

  if (accion === "todo") {
    aplicarFiltro({ desde: null, hasta: null, etiqueta: "Todo el historial" });
    return;
  }
  await mostrarMes(ahora.getFullYear(), ahora.getMonth() + 1);
  if (accion === "hoy") aplicarFiltro(filtroDia(aISO(ahora)));
  if (accion === "semana") aplicarFiltro(filtroSemana(ahora));
  if (accion === "mes") aplicarFiltro(filtroMes(ahora.getFullYear(), ahora.getMonth() + 1));
});

document.getElementById("aplicar-periodo").addEventListener("click", () => {
  errorPeriodo.textContent = "";
  const desde = campoDesde.value;
  const hasta = campoHasta.value;

  if (!desde && !hasta) {
    errorPeriodo.textContent = "Elegí al menos una fecha.";
    return;
  }
  if (desde && hasta && desde > hasta) {
    errorPeriodo.textContent = "La fecha «desde» no puede ser posterior a «hasta».";
    return;
  }
  let etiqueta;
  if (desde && hasta) etiqueta = `Del ${formatoFechaCorta(desde)} al ${formatoFechaCorta(hasta)}`;
  else if (desde) etiqueta = `Desde el ${formatoFechaCorta(desde)}`;
  else etiqueta = `Hasta el ${formatoFechaCorta(hasta)}`;

  aplicarFiltro({ desde: desde || null, hasta: hasta || null, etiqueta });
});

botonMas.addEventListener("click", () => cargarLista(false));

// ---------- Inicio ----------
(async () => {
  try {
    await cargarCalendario();
    aplicarFiltro(filtroMes(mesVisible.anio, mesVisible.mes));
  } catch (e) {
    estado.textContent = e.message;
  }
})();