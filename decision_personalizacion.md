# Decisión de personalización

## 1. El problema
El clasificador de errores del cliente no responde con un formato consistente.

## 2. Resultado del método de decisión
- Fine-tuning completo: 3 puntos
- PEFT: 3 puntos
- RAG: 0 puntos

**Empate entre: Fine-tuning completo, PEFT**

## 3. Técnica elegida y por qué
Elijo PEFT. El empate con fine-tuning completo se resuelve por costo: el problema es la consistencia del formato, y PEFT permite entrenar menos parámetros. La elección se debe validar con ejemplos que no se usaron durante el entrenamiento.

## 4. Qué necesitarías para ejecutarla
Tengo 200 ejemplos etiquetados y revisados. Etiquetarlos a 5 minutos cada uno representa unas 16.67 horas de trabajo. Antes de entrenar, reviso el balance entre categorías y valido el dataset.