# Decisión de arquitectura: elección de modelo

## Modelo elegido

El cliente robusto `src/GATE_1/consumir_gemini.py` y el cliente
`src/GATE_1/monolitico.py`, compartido por el banco de prompts y la medición
de latencia, usan **Gemini 3.8 Flash** (`gemini-3.8-flash`). El segundo acepta
una instrucción del sistema en cada solicitud.

El cliente de latencia y del banco de prompts fija la tarifa de Gemini 3.8 Flash
descrita más adelante. No se incluyen comparaciones de latencia o calidad porque
el repositorio no conserva mediciones reproducibles para otros modelos.

El módulo `src/GATE_1/cliente.py` compone `monolitico.py` con
`cliente_reintento.py`: clasifica 401/403 como errores no reintentables y 429,
5xx, timeout y conexión como fallos transitorios. Los reintentos usan backoff
exponencial con jitter y un máximo configurable de 30 segundos por espera. El
cliente ejecuta como máximo tres intentos totales por operación de forma
predeterminada. Tras validar y extraer una respuesta, `registrar_costo` utiliza
`calcular_costo` para sumar al acumulado en memoria la estimación basada en los
tokens reales y las tarifas de este documento. El costo de sesión no se guarda
en disco. Los clientes anteriores conservan su comportamiento; la política de
reintentos y el registro corresponden a la interfaz `consultar_modelo`.

El punto de entrada `python -m src.GATE_1.cliente` realiza una sola consulta de
ejemplo. La función independiente `ejecutar_ensayo()` realiza diez consultas y
muestra por cada respuesta exitosa el texto resumido, el total de tokens
reportado, el costo de esa operación y el acumulado. El ensayo puede realizar
hasta treinta solicitudes si las diez preguntas agotan los tres intentos cada
una. Un error transitorio agotado se informa y permite continuar; los errores
permanentes detienen el ensayo.

Desde la raíz, el ensayo se puede iniciar sin modificar el bloque `__main__`:

```console
python -c "from src.GATE_1.cliente import ejecutar_ensayo; raise SystemExit(ejecutar_ensayo())"
```

## Diagrama de arquitectura

![Diagrama de arquitectura de la miniaplicación](./diagrama_arquitectura.jpg)

El flujo robusto de consulta es:

1. `obtener_dato_de_prueba` recibe la pregunta y rechaza valores vacíos.
2. La configuración carga `GEMINI_API_KEY` desde el `.env` del proyecto; si falta o conserva el valor de ejemplo, informa el error.
3. La aplicación prepara el cuerpo de la solicitud y envía una petición `POST` al endpoint `generateContent`, con la clave en el encabezado y un tiempo límite de 30 segundos.
4. La respuesta HTTP se valida. Los errores de conexión, tiempo de espera, estado HTTP, JSON inválido o formato inesperado se convierten en mensajes explícitos.
5. `extraer_texto` obtiene y concatena las partes de texto del primer candidato, y devuelve la respuesta.

Este flujo corresponde a `src/GATE_1/consumir_gemini.py`. `src/GATE_1/monolitico.py` también mantiene la clave fuera de la URL y convierte errores de configuración, conexión, tiempo de espera, HTTP y respuesta JSON en excepciones específicas derivadas de `GeminiError`. Ambos clientes validan las preguntas y el contenido de las respuestas.

Los puntos de entrada `main.py`, `latencia.py` y `prompts/banco.py` capturan los errores esperables de sus operaciones y devuelven un código de salida distinto de cero. El cálculo de costos, la configuración de latencia y la división también rechazan entradas inválidas explícitamente. El verificador `revision_gate_1.py --omitir-api` cubre estos rechazos localmente sin realizar solicitudes a Gemini.

## Medición de latencia y estimación de costo

La clase `Latencia`, en `src/GATE_1/latencia.py`, realiza cuatro solicitudes de prueba por defecto usando `gemini-3.8-flash` mediante las funciones de `src/GATE_1/monolitico.py`. Imprime el tiempo de cada solicitud, el promedio y estima el costo de la última respuesta con `calcular_costo`, de `src/GATE_1/costo.py`. La prueba se ejecuta al lanzar el módulo o llamar `Latencia.ejecutar()`; importarlo no realiza solicitudes.

`enviar_peticion` conserva el JSON completo de Gemini, incluidos los metadatos
`usageMetadata` cuando están presentes. El ejemplo ejecutable en
`src/GATE_1/monolitico.py` extrae y muestra los tokens de entrada
(`promptTokenCount`), de salida (`candidatesTokenCount`) y el total
(`totalTokenCount`). Si faltan o tienen un formato inválido, el cliente lo
comunica como `GeminiResponseError`. El módulo `costo.py` usa los contadores de
entrada, salida y, cuando viene separado, `thoughtsTokenCount` para estimar el
costo. El cliente modular `cliente.py`, además, informa después de cada consulta
exitosa el total de tokens reportado, el costo de esa operación y el costo
acumulado. El total de tokens mostrado es `totalTokenCount`; la estimación de
costo aplica el precio de entrada a `promptTokenCount` y el precio de salida a
`candidatesTokenCount` más `thoughtsTokenCount` si está presente. Si el servicio
no incluye metadatos válidos, se informa el error y no se contabiliza un costo
estimado para esa respuesta.

## Precios oficiales y cálculo de costo

El cálculo del proyecto usa la tarifa **Standard de pago** publicada por Google
para Gemini 3.8 Flash: **USD 0,75 por millón de tokens de entrada** y
**USD 3,75 por millón de tokens de salida** (incluye tokens de pensamiento).
Equivale a USD 0,00000075 y USD 0,00000375 por token, respectivamente. Son
precios publicados para el nivel Standard de pago hasta el **31 de diciembre
de 2026**, no cargos de facturación consultados en tiempo real. Google también
publica acceso gratuito para este modelo; el cálculo local usa el precio de
pago Standard y no consulta qué nivel de facturación tiene la clave.

| Modelo y modalidad | Entrada (USD / 1 millón de tokens) | Salida (USD / 1 millón de tokens) | Vigencia publicada |
|---|---:|---:|---|
| Gemini 3.8 Flash, Standard de pago | 0,75 | 3,75 | Hasta el 31-12-2026 |

La medición usa los tokens reales devueltos en `usageMetadata` para la última
solicitud y muestra una estimación en USD. Incluye `thoughtsTokenCount` si la
API lo devuelve por separado. No incluye cargos de herramientas/grounding,
almacenamiento de caché, impuestos, créditos, descuentos ni otras modalidades
de servicio, por lo que el total de la factura puede diferir. El costo real
facturado debe verificarse en Google AI Studio o Google Cloud.

Fuente oficial: [precios de Gemini API](https://ai.google.dev/gemini-api/docs/pricing),
consultada el **22 de octubre de 2026**. La página indica que la tarifa Standard
de Gemini 3.8 Flash cambia a USD 1,50/M de entrada y USD 7,50/M de salida desde
el **1 de enero de 2027**; revisa y actualiza las constantes en `costo.py` a
partir de esa fecha.

## Contingencia: disponibilidad y límites de tokens

Una demora o un error de Gemini no implica necesariamente que el modelo haya
dejado de funcionar. El nuevo cliente `cliente.py` reintenta automáticamente
los errores 429, 5xx, timeout y conexión hasta tres intentos totales por
operación. Entre ellos calcula una espera exponencial desde 2 segundos, duplica
la espera para el siguiente intento, añade jitter de hasta el 10 % y limita
cada espera a 30 segundos. Informa en consola cada reintento. Los demás
consumidores conservan su comportamiento actual. Antes de cambiar el modelo,
revisa el estado HTTP y el mensaje de la API:

- **HTTP 429** o `RESOURCE_EXHAUSTED`: puede indicar cuota o límite de solicitudes
  alcanzado. Reduce la frecuencia, espera y vuelve a intentar con espera
  incremental. Cambiar a otro modelo solo ayudará si ese modelo tiene cuota y
  capacidad disponibles para la misma clave y proyecto.
- **HTTP 503** o un mensaje de servicio ocupado: suele ser una condición
  transitoria de capacidad. Espera y reintenta; si persiste, prueba un modelo
  alternativo disponible en tu cuenta.
- **Error por límite de tokens/contexto** (normalmente comunicado como una
  solicitud inválida): reduce el texto de entrada, elimina contexto redundante
  o divide el trabajo en partes. Cambiar de modelo no resuelve por sí solo el
  exceso de tokens; solo podría servir si el modelo alternativo documenta un
  contexto mayor y la cuenta permite usarlo.
- **HTTP 400**, autenticación o nombre de modelo inválido: revisa el cuerpo de
  la solicitud, la clave y que el identificador del modelo esté habilitado
  antes de repetirla. Reintentar sin corregir la causa no suele ayudar.

### Reintentos y cambio manual de modelo

El proyecto no cambia de modelo automáticamente. El cliente modular
`cliente.py` reintenta errores transitorios; `monolitico.py`, usado por la
latencia y el banco de prompts, no aplica reintentos. Para cambiar el cliente
compartido por la latencia y el banco de prompts,
edita la variable `modelo` de `src/GATE_1/monolitico.py` y usa un identificador
que aparezca habilitado para tu cuenta. Por ejemplo, podrías probar
`gemini-3.6-flash` como alternativa a `gemini-3.8-flash` **si la API la ofrece
para tu proyecto**. El cliente independiente `src/GATE_1/consumir_gemini.py`
tiene su propia constante `MODEL`; cambiar un cliente no cambia el otro.

Después del cambio, ejecuta `python src\GATE_1\revision_gate_1.py --omitir-api`
para validar localmente el formato y luego realiza una petición
de prueba con una pregunta pequeña. Confirma que el identificador del modelo,
el esquema JSON requerido, los límites de tokens, la cuota y el precio estén
vigentes en la documentación y consola de Google AI para tu cuenta. La
disponibilidad y los límites pueden variar por proyecto, región y fecha.

## Comparación de modelos

Se eliminó la comparación histórica de costos, latencias y calidad porque no
identificaba el segundo modelo ni incluía mediciones reproducibles. Los precios
que se conservan en esta documentación son los precios públicos de Google para
el modelo actualmente usado por la medición de latencia, no resultados de una
prueba inventada o una factura individual.
