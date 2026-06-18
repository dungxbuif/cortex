from __future__ import annotations

from concurrent import futures
import os

os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")

import grpc

from ai_service.grpc.handlers import register_services
from ai_service.homelab.repository import PostgresPsqlHomelabRepository
from ai_service.homelab.service import HomelabService
from ai_service.providers.embedding import default_embedder
from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService


def create_server(
    secondbrain_service: SecondBrainService | None = None,
    homelab_service: HomelabService | None = None,
    max_workers: int = 10,
) -> grpc.Server:
    embedder = None if secondbrain_service and homelab_service else default_embedder()
    sb_service = secondbrain_service or SecondBrainService(
        repository=PostgresPsqlSecondBrainRepository.from_env(),
        embedder=embedder,
    )
    hl_service = homelab_service or HomelabService(
        repository=PostgresPsqlHomelabRepository.from_env(),
        embedder=embedder,
    )
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    register_services(server, sb_service, hl_service)
    return server


def serve(port: int = 50051) -> None:
    server = create_server()
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"gRPC Server listening on port {port}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve(port=int(os.getenv("AI_GRPC_PORT", "50051")))
