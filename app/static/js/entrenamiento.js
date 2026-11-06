// Pantalla de entrenamiento.
// Requiere: api.js y ejercicios-ui.js

requerirSesion();

const entrenamientoId = new URLSearchParams(window.location.search).get("id");
if (!entrenamientoId) window.location.href = "/entrenar.html";

const CARITAS_CANSANCIO = ["😄", "🙂", "😐", "😓", "😫"];
const ETIQUETAS_CANSANCIO = ["Nada cansado", "Poco cansado", "Normal", "Cansado", "Agotado"];
const CARITAS_ANIMO = ["😞", "🙁", "😐", "🙂", "😄"];
const ETIQUETAS_ANIMO = ["Muy mal", "Mal", "Normal", "Bien", "Excelente"];

const vistaEntrenamiento = document.getElementById("vista-entrenamiento");
const vistaResumen = document.getElementById("vista-resumen");
const tituloPagina = document.getElementById("titulo");
const cronometro = document.getElementById("cronometro");
const estadoGuardado = document.getElementById("estado-guardado");
const listaEjercicios = document.getElementById("lista-ejercicios");
const mensajeError = document.getElementById("error");
const dialogoFinalizar = document.getElementById("dialogo-finalizar");
const formFinalizar = document.getElementById("form-finalizar");
const errorFinalizar = document.getElementById("error-finalizar");
const botonConfirmar = document.getElementById("confirmar-finalizar");

let grupos = [];
let perfil = null;
let estado = { ejercicios: [] };
let inicio = null;
let intervaloCronometro = null;

// Guardado automático
let version = 0;
let temporizadorGuardado = null;
let guardando = false;
let pendiente = false;

// Datos opcionales del cierre
let cierre = { aguaMl: null, dificultad: null, cansancio: null, animo: null };

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

function mostrarError(mensaje) {
  mensajeError.textContent = mensaje;
}

function formatoDuracion(totalSegundos) {
  const horas = Math.floor(totalSegundos / 3600);
  const minutos = Math.floor((totalSegundos % 3600) / 60);
  const segundos = totalSegundos % 60;
  const mm = String(minutos).padStart(2, "0");
  const ss = String(segundos).padStart(2, "0");
  return horas > 0 ? `${horas}:${mm}:${ss}` : `${mm}:${ss}`;
}

// ---------- Cronómetro ----------
function iniciarCronometro() {
  const actualizar = () => {
    const segundos = Math.max(0, Math.floor((Date.now() - inicio.getTime()) / 1000));
    cronometro.textContent = formatoDuracion(segundos);
  };
  actualizar();
  intervaloCronometro = setInterval(actualizar, 1000);
}

// ---------- Estado ----------
function desdeRespuesta(entrenamiento) {
  return {
    ejercicios: entrenamiento.ejercicios.map((item) => ({
      id: item.id,
      ejercicio_id: item.ejercicio.id,
      nombre: item.ejercicio.nombre,
      grupo: item.ejercicio.grupo_principal,
      tipoMedicion: item.ejercicio.tipo_medicion,
      usaPesoCorporal: item.ejercicio.usa_peso_corporal,
      notas: item.notas || "",
      series: item.series.map((serie) => ({
        id: serie.id,
        peso: serie.peso_kg ?? "",
        reps: serie.repeticiones,
        duracionSegundos: serie.duracion_segundos,
        completada: serie.completada,
      })),
    })),
  };
}

function cambio() {
  version += 1;
  estadoGuardado.textContent = "Guardando…";
  clearTimeout(temporizadorGuardado);
  temporizadorGuardado = setTimeout(guardar, 600);
}

function armarCuerpo() {
  const ejercicios = [];
  for (const ejercicio of estado.ejercicios) {
    const series = [];
    const esTiempo = ejercicio.tipoMedicion === "TIEMPO";
    for (const serie of ejercicio.series) {
      if (esTiempo) {
        const duracion = Number(serie.duracionSegundos);
        if (!Number.isInteger(duracion) || duracion < 1 || duracion > 86400) return null;
        series.push({
          id: serie.id ?? null,
          peso_kg: null,
          repeticiones: null,
          duracion_segundos: duracion,
          completada: !!serie.completada,
        });
        continue;
      }

      const reps = Number(serie.reps);
      if (!Number.isInteger(reps) || reps < 1 || reps > 200) return null;
      let peso = null;
      if (!ejercicio.usaPesoCorporal && serie.peso !== "" && serie.peso !== null) {
        peso = Number(serie.peso);
        if (Number.isNaN(peso) || peso < 0 || peso > 1000) return null;
      }
      series.push({
        id: serie.id ?? null,
        peso_kg: peso,
        repeticiones: reps,
        duracion_segundos: null,
        completada: !!serie.completada,
      });
    }
    ejercicios.push({
      id: ejercicio.id ?? null,
      ejercicio_id: ejercicio.ejercicio_id,
      notas: (ejercicio.notas || "").trim() || null,
      series,
    });
  }
  return { ejercicios };
}

// Si no hubo cambios mientras se guardaba, se copian los ids nuevos del servidor
function fusionarIds(respuesta) {
  if (respuesta.ejercicios.length !== estado.ejercicios.length) return;
  estado.ejercicios.forEach((ejercicio, i) => {
    const remoto = respuesta.ejercicios[i];
    ejercicio.id = remoto.id;
    if (remoto.series.length === ejercicio.series.length) {
      ejercicio.series.forEach((serie, j) => {
        serie.id = remoto.series[j].id;
        serie.peso = remoto.series[j].peso_kg ?? "";
        serie.duracionSegundos = remoto.series[j].duracion_segundos;
      });
    }
  });
}

async function guardar() {
  clearTimeout(temporizadorGuardado);
  if (guardando) {
    pendiente = true;
    return true;
  }
  const cuerpo = armarCuerpo();
  if (!cuerpo) {
    estadoGuardado.textContent = "Revisá los datos de duración, repeticiones y pesos para guardar";
    return false;
  }

  guardando = true;
  const versionEnviada = version;
  let correcto = false;
  try {
    const respuesta = await apiFetch(`/entrenamientos/${entrenamientoId}`, { method: "PUT", body: cuerpo });
    if (versionEnviada === version) fusionarIds(respuesta);
    estadoGuardado.textContent = "Guardado ✓";
    mostrarError("");
    correcto = true;
  } catch (e) {
    if (e.status === 409) {
      window.location.href = "/entrenar.html";
      return false;
    }
    estadoGuardado.textContent = "No se pudo guardar";
    mostrarError(e.message);
  } finally {
    guardando = false;
  }

  if (correcto && pendiente) {
    pendiente = false;
    return guardar();
  }
  pendiente = false;
  return correcto;
}

async function guardarYEsperar() {
  while (guardando) await new Promise((resolver) => setTimeout(resolver, 100));
  return guardar();
}

// ---------- Dibujo de ejercicios y series ----------
function botonIcono(simbolo, titulo, accion, extra = "") {
  return el("button", {
    type: "button",
    class: "boton-icono " + extra,
    title: titulo,
    "aria-label": titulo,
    onclick: accion,
    text: simbolo,
  });
}

function filaSerie(serie, indice, ejercicio) {
  const peso = el("input", {
    type: "number", min: 0, max: 1000, step: 0.5, inputmode: "decimal",
    value: serie.peso, placeholder: "—", "aria-label": `Peso de la serie ${indice + 1}`,
    disabled: ejercicio.usaPesoCorporal,
    oninput: (evento) => { serie.peso = evento.target.value; cambio(); },
  });
  const reps = el("input", {
    type: "number", min: 1, max: 200, step: 1, inputmode: "numeric",
    value: serie.reps, "aria-label": `Repeticiones de la serie ${indice + 1}`,
    oninput: (evento) => { serie.reps = evento.target.value; cambio(); },
  });
  const check = el("button", {
    type: "button",
    class: "check-serie" + (serie.completada ? " hecha" : ""),
    title: "Marcar como hecha",
    "aria-pressed": String(serie.completada),
    text: serie.completada ? "✓" : "",
    onclick: () => {
      serie.completada = !serie.completada;
      cambio();
      pintarEjercicios();
    },
  });
  return el(
    "div",
    { class: "fila-serie" + (serie.completada ? " completa" : "") },
    el("span", { class: "num-serie", text: String(indice + 1) }),
    peso, reps, check
  );
}

function filaTiempo(serie) {
  const minutos = serie.duracionSegundos === null || serie.duracionSegundos === undefined
    ? ""
    : Number((serie.duracionSegundos / 60).toFixed(2));
  const entrada = el("input", {
    type: "number", min: 0.5, max: 1440, step: 0.5, inputmode: "decimal",
    value: minutos, placeholder: "Minutos", "aria-label": "Duración en minutos",
    oninput: (evento) => {
      const valor = evento.target.value;
      serie.duracionSegundos = valor === "" ? null : Math.round(Number(valor) * 60);
      cambio();
    },
  });
  const check = el("button", {
    type: "button",
    class: "check-serie" + (serie.completada ? " hecha" : ""),
    title: "Marcar como hecha",
    "aria-pressed": String(serie.completada),
    text: serie.completada ? "✓" : "",
    onclick: () => {
      serie.completada = !serie.completada;
      cambio();
      pintarEjercicios();
    },
  });
  return el("div", { class: "fila-tiempo" },
    el("label", { class: "campo-chico" }, "Duración (min)", entrada),
    check
  );
}

function tarjetaEjercicio(ejercicio, indice) {
  const cabecera = el(
    "div",
    { class: "ej-cabecera" },
    el(
      "div", {},
      el("strong", { text: ejercicio.nombre }),
      el("span", { class: "tag principal", text: etiquetaGrupo(grupos, ejercicio.grupo) })
    ),
    botonIcono("✕", "Quitar ejercicio", () => {
      if (!window.confirm(`¿Quitar "${ejercicio.nombre}" del entrenamiento?`)) return;
      estado.ejercicios.splice(indice, 1);
      cambio();
      pintarEjercicios();
    }, "peligro")
  );

  if (ejercicio.tipoMedicion === "TIEMPO") {
    const notas = el("textarea", {
      rows: 1, maxlength: 500, placeholder: "Notas (opcional)", text: ejercicio.notas,
      oninput: (evento) => { ejercicio.notas = evento.target.value; cambio(); },
    });
    return el(
      "div",
      { class: "ej-tarjeta ejercicio-tiempo" },
      cabecera,
      el("p", { class: "rutina-meta", text: "Registrá el tiempo total realizado. Este ejercicio no suma volumen de fuerza." }),
      ...ejercicio.series.map(filaTiempo),
      notas
    );
  }

  const encabezado = el(
    "div",
    { class: "fila-serie encabezado" },
    el("span", { text: "Serie" }), el("span", { text: "Peso (kg)" }), el("span", { text: "Reps" }), el("span", { text: "Hecha" })
  );

  const accionesSeries = el(
    "div",
    { class: "acciones-series" },
    el("button", {
      type: "button", class: "boton-chico", text: "+ Serie",
      onclick: () => {
        const anterior = ejercicio.series[ejercicio.series.length - 1];
        ejercicio.series.push({
          id: null,
          peso: anterior ? anterior.peso : "",
          reps: anterior ? anterior.reps : 10,
          completada: false,
        });
        cambio();
        pintarEjercicios();
      },
    }),
    el("button", {
      type: "button", class: "boton-chico", text: "− Serie",
      disabled: ejercicio.series.length <= 1,
      onclick: () => {
        ejercicio.series.pop();
        cambio();
        pintarEjercicios();
      },
    })
  );

  const notas = el("textarea", {
    rows: 1, maxlength: 500, placeholder: "Notas (opcional)", text: ejercicio.notas,
    oninput: (evento) => { ejercicio.notas = evento.target.value; cambio(); },
  });

  return el(
    "div",
    { class: "ej-tarjeta" },
    cabecera,
    ...(ejercicio.usaPesoCorporal
      ? [el("p", { class: "rutina-meta", text: perfil && perfil.peso_actual_kg
          ? `Carga automática: ${perfil.peso_actual_kg} kg (peso de tu perfil)`
          : "No hay un peso cargado en tu perfil; el volumen no podrá calcularse hasta registrarlo." })]
      : []),
    encabezado, ...ejercicio.series.map((serie, i) => filaSerie(serie, i, ejercicio)), accionesSeries, notas
  );
}


function pintarEjercicios() {
  if (!estado.ejercicios.length) {
    listaEjercicios.replaceChildren(
      el("p", { class: "estado-lista", text: "Todavía no agregaste ejercicios. Usá “+ Agregar ejercicio”." })
    );
    return;
  }
  listaEjercicios.replaceChildren(...estado.ejercicios.map(tarjetaEjercicio));
}

// ---------- Cierre del entrenamiento ----------
function crearRating(contenedor, simbolo, alCambiar) {
  let valor = null;
  const botones = [1, 2, 3, 4, 5].map((n) =>
    el("button", {
      type: "button", class: "rating-item", "aria-label": `${n} de 5`, text: simbolo,
      onclick: () => {
        valor = valor === n ? null : n;
        pintar();
        alCambiar(valor);
      },
    })
  );
  function pintar() {
    botones.forEach((boton, i) => boton.classList.toggle("activo", valor !== null && i < valor));
  }
  contenedor.replaceChildren(...botones);
}

function crearCaritas(contenedor, emojis, etiquetas, alCambiar) {
  let valor = null;
  const botones = emojis.map((emoji, i) =>
    el("button", {
      type: "button", class: "carita", title: etiquetas[i], "aria-label": etiquetas[i], text: emoji,
      onclick: () => {
        valor = valor === i + 1 ? null : i + 1;
        pintar();
        alCambiar(valor);
      },
    })
  );
  function pintar() {
    botones.forEach((boton, i) => boton.classList.toggle("activa", valor === i + 1));
  }
  contenedor.replaceChildren(...botones);
}

function crearAgua() {
  const contenedor = document.getElementById("agua-opciones");
  const total = document.getElementById("agua-total");
  const usaBotella = perfil && perfil.unidad_hidratacion === "BOTELLAS" && perfil.ml_botella;

  if (usaBotella) {
    const opciones = [[0, "Nada"], [0.5, "½ botella"], [1, "1 botella"], [1.5, "1½ botellas"], [2, "2 botellas"]];
    const chips = opciones.map(([multiplo, etiqueta]) =>
      el("button", {
        type: "button", class: "chip", text: etiqueta,
        onclick: () => {
          cierre.aguaMl = Math.round(multiplo * perfil.ml_botella);
          chips.forEach((chip) => chip.classList.remove("activo"));
          event.currentTarget.classList.add("activo");
          total.textContent = `≈ ${cierre.aguaMl} ml`;
        },
      })
    );
    contenedor.replaceChildren(...chips);
    total.textContent = "";
  } else {
    const entrada = el("input", {
      type: "number", min: 0, max: 10000, step: 50, inputmode: "numeric", placeholder: "Mililitros (ml)",
      oninput: (evento) => {
        cierre.aguaMl = evento.target.value === "" ? null : Number(evento.target.value);
      },
    });
    contenedor.replaceChildren(entrada);
    total.textContent = "";
  }
}

async function abrirFinalizar() {
  mostrarError("");
  const guardado = await guardarYEsperar();
  if (!guardado) {
    mostrarError("Revisá los datos de duración, repeticiones y pesos antes de terminar.");
    return;
  }

  const todas = estado.ejercicios.reduce((suma, e) => suma + e.series.length, 0);
  const hechas = estado.ejercicios.reduce((suma, e) => suma + e.series.filter((s) => s.completada).length, 0);
  if (hechas === 0) {
    mostrarError("Marcá al menos un ejercicio o registro como hecho para terminar.");
    return;
  }

  document.getElementById("aviso-series").textContent =
    todas > hechas
      ? `${hechas} registro${hechas === 1 ? "" : "s"} completado${hechas === 1 ? "" : "s"}. Los ${todas - hechas} pendientes no se van a guardar.`
      : `${hechas} registro${hechas === 1 ? "" : "s"} completado${hechas === 1 ? "" : "s"}. ¡Bien ahí!`;

  cierre = { aguaMl: null, dificultad: null, cansancio: null, animo: null };
  errorFinalizar.textContent = "";
  botonConfirmar.disabled = false;
  crearAgua();
  crearRating(document.getElementById("rating-dificultad"), "💪", (v) => { cierre.dificultad = v; });
  crearCaritas(document.getElementById("caritas-cansancio"), CARITAS_CANSANCIO, ETIQUETAS_CANSANCIO, (v) => { cierre.cansancio = v; });
  crearCaritas(document.getElementById("caritas-animo"), CARITAS_ANIMO, ETIQUETAS_ANIMO, (v) => { cierre.animo = v; });
  dialogoFinalizar.showModal();
}

formFinalizar.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  errorFinalizar.textContent = "";
  botonConfirmar.disabled = true;
  try {
    const entrenamiento = await apiFetch(`/entrenamientos/${entrenamientoId}/finalizar`, {
      method: "POST",
      body: {
        agua_ml: cierre.aguaMl,
        dificultad: cierre.dificultad,
        cansancio: cierre.cansancio,
        animo: cierre.animo,
      },
    });
    dialogoFinalizar.close();
    clearInterval(intervaloCronometro);
    mostrarResumen(entrenamiento);
    document.getElementById("resumen-encabezado").textContent = "¡Entrenamiento terminado!";
  } catch (e) {
    errorFinalizar.textContent = e.message;
    botonConfirmar.disabled = false;
  }
});

// ---------- Resumen ----------
function datoResumen(valor, etiqueta) {
  return el("div", { class: "dato" }, el("strong", { text: valor }), el("span", { text: etiqueta }));
}

function mostrarResumen(entrenamiento) {
  vistaEntrenamiento.classList.add("oculto");
  vistaResumen.classList.remove("oculto");

  document.getElementById("resumen-titulo").textContent =
    `${entrenamiento.titulo} · ${formatoFechaLarga(entrenamiento.fecha)}`;
  document.getElementById("resumen-datos").replaceChildren(
    datoResumen(formatoDuracion(entrenamiento.duracion_segundos || 0), "Duración"),
    datoResumen(`${entrenamiento.volumen_total_kg} kg`, "Volumen total"),
    datoResumen(String(entrenamiento.series_completadas), "Registros completados"),
    datoResumen(entrenamiento.agua_ml ? `${entrenamiento.agua_ml} ml` : "—", "Agua")
  );

  const musculos = new Set();
  entrenamiento.ejercicios.forEach((item) => {
    musculos.add(etiquetaGrupo(grupos, item.ejercicio.grupo_principal));
    if (item.ejercicio.grupo_secundario) musculos.add(etiquetaGrupo(grupos, item.ejercicio.grupo_secundario));
  });
  document.getElementById("resumen-musculos").replaceChildren(
    ...[...musculos].map((nombre) => el("span", { class: "tag principal", text: nombre }))
  );

  const emojis = [];
  if (entrenamiento.dificultad) emojis.push(el("span", { title: "Dificultad", text: "💪".repeat(entrenamiento.dificultad) }));
  if (entrenamiento.cansancio) emojis.push(el("span", { title: "Cansancio", text: CARITAS_CANSANCIO[entrenamiento.cansancio - 1] }));
  if (entrenamiento.animo) emojis.push(el("span", { title: "Ánimo", text: CARITAS_ANIMO[entrenamiento.animo - 1] }));
  document.getElementById("resumen-estado").replaceChildren(...emojis);

  document.getElementById("resumen-ejercicios").replaceChildren(
    ...entrenamiento.ejercicios.map((item) => {
      const esTiempo = item.ejercicio.tipo_medicion === "TIEMPO";
      const cabecera = el(
        "div",
        { class: "resumen-cabecera" },
        el("strong", { text: item.ejercicio.nombre }),
        el("span", { text: esTiempo ? "Por tiempo · sin volumen" : `${item.volumen_kg} kg de volumen` })
      );
      const series = el(
        "ul",
        { class: "series-detalle" },
        ...item.series.map((serie) => el("li", {
          text: esTiempo
            ? `Duración: ${formatoDuracion(serie.duracion_segundos || 0)}`
            : `Serie ${serie.numero}: ${serie.peso_kg ?? "—"} kg × ${serie.repeticiones}`
        }))
      );
      const hijos = [cabecera, series];
      if (item.notas) hijos.push(el("p", { class: "rutina-meta", text: `📝 ${item.notas}` }));
      return el("li", { class: "con-detalle" }, ...hijos);
    })
  );

  cargarRecords(entrenamiento.id);
}

// ---------- Récords (RF-24) ----------
function textoRecord(pr) {
  if (pr.tipo === "PESO") {
    return `Nuevo récord de peso en ${pr.nombre}: ${pr.valor} kg (antes ${pr.anterior} kg)`;
  }
  if (pr.tipo === "VOLUMEN") {
    return `Nuevo récord de volumen en ${pr.nombre}: ${pr.valor} kg en una sesión (antes ${pr.anterior} kg)`;
  }
  if (pr.tipo === "DURACION") {
    return `Nuevo récord de duración en ${pr.nombre}: ${formatoDuracion(pr.valor)} (antes ${formatoDuracion(pr.anterior)})`;
  }
  return `Nuevo récord en ${pr.nombre}: ${pr.valor} repeticiones con ${pr.peso_kg} kg (antes ${pr.anterior})`;
}

async function cargarRecords(id) {
  const contenedor = document.getElementById("resumen-records");
  try {
    const prs = await apiFetch(`/estadisticas/entrenamientos/${id}/prs`);
    if (!prs.length) {
      contenedor.classList.add("oculto");
      return;
    }
    contenedor.replaceChildren(
      el("strong", { text: "🏆 ¡Récords personales!" }),
      ...prs.map((pr) => el("p", { text: textoRecord(pr) }))
    );
    contenedor.classList.remove("oculto");
  } catch (e) {
    contenedor.classList.add("oculto");
  }
}

// ---------- Eventos ----------
document.getElementById("agregar-ejercicio").addEventListener("click", () => {
  abrirSelectorEjercicios((elegido) => {
    estado.ejercicios.push({
      id: null,
      ejercicio_id: elegido.id,
      nombre: elegido.nombre,
      grupo: elegido.grupo_principal,
      tipoMedicion: elegido.tipo_medicion,
      usaPesoCorporal: elegido.usa_peso_corporal,
      notas: "",
      series: [elegido.tipo_medicion === "TIEMPO"
        ? { id: null, peso: "", reps: null, duracionSegundos: null, completada: false }
        : { id: null, peso: "", reps: 10, duracionSegundos: null, completada: false }],
    });
    cambio();
    pintarEjercicios();
  });
});

document.getElementById("terminar").addEventListener("click", abrirFinalizar);
document.getElementById("cerrar-finalizar").addEventListener("click", () => dialogoFinalizar.close());

document.getElementById("descartar").addEventListener("click", async () => {
  if (!window.confirm("¿Descartar este entrenamiento? Se pierde todo lo registrado.")) return;
  try {
    await apiFetch(`/entrenamientos/${entrenamientoId}`, { method: "DELETE" });
    window.location.href = "/entrenar.html";
  } catch (e) {
    mostrarError(e.message);
  }
});

// ---------- Inicio ----------
(async () => {
  try {
    [grupos, perfil] = await Promise.all([
      obtenerGrupos(),
      apiFetch("/perfil").catch(() => null), // el trainer no tiene este perfil
    ]);
    const entrenamiento = await apiFetch(`/entrenamientos/${entrenamientoId}`);

    if (entrenamiento.estado === "FINALIZADO") {
      mostrarResumen(entrenamiento);
      return;
    }

    tituloPagina.textContent = entrenamiento.titulo;
    inicio = new Date(entrenamiento.iniciado_en);
    estado = desdeRespuesta(entrenamiento);
    iniciarCronometro();
    pintarEjercicios();
  } catch (e) {
    if (e.status === 404) {
      window.location.href = "/entrenar.html";
      return;
    }
    mostrarError(e.message);
  }
})();