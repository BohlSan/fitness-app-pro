// Utilidades de fechas para el frontend.
// Las fechas del servidor llegan como "YYYY-MM-DD" y se interpretan en hora local
// (new Date("YYYY-MM-DD") las tomaría como UTC y podría correr un día).

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];
const DIAS_LARGO = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function pad2(numero) {
  return String(numero).padStart(2, "0");
}

function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function nombreMes(indice) {
  return MESES[indice];
}

function aISO(fecha) {
  return `${fecha.getFullYear()}-${pad2(fecha.getMonth() + 1)}-${pad2(fecha.getDate())}`;
}

function desdeISO(texto) {
  const [anio, mes, dia] = texto.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function formatoFechaLarga(texto) {
  const fecha = desdeISO(texto);
  return `${DIAS_LARGO[fecha.getDay()]} ${fecha.getDate()} de ${MESES[fecha.getMonth()]}`;
}

function formatoFechaCorta(texto) {
  const fecha = desdeISO(texto);
  return `${pad2(fecha.getDate())}/${pad2(fecha.getMonth() + 1)}/${fecha.getFullYear()}`;
}

function formatoDuracionCorta(totalSegundos) {
  if (totalSegundos === null || totalSegundos === undefined) return "—";
  const horas = Math.floor(totalSegundos / 3600);
  const minutos = Math.floor((totalSegundos % 3600) / 60);
  if (horas > 0) return `${horas} h ${minutos} min`;
  return minutos === 0 ? "<1 min" : `${minutos} min`;
}