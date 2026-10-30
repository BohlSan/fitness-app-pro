// Widgets de racha e hidratación (Home y Progreso).
// Requiere: api.js

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

function numeroLocal(valor, decimales = 0) {
  return Number(valor).toLocaleString("es-AR", { maximumFractionDigits: decimales });
}

function conUnidad(cantidad, singular, plural) {
  return `${cantidad} ${cantidad === 1 ? singular : plural}`;
}

// ---------- Racha ----------
async function pintarRacha(contenedor) {
  try {
    const racha = await apiFetch("/racha");

    let mensaje;
    if (racha.racha_actual === 0 && racha.racha_maxima === 0) {
      mensaje = "Entrená hoy y arrancá tu primera racha.";
    } else if (racha.en_riesgo) {
      const faltan = racha.faltan_esta_semana;
      mensaje = `⚠️ Tu racha está en riesgo: ${faltan === 1 ? "te falta" : "te faltan"} ${conUnidad(faltan, "día", "días")} para la meta de esta semana.`;
    } else if (racha.cumplida_esta_semana) {
      mensaje = "✅ ¡Meta semanal cumplida!";
    } else if (racha.racha_actual === 0) {
      mensaje = "Tu racha se reinició. ¡Empezá una nueva esta semana!";
    } else {
      const faltan = racha.faltan_esta_semana;
      mensaje = `${faltan === 1 ? "Te falta" : "Te faltan"} ${conUnidad(faltan, "día", "días")} para la meta de esta semana.`;
    }

    contenedor.replaceChildren(
      el(
        "div",
        { class: "racha-numero" },
        String(racha.racha_actual),
        el("small", { text: racha.racha_actual === 1 ? "día" : "días" })
      ),
      el(
        "div",
        { class: "racha-texto" },
        el("strong", { text: "🔥 Tu racha" }),
        el("p", {
          class: "rutina-meta",
          text: `Récord: ${racha.racha_maxima} · Esta semana: ${racha.dias_esta_semana}/${racha.meta_semanal} días`,
        }),
        el("p", { class: "racha-mensaje", text: mensaje })
      )
    );
    contenedor.classList.remove("oculto");
  } catch (e) {
    // El trainer o quien no completó el perfil no tiene racha
    contenedor.classList.add("oculto");
  }
}

// ---------- Hidratación ----------
function abrirConfiguracionHidratacion(dia, alGuardar) {
  const dialogo = el("dialog", { class: "dialogo" });

  const selectUnidad = el(
    "select",
    {},
    el("option", { value: "ML", text: "Mililitros" }),
    el("option", { value: "VASOS", text: "Vasos" }),
    el("option", { value: "BOTELLAS", text: "Botellas" })
  );
  selectUnidad.value = dia.unidad;

  const campoVaso = el("input", { type: "number", min: 50, max: 1000, step: 10, value: dia.ml_vaso });
  const campoBotella = el("input", {
    type: "number", min: 100, max: 5000, step: 50, placeholder: "750", value: dia.ml_botella ?? "",
  });
  const campoMeta = el("input", { type: "number", min: 500, max: 10000, step: 100, value: dia.meta_ml });
  const etiquetaBotella = el("label", {}, "Mililitros de tu botella", campoBotella);
  const error = el("p", { class: "mensaje-error", role: "alert" });

  const alternarBotella = () =>
    etiquetaBotella.classList.toggle("oculto", selectUnidad.value !== "BOTELLAS");
  selectUnidad.addEventListener("change", alternarBotella);
  alternarBotella();

  const formulario = el(
    "form",
    { class: "dialogo-cuerpo", novalidate: true },
    el("label", {}, "Registrar mi hidratación en", selectUnidad),
    el("label", {}, "Mililitros de un vaso", campoVaso),
    etiquetaBotella,
    el("label", {}, "Meta diaria (ml)", campoMeta),
    error,
    el("button", { type: "submit", class: "boton", text: "Guardar" })
  );

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    error.textContent = "";

    const vaso = Number(campoVaso.value);
    const botella = Number(campoBotella.value);
    const meta = Number(campoMeta.value);
    const usaBotella = selectUnidad.value === "BOTELLAS";

    if (!Number.isInteger(vaso) || vaso < 50 || vaso > 1000) {
      error.textContent = "El vaso tiene que ser de entre 50 y 1000 ml.";
      return;
    }
    if (usaBotella && (!Number.isInteger(botella) || botella < 100 || botella > 5000)) {
      error.textContent = "La botella tiene que ser de entre 100 y 5000 ml.";
      return;
    }
    if (!Number.isInteger(meta) || meta < 500 || meta > 10000) {
      error.textContent = "La meta diaria tiene que ser de entre 500 y 10000 ml.";
      return;
    }

    const cuerpo = { unidad_hidratacion: selectUnidad.value, ml_vaso: vaso, meta_hidratacion_ml: meta };
    if (usaBotella) cuerpo.ml_botella = botella;
    try {
      await apiFetch("/perfil", { method: "PATCH", body: cuerpo });
      dialogo.close();
      alGuardar();
    } catch (e) {
      error.textContent = e.message;
    }
  });

  dialogo.append(
    el(
      "div",
      { class: "dialogo-cabecera" },
      el("h2", { text: "Configurar hidratación" }),
      el("button", { type: "button", class: "cerrar", "aria-label": "Cerrar", text: "×", onclick: () => dialogo.close() })
    ),
    formulario
  );
  document.body.appendChild(dialogo);
  dialogo.addEventListener("close", () => dialogo.remove());
  dialogo.addEventListener("click", (evento) => {
    if (evento.target === dialogo) dialogo.close();
  });
  dialogo.showModal();
}

/**
 * Dibuja el progreso de hidratación del día con botones para sumar agua.
 * Opciones: alCambiar() se llama después de cada cambio (por ejemplo, para refrescar un gráfico).
 */
async function crearWidgetHidratacion(contenedor, { alCambiar = null } = {}) {
  let dia = null;
  let mensaje = "";

  function textoProgreso() {
    const total = dia.total_ml;
    const meta = dia.meta_ml;
    if (dia.unidad === "VASOS") {
      return `${numeroLocal(total / dia.ml_vaso, 1)} de ${numeroLocal(meta / dia.ml_vaso, 1)} vasos`;
    }
    if (dia.unidad === "BOTELLAS" && dia.ml_botella) {
      return `${numeroLocal(total / dia.ml_botella, 1)} de ${numeroLocal(meta / dia.ml_botella, 1)} botellas`;
    }
    return `${numeroLocal(total)} de ${numeroLocal(meta)} ml`;
  }

  async function ejecutar(accion) {
    mensaje = "";
    try {
      dia = await accion();
      if (alCambiar) alCambiar();
    } catch (e) {
      mensaje = e.message;
    }
    pintar();
  }

  const agregar = (ml) =>
    ejecutar(() => apiFetch("/hidratacion", { method: "POST", body: { cantidad_ml: ml } }));

  const deshacer = () =>
    ejecutar(() => {
      const ultimo = dia.registros[dia.registros.length - 1];
      return apiFetch(`/hidratacion/${ultimo.id}`, { method: "DELETE" });
    });

  function otraCantidad() {
    const texto = window.prompt("¿Cuántos ml tomaste?");
    if (texto === null) return;
    const ml = Number(texto);
    if (!Number.isInteger(ml) || ml < 10 || ml > 3000) {
      mensaje = "Ingresá una cantidad entera de ml entre 10 y 3000.";
      pintar();
      return;
    }
    agregar(ml);
  }

  function boton(texto, accion, deshabilitado = false) {
    return el("button", { type: "button", class: "boton-chico", text: texto, disabled: deshabilitado, onclick: accion });
  }

  function pintar() {
    const botones = [boton(`+ Vaso (${dia.ml_vaso} ml)`, () => agregar(dia.ml_vaso))];
    if (dia.ml_botella) {
      botones.push(boton(`+ Botella (${dia.ml_botella} ml)`, () => agregar(dia.ml_botella)));
    }
    botones.push(
      boton("+ Otra cantidad", otraCantidad),
      boton("Deshacer último", deshacer, dia.registros.length === 0),
      boton("⚙ Configurar", () =>
        abrirConfiguracionHidratacion(dia, () => ejecutar(() => apiFetch("/hidratacion"))))
    );

    const detalle = dia.entrenamiento_ml > 0
      ? `Incluye ${numeroLocal(dia.entrenamiento_ml)} ml que tomaste entrenando. Total: ${numeroLocal(dia.total_ml)} ml.`
      : `Total: ${numeroLocal(dia.total_ml)} ml. El agua que tomes entrenando se suma sola.`;

    contenedor.replaceChildren(
      el("h3", { text: "💧 Hidratación de hoy" }),
      el("div", { class: "barra-agua" }, el("div", { style: `width: ${Math.min(dia.porcentaje, 100)}%` })),
      el("p", { class: "agua-texto", text: `${textoProgreso()}${dia.cumplida ? " ✅" : ""}` }),
      el("p", { class: "agua-detalle", text: detalle }),
      el("div", { class: "agua-botones" }, ...botones),
      el("p", { class: "mensaje-error", text: mensaje })
    );
  }

  try {
    dia = await apiFetch("/hidratacion");
    pintar();
  } catch (e) {
    // El trainer o quien no completó el perfil no registra hidratación
    contenedor.classList.add("oculto");
  }
}