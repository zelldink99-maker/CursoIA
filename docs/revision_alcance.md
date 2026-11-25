# Revision del alcance

Revisor: Igor Inostroza (autorrevision)
Fecha: 2026-11-25

- Hallazgo 1: CA-09 no comprobaba que cada registro conservara los conteos agregados requeridos por RNF-03.
  Decisión: aceptado. Cambio: CA-09 ahora exige `trace_id`, estado, duracion y conteos agregados.

- Hallazgo 2: RF-05 pide periodo y datos usados para ambos reportes, pero solo habia un criterio para el periodo del reporte de ventas.
  Decisión: aceptado. Cambio: se agrego CA-11 para el periodo y archivo de origen del reporte de calidad, y H1 ahora lo cubre.

La autorrevision registra los dos hallazgos y los cambios aplicados a la ficha.
