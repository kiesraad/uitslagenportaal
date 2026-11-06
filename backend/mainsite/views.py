from django.conf import settings
from django.db import Error, connection
from django.http import HttpResponseRedirect, JsonResponse


class HttpResponseMailtoRedirect(HttpResponseRedirect):
    allowed_schemes = ["mailto"]


def healthz(request):
    """
    Readiness probe for the backend pods; checks the database only.

    Redis and object storage are left out: failing here pulls the pod from the Service,
    which is too drastic for an outage most pages survive. The query is needed because
    persistent connections (CONN_MAX_AGE) would otherwise hide a lost database.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    # Not DatabaseError: a closed connection raises InterfaceError, which is not a subclass.
    except Error:
        return JsonResponse({"status": "unhealthy"}, status=503)

    return JsonResponse({"status": "ok"})


def report_technical_issue(request):
    """Redirect to the technical issue mailbox, keeping its address out of the page source."""
    return HttpResponseMailtoRedirect(f"mailto:{settings.TECHNICAL_ISSUE_EMAIL}")
