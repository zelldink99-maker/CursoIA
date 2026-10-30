# Límites de la métrica de evaluación

## Qué mide

Precisión, cobertura y F1 miden coincidencias de palabras entre la respuesta y
la referencia, contando repeticiones. No evalúan por sí solas el significado ni
la veracidad de una respuesta.

## Modos de falla conocidos

- **Sinónimos y paráfrasis correctas:** pueden puntuar bajo aunque conserven el
  significado; por ejemplo, «el auto es veloz» y «el vehículo es rápido».
- **Datos incorrectos:** una fecha o cifra equivocada puede puntuar alto si el
  resto de la respuesta coincide con la referencia. Por ejemplo, responder
  «Python fue creado en 1989 por Guido van Rossum, pensado como sucesor de
  ABC» frente a la referencia «Python fue creado en 1991 por Guido van
  Rossum» obtiene F1 aproximado 0.667, aunque el año sea incorrecto.
- **Negaciones omitidas:** quitar o cambiar una negación puede invertir el
  significado y conservar casi todas las palabras coincidentes.
- **Omisiones importantes:** una respuesta puede tener precisión perfecta y
  aun así dejar fuera un dato central. Por ejemplo, omitir el marcador «3 a 1»
  deja precisión 1.0, cobertura aproximada 0.643 y F1 aproximado 0.783 en el
  caso ilustrativo del Bloque 17.

## Muestra revisada

No se afirma aquí que los resultados actuales ya hayan sido revisados a mano.
Para preparar la revisión sobre los resultados reales, el comando documentado
en el README selecciona hasta cinco casos con F1 más bajo y cinco con F1 más
alto. Si hay menos de diez, reparte los casos disponibles entre ambos extremos
sin duplicarlos. Registra en este documento el tamaño real de la muestra, la
fecha y los patrones observados después de completar la revisión.

## Rúbrica manual

Para cada caso, completa `revision_cualitativa.json`:

- **Corrección factual:** `sí`, `no` o `parcialmente`; ¿coinciden los datos
  verificables con la referencia?
- **Completitud:** `sí`, `no` o `parcialmente`; ¿se cubre la información
  importante de la referencia?
- **Contradicción:** `sí` o `no`; ¿la respuesta afirma lo contrario de la
  referencia?
- **Justificación:** explica brevemente cada calificación; ante una duda, usa
  `parcialmente` en vez de forzar una respuesta.

## Recomendación de uso

Usa F1 para priorizar y comparar respuestas en volumen, no como prueba de
corrección; revisa siempre a mano respuestas con fechas, cifras, nombres
propios, negaciones o un F1 inesperadamente alto o bajo.
