from __future__ import annotations

from typing import Callable, TypeVar

import grpc

from ai_service.grpc import cortex_pb2, cortex_pb2_grpc
from ai_service.homelab.service import HomelabService
from ai_service.secondbrain.service import SecondBrainService

T = TypeVar("T")


class SecondBrainServicer(cortex_pb2_grpc.SecondBrainServiceServicer):
    def __init__(self, service: SecondBrainService) -> None:
        self.service = service

    def HealthCheck(self, request, context):
        return cortex_pb2.HealthCheckResponse(status="ok")

    def CreateCapture(self, request, context):
        return _grpc_guard(
            context,
            lambda: cortex_pb2.CreateCaptureResponse(
                capture=_capture_record(
                    self.service.create_capture(
                        raw_text=request.raw_text,
                        source=request.source or "grpc",
                        owner_id=request.owner_id or "owner",
                    )
                )
            ),
        )

    def ListCaptures(self, request, context):
        return _grpc_guard(
            context,
            lambda: cortex_pb2.ListCapturesResponse(
                captures=[_capture_record(capture) for capture in self.service.list_captures(request.owner_id or "owner")]
            ),
        )

    def GetSyncStatus(self, request, context):
        return _grpc_guard(
            context,
            lambda: _sync_status_response(self.service.get_sync_status(request.owner_id or "owner")),
        )

    def SearchSecondBrain(self, request, context):
        return _grpc_guard(
            context,
            lambda: cortex_pb2.SearchResponse(
                results=[
                    _search_result(result.chunk, result.document, result.score)
                    for result in self.service.search_knowledge(
                        query=request.query,
                        owner_id=request.owner_id or "owner",
                        top_k=request.top_k or 5,
                    )
                ]
            ),
        )


class HomelabServicer(cortex_pb2_grpc.HomelabServiceServicer):
    def __init__(self, service: HomelabService) -> None:
        self.service = service

    def HealthCheck(self, request, context):
        return cortex_pb2.HealthCheckResponse(status="ok")

    def SyncHomelab(self, request, context):
        return _grpc_guard(
            context,
            lambda: _homelab_sync_response(
                self.service.sync_repository(
                    repo_path=request.repo_path,
                    repo_url=request.repo_url or "github.com/dungxbuif/Homelab",
                    branch=request.branch or "main",
                    commit_sha=request.commit_sha or "latest",
                    owner_id=request.owner_id or "homelab",
                )
            ),
        )

    def SearchHomelab(self, request, context):
        return _grpc_guard(
            context,
            lambda: cortex_pb2.SearchResponse(
                results=[
                    _search_result(result.chunk, result.document, result.score)
                    for result in self.service.search_knowledge(
                        query=request.query,
                        owner_id=request.owner_id or "homelab",
                        top_k=request.top_k or 5,
                    )
                ]
            ),
        )

    def ValidateLinks(self, request, context):
        return _grpc_guard(
            context,
            lambda: cortex_pb2.ValidateLinksResponse(
                status="completed",
                broken_links=[
                    cortex_pb2.BrokenLink(
                        source_file=str(row.get("source_file", "")),
                        line_number=int(row.get("line_number", 0)),
                        raw_link=str(row.get("raw_link", "")),
                        reason=str(row.get("reason", "")),
                    )
                    for row in self.service.validate_markdown_links(request.repo_path)
                ],
            ),
        )


def register_services(server: grpc.Server, secondbrain_service: SecondBrainService, homelab_service: HomelabService) -> None:
    cortex_pb2_grpc.add_SecondBrainServiceServicer_to_server(SecondBrainServicer(secondbrain_service), server)
    cortex_pb2_grpc.add_HomelabServiceServicer_to_server(HomelabServicer(homelab_service), server)


def _grpc_guard(context, fn: Callable[[], T]) -> T:
    try:
        return fn()
    except ValueError as exc:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
    except FileNotFoundError as exc:
        context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
    except KeyError as exc:
        context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
    except RuntimeError as exc:
        context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
    except Exception as exc:
        context.abort(grpc.StatusCode.INTERNAL, str(exc))


def _capture_record(capture) -> cortex_pb2.CaptureRecord:
    return cortex_pb2.CaptureRecord(
        id=capture.id,
        status=str(capture.status),
        raw_text=capture.raw_text,
        normalized_markdown=capture.normalized_markdown,
        vault_path=capture.vault_path or "",
        created_at=capture.created_at.isoformat(),
    )


def _sync_status_response(status) -> cortex_pb2.GetSyncStatusResponse:
    return cortex_pb2.GetSyncStatusResponse(
        total_documents=int(status.total_documents),
        indexed_documents=int(status.indexed_documents),
        total_chunks=int(status.total_chunks),
    )


def _homelab_sync_response(result: dict) -> cortex_pb2.SyncHomelabResponse:
    return cortex_pb2.SyncHomelabResponse(
        status=str(result.get("status", "")),
        processed_files=int(result.get("processed_files", 0)),
        skipped_files=int(result.get("skipped_files", 0)),
        failed_files=int(result.get("failed_files", 0)),
    )


def _search_result(chunk, document, score: float) -> cortex_pb2.SearchResult:
    return cortex_pb2.SearchResult(
        chunk=cortex_pb2.ChunkMetadata(
            id=chunk.id,
            document_id=chunk.document_id,
            owner_id=chunk.owner_id,
            file_path=getattr(chunk, "vault_path", getattr(chunk, "file_path", "")),
            chunk_index=int(chunk.chunk_index),
            content=chunk.content,
            heading_chain=list(chunk.heading_chain),
            token_count=int(chunk.token_count),
        ),
        document=cortex_pb2.DocumentMetadata(
            id=document.id,
            owner_id=document.owner_id,
            repo_url=getattr(document, "repo_url", ""),
            branch=getattr(document, "branch", ""),
            commit_sha=getattr(document, "commit_sha", ""),
            file_path=getattr(document, "vault_path", getattr(document, "file_path", "")),
            checksum=document.checksum,
            index_status=str(document.index_status),
            indexed_at=document.indexed_at.isoformat(),
        ),
        score=float(score),
    )
