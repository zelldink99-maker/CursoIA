# Bloque 32: versionado, supervisión y matriz de riesgos

Este bloque entrega un único módulo dentro del paquete `src/GATE_2`:

```console
python -m src.GATE_2.unidad_completa_supervision
```

El archivo combina los tres ejercicios anteriores para mostrar una corrida
completa sin modificar archivos ni realizar llamadas a Gemini.

## Paso 1: versionado y diff

El script registra la versión inicial y una versión que agrega la instrucción
anti-inyección del Bloque 31. Calcula huellas SHA-256 abreviadas y presenta el
diff en formato unificado. Los valores exactos pueden cambiar si se modifica
el texto real del prompt.

Salida esperada:

```text
0037a44f2a2 - version inicial
ba5b9a997ba3 - agrega instruccion anti-inyeccion (Bloque 31)
ultima version activa: ba5b9a997ba3
```

## Paso 2: supervisión humana

El archivo construye un grafo LangGraph con un nodo `supervisar`. Antes de
activar la versión nueva, `interrupt()` detiene la ejecución y devuelve el
motivo y la huella propuesta. La prueba reanuda el mismo hilo con
`Command(resume=True)`, ejecuta el nodo `aplicar` y activa la huella.

El resultado muestra un punto de supervisión como:

```text
pendiente: {'motivo': 'aprobar nueva version de prompt en produccion',
'huella_propuesta': 'ba5b9a997ba3'}
version ba5b9a997ba3 activada
```

## Paso 3: matriz de riesgos

La matriz contiene cinco riesgos concretos y los ordena por probabilidad por
impacto, de mayor a menor. Los niveles son `CRITICO`, `ALTO`, `MEDIO` y `BAJO`.
Cada fila incluida en los límites de categoría se marca con `[AL LIMITE]`.

Todo riesgo alto o crítico necesita una acción de revisión humana asociada.
Los puntajes son un ejemplo de estimación; deben ajustarse con evidencia real
del proyecto.

## Dependencia y pruebas

El entorno necesita LangGraph declarado en `requirements.txt`:

```console
python -m pip install -r requirements.txt
python -m src.GATE_2.unidad_completa_supervision
python -m pytest tests/test_bloque32.py tests/test_supervision_riesgos.py -q
```

Los riesgos críticos y altos requieren revisión humana antes de cerrar su
estimación o desplegar una mitigación asociada.
