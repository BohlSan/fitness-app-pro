// Piezas del módulo de entrenadores.
// Requiere: api.js y fechas-ui.js

const ETIQUETAS_CUOTA = {
  AL_DIA: "Al día ✅",
  PENDIENTE: "Pendiente ⏳",
  VENCIDA: "Vencida ⚠️",
};

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

/** Tarjeta de la persona que entrena: ver, pedir o terminar la relación con su entrenador. */
async function crearTarjetaEntrenador(contenedor) {
  let vinculo = null;
  let mensaje = "";

  async function ejecutar(accion) {
    mensaje = "";
    try {
      await accion();
      vinculo = await apiFetch("/vinculo");
    } catch (e) {
      mensaje = e.message;
    }
    pintar();
  }

  function pintar() {
    const hijos = [el("h3", { text: "🤝 Mi entrenador" })];

    if (!vinculo) {
      const campo = el("input", {
        type: "text", maxlength: 12, placeholder: "Código de tu entrenador", autocomplete: "off",
      });
      hijos.push(
        el("p", {
          class: "agua-detalle",
          text: "Si tenés un personal trainer, ingresá su código para que pueda acompañar tu progreso.",
        }),
        el(
          "div",
          { class: "agua-botones" },
          campo,
          el("button", {
            type: "button", class: "boton-chico", text: "Vincular",
            onclick: () =>
              ejecutar(() =>
                apiFetch("/vinculo", { method: "POST", body: { codigo: campo.value.trim().toUpperCase() } })
              ),
          })
        )
      );
    } else if (vinculo.estado === "PENDIENTE") {
      hijos.push(
        el("p", {
          class: "agua-texto",
          text: `Solicitud enviada a ${vinculo.trainer.nombre}. Falta que la acepte.`,
        }),
        el(
          "div",
          { class: "agua-botones" },
          el("button", {
            type: "button", class: "boton-chico", text: "Cancelar solicitud",
            onclick: () => ejecutar(() => apiFetch("/vinculo", { method: "DELETE" })),
          })
        )
      );
    } else {
      hijos.push(
        el("p", {
          class: "agua-texto",
          text: `${vinculo.trainer.nombre} es tu entrenador desde el ${formatoFechaCorta(vinculo.inicio)}.`,
        }),
        el("p", { class: "agua-detalle", text: `Cuota: ${ETIQUETAS_CUOTA[vinculo.estado_cuota]}` }),
        el(
          "div",
          { class: "agua-botones" },
          el("button", {
            type: "button", class: "boton-chico peligro", text: "Dejar de ser su cliente",
            onclick: () => {
              if (!window.confirm(`¿Dejar de ser cliente de ${vinculo.trainer.nombre}? Va a dejar de ver tu información.`)) return;
              ejecutar(() => apiFetch("/vinculo", { method: "DELETE" }));
            },
          })
        )
      );
    }

    hijos.push(el("p", { class: "mensaje-error", text: mensaje }));
    contenedor.replaceChildren(...hijos);
  }

  try {
    vinculo = await apiFetch("/vinculo");
  } catch (e) {
    contenedor.classList.add("oculto"); // solo para quien entrena como usuario
    return;
  }
  pintar();
}