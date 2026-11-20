"""Callbacks de LangChain para una traza compacta y correlacionada por consulta."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class TrazaCallbacks(BaseCallbackHandler):
    """Captura eventos de retriever y LLM sin guardar preguntas ni respuestas."""

    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or f"trace-{uuid4().hex[:8]}"
        self.eventos: list[dict[str, Any]] = []

    def _registrar(
        self,
        evento: str,
        run_id: UUID,
        parent_run_id: UUID | None,
        **campos: Any,
    ) -> None:
        self.eventos.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "trace_id": self.trace_id,
                "evento": evento,
                "run_id": str(run_id),
                "parent_run_id": (
                    str(parent_run_id) if parent_run_id is not None else None
                ),
                **campos,
            }
        )

    def on_retriever_start(
        self,
        serialized: dict[str, Any],
        query: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        del serialized, kwargs
        self._registrar(
            "retriever_start",
            run_id,
            parent_run_id,
            query_len=len(query),
        )

    def on_retriever_end(
        self,
        documents: list[Document],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        del kwargs
        self._registrar(
            "retriever_end",
            run_id,
            parent_run_id,
            n_documentos=len(documents),
        )

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        del serialized, kwargs
        self._registrar(
            "llm_start",
            run_id,
            parent_run_id,
            n_prompts=len(prompts),
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        del serialized, kwargs
        self._registrar(
            "llm_start",
            run_id,
            parent_run_id,
            n_prompts=len(messages),
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        del kwargs
        caracteres = sum(
            len(generacion.text)
            for grupo in response.generations
            for generacion in grupo
        )
        self._registrar(
            "llm_end",
            run_id,
            parent_run_id,
            chars_respuesta=caracteres,
        )

    def guardar(self, archivo: str | Path) -> None:
        """Agrega los eventos de esta traza a un archivo JSONL."""
        with Path(archivo).open("a", encoding="utf-8") as destino:
            for evento in self.eventos:
                destino.write(json.dumps(evento, ensure_ascii=False) + "\n")
