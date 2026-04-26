"""
KPI Module - Centralized KPI management for UniSmart AI
"""

from app.modules.kpis.routes import router
from app.modules.kpis.models import *
from app.modules.kpis.services import KPIService, AlertService, RankingService