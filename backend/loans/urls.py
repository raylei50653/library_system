from rest_framework.routers import DefaultRouter
from .views import LoanViewSet, ReservationViewSet, AdminLoanViewSet

router = DefaultRouter()
router.register(r"loans", LoanViewSet, basename="loans")
router.register(r"reservations", ReservationViewSet, basename="reservations")
router.register(r"admin/loans", AdminLoanViewSet, basename="admin-loans")

urlpatterns = router.urls
