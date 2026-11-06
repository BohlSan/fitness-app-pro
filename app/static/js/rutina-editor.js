// Editor de rutinas.
// Requiere: api.js, ejercicios-ui.js y rutinas-comun.js

requerirSesion();

let rutinaId = new URLSearchParams(window.location.search).get("id");

const campoNombre = document.getElementById("nombre");
const campoDescripcion = document.getElementById("descripcion");
const tabsDias = document.getElementById("tabs-dias");
const panelDia = document.getElementById("panel-dia");
const zonaAgregarDia = document.getElementById("agregar-dia");
const selectDia = document.getElementById("select-dia");
const mensajeError = document.getElementById("error");
const botonGuardar = document.getElementById("guardar");
const botonEliminar = document.getElementById("eliminar");

let grupos = [];
let estado = { nombre: "", descripcion: "", dias: [] };
let diaActivo = 0;

const DIAS_JS = ["DOMINGO", "LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"];

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

function mostrarError(mensaje) {
  mensajeError.textContent = mensaje;
  if (mensaje) mensajeError.scrollIntoView({ behavior: "smooth", block: "center" });
}

// ---------- Estado ----------
function desdeRespuesta(rutina) {
  return {
    nombre: rutina.nombre,
    descripcion: rutina.descripcion || "",
    dias: rutina.dias.map((dia) => ({
      id: dia.id,
      dia_semana: dia.dia_semana,
      nombre: dia.nombre,
      ejercicios: dia.ejercicios.map((item) => ({
        id: item.id,
        ejercicio_id: item.ejercicio.id,
        nombre_ejercicio: item.ejercicio.nombre,
        grupo: item.ejercicio.grupo_principal,
        tipo_medicion: item.ejercicio.tipo_medicion,
        usa_peso_corporal: item.ejercicio.usa_peso_corporal,
        series: item.series,
        repeticiones: item.repeticiones,
        duracion_sugerida_segundos: item.duracion_sugerida_segundos ?? null,
        peso: item.peso_sugerido_kg ?? "",
        descanso: item.descanso_segundos ?? "",
      })),
    })),
  };
}

function ordenarDias() {
  estado.dias.sort((a, b) => ordenDia(a.dia_semana) - ordenDia(b.dia_semana));
}

function indiceDeHoy() {
  const hoy = DIAS_JS[new Date().getDay()];
  const indice = estado.dias.findIndex((dia) => dia.dia_semana === hoy);
  return indice >= 0 ? indice : 0;
}

// ---------- Dibujo ----------
function botonIcono(simbolo, titulo, accion, deshabilitado = false, extra = "") {
  return el("button", {
    type: "button",
    class: "boton-icono " + extra,
    title: titulo,
    "aria-label": titulo,
    disabled: deshabilitado,
    onclick: accion,
    text: simbolo,
  });
}

function campoNumero(etiqueta, valor, min, max, paso, alCambiar) {
  const input = el("input", {
    type: "number",
    min: min,
    max: max,
    step: paso,
    value: valor,
    inputmode: "decimal",
    oninput: (evento) => alCambiar(evento.target.value),
  });
  return el("label", { class: "campo-chico" }, etiqueta, input);
}

function mover(dia, indice, delta) {
  const destino = indice + delta;
  [dia.ejercicios[indice], dia.ejercicios[destino]] = [dia.ejercicios[destino], dia.ejercicios[indice]];
  render();
}

function tarjetaEjercicio(dia, ejercicio, indice) {
  const titulo = el(
    "div",
    {},
    el("strong", { text: ejercicio.nombre_ejercicio }),
    el("span", { class: "tag principal", text: etiquetaGrupo(grupos, ejercicio.grupo) })
  );
  const botones = el(
    "div",
    { class: "ej-botones" },
    botonIcono("↑", "Subir", () => mover(dia, indice, -1), indice === 0),
    botonIcono("↓", "Bajar", () => mover(dia, indice, 1), indice === dia.ejercicios.length - 1),
    botonIcono("✕", "Quitar ejercicio", () => {
      dia.ejercicios.splice(indice, 1);
      render();
    }, false, "peligro")
  );
  const esTiempo = ejercicio.tipo_medicion === "TIEMPO";
  const controles = esTiempo
    ? [campoNumero(
        "Duración objetivo (min)",
        ejercicio.duracion_sugerida_segundos === null ? "" : ejercicio.duracion_sugerida_segundos / 60,
        0.5, 1440, 0.5,
        (v) => { ejercicio.duracion_sugerida_segundos = v === "" ? null : Math.round(Number(v) * 60); }
      )]
    : [
        campoNumero("Series", ejercicio.series, 1, 20, 1, (v) => { ejercicio.series = v; }),
        campoNumero("Repeticiones", ejercicio.repeticiones, 1, 100, 1, (v) => { ejercicio.repeticiones = v; }),
        ...(ejercicio.usa_peso_corporal
          ? [el("p", { class: "rutina-meta", text: "Carga: se copia tu peso del perfil al entrenar." })]
          : [campoNumero("Peso sugerido (kg)", ejercicio.peso, 0, 1000, 0.5, (v) => { ejercicio.peso = v; })]),
        campoNumero("Descanso (seg)", ejercicio.descanso, 0, 3600, 5, (v) => { ejercicio.descanso = v; }),
      ];
  const campos = el("div", { class: "ej-campos" }, ...controles);
  return el("div", { class: "ej-tarjeta" }, el("div", { class: "ej-cabecera" }, titulo, botones), campos);
}


function pintarTabs() {
  tabsDias.replaceChildren(
    ...estado.dias.map((dia, indice) =>
      el("button", {
        type: "button",
        class: "tab" + (indice === diaActivo ? " activa" : ""),
        text: etiquetaDiaCorta(dia.dia_semana),
        onclick: () => {
          diaActivo = indice;
          render();
        },
      })
    )
  );
}

function pintarSelectorDia() {
  const usados = new Set(estado.dias.map((dia) => dia.dia_semana));
  const libres = DIAS_SEMANA.filter((dia) => !usados.has(dia.valor));
  selectDia.replaceChildren(
    ...libres.map((dia) => el("option", { value: dia.valor, text: dia.etiqueta }))
  );
  zonaAgregarDia.classList.toggle("oculto", libres.length === 0);
}

function pintarPanel() {
  panelDia.replaceChildren();
  if (!estado.dias.length) {
    panelDia.append(el("p", { class: "estado-lista", text: "Agregá el primer día de entrenamiento." }));
    return;
  }

  const dia = estado.dias[diaActivo];

  const campoNombreDia = el("input", {
    type: "text",
    maxlength: 100,
    placeholder: "Ej: Pecho y tríceps",
    value: dia.nombre,
    oninput: (evento) => { dia.nombre = evento.target.value; },
  });
  panelDia.append(
    el("label", { class: "campo-simple" }, `Entrenamiento del ${etiquetaDia(dia.dia_semana).toLowerCase()}`, campoNombreDia)
  );

  dia.ejercicios.forEach((ejercicio, indice) => panelDia.append(tarjetaEjercicio(dia, ejercicio, indice)));

  panelDia.append(
    el("button", {
      type: "button",
      class: "boton secundario",
      text: "+ Agregar ejercicio",
      onclick: () =>
        abrirSelectorEjercicios((elegido) => {
          dia.ejercicios.push({
            id: null,
            ejercicio_id: elegido.id,
            nombre_ejercicio: elegido.nombre,
            grupo: elegido.grupo_principal,
            tipo_medicion: elegido.tipo_medicion,
            usa_peso_corporal: elegido.usa_peso_corporal,
            series: elegido.tipo_medicion === "TIEMPO" ? null : 3,
            repeticiones: elegido.tipo_medicion === "TIEMPO" ? null : 10,
            duracion_sugerida_segundos: elegido.tipo_medicion === "TIEMPO" ? 600 : null,
            peso: "",
            descanso: "",
          });
          render();
        }),
    }),
    el("button", {
      type: "button",
      class: "boton-chico peligro",
      text: "Quitar este día",
      onclick: () => {
        if (!window.confirm("¿Quitar este día de la rutina?")) return;
        estado.dias.splice(diaActivo, 1);
        diaActivo = Math.max(0, diaActivo - 1);
        render();
      },
    })
  );
}

function render() {
  pintarTabs();
  pintarSelectorDia();
  pintarPanel();
}

// ---------- Validación y guardado ----------
function validar() {
  if (!estado.nombre.trim()) return "Ponele un nombre a la rutina.";
  if (!estado.dias.length) return "Agregá al menos un día de entrenamiento.";

  for (const dia of estado.dias) {
    const nombreDia = etiquetaDia(dia.dia_semana).toLowerCase();
    if (!dia.nombre.trim()) return `Completá el nombre del entrenamiento del ${nombreDia}.`;
    if (!dia.ejercicios.length) return `El ${nombreDia} necesita al menos un ejercicio.`;

    for (const ejercicio of dia.ejercicios) {
      const nombre = ejercicio.nombre_ejercicio;
      if (ejercicio.tipo_medicion === "TIEMPO") {
        const duracion = Number(ejercicio.duracion_sugerida_segundos);
        if (!Number.isInteger(duracion) || duracion < 1 || duracion > 86400) {
          return `Revisá la duración objetivo de "${nombre}" (entre 1 segundo y 24 horas).`;
        }
        continue;
      }
      const series = Number(ejercicio.series);
      const repeticiones = Number(ejercicio.repeticiones);
      if (!Number.isInteger(series) || series < 1 || series > 20) {
        return `Revisá las series de "${nombre}" (entre 1 y 20).`;
      }
      if (!Number.isInteger(repeticiones) || repeticiones < 1 || repeticiones > 100) {
        return `Revisá las repeticiones de "${nombre}" (entre 1 y 100).`;
      }
      if (!ejercicio.usa_peso_corporal && ejercicio.peso !== "" && !(Number(ejercicio.peso) >= 0 && Number(ejercicio.peso) <= 1000)) {
        return `Revisá el peso de "${nombre}" (entre 0 y 1000 kg).`;
      }
      if (
        ejercicio.descanso !== "" &&
        !(Number.isInteger(Number(ejercicio.descanso)) && Number(ejercicio.descanso) >= 0 && Number(ejercicio.descanso) <= 3600)
      ) {
        return `Revisá el descanso de "${nombre}" (entre 0 y 3600 segundos).`;
      }
    }
  }
  return "";
}

function armarCuerpo() {
  return {
    nombre: estado.nombre.trim(),
    descripcion: estado.descripcion.trim() || null,
    dias: estado.dias.map((dia) => ({
      id: dia.id ?? null,
      dia_semana: dia.dia_semana,
      nombre: dia.nombre.trim(),
      ejercicios: dia.ejercicios.map((ejercicio) => ({
        id: ejercicio.id ?? null,
        ejercicio_id: ejercicio.ejercicio_id,
        series: ejercicio.tipo_medicion === "TIEMPO" ? null : Number(ejercicio.series),
        repeticiones: ejercicio.tipo_medicion === "TIEMPO" ? null : Number(ejercicio.repeticiones),
        duracion_sugerida_segundos: ejercicio.tipo_medicion === "TIEMPO" ? Number(ejercicio.duracion_sugerida_segundos) : null,
        peso_sugerido_kg: ejercicio.usa_peso_corporal || ejercicio.tipo_medicion === "TIEMPO" || ejercicio.peso === "" ? null : Number(ejercicio.peso),
        descanso_segundos: ejercicio.tipo_medicion === "TIEMPO" || ejercicio.descanso === "" ? null : Number(ejercicio.descanso),
      })),
    })),
  };
}

async function guardar() {
  mostrarError("");
  const problema = validar();
  if (problema) {
    mostrarError(problema);
    return;
  }

  botonGuardar.disabled = true;
  try {
    if (rutinaId) {
      await apiFetch(`/rutinas/${rutinaId}`, { method: "PUT", body: armarCuerpo() });
    } else {
      await apiFetch("/rutinas", { method: "POST", body: armarCuerpo() });
    }
    window.location.href = "/entrenar.html";
  } catch (e) {
    mostrarError(e.message);
    botonGuardar.disabled = false;
  }
}

// ---------- Eventos ----------
campoNombre.addEventListener("input", () => { estado.nombre = campoNombre.value; });
campoDescripcion.addEventListener("input", () => { estado.descripcion = campoDescripcion.value; });

document.getElementById("btn-agregar-dia").addEventListener("click", () => {
  const elegido = selectDia.value;
  if (!elegido) return;
  estado.dias.push({ id: null, dia_semana: elegido, nombre: "", ejercicios: [] });
  ordenarDias();
  diaActivo = estado.dias.findIndex((dia) => dia.dia_semana === elegido);
  render();
});

botonGuardar.addEventListener("click", guardar);

// Guarda la rutina y arranca el entrenamiento del día que se está viendo
document.getElementById("iniciar").addEventListener("click", async () => {
  mostrarError("");
  const problema = validar();
  if (problema) {
    mostrarError(problema);
    return;
  }

  const diaSemana = estado.dias[diaActivo].dia_semana;
  const botonIniciar = document.getElementById("iniciar");
  botonIniciar.disabled = true;
  try {
    const rutina = rutinaId
      ? await apiFetch(`/rutinas/${rutinaId}`, { method: "PUT", body: armarCuerpo() })
      : await apiFetch("/rutinas", { method: "POST", body: armarCuerpo() });

    // La rutina queda guardada: se sigue trabajando sobre ella
    rutinaId = String(rutina.id);
    history.replaceState(null, "", `/rutina.html?id=${rutina.id}`);
    document.getElementById("titulo-pagina").textContent = "Editar rutina";
    botonEliminar.classList.remove("oculto");
    estado = desdeRespuesta(rutina);
    ordenarDias();
    diaActivo = estado.dias.findIndex((dia) => dia.dia_semana === diaSemana);
    render();

    const dia = rutina.dias.find((d) => d.dia_semana === diaSemana);
    const entrenamiento = await apiFetch("/entrenamientos", {
      method: "POST",
      body: { rutina_id: rutina.id, dia_id: dia.id },
    });
    window.location.href = `/entrenamiento.html?id=${entrenamiento.id}`;
  } catch (e) {
    mostrarError(e.message);
    botonIniciar.disabled = false;
  }
});

botonEliminar.addEventListener("click", async () => {
  if (!window.confirm("¿Eliminar esta rutina? Esta acción no se puede deshacer.")) return;
  try {
    await apiFetch(`/rutinas/${rutinaId}`, { method: "DELETE" });
    window.location.href = "/entrenar.html";
  } catch (e) {
    mostrarError(e.message);
  }
});

// ---------- Inicio ----------
(async () => {
  try {
    grupos = await obtenerGrupos();
    if (rutinaId) {
      const rutina = await apiFetch(`/rutinas/${rutinaId}`);
      estado = desdeRespuesta(rutina);
      // Rutina de un cliente: el trainer la modifica, pero no la entrena
      if (rutina.propietario_id !== obtenerUsuario().id) {
        document.getElementById("iniciar").classList.add("oculto");
      }
      document.getElementById("titulo-pagina").textContent = "Editar rutina";
      botonEliminar.classList.remove("oculto");
      ordenarDias();
      diaActivo = indiceDeHoy();
    }
    campoNombre.value = estado.nombre;
    campoDescripcion.value = estado.descripcion;
    render();
  } catch (e) {
    if (e.status === 404) {
      window.location.href = "/entrenar.html";
      return;
    }
    mostrarError(e.message);
  }
})();