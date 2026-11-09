# Bloque 23: autonomía, supervisión humana y trazas

Este bloque amplía el agente con herramientas del Bloque 21 y la memoria por
sesión del Bloque 22. Distingue las acciones que pueden ejecutarse libremente
de las que requieren aprobación y deja un registro persistente de las
decisiones observables del agente.

## Riesgo y supervisión humana

La autonomía es cuánto puede hacer el agente sin intervención. Clasifica cada
herramienta según sus consecuencias:

- **Bajo, solo lectura:** consultar, buscar o calcular sin cambiar estado.
- **Medio, escritura reversible:** modificar una preferencia o guardar una
  nota que se pueda corregir.
- **Alto, escritura irreversible o con impacto económico:** enviar un correo,
  cancelar un pedido o generar un reembolso.

En el agente de este proyecto, `buscar_en_documentacion` es de riesgo bajo:
solo consulta políticas incluidas en el código. `calcular_costo_tokens_gemini`
también es de riesgo bajo: estima un valor usando las tarifas del proyecto y
no ejecuta una operación económica. Ninguna herramienta modifica sistemas ni
produce efectos externos; por eso actualmente no hay una acción de riesgo alto
que deba bloquearse para aprobación.

Si en el futuro se agrega una herramienta irreversible, la confirmación debe
ocurrir dentro de su ruta de ejecución y antes del efecto real. La falta de
respuesta o un rechazo deben producir siempre el resultado seguro: no ejecutar.
No se debe aplicar la misma fricción a las búsquedas y cálculos de bajo riesgo.
Una aprobación recibida desde una terminal es solo una demostración; en un
sistema real debe provenir de una interfaz de aprobación autenticada. El
ejemplo de `select.select()` sobre `stdin` solo es válido en Linux y macOS;
Windows necesita otro mecanismo, y la espera debe tener un timeout explícito.

## Registro de decisiones observables

`src/GATE_1/trazas_agente.py` guarda cada interacción en
`trazas_agente.jsonl`, una línea JSON por llamada. El registro contiene
timestamp UTC, sesión, entrada, herramientas, argumentos, observaciones y
respuesta final. Si el ejecutor no devuelve `intermediate_steps`, registra
`acciones` como una lista vacía. El archivo se crea en la raíz del proyecto al
ejecutar el agente desde allí; el ejemplo principal lo guarda explícitamente
en esa ubicación.

El registro describe el comportamiento observable, no el razonamiento privado
del modelo. Los argumentos pueden contener información sensible: protege el
archivo y define retención antes de usarlo con datos reales.

El analizador `marcar_repeticiones_sospechosas` busca la misma herramienta en
llamadas consecutivas dentro de una interacción. Solo marca candidatos para
revisión humana; una repetición no demuestra por sí sola que haya un error.
JSON corrupto se informa explícitamente en lugar de ignorarse.

Ejecuta el agente desde la raíz para generar trazas (requiere `GEMINI_API_KEY`
y puede generar costos):

```console
python -m src.GATE_1.agente_con_herramientas
```

Revisa repeticiones desde la raíz:

```console
python -c "from src.GATE_1.trazas_agente import marcar_repeticiones_sospechosas; marcar_repeticiones_sospechosas()"
```

Las pruebas del registrador y el analizador no usan Gemini:

```console
python -m pytest tests/test_trazas_agente.py -q
```

## Límites de autonomía del agente de soporte

### Herramientas y nivel de riesgo

- `buscar_en_documentacion`: **bajo**. Lee información fija del proyecto; no
  modifica datos.
- `calcular_costo_tokens_gemini`: **bajo**. Realiza una estimación local; no
  inicia un cobro ni altera el sistema.

### Herramientas que requieren aprobación humana

Actualmente, ninguna. Si se agrega una operación de escritura irreversible o
con impacto económico, debe requerir una aprobación humana antes de ejecutarse,
con timeout y rechazo por defecto, y registrar también el resultado de esa
decisión.

### Revisión de trazas

- **Frecuencia:** semanal cuando se use el agente con interacciones reales.
- **Qué revisar:** repeticiones consecutivas, argumentos inesperados y
  respuestas finales que no estén respaldadas por las observaciones.
- **Riesgo alto:** no hay herramientas de ese nivel hoy. Cuando se incorpore
  una, revisar todas sus invocaciones y comprobar que cada una tenga un
  resultado de aprobación o rechazo.
- **Volumen:** priorizar las interacciones con acciones sensibles y tomar una
  muestra regular del resto; el analizador solo prioriza candidatos, no
  reemplaza la revisión.

### Qué hacer ante un comportamiento inesperado

1. Deshabilitar temporalmente la herramienta implicada o detener el agente si
   no se puede aislar la causa.
2. Conservar la traza y revisar entrada, argumentos, observaciones y respuesta
   final; no borrar el registro original.
3. Comprobar si la descripción de la herramienta y las instrucciones del
   agente delimitan correctamente cuándo usarla.
4. Corregir la descripción, validación o política de acceso y agregar una
   prueba para el caso observado.
5. Volver a habilitar la herramienta después de verificar el comportamiento
   con pruebas locales; revisar las trazas posteriores.
