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
- RNF-01: El endpoint responde en menos de 10 segundos en al menos 9 de cada 10 consultas del conjunto de prueba.
- RNF-02: En las 10 consultas del conjunto de prueba, los indicadores numericos de los reportes coinciden con los valores calculados directamente desde el archivo o la tabla procesada.
- RNF-03: En los registros de las 10 consultas de prueba no aparece el texto completo de las preguntas ni el contenido completo de los datos; solo se registran campos tecnicos necesarios, como identificador de traza, estado y duracion.
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
Exposicion: servicio FastAPI con un endpoint de consulta que recibe preguntas y devuelve respuestas en JSON.
Empaquetado: imagen Docker que ejecuta el servicio y recibe como entrada los datos procesados y el indice persistido.

El flujo comienza con un archivo CSV simulado. El proceso ETL conserva los datos procesados y las filas rechazadas con sus motivos. La persona envia una pregunta al servicio FastAPI. LangGraph selecciona el reporte, consulta las metricas o los conteos necesarios y usa las definiciones almacenadas en Chroma. Las funciones controladas producen los indicadores para evitar que el modelo invente valores; la respuesta vuelve al usuario como JSON.

## 4. Criterios de aceptacion
[PENDIENTE: se completa en el Bloque 34]

## 5. Plan de construccion por hitos
[PENDIENTE: se completa en el Bloque 34]
