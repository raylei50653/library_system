from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import Loan
from .serializers import (
    LoanListSerializer,
    LoanCreateSerializer,
    ReservationCreateSerializer,
    LoanActionSerializer,
    AdminLoanPatchSerializer,
)
from .permissions import IsOwnerOrAdmin
from . import services


class LoanViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = Loan.objects.all().select_related("book")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return LoanCreateSerializer
        return LoanListSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(type=Loan.Type.LOAN)
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOwnerOrAdmin])
    def return_(self, request, pk=None):
        loan = self.get_object()
        services.return_loan(loan=loan)
        return Response(LoanActionSerializer(loan).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOwnerOrAdmin])
    def renew(self, request, pk=None):
        loan = self.get_object()
        services.renew_loan(loan=loan)
        return Response(LoanActionSerializer(loan).data)


class ReservationViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    queryset = Loan.objects.all().select_related("book")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreateSerializer
        return LoanListSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(type=Loan.Type.RESERVATION)
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        return qs.order_by("-created_at")


class AdminLoanViewSet(mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    queryset = Loan.objects.all().select_related("book", "user")
    permission_classes = [IsAdminUser]
    serializer_class = AdminLoanPatchSerializer

    def partial_update(self, request, *args, **kwargs):
        # 僅允許管理員人工修改狀態（例如補救資料）
        return super().partial_update(request, *args, **kwargs)
