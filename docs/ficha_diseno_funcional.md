# Ficha de Diseno Funcional

## 1. Problema de negocio

El equipo encargado de revisar las ventas recibe archivos con datos que ya pasaron por un proceso ETL, pero debe revisar manualmente si quedaron registros incompletos o duplicados antes de preparar sus resultados. Como estimacion inicial, se revisan dos archivos por semana y cada revision toma cerca de una hora, entre localizar problemas y calcular los indicadores. Esto retrasa la entrega de informacion y hace que los resultados dependan de quien realice la revision. Se espera que una persona pueda identificar los principales problemas de calidad y obtener un resumen de ventas en menos de dos minutos por consulta.

Las cantidades anteriores son supuestos de diseno, no datos medidos de una empresa.

## 2. Requerimientos y alcance (MVP)

### Requerimientos funcionales
- RF-01: El usuario envia una pregunta de texto al endpoint de consulta y recibe la respuesta en formato JSON.
- RF-02: El sistema genera un reporte de calidad post-ETL que incluye las filas procesadas, las filas rechazadas y los conteos de valores faltantes, duplicados y datos invalidos.
- RF-03: El sistema genera un reporte de resultados de ventas con los indicadores disponibles para el periodo solicitado, como ventas totales y cantidad de pedidos.
- RF-04: El sistema determina, a partir de la pregunta, cual de los dos tipos de reporte debe generar.
- RF-05: Cada reporte indica el periodo analizado y los datos o metricas usados para elaborarlo.
- RF-06: El sistema permite exportar un resumen de resultados en formato CSV.
- RF-07: El sistema compara los resultados con un periodo anterior.
- RF-08: El sistema permite filtrar los resultados por una categoria adicional.
- RF-09: El sistema se conecta con el sistema real de ventas de una empresa.
- RF-10: El sistema ofrece una interfaz web con inicio de sesion e historial.
- RF-11: El sistema envia reportes automaticamente por correo o mensajeria.
- RF-12: El sistema modifica o corrige automaticamente los datos de origen.

### Requerimientos no funcionales
- RNF-01: En las 10 consultas de la suite de aceptacion, al menos 9 terminan en menos de 30 segundos, medidos de extremo a extremo desde el cliente.
- RNF-02: En las 10 consultas del conjunto de prueba, los indicadores numericos de los reportes coinciden con los valores calculados directamente desde el archivo o la tabla procesada.
- RNF-03: En los registros de las 10 consultas de prueba no aparecen los campos de pregunta, respuesta ni contenido de filas; solo se registran identificador de traza, estado, duracion y conteos agregados.
- RNF-04: El servicio se ejecuta desde cero en un contenedor, siguiendo el README, en menos de 10 minutos.

### Alcance
Imprescindible: RF-01, RF-02, RF-03, RF-04, RF-05
Deseable: RF-06, RF-07, RF-08
Fuera de alcance: RF-09 (requiere conexion con el sistema real de ventas de una empresa), RF-10 (exige una interfaz web con inicio de sesion e historial que no es necesaria para el flujo principal), RF-11 (requiere credenciales e integracion con servicios externos de correo o mensajeria), RF-12 (modificaria datos de origen sin aprobacion y supera el objetivo de revision y reporte)

## 3. Arquitectura de la solucion

Diagrama: docs/diagrama_arquitectura.png

Modelo: modelo de lenguaje mediante API, con la clave guardada en variables de entorno y no incluida en el repositorio.
Vector store: Chroma persistido para guardar el diccionario de datos y las definiciones de los indicadores.
Orquestacion: LangGraph coordina la identificacion del tipo de pregunta, la consulta de datos procesados y la generacion del reporte correspondiente.
Exposicion: FastAPI con un endpoint de consulta que recibe preguntas y devuelve respuestas en JSON.
Empaquetado: imagen Docker que ejecuta el servicio y recibe como entrada los datos procesados y el indice persistido.

El flujo comienza con un archivo CSV simulado. El proceso ETL conserva los datos procesados y las filas rechazadas con sus motivos. La persona envia una pregunta al servicio FastAPI. LangGraph selecciona el reporte, consulta las metricas o los conteos necesarios y usa las definiciones almacenadas en Chroma. Las funciones controladas producen los indicadores para evitar que el modelo invente valores; la respuesta vuelve al usuario como JSON.

## 4. Criterios de aceptacion
- CA-01 (RF-01): Al enviar `{"pregunta":"ventas de noviembre de 2026"}` a `POST /consultar`, el servicio responde HTTP 200 con `Content-Type: application/json` y las claves `respuesta` y `fuentes`.
- CA-02 (RF-02): Para `data/ventas_prueba.csv`, el reporte de calidad indica 2 filas procesadas, 2 rechazadas, 1 duplicado y 1 valor faltante.
- CA-03 (RF-03): Para `data/ventas_prueba.csv`, la consulta de noviembre de 2026 devuelve ventas totales 300 y 2 pedidos.
- CA-04 (RF-04): Ante "¿Qué problemas de calidad tiene el archivo?", el campo `tipo_reporte` de `respuesta` es `calidad`; ante "¿Cuánto se vendió en noviembre de 2026?", `tipo_reporte` es `ventas`.
- CA-05 (RF-05): La consulta de ventas de noviembre de 2026 sobre `data/ventas_prueba.csv` devuelve el periodo `2026-11` y las metricas calculadas a partir de las dos filas validas de ese periodo.
- CA-06 (RF-03): Al consultar noviembre de 2027, periodo sin filas en `data/ventas_prueba.csv`, la respuesta indica que no hay datos y no presenta ventas totales ni cantidad de pedidos como valores numericos.
- CA-07 (RNF-01): En las 10 consultas de la suite de aceptacion, al menos 9 finalizan en menos de 30 segundos de extremo a extremo.
- CA-08 (RNF-02): Para las 10 consultas del conjunto de prueba, todos los indicadores numericos coinciden exactamente con el calculo independiente sobre las filas procesadas.
- CA-09 (RNF-03): Despues de las 10 consultas de prueba, ningun registro contiene los campos de pregunta, respuesta o contenido de filas; cada registro conserva `trace_id`, estado, duracion y conteos agregados.
- CA-10 (RNF-04): En un entorno limpio con Docker instalado, siguiendo unicamente el README, el contenedor queda disponible y responde a la consulta de CA-01 en 10 minutos o menos.
- CA-11 (RF-05): El reporte de calidad de `data/ventas_prueba.csv` indica el periodo `2026-11` y el nombre del archivo analizado.

## 5. Plan de construccion por hitos
Horas disponibles: 30 h
Margen de imprevistos: 6 h
- H1 (2.5 h): Preparar el archivo de prueba y el proceso ETL con conteos reproducibles de calidad. Cubre: RF-02, RF-05. Se comprueba con: CA-02, CA-08, CA-11.
- H2 (3 h): Exponer el endpoint de consulta y una respuesta JSON estable. Cubre: RF-01. Se comprueba con: CA-01.
- H3 (4 h): Calcular ventas por periodo y responder correctamente cuando el periodo no tiene filas. Cubre: RF-03, RF-05. Se comprueba con: CA-03, CA-05, CA-06.
- H4 (3 h): Enrutar la pregunta al reporte de calidad o al de ventas. Cubre: RF-04. Se comprueba con: CA-04.
- H5 (1.5 h): Empaquetar el servicio y comprobar su arranque con Docker. Cubre: RNF-04. Se comprueba con: CA-10.
- H6 (9 h): Ejecutar pruebas de latencia, exactitud y privacidad; completar documentacion y ensayo de defensa. Cubre: RNF-01, RNF-02, RNF-03. Se comprueba con: CA-07, CA-08, CA-09.
