from fastapi import APIRouter

from app.api.routes.system import router as system_router
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.documents import router as documents_router
from app.api.routes.advisor import router as advisor_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.portal import router as portal_router, admin_router
from app.api.routes.tools import router as tools_router, admin_router as analytics_router
from app.api.routes.site import router as site_router
from app.api.routes.legal import router as legal_router, manage_router as legal_manage_router
from app.api.routes.enhancements import router as enhancements_router
from app.api.routes.financial_statements import router as financial_statements_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(documents_router)
api_router.include_router(advisor_router)
api_router.include_router(consultations_router)
api_router.include_router(portal_router)
api_router.include_router(admin_router)
api_router.include_router(tools_router)
api_router.include_router(analytics_router)
api_router.include_router(site_router)
api_router.include_router(legal_router)
api_router.include_router(legal_manage_router)
api_router.include_router(enhancements_router)
api_router.include_router(financial_statements_router)
