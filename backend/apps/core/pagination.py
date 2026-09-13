"""
Standardized Pagination Classes for LifePilot REST API Endpoints.

Provides predictable paginated envelopes for listing models such as
ApprovalRequests, AuditLogs, AgentRuns, and Integrations.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for general list endpoints.

    Default page size: 20 items.
    Max page size: 100 items.
    Query params: ?page=1&page_size=20
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class HighVolumeAuditLogPagination(PageNumberPagination):
    """
    Optimized pagination class for dense/high-volume audit logs and execution traces.

    Default page size: 50 items.
    Max page size: 250 items.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 250

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class CompactMetricsPagination(PageNumberPagination):
    """
    Compact pagination class for dashboard widgets and quick feeds.

    Default page size: 5 items.
    Max page size: 20 items.
    """

    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )