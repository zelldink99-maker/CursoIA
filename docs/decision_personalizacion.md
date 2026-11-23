# Decisión de personalización para el servicio RAG del proyecto

## 1. El problema

El servicio responde preguntas sobre el código y la documentación de este
repositorio. Ese contenido cambia al evolucionar el proyecto y cada respuesta
debe poder rastrearse hasta una fuente concreta. El corpus implementado tiene
cinco documentos base y la evaluación de recuperación contiene diez preguntas
etiquetadas.

## 2. Comparación de estrategias

Se aplicaron las cinco preguntas del método
`recomendar_estrategia` en
[`src/GATE_2/decision_personalizacion.py`](../src/GATE_2/decision_personalizacion.py):

| Criterio | Evidencia para este proyecto | Respuesta |
| --- | --- | --- |
| La información cambia seguido | El índice representa fuentes del repositorio y debe actualizarse cuando cambian esos archivos. | Sí |
| El problema principal es formato o tono | La necesidad principal es recuperar hechos actuales con su fuente, no cambiar el estilo del modelo. | No |
| Hay un dataset grande, etiquetado y de calidad | Hay diez casos de evaluación de recuperación, no cientos de pares de entrenamiento revisados. | No |
| Hay que iterar rápido o limitar el costo de entrenamiento | Los cambios al corpus pueden reindexarse sin entrenar un modelo. | Sí |
| Se necesitan múltiples variantes | El servicio tiene una sola política de respuesta y una sola base documental del proyecto. | No |

| Técnica | Puntaje |
| --- | ---: |
| RAG | 5 |
| Fine-tuning completo | 0 |
| PEFT | 1 |

## 3. Técnica elegida y por qué

Elijo **RAG**. El repositorio ya ofrece un índice Chroma persistido, una
actualización incremental por IDs estables, recuperación con filtro de
inyección y validación de citas. Las fuentes pueden cambiar sin volver a
entrenar el modelo, y las citas permiten verificar cada respuesta. Fine-tuning
completo o PEFT no resolverían por sí solos la necesidad de consultar
información actualizada ni reemplazarían el índice; además, el proyecto no
tiene un dataset de entrenamiento suficientemente grande y revisado.

La decisión se revisaría si el problema observado cambiara a un formato
inconsistente demostrado en una muestra de respuestas y existieran ejemplos
etiquetados de calidad. La puntuación orienta la decisión, no reemplaza esa
revisión con evidencia.

## 4. Qué necesita la opción elegida

- Mantener metadatos `source` e IDs estables para cada chunk.
- Reindexar el corpus cuando cambien las fuentes y comprobar que el índice
  persistido quedó actualizado.
- Revisar precisión@k, recall@k y F1 sobre las preguntas etiquetadas antes de
  modificar el tamaño de chunk o el valor de `k`.
- Medir latencia, tokens y costo estimado por consulta; los precios son una
  estimación local, no una factura.

Comprobaciones relacionadas:

```console
python -m pytest tests/test_indexar_corpus.py tests/test_evaluacion_recuperacion.py -q
python -m pytest tests/test_decision_personalizacion.py -q
```
