# Bloque 30: decisión fundamentada de estrategia de personalización

Este bloque convierte la comparación de RAG, fine-tuning completo y PEFT en
una decisión repetible para un proyecto real. Primero estima los costos de
etiquetado, infraestructura y tiempo; después puntúa cinco criterios y redacta
una decisión con evidencia. La implementación local está en
[`src/GATE_1/decision_personalizacion.py`](../src/GATE_1/decision_personalizacion.py).

## Requisitos

Usa Python 3.10 o superior y el entorno de este proyecto. Los cálculos y la
recomendación solo usan Python estándar; la consulta opcional de estadísticas
usa `google-genai` y `.env`, ya configurados en los bloques anteriores. Las
pruebas locales no necesitan una clave ni hacen llamadas a Gemini:

```console
python -m pytest tests/test_decision_personalizacion.py -q
```

## 1. Los tres costos de personalizar

Fine-tuning y PEFT necesitan ejemplos con salidas exactas y correctas. El
trabajo humano de etiquetar no aparece en la factura de la API; las etiquetas
contradictorias producen un modelo inconsistente y balancear categorías poco
frecuentes también requiere tiempo. RAG, en cambio, puede indexar documentos
existentes sin etiquetarlos.

Calcula el costo humano antes de comprometerte con el tamaño del dataset:

```python
from src.GATE_1.decision_personalizacion import estimar_costo_de_etiquetar

horas, costo = estimar_costo_de_etiquetar(8, 5, 25)
print(f"{horas:.2f} horas, aprox ${costo:.2f}")

horas2, costo2 = estimar_costo_de_etiquetar(200, 5, 25)
print(f"{horas2:.2f} horas, aprox ${costo2:.2f}")
print(f"factor de crecimiento en horas: {horas2 / horas:.1f}x")
```

Salida:

```text
0.67 horas, aprox $16.67
16.67 horas, aprox $416.67
factor de crecimiento en horas: 25.0x
```

### Mini-ejercicio: 500 ejemplos y segunda revisión

Cada uno de 500 ejemplos toma 4 minutos a $20 por hora. El 20 % requiere una
segunda revisión de 2 minutos:

```python
from src.GATE_1.decision_personalizacion import estimar_costo_de_etiquetar

horas_base, costo_base = estimar_costo_de_etiquetar(500, 4, 20)
horas_rev, costo_rev = estimar_costo_de_etiquetar(500 * 0.20, 2, 20)
total_horas = horas_base + horas_rev
total_costo = costo_base + costo_rev

print(f"etiquetado base: {horas_base:.2f} horas, aprox ${costo_base:.2f}")
print(f"segunda revision: {horas_rev:.2f} horas, aprox ${costo_rev:.2f}")
print(f"total: {total_horas:.2f} horas, aprox ${total_costo:.2f}")
print(f"jornadas de 8 horas: {total_horas / 8:.1f}")
```

Resultado: 33.33 horas y $666.67 para el etiquetado base; 3.33 horas y $66.67
para la revisión; en total, 36.67 horas, $733.33 y 4.6 jornadas de ocho horas.

RAG mantiene un vector store disponible, respaldado y actualizado mientras
está en producción. Un modelo afinado mediante una API gestionada no requiere
una base vectorial adicional para servir, aunque el entrenamiento sí consume
cómputo. Una API gestionada abstrae ese cómputo; al entrenar PEFT sobre pesos
abiertos, la infraestructura de entrenamiento corre por tu cuenta.

Para estimar tokens, el Bloque 28 usó una aproximación porque no se había
ejecutado la consulta real. Al terminar el tuning, el SDK informa las
estadísticas exactas del dataset:

```python
from dotenv import load_dotenv
from google import genai
from src.GATE_1.decision_personalizacion import obtener_estadisticas_tuning

load_dotenv()
client = genai.Client()
nombre_trabajo = "NOMBRE_DE_TU_TRABAJO"

try:
    stats = obtener_estadisticas_tuning(client, nombre_trabajo)
except (RuntimeError, ValueError) as error:
    raise SystemExit(str(error)) from error

print("ejemplos usados:", stats.tuning_dataset_example_count)
print("ejemplos truncados:", stats.total_truncated_example_count)
print("tokens facturables totales:", stats.total_billable_token_count)
print("caracteres facturables totales:", stats.total_billable_character_count)
print("pasos de entrenamiento:", stats.tuning_step_count)
print("razones de truncado:", stats.dropped_example_reasons)
print("caracteres de tuning:", stats.total_tuning_character_count)
```

Reemplaza `NOMBRE_DE_TU_TRABAJO` por el `trabajo.name` devuelto al enviar el
tuning. Esta consulta solo recupera un trabajo existente; no inicia un
entrenamiento. Si aún no hay estadísticas, espera a que el trabajo termine. Si
`total_truncated_example_count` es mayor que cero, revisa los ejemplos largos:
la API puede recortarlos antes de entrenar. Compara también los caracteres de
tuning con los facturables. Los tipos y campos pueden verificarse en la versión
instalada con `types.SupervisedTuningDataStats.model_fields.keys()`.

El tiempo de iteración también cambia: un prompt se prueba al instante; agregar
un documento a RAG toma segundos o minutos; cada intento de fine-tuning o PEFT
puede tardar de minutos a horas y consume cómputo. Valida el dataset antes de
cada envío y define de antemano qué métrica vas a observar.

| Dimensión | RAG | Fine-tuning / PEFT |
| --- | --- | --- |
| Datos | Indexa fuentes existentes; no necesita ejemplos etiquetados. | Cada ejemplo requiere una salida correcta; hay que estimar y revisar el trabajo humano. |
| Infraestructura | Mantiene vector store, respaldos e índice actualizado. | La API gestionada oculta el cómputo de entrenamiento; el modelo afinado se consulta como un modelo de API. |
| Cómputo | Se mide por flujo de consulta (Bloque 28). | La API informa tokens facturables del trabajo ejecutado. |
| Tiempo | Segundos a minutos para observar cambios. | Minutos a horas por intento; cada intento tiene un costo. |
| Riesgo principal | Mantener el índice al día. | Etiquetas inconsistentes o ejemplos truncados. |

## 2. Comparar estrategias con cinco preguntas

La función `recomendar_estrategia` suma puntos con estas reglas:

| Criterio respondido con `True` | RAG | Fine-tuning completo | PEFT |
| --- | ---: | ---: | ---: |
| La información cambia seguido | +3 | — | — |
| El problema es formato o tono | — | +1 | +2 |
| Hay dataset grande, etiquetado y de calidad | — | +2 | +1 |
| Presupuesto limitado o necesidad de iterar rápido | +2 | — | +1 |
| Se necesitan múltiples variantes | — | — | +2 |

Todas las respuestas deben ser booleanos reales (`True` o `False`), no textos
como `"si"`. La función detecta claves faltantes y devuelve todas las técnicas
empatadas. Este caso muestra el empate entre fine-tuning completo y PEFT:

```python
from src.GATE_1.decision_personalizacion import recomendar_estrategia

respuestas_caso2 = {
    "informacion_cambia_seguido": False,
    "problema_de_formato_o_tono": True,
    "dataset_grande_y_de_calidad": True,
    "presupuesto_limitado_o_iterar_rapido": False,
    "necesita_multiples_variantes": False,
}
puntos2, ganadoras2 = recomendar_estrategia(respuestas_caso2)
print("caso 2:", puntos2)
print("candidatas empatadas:", ganadoras2)
```

```text
caso 2: {'RAG': 0, 'Fine-tuning completo': 3, 'PEFT': 3}
candidatas empatadas: ['Fine-tuning completo', 'PEFT']
```

No uses solo `max(puntos, key=puntos.get)` para decidir: en caso de empate
oculta las demás técnicas y elige la primera por orden del diccionario. La
función anterior busca todas las técnicas cuyo puntaje iguala al máximo.

Puedes analizar la sensibilidad del empate cambiando una respuesta a la vez:

```python
for clave in respuestas_caso2:
    variante = dict(respuestas_caso2)
    variante[clave] = not variante[clave]
    _, ganadoras_v = recomendar_estrategia(variante)
    cambio = "CAMBIA" if set(ganadoras_v) != set(ganadoras2) else "igual"
    print(f"{clave} -> {variante[clave]}: {ganadoras_v} [{cambio}]")
```

En este caso las cinco respuestas mueven el resultado. Si tu caso da empate,
revisa con evidencia la respuesta que más dudas te generó. Como contraste, un
bot con información cambiante, problema de formato y presupuesto limitado
obtiene RAG: 5 puntos; PEFT: 3; fine-tuning completo: 1.


## 3. Actividad core: redactar la decisión de tu proyecto

No necesitas acceso a la API para esta actividad. Usa evidencia de tu proyecto
para responder las cinco preguntas; los umbrales siguientes son orientativos:

| Clave | Responde `True` si... | Evidencia que puedes reunir |
| --- | --- | --- |
| `informacion_cambia_seguido` | El contenido cambia al menos una vez al mes. | Cuenta las fuentes modificadas en los últimos tres meses. |
| `problema_de_formato_o_tono` | 3 o más de 20 respuestas fallan el formato o tono esperado. | Revisa 20 respuestas con una rúbrica fija. |
| `dataset_grande_y_de_calidad` | Ya tienes 200 ejemplos etiquetados y ninguno de una muestra de 20 es contradictorio. | Cuenta los ejemplos y revisa 20 al azar. |
| `presupuesto_limitado_o_iterar_rapido` | Puedes pagar como máximo 2 entrenamientos, o necesitas el resultado en menos de un día. | Anota el presupuesto y el tiempo máximo por iteración. |
| `necesita_multiples_variantes` | Necesitas dos o más comportamientos personalizados. | Cuenta variantes por cliente, idioma o producto. |

Anota el hecho o número que sustenta cada respuesta. Para ver en consola una
corrida completa y crear un documento de ejemplo, ejecuta desde la raíz:

```console
python -m src.GATE_1.decision_personalizacion
```

El programa imprime los puntajes y las cuatro secciones completas, y guarda
`decision_personalizacion.md` en la carpeta actual. Es una demostración con el
caso de ejemplo de abajo, no una decisión automática sobre tu proyecto. El
programa se niega a sobrescribir un archivo existente. Para preparar tu propia
actividad, edita `respuestas_ejemplo`, el problema y los textos de justificación
y requisitos en `main()`; basa las respuestas en la evidencia de tu proyecto.
La función generadora también permite producir un esqueleto con marcadores:

```python
from pathlib import Path

from src.GATE_1.decision_personalizacion import (
    generar_esqueleto_decision,
    recomendar_estrategia,
)

respuestas_mi_caso = {
    "informacion_cambia_seguido": False,  # Sustituye por evidencia de tu caso.
    "problema_de_formato_o_tono": True,
    "dataset_grande_y_de_calidad": False,
    "presupuesto_limitado_o_iterar_rapido": True,
    "necesita_multiples_variantes": False,
}
problema = "Describe en una o dos oraciones la carencia del sistema."

puntos, ganadoras = recomendar_estrategia(respuestas_mi_caso)
esqueleto = generar_esqueleto_decision(problema, puntos, ganadoras)
Path("decision_personalizacion.md").write_text(esqueleto, encoding="utf-8")
print(esqueleto)
```

El ejemplo del fragmento contiene respuestas ilustrativas: reemplázalas y
agrega al documento la evidencia real antes de usarlo como decisión. Completa
estas cuatro secciones, en orden:

1. **El problema:** describe el comportamiento o carencia sin nombrar todavía
   una técnica.
2. **Resultado:** registra los puntajes y las candidatas ganadoras; si hubo
   empate, indícalo explícitamente.
3. **Técnica elegida y por qué:** justifica un ganador o resuelve el empate con
   los costos de datos, cómputo, infraestructura y tiempo.
4. **Qué necesitas para ejecutarla:** indica corpus pendiente de indexar, o
   cuántos ejemplos etiquetados tienes y cuántos faltan.

No escribas “varios ejemplos” o “muchos documentos”: usa cantidades y estima
el tiempo faltante con `estimar_costo_de_etiquetar`. La decisión final sigue
requiriendo criterio cualitativo: el puntaje orienta, no reemplaza el análisis.


## Problemas frecuentes

- **Todos los puntos quedan en cero:** confirma que pasaste booleanos `True` o
  `False`, no cadenas de texto.
- **Empate entre técnicas:** es un resultado legítimo; usa la evidencia y los
  costos para elegir y registra el motivo.
- **Faltan claves o aparece `TypeError`:** completa las cinco respuestas con
  booleanos reales.
- **No se pueden consultar estadísticas:** verifica el nombre del trabajo y la
  clave configurada; espera a que termine si aún no hay estadísticas.
- **Hay ejemplos truncados:** recorta deliberadamente los casos largos y vuelve
  a validarlos antes de enviar otro trabajo.
- **`NameError` en el script de actividad:** ejecuta primero la celda o bloque
  donde definiste cada variable.
