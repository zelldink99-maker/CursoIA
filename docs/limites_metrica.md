# Límites de la métrica de evaluación

## Qué mide

Precisión, cobertura y F1 comparan las palabras de una respuesta generada con
las de su referencia, contando repeticiones; no determinan por sí solas si la
respuesta es verdadera, completa o equivalente en significado.

## Modos de falla conocidos

Estos son riesgos que motivan la revisión; los ejemplos siguientes son
ilustrativos y no se presentan como resultados revisados de este proyecto:

- **Sinónimos y paráfrasis:** pueden puntuar bajo aunque conserven el sentido;
  «el auto es veloz» y «el vehículo es rápido» comparten pocas palabras.
- **Datos equivocados:** una fecha o cifra incorrecta puede puntuar alto si
  coincide el resto de la frase; cambiar 1991 por 1989 conserva casi todos los
  tokens de «Python fue creado en 1991 por Guido van Rossum».
- **Negaciones omitidas:** retirar «no» puede invertir una afirmación y apenas
  cambiar la coincidencia léxica.
- **Omisiones importantes:** omitir «3 a 1» de «El equipo ganó el partido por
  3 goles a 1, en su estadio local» conserva las demás palabras, pero pierde el
  resultado principal.

Después de completar la rúbrica, añade aquí los patrones que sí aparecieron en
esta muestra. Cada hallazgo debe señalar un caso real de `revision_manual.json`
con esta forma:

- Consulta: PENDIENTE | F1: 0.00 | Hallazgo: PENDIENTE

## Muestra revisada

La revisión del proyecto todavía no se ha ejecutado. Completa estos datos
después de revisar manualmente el JSON; no los presentes como hallazgos antes
de hacerlo:

- Respuestas generadas: PENDIENTE
- Casos revisados: PENDIENTE
- Fecha de revisión: PENDIENTE
- Criterio de selección: PENDIENTE (incluye los cinco F1 más bajos y los cinco más altos).

En cada caso, califica corrección factual y completitud con `sí`, `no` o
`parcialmente`, contradicción con `sí` o `no`, y explica las decisiones en el
campo `nota`.

## Recomendación de uso

En este pipeline, usa F1 para comparar respuestas en volumen y priorizar
lecturas, no como prueba de corrección. Revisa manualmente fechas, cifras,
nombres, negaciones, omisiones importantes y cualquier F1 inesperadamente alto
o bajo. Después de la muestra, ajusta esta recomendación a los errores que
realmente hayas encontrado: PENDIENTE.
