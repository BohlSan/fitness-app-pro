// Componentes reutilizables del catálogo de ejercicios.
// Requiere haber cargado antes /js/api.js

let _gruposCache = null;

async function obtenerGrupos() {
  if (!_gruposCache) _gruposCache = await apiFetch("/ejercicios/grupos");
  return _gruposCache;
}

function etiquetaGrupo(grupos, valor) {
  const grupo = grupos.find((g) => g.valor === valor);
  return grupo ? grupo.etiqueta : valor;
}

function crearTag(texto, clase) {
  const tag = document.createElement("span");
  tag.className = "tag " + clase;
  tag.textContent = texto;
  return tag;
}

/**
 * Dibuja un buscador (texto + grupo muscular + "solo míos") con su lista.
 * Opciones:
 *   onSeleccionar(ejercicio): si se pasa, cada ejercicio es clickeable (modo selector)
 *   renderAcciones(ejercicio): devuelve un elemento con botones extra, o null (modo gestión)
 * Devuelve { recargar() }.
 */
async function crearBuscadorEjercicios(contenedor, { onSeleccionar = null, renderAcciones = null } = {}) {
  const grupos = await obtenerGrupos();
  const usuario = obtenerUsuario();
  let numeroPeticion = 0;
  let temporizador = null;

  const filtros = document.createElement("div");
  filtros.className = "buscador-filtros";

  const campoBusqueda = document.createElement("input");
  campoBusqueda.type = "search";
  campoBusqueda.placeholder = "Buscar por nombre…";
  campoBusqueda.setAttribute("aria-label", "Buscar ejercicio");

  const selectGrupo = document.createElement("select");
  selectGrupo.setAttribute("aria-label", "Filtrar por grupo muscular");
  const opcionTodos = document.createElement("option");
  opcionTodos.value = "";
  opcionTodos.textContent = "Todos los grupos";
  selectGrupo.appendChild(opcionTodos);
  grupos.forEach((grupo) => {
    const opcion = document.createElement("option");
    opcion.value = grupo.valor;
    opcion.textContent = grupo.etiqueta;
    selectGrupo.appendChild(opcion);
  });

  const etiquetaPropios = document.createElement("label");
  etiquetaPropios.className = "solo-propios";
  const checkPropios = document.createElement("input");
  checkPropios.type = "checkbox";
  etiquetaPropios.append(checkPropios, document.createTextNode(" Solo mis ejercicios"));

  filtros.append(campoBusqueda, selectGrupo, etiquetaPropios);

  const estado = document.createElement("p");
  estado.className = "estado-lista";
  estado.setAttribute("role", "status");

  const lista = document.createElement("ul");
  lista.className = "lista-ejercicios";

  contenedor.replaceChildren(filtros, estado, lista);

  function crearItem(ejercicio) {
    const esPropio = ejercicio.creador_id === usuario.id;
    const item = document.createElement("li");
    item.className = "ejercicio-item";

    const info = document.createElement("div");
    info.className = "ejercicio-info";
    const nombre = document.createElement("strong");
    nombre.textContent = ejercicio.nombre;

    const tags = document.createElement("div");
    tags.className = "ejercicio-tags";
    tags.append(crearTag(etiquetaGrupo(grupos, ejercicio.grupo_principal), "principal"));
    if (ejercicio.grupo_secundario) {
      tags.append(crearTag(etiquetaGrupo(grupos, ejercicio.grupo_secundario), "secundario"));
    }
    tags.append(crearTag(esPropio ? "Propio" : "Catálogo", esPropio ? "propio" : "catalogo"));
    tags.append(crearTag(ejercicio.tipo_medicion === "TIEMPO" ? "Por tiempo" : "Por repeticiones", "secundario"));
    if (ejercicio.usa_peso_corporal) tags.append(crearTag("Peso corporal", "secundario"));

    info.append(nombre, tags);
    if (ejercicio.descripcion) {
      const descripcion = document.createElement("p");
      descripcion.textContent = ejercicio.descripcion;
      info.append(descripcion);
    }
    item.append(info);

    if (renderAcciones) {
      const acciones = renderAcciones(ejercicio);
      if (acciones) item.append(acciones);
    }

    if (onSeleccionar) {
      item.classList.add("seleccionable");
      item.tabIndex = 0;
      item.addEventListener("click", (evento) => {
        if (evento.target.closest(".ejercicio-acciones")) return;
        onSeleccionar(ejercicio);
      });
      item.addEventListener("keydown", (evento) => {
        if (evento.key === "Enter" || evento.key === " ") {
          evento.preventDefault();
          onSeleccionar(ejercicio);
        }
      });
    }
    return item;
  }

  function pintar(ejercicios) {
    lista.replaceChildren(...ejercicios.map(crearItem));
    estado.textContent = ejercicios.length
      ? `${ejercicios.length} ejercicio${ejercicios.length === 1 ? "" : "s"}`
      : "No encontramos ejercicios con esos filtros.";
  }

  async function cargar() {
    const params = new URLSearchParams();
    if (campoBusqueda.value.trim()) params.set("q", campoBusqueda.value.trim());
    if (selectGrupo.value) params.set("grupo", selectGrupo.value);
    if (checkPropios.checked) params.set("solo_propios", "true");

    const miPeticion = ++numeroPeticion;
    estado.textContent = "Cargando…";
    try {
      const ejercicios = await apiFetch(`/ejercicios?${params.toString()}`);
      // Si ya hay una búsqueda más nueva, se descarta esta respuesta
      if (miPeticion === numeroPeticion) pintar(ejercicios);
    } catch (e) {
      if (miPeticion === numeroPeticion) estado.textContent = e.message;
    }
  }

  campoBusqueda.addEventListener("input", () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(cargar, 250);
  });
  selectGrupo.addEventListener("change", cargar);
  checkPropios.addEventListener("change", cargar);

  await cargar();
  return { recargar: cargar };
}

/**
 * Abre una ventana para elegir un ejercicio del catálogo.
 * onSeleccionar(ejercicio) se llama con el ejercicio elegido.
 */
function abrirSelectorEjercicios(onSeleccionar) {
  const dialogo = document.createElement("dialog");
  dialogo.className = "dialogo";

  const cabecera = document.createElement("div");
  cabecera.className = "dialogo-cabecera";
  const titulo = document.createElement("h2");
  titulo.textContent = "Elegí un ejercicio";
  const cerrar = document.createElement("button");
  cerrar.type = "button";
  cerrar.className = "cerrar";
  cerrar.setAttribute("aria-label", "Cerrar");
  cerrar.textContent = "×";
  cerrar.addEventListener("click", () => dialogo.close());
  cabecera.append(titulo, cerrar);

  const cuerpo = document.createElement("div");
  cuerpo.className = "dialogo-cuerpo";

  dialogo.append(cabecera, cuerpo);
  document.body.appendChild(dialogo);
  dialogo.addEventListener("close", () => dialogo.remove());
  dialogo.addEventListener("click", (evento) => {
    if (evento.target === dialogo) dialogo.close();
  });

  crearBuscadorEjercicios(cuerpo, {
    onSeleccionar: (ejercicio) => {
      dialogo.close();
      onSeleccionar(ejercicio);
    },
  });
  dialogo.showModal();
}