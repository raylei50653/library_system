# books/urls.py
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")
router.register(r"categories", CategoryViewSet, basename="category")

urlpatterns = router.urls

