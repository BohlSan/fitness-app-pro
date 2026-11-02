// Pantalla de configuración.
// Requiere: api.js, fechas-ui.js y entrenador-ui.js

requerirSesion();

const sesion = obtenerUsuario();
let cuentaActual = null;
let perfilActual = null;

function campo(id) {
  return document.getElementById(id);
}

function valor(id) {
  return campo(id).value.trim();
}

function mensaje(id, texto, correcto = false) {
  const nodo = campo(id);
  nodo.textContent = texto;
  nodo.classList.toggle("mensaje-ok", correcto);
}

// ---------- Cuenta ----------
async function cargarCuenta() {
  cuentaActual = await apiFetch("/auth/me");
  campo("cuenta-nombre").value = cuentaActual.nombre;
  campo("cuenta-email").value = cuentaActual.email;
}

campo("cuenta-email").addEventListener("input", () => {
  const cambio = valor("cuenta-email").toLowerCase() !== cuentaActual.email;
  campo("grupo-password-email").classList.toggle("oculto", !cambio);
});

campo("form-cuenta").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensaje("msg-cuenta", "");

  const cuerpo = {};
  if (valor("cuenta-nombre") !== cuentaActual.nombre) cuerpo.nombre = valor("cuenta-nombre");
  if (valor("cuenta-email").toLowerCase() !== cuentaActual.email) {
    cuerpo.email = valor("cuenta-email");
    cuerpo.password_actual = campo("cuenta-password").value;
    if (!cuerpo.password_actual) {
      mensaje("msg-cuenta", "Ingresá tu contraseña actual para cambiar el email.");
      return;
    }
  }
  if (!Object.keys(cuerpo).length) {
    mensaje("msg-cuenta", "No hay cambios para guardar.");
    return;
  }

  try {
    cuentaActual = await apiFetch("/cuenta/datos", { method: "PATCH", body: cuerpo });
    localStorage.setItem(USER_KEY, JSON.stringify(cuentaActual));
    campo("cuenta-password").value = "";
    campo("grupo-password-email").classList.add("oculto");
    mensaje("msg-cuenta", "Cuenta actualizada ✓", true);
  } catch (e) {
    mensaje("msg-cuenta", e.message);
  }
});

// ---------- Contraseña ----------
campo("form-password").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensaje("msg-password", "");

  const actual = campo("pass-actual").value;
  const nueva = campo("pass-nueva").value;
  if (!actual) return mensaje("msg-password", "Ingresá tu contraseña actual.");
  if (nueva.length < 8) return mensaje("msg-password", "La contraseña nueva debe tener al menos 8 caracteres.");
  if (nueva !== campo("pass-repetida").value) return mensaje("msg-password", "Las contraseñas nuevas no coinciden.");

  try {
    await apiFetch("/cuenta/password", {
      method: "PUT",
      body: { password_actual: actual, password_nueva: nueva },
    });
    ["pass-actual", "pass-nueva", "pass-repetida"].forEach((id) => { campo(id).value = ""; });
    mensaje("msg-password", "Contraseña actualizada ✓", true);
  } catch (e) {
    mensaje("msg-password", e.message);
  }
});

// ---------- Datos y objetivos ----------
function pintarPerfil() {
  campo("perfil-nacimiento").value = perfilActual.fecha_nacimiento;
  campo("perfil-genero").value = perfilActual.genero;
  campo("perfil-altura").value = perfilActual.altura_cm;
  campo("perfil-peso").value = perfilActual.peso_actual_kg;
  campo("perfil-objetivo").value = perfilActual.objetivo;
  campo("perfil-dias").value = perfilActual.dias_entrenamiento_semana;
  campo("perfil-unidad").value = perfilActual.unidad_hidratacion;
  campo("perfil-meta").value = perfilActual.meta_hidratacion_ml;
  campo("perfil-ml-vaso").value = perfilActual.ml_vaso;
  campo("perfil-ml-botella").value = perfilActual.ml_botella ?? "";
  alternarBotella();
}

function alternarBotella() {
  campo("grupo-ml-botella").classList.toggle("oculto", campo("perfil-unidad").value !== "BOTELLAS");
}
campo("perfil-unidad").addEventListener("change", alternarBotella);

function leerPerfil() {
  const unidad = valor("perfil-unidad");
  return {
    fecha_nacimiento: valor("perfil-nacimiento"),
    genero: valor("perfil-genero"),
    altura_cm: Number(valor("perfil-altura")),
    peso_actual_kg: Number(valor("perfil-peso")),
    objetivo: valor("perfil-objetivo"),
    dias_entrenamiento_semana: Number(valor("perfil-dias")),
    unidad_hidratacion: unidad,
    ml_vaso: Number(valor("perfil-ml-vaso")),
    ml_botella: unidad === "BOTELLAS" ? Number(valor("perfil-ml-botella")) : null,
    meta_hidratacion_ml: Number(valor("perfil-meta")),
  };
}

function validarPerfil(datos) {
  if (!datos.fecha_nacimiento) return "Ingresá tu fecha de nacimiento.";
  if (!(datos.altura_cm >= 100 && datos.altura_cm <= 250)) return "La altura tiene que estar entre 100 y 250 cm.";
  if (!(datos.peso_actual_kg > 20 && datos.peso_actual_kg <= 400)) return "Ingresá un peso válido en kg (más de 20 y hasta 400).";
  if (!(Number.isInteger(datos.dias_entrenamiento_semana) && datos.dias_entrenamiento_semana >= 1 && datos.dias_entrenamiento_semana <= 7)) {
    return "Los días de entrenamiento por semana van de 1 a 7.";
  }
  if (!(datos.ml_vaso >= 50 && datos.ml_vaso <= 1000)) return "El vaso tiene que ser de entre 50 y 1000 ml.";
  if (!(datos.meta_hidratacion_ml >= 500 && datos.meta_hidratacion_ml <= 10000)) return "La meta diaria tiene que ser de entre 500 y 10000 ml.";
  if (datos.unidad_hidratacion === "BOTELLAS" && !(datos.ml_botella >= 100 && datos.ml_botella <= 5000)) {
    return "La botella tiene que ser de entre 100 y 5000 ml.";
  }
  return "";
}

campo("form-perfil").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensaje("msg-perfil", "");

  const nuevo = leerPerfil();
  const problema = validarPerfil(nuevo);
  if (problema) return mensaje("msg-perfil", problema);

  // Solo se envía lo que cambió: así, editar la altura no registra un peso del día
  const cambios = {};
  Object.entries(nuevo).forEach(([clave, dato]) => {
    if (clave === "ml_botella") {
      if (dato !== null && dato !== perfilActual.ml_botella) cambios[clave] = dato;
    } else if (dato !== perfilActual[clave]) {
      cambios[clave] = dato;
    }
  });
  if (!Object.keys(cambios).length) return mensaje("msg-perfil", "No hay cambios para guardar.");

  try {
    perfilActual = await apiFetch("/perfil", { method: "PATCH", body: cambios });
    pintarPerfil();
    mensaje("msg-perfil", "Datos actualizados ✓", true);
  } catch (e) {
    mensaje("msg-perfil", e.message);
  }
});

async function cargarPerfil() {
  try {
    perfilActual = await apiFetch("/perfil");
  } catch (e) {
    if (e.status === 404) window.location.href = "/formulario.html"; // perfil sin completar
    return;
  }
  campo("seccion-perfil").classList.remove("oculto");
  pintarPerfil();
}

// ---------- Sesión y eliminación de cuenta ----------
campo("cerrar-sesion").addEventListener("click", cerrarSesion);

campo("confirmacion").addEventListener("input", () => {
  campo("eliminar-cuenta").disabled = campo("confirmacion").value !== "ELIMINAR";
});

campo("eliminar-cuenta").addEventListener("click", async () => {
  mensaje("msg-eliminar", "");
  if (campo("confirmacion").value !== "ELIMINAR") return;
  if (!window.confirm("¿Eliminar tu cuenta definitivamente? No se puede deshacer.")) return;

  campo("eliminar-cuenta").disabled = true;
  try {
    await apiFetch("/cuenta/eliminar", { method: "POST", body: { confirmacion: "ELIMINAR" } });
    cerrarSesion(); // la cuenta ya no existe: se limpia la sesión y se vuelve al inicio
  } catch (e) {
    mensaje("msg-eliminar", e.message);
    campo("eliminar-cuenta").disabled = false;
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
  await seguro(cargarCuenta);

  if (sesion && sesion.rol === "USUARIO") {
    await seguro(cargarPerfil);
    crearTarjetaEntrenador(campo("tarjeta-entrenador")).then(() => {
      // La tarjeta se oculta sola si no corresponde; si quedó visible, se muestra
    });
    campo("tarjeta-entrenador").classList.remove("oculto");
  } else {
    campo("seccion-trainer").classList.remove("oculto");
  }
})();