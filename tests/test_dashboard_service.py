"""
test_dashboard_service.py — Unit & Integration Tests for Data Dashboard Backend.
================================================================================
Tests all data aggregation services, controllers, and FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.services.dashboard_data_service import DashboardDataService
from src.controllers.dashboard_controller import DashboardController
from src.validators.dashboard_schemas import DashboardChatRequestSchema, RAGSearchRequestSchema
from dashboard_server import app


@pytest.fixture
def data_service():
    return DashboardDataService()


@pytest.fixture
def controller(data_service):
    return DashboardController(data_service=data_service)


@pytest.fixture
def client():
    return TestClient(app)


class TestDashboardDataService:
    def test_overview_kpis(self, data_service):
        kpis = data_service.get_overview_kpis()
        assert "total_debates" in kpis
        assert "avg_consensus" in kpis
        assert "rag_chunks" in kpis
        assert "local_llm" in kpis
        assert "system_tasks" in kpis

    def test_souls_retrieval(self, data_service):
        souls = data_service.get_souls()
        assert isinstance(souls, list)
        if souls:
            first = souls[0]
            assert "id" in first
            assert "name" in first
            assert "role" in first

    def test_debates_retrieval(self, data_service):
        debates = data_service.get_debates()
        assert "sessions" in debates
        assert "convergence_chart" in debates
        assert len(debates["sessions"]) > 0
        first_session = debates["sessions"][0]
        assert "topic" in first_session
        assert "consensus_score" in first_session

    def test_rag_data(self, data_service):
        rag = data_service.get_rag_data()
        assert "total_chunks" in rag
        assert "documents" in rag
        assert isinstance(rag["documents"], list)

    def test_research_data(self, data_service):
        research = data_service.get_research_data()
        assert "studies" in research
        assert "ablation_chart" in research
        assert "safety_chart" in research
        assert "safety_study" in research["studies"]

    def test_governance_data(self, data_service):
        gov = data_service.get_governance()
        assert "total_tasks" in gov
        assert "completed_count" in gov
        assert "recent_tasks" in gov

    def test_models_data(self, data_service):
        models = data_service.get_models_data()
        assert "default_model" in models
        assert "backend" in models
        assert "ollama_running" in models


class TestDashboardController:
    def test_controller_kpis(self, controller):
        res = controller.get_kpis()
        assert res["success"] is True
        assert "total_debates" in res["data"]

    def test_controller_search_rag_valid(self, controller):
        res = controller.search_rag({"query": "antigravity", "limit": 3})
        assert res["success"] is True
        assert "data" in res

    def test_controller_search_rag_empty_fails(self, controller):
        res = controller.search_rag({"query": "   ", "limit": 3})
        assert res["success"] is False
        assert "error" in res


class TestFastAPIEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_api_kpis(self, client):
        resp = client.get("/api/kpis")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_debates" in data

    def test_api_debates(self, client):
        resp = client.get("/api/debates")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data

    def test_api_rag(self, client):
        resp = client.get("/api/rag")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_chunks" in data

    def test_api_rag_search_valid(self, client):
        resp = client.post("/api/rag/search", json={"query": "agent", "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_api_rag_search_invalid(self, client):
        resp = client.post("/api/rag/search", json={"query": "", "limit": 2})
        assert resp.status_code == 422

    def test_api_research(self, client):
        resp = client.get("/api/research")
        assert resp.status_code == 200
        data = resp.json()
        assert "studies" in data

    def test_api_governance(self, client):
        resp = client.get("/api/governance")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tasks" in data

    def test_api_models(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "default_model" in data
