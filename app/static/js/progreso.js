// Sección de progreso.
// Requiere: Chart.js, api.js, ejercicios-ui.js y fechas-ui.js

requerirSesion();

const COLOR = "#1f7a4d";
const COLOR_SUAVE = "rgba(31, 122, 77, 0.15)";
const COLOR_TENDENCIA = "#d9822b";

const sesionActual = obtenerUsuario();
const graficos = {};
let periodoDias = 30;
let metrica = "peso";
let ejerciciosEntrenados = [];

// ---------- Utilidades ----------
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

function formatoNumero(valor, decimales = 1) {
  return Number(valor).toLocaleString("es-AR", { maximumFractionDigits: decimales });
}

function fechaCorta(iso) {
  const fecha = desdeISO(iso);
  return `${pad2(fecha.getDate())}/${pad2(fecha.getMonth() + 1)}`;
}

function dato(valor, etiqueta) {
  return el("div", { class: "dato" }, el("strong", { text: valor }), el("span", { text: etiqueta }));
}

function rangoPeriodo() {
  if (!periodoDias) return {};
  const desde = new Date();
  desde.setDate(desde.getDate() - periodoDias + 1);
  return { desde: aISO(desde) };
}

function dibujar(clave, idCanvas, configuracion) {
  if (typeof Chart === "undefined") return; // la librería no se pudo cargar
  if (graficos[clave]) graficos[clave].destroy();
  graficos[clave] = new Chart(document.getElementById(idCanvas), configuracion);
}

const OPCIONES_BASE = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
};

// ---------- Resumen y frecuencia ----------
async function cargarResumen() {
  const resumen = await apiFetch(`/estadisticas/resumen?${new URLSearchParams(rangoPeriodo())}`);

  const duracion =
    resumen.duracion_promedio_segundos === null ? null : Math.round(resumen.duracion_promedio_segundos);
  document.getElementById("datos-resumen").replaceChildren(
    dato(String(resumen.cantidad_entrenamientos), "Entrenamientos"),
    dato(formatoNumero(resumen.frecuencia_semanal, 2), "Por semana"),
    dato(formatoDuracionCorta(duracion), "Duración promedio"),
    dato(`${formatoNumero(resumen.volumen_total_kg, 0)} kg`, "Volumen acumulado"),
    dato(
      resumen.agua_promedio_ml === null ? "—" : `${formatoNumero(resumen.agua_promedio_ml, 0)} ml`,
      "Agua por entrenamiento"
    )
  );

  dibujar("semanas", "grafico-semanas", {
    type: "bar",
    data: {
      labels: resumen.por_semana.map((semana) => fechaCorta(semana.semana_inicio)),
      datasets: [{ data: resumen.por_semana.map((semana) => semana.cantidad), backgroundColor: COLOR }],
    },
    options: { ...OPCIONES_BASE, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

// ---------- Peso corporal ----------
function textoTendencia(tendencia) {
  if (!tendencia) return "Registrá tu peso en al menos dos días distintos para ver la tendencia.";
  const cambio = formatoNumero(Math.abs(tendencia.pendiente_kg_semana), 2);
  if (tendencia.direccion === "BAJA") return `📉 Tu peso viene bajando ${cambio} kg por semana.`;
  if (tendencia.direccion === "SUBE") return `📈 Tu peso viene subiendo ${cambio} kg por semana.`;
  return "➡️ Tu peso se mantiene estable.";
}

function pintarPeso(evolucion) {
  const variacion = evolucion.variacion_kg;
  document.getElementById("datos-peso").replaceChildren(
    dato(evolucion.peso_inicial === null ? "—" : `${formatoNumero(evolucion.peso_inicial)} kg`, "Inicial"),
    dato(evolucion.peso_actual === null ? "—" : `${formatoNumero(evolucion.peso_actual)} kg`, "Actual"),
    dato(
      variacion === null ? "—" : `${variacion > 0 ? "+" : ""}${formatoNumero(variacion)} kg`,
      "Variación"
    )
  );
  document.getElementById("texto-tendencia").textContent = textoTendencia(evolucion.tendencia);

  const datasets = [
    {
      label: "Peso",
      data: evolucion.registros.map((registro) => registro.peso_kg),
      borderColor: COLOR,
      backgroundColor: COLOR_SUAVE,
      pointRadius: 4,
      tension: 0.2,
    },
  ];
  if (evolucion.tendencia) {
    datasets.push({
      label: "Tendencia",
      data: evolucion.tendencia.puntos.map((punto) => punto.peso_kg),
      borderColor: COLOR_TENDENCIA,
      borderDash: [6, 6],
      pointRadius: 0,
    });
  }
  dibujar("peso", "grafico-peso", {
    type: "line",
    data: { labels: evolucion.registros.map((registro) => fechaCorta(registro.fecha)), datasets },
    options: { ...OPCIONES_BASE, plugins: { legend: { display: true } } },
  });
}

async function cargarPeso() {
  pintarPeso(await apiFetch("/peso"));
}

document.getElementById("form-peso").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const error = document.getElementById("error-peso");
  error.textContent = "";

  const peso = Number(document.getElementById("peso-valor").value);
  if (!document.getElementById("peso-valor").value || peso <= 20 || peso > 400) {
    error.textContent = "Ingresá un peso válido en kg (más de 20 y hasta 400).";
    return;
  }

  const boton = document.getElementById("peso-guardar");
  boton.disabled = true;
  try {
    const evolucion = await apiFetch("/peso", {
      method: "POST",
      body: { fecha: document.getElementById("peso-fecha").value || null, peso_kg: peso },
    });
    pintarPeso(evolucion);
    document.getElementById("peso-valor").value = "";
  } catch (e) {
    error.textContent = e.message;
  } finally {
    boton.disabled = false;
  }
});

// ---------- Ejercicios y mejores marcas ----------
function pintarMarcas() {
  const lista = document.getElementById("lista-marcas");
  if (!ejerciciosEntrenados.length) {
    lista.replaceChildren(el("li", { text: "Cuando entrenes vas a ver acá tus récords." }));
    return;
  }
  lista.replaceChildren(
    ...ejerciciosEntrenados.map((ejercicio) =>
      el(
        "li",
        {},
        el(
          "div",
          { class: "marca-fila", style: "width: 100%" },
          el("strong", { text: ejercicio.nombre }),
          el("span", {
            class: "valores",
            text:
              (ejercicio.mayor_peso_kg ? `🏆 ${formatoNumero(ejercicio.mayor_peso_kg)} kg` : "🏆 Peso corporal") +
              (ejercicio.mejor_volumen_sesion_kg
                ? ` · 📦 ${formatoNumero(ejercicio.mejor_volumen_sesion_kg, 0)} kg en una sesión`
                : ""),
          })
        )
      )
    )
  );
}

async function cargarDetalleEjercicio() {
  const id = document.getElementById("select-ejercicio").value;
  if (!id) return;
  const detalle = await apiFetch(`/estadisticas/ejercicios/${id}?${new URLSearchParams(rangoPeriodo())}`);

  const marcas = detalle.marcas;
  document.getElementById("datos-ejercicio").replaceChildren(
    dato(`${formatoNumero(detalle.volumen_total_kg, 0)} kg`, "Volumen en el período"),
    dato(
      marcas.mayor_peso
        ? `${formatoNumero(marcas.mayor_peso.peso_kg)} kg × ${marcas.mayor_peso.repeticiones}`
        : "—",
      "Mayor peso (histórico)"
    ),
    dato(
      marcas.mejor_volumen_sesion ? `${formatoNumero(marcas.mejor_volumen_sesion.volumen_kg, 0)} kg` : "—",
      "Mejor volumen en una sesión"
    )
  );

  const sesiones = detalle.sesiones;
  document.getElementById("aviso-ejercicio").textContent = sesiones.length
    ? ""
    : "No entrenaste este ejercicio en el período elegido.";
  dibujar("ejercicio", "grafico-ejercicio", {
    type: metrica === "peso" ? "line" : "bar",
    data: {
      labels: sesiones.map((sesion) => fechaCorta(sesion.fecha)),
      datasets: [
        {
          data: sesiones.map((sesion) => (metrica === "peso" ? sesion.peso_max_kg : sesion.volumen_kg)),
          borderColor: COLOR,
          backgroundColor: metrica === "peso" ? COLOR_SUAVE : COLOR,
          pointRadius: 4,
          tension: 0.2,
        },
      ],
    },
    options: { ...OPCIONES_BASE, scales: { y: { beginAtZero: metrica === "volumen" } } },
  });

  document.getElementById("reps-por-peso").replaceChildren(
    ...marcas.repeticiones_por_peso.slice(0, 8).map((marca) =>
      el(
        "li",
        {},
        el("span", { text: marca.peso_kg > 0 ? `${formatoNumero(marca.peso_kg)} kg` : "Peso corporal" }),
        el("span", { text: `${marca.repeticiones} repeticiones · ${formatoFechaCorta(marca.fecha)}` })
      )
    )
  );
}

async function cargarEjercicios() {
  ejerciciosEntrenados = await apiFetch("/estadisticas/ejercicios");
  pintarMarcas();

  const hay = ejerciciosEntrenados.length > 0;
  document.getElementById("sin-ejercicios").classList.toggle("oculto", hay);
  document.getElementById("zona-ejercicio").classList.toggle("oculto", !hay);
  if (!hay) return;

  const select = document.getElementById("select-ejercicio");
  select.replaceChildren(
    ...ejerciciosEntrenados.map((ejercicio) =>
      el("option", { value: ejercicio.ejercicio_id, text: `${ejercicio.nombre} (${ejercicio.sesiones} sesiones)` })
    )
  );
  await cargarDetalleEjercicio();
}

// ---------- Eventos ----------
function activarChip(contenedor, boton) {
  contenedor.querySelectorAll(".chip").forEach((chip) => chip.classList.remove("activo"));
  boton.classList.add("activo");
}

document.getElementById("periodos").addEventListener("click", async (evento) => {
  const boton = evento.target.closest("[data-dias]");
  if (!boton) return;
  periodoDias = Number(boton.dataset.dias);
  activarChip(document.getElementById("periodos"), boton);
  await Promise.all([seguro(cargarResumen), seguro(cargarDetalleEjercicio)]);
});

document.getElementById("metricas").addEventListener("click", async (evento) => {
  const boton = evento.target.closest("[data-metrica]");
  if (!boton) return;
  metrica = boton.dataset.metrica;
  activarChip(document.getElementById("metricas"), boton);
  await seguro(cargarDetalleEjercicio);
});

document.getElementById("select-ejercicio").addEventListener("change", () => seguro(cargarDetalleEjercicio));

// ---------- Inicio ----------
// Cada sección carga por su cuenta: si una falla, las otras se muestran igual
async function seguro(funcion) {
  try {
    await funcion();
  } catch (e) {
    console.error(e);
  }
}

(async () => {
  const hoyISO = aISO(new Date());
  const campoFecha = document.getElementById("peso-fecha");
  campoFecha.value = hoyISO;
  campoFecha.max = hoyISO;

  if (sesionActual && sesionActual.rol !== "USUARIO") {
    document.getElementById("seccion-peso").classList.add("oculto");
  }

  await Promise.all([
    seguro(cargarResumen),
    sesionActual && sesionActual.rol === "USUARIO" ? seguro(cargarPeso) : Promise.resolve(),
    seguro(cargarEjercicios),
  ]);
})();