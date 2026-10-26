const DIAS_SEMANA = [
  { valor: "LUNES", etiqueta: "Lunes" },
  { valor: "MARTES", etiqueta: "Martes" },
  { valor: "MIERCOLES", etiqueta: "Miércoles" },
  { valor: "JUEVES", etiqueta: "Jueves" },
  { valor: "VIERNES", etiqueta: "Viernes" },
  { valor: "SABADO", etiqueta: "Sábado" },
  { valor: "DOMINGO", etiqueta: "Domingo" },
];

function etiquetaDia(valor) {
  const dia = DIAS_SEMANA.find((d) => d.valor === valor);
  return dia ? dia.etiqueta : valor;
}

function etiquetaDiaCorta(valor) {
  return etiquetaDia(valor).slice(0, 3);
}

function ordenDia(valor) {
  return DIAS_SEMANA.findIndex((d) => d.valor === valor);
}