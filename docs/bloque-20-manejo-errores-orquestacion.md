# Bloque 20: manejo de errores en el flujo orquestado

Esta guía documenta cómo mantener disponible el flujo de soporte cuando falla
una ruta o la clasificación, y cómo verificar esos comportamientos sin llamar
a Gemini.

## Implementación

El flujo del Bloque 19 está en `src/GATE_1/enrutamiento.py`. En el Bloque 20 se
agregaron dos niveles de protección:

1. **Fallback en cada ruta.** `construir_cadena_con_enrutamiento` envuelve las
   rutas de queja, sugerencia y pregunta con `with_fallbacks`. Si una ruta falla
   con una excepción, la respuesta alternativa es:

   > Gracias por tu mensaje. Un miembro de nuestro equipo te va a responder
   > pronto.

   `construir_cadena_queja_segura` también permite envolver una ruta de queja
   por separado, por ejemplo, en una prueba o al componer otra chain.
2. **Protección del flujo completo.** `procesar_mensaje_seguro(cadena,
   mensaje)` envuelve `cadena.invoke(...)` en un `try/except`. Si falla un paso
   que no está cubierto por un fallback —por ejemplo, el clasificador antes de
   que `RunnableBranch` seleccione una ruta— registra el traceback mediante
   `logger.exception` y devuelve:

   > No pudimos procesar tu mensaje en este momento. Intenta de nuevo más tarde.

Las técnicas son complementarias: el fallback ofrece continuidad cuando falla
una ruta; el `try/except` final evita que un error anterior o no previsto se
propague al consumidor. La llamada de ejemplo de `main()` usa
`procesar_mensaje_seguro`. Los consumidores que invoquen directamente la chain
con `.invoke()` deben usar esa función si necesitan también la protección
general.

`with_fallbacks` responde a excepciones, no a una operación que queda esperando
indefinidamente. Para limitar la espera, configura un `timeout` en el modelo
que lo admita; un timeout que genere una excepción podrá activar el fallback.

## Checklist de revisión

Antes de dar por terminado un cambio al flujo, verifica:

| Parte | Qué comprobar |
|---|---|
| Clasificación | Normaliza la categoría antes de compararla; prueba espacios y mayúsculas, y considera entradas vacías o ambiguas. |
| Bifurcación | Prueba cada categoría y la ruta por defecto para categorías desconocidas. |
| Rutas | Confirma que cada ruta conserva su prompt y respuesta propios y que cuenta con fallback o queda cubierta por la protección general. |
| Flujo completo | Simula un error de clasificación y comprueba que la función segura devuelve una respuesta entendible y registra el fallo. |

No hace falta probar todas las combinaciones de mensajes ni agregar capas de
fallback a cada operación interna. Una prueba por ruta, la ruta por defecto,
una prueba de fallback y una prueba de error en clasificación son una cobertura
razonable para estos comportamientos.

## Pruebas

Desde la raíz del repositorio:

```console
python -m pytest tests/test_orquestacion.py -q
```

La suite usa respuestas simuladas; no requiere `.env`, credenciales ni acceso
a la API. Incluye:

- Normalización de clasificación y selección de cada ruta, incluida la ruta
  por defecto.
- Ejecución de la chain completa con un modelo falso.
- Fallos simulados en las tres rutas y verificación de la respuesta fallback.
- Fallo simulado en el clasificador y verificación de que
  `procesar_mensaje_seguro` no propaga la excepción y registra el error.

Para comprobar específicamente el caso de clasificación:

```console
python -m pytest tests/test_orquestacion.py::test_procesar_mensaje_seguro_registra_y_no_propaga_fallo_de_clasificacion -q
```

La prueba configura `side_effect=ConnectionError(...)` en el clasificador. El
fallo ocurre antes de que `RunnableBranch` seleccione una ruta, por lo que los
fallbacks de las rutas no pueden manejarlo; lo captura el `try/except` de
`procesar_mensaje_seguro`.

## Diagnóstico de problemas comunes

- **El fallo de clasificación llega al llamador:** verifica que se llame a
  `procesar_mensaje_seguro(cadena, mensaje)` en lugar de invocar la chain
  directamente.
- **Una prueba de fallback no está probando realmente la excepción:** usa un
  `RunnableLambda` cuya función lance una excepción. Para un `MagicMock`
  utilizado como paso de clasificación, configura `side_effect` directamente
  en el mock; no configures `invoke.side_effect`.
- **La respuesta esperada cambió:** las pruebas comprueban palabras clave del
  mensaje de respaldo, no que la respuesta del modelo sea idéntica.
- **La ejecución real falla al crear el modelo:** comprueba que `load_dotenv()`
  se ejecute antes de crear `ChatGoogleGenerativeAI` y que `.env` defina
  `GEMINI_API_KEY`.
- **La chain tarda sin producir una excepción:** `with_fallbacks` no es un
  timeout; limita el tiempo en la configuración del modelo.
- **El log no muestra suficiente información al depurar:** el código usa
  `logger.exception`, que registra el mensaje y el traceback. En una aplicación
  de larga duración, configura los handlers de `logging` según el destino
  operativo requerido.

## Cuándo repetir la revisión

Vuelve a ejecutar estas pruebas antes de integrar cambios que afecten prompts
o rutas, después de agregar una categoría y cuando un fallo nuevo aparezca en
ejecución. Si el problema es la clasificación o su normalización, corrige ese
paso; si falta cobertura, agrega una prueba antes de ampliar el manejo general
de excepciones.
