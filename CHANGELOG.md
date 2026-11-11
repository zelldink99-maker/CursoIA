# Changelog

Los cambios importantes del proyecto se documentan en este archivo.

## [No publicado] - 2026-11-11

### Añadido

- Selector central `modeloIA` en `.env`, con `gemini-3.8-flash` como valor
  predeterminado y `gemini-3.5-flash` como alternativa.
- Factory compartida para inicializar clientes LangChain con el modelo
  seleccionado.
- Documentación del ajuste del modelo y de la limitación actual de las tarifas
  del estimador de costos, que corresponden a Gemini 3.8 Flash.
- Ejecución directa de `tests/test_replica_corpus_ejemplo.py` mediante pytest.

### Corregido

- Eliminadas las referencias de modelo fijas de las inicializaciones LangChain,
  endpoints HTTP y scripts de prueba para que todos lean la configuración común.
- Agregada la raíz del proyecto a `sys.path` al ejecutar directamente la prueba
  de réplica, evitando `ModuleNotFoundError: No module named 'src'`.
- Corregida la comprobación del modelo en el verificador local del proyecto.
