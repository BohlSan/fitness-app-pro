# Cobertura de requerimientos

## Requerimientos funcionales

| RF | Requerimiento | Estado | Dónde |
|---|---|---|---|
| RF-01 | Registro de usuario | Cumplido (sin Google) | `routers/auth.py`; el objetivo físico se pide en el formulario de perfil que sigue al registro |
| RF-02 | Inicio de sesión | Cumplido (sin Google) | `routers/auth.py` |
| RF-03 | Gestión del perfil | Cumplido | Formulario inicial, `routers/perfil.py` y pantalla de Configuración |
| RF-04 | Roles | Cumplido | `dependencies.py` (`require_role`) |
| RF-05 | Catálogo de ejercicios | Cumplido | `routers/ejercicios.py`, seed de 43 ejercicios |
| RF-06 | Creación de rutinas | Cumplido | `routers/rutinas.py`; el autor puede ser un usuario o un trainer |
| RF-07 | Días de una rutina | Cumplido | `dias_rutina` |
| RF-08 | Ejercicios dentro de una rutina | Cumplido | `rutina_ejercicios` (series, repeticiones, peso, descanso y orden) |
| RF-09 | Modificación de rutinas | Cumplido | `PUT /rutinas/{id}`, para el propietario y el trainer autorizado |
| RF-10 | Eliminación de rutinas | Cumplido | El historial sobrevive (`SET NULL` y título copiado) |
| RF-11 | Asignación por el trainer | Cumplido | `asignacion_service.py` |
| RF-12 | Administración de clientes | Cumplido | `routers/trainer.py`, con Observer |
| RF-13 | Relación entrenador-cliente | Cumplido | `vinculo_service.py` (estados, cuota y pagos) |
| RF-14 a RF-17 | Entrenamientos y series | Cumplido | `entrenamiento_service.py` |
| RF-18 | Dificultad, cansancio y ánimo | Cumplido | Cierre del entrenamiento (💪 y cáritas) |
| RF-19 y RF-20 | Historial y calendario | Cumplido | `historial_service.py`, `historial.html` |
| RF-21 y RF-22 | Peso corporal y evolución | Cumplido | `peso_service.py`, con tendencia |
| RF-23 | Volumen | Cumplido | `calculos.py`, estadísticas por ejercicio y período |
| RF-24 | Mejores marcas y PRs | Cumplido | `calculos.py`, récords al terminar cada sesión |
| RF-25 | Estadísticas | Cumplido | `estadisticas_service.py` |
| RF-26 | Racha | Cumplido | `calcular_racha` (regla definida en el README del equipo) |
| RF-27 | Hidratación | Cumplido | `hidratacion_service.py`, meta y equivalencias configurables |
| RF-28 | Consulta del progreso | Cumplido | `progreso.html` |
| RF-29 | Progreso de clientes | Cumplido | `/trainer/clientes/{id}/…` |
| RF-30 | Control de permisos | Cumplido | `cliente_autorizado` y propiedad de recursos |
| RF-31 | Persistencia | Cumplido | PostgreSQL; `tests/test_persistencia.py` |

## Requerimientos no funcionales

| RNF | Cómo se atiende |
|---|---|
| RNF-01 Seguridad de autenticación | Contraseñas con bcrypt. El registro con Google quedó fuera del MVP |
| RNF-02 Autorización | En el backend: `require_role`, `cliente_autorizado` y verificación de propiedad en los servicios |
| RNF-03 Integridad | Claves foráneas con política `ON DELETE`, restricciones únicas e índices parciales |
| RNF-04 Disponibilidad | Servicio sin estado (JWT) desplegado en Render, base en Supabase |
| RNF-05 Rendimiento | Carga anticipada de relaciones, índices, paginación y agregaciones en SQL |
| RNF-06 Escalabilidad | Patrón Factory, Observer, enumerados no nativos y servicios reutilizables |
| RNF-07 Mantenibilidad | Separación en routers, servicios, esquemas y modelos |
| RNF-08 Reutilización | Un ejercicio se referencia por id y no se duplica; componentes de frontend compartidos |
| RNF-09 Interfaz | Rutinas, entrenamiento actual, historial, progreso y perfil accesibles desde el inicio |
| RNF-10 Compatibilidad | HTML, CSS y JavaScript estándar para navegadores actuales. No se implementó PWA |
| RNF-11 Responsive | Diseño *mobile-first* con grillas adaptables |
| RNF-12 Validación | Pydantic en el servidor y validaciones en el formulario |
| RNF-13 Manejo de errores | Mensajes comprensibles; los errores internos no exponen detalles |
| RNF-14 Recuperación | Un `commit` por operación y `rollback` ante errores |
| RNF-15 Privacidad | 404 para recursos ajenos; el trainer solo ve lo necesario de sus clientes activos |
| RNF-16 Auditoría | Tabla `auditoria`: rutinas, relaciones, pagos y cuenta |
| RNF-17 Documentación | Este directorio `docs/` y el README |