from django.db import Error, connection
from django.http import JsonResponse


def healthz(request):
    """
    Readiness for the backend pods. Liveness is a TCP check instead, because restarting
    a pod cannot mend a database that is down.

    Only the database is checked. Granian accepting a connection says nothing about
    whether a request can be served, and the database is the dependency without which
    none can be. Redis and object storage are deliberately left out: failing here
    withdraws the pod from the Service, so including them would pull the whole site out
    of rotation over an outage most pages would survive.

    The query is what makes this honest. Persistent connections are held for
    CONN_MAX_AGE, and merely asking for the connection object sends nothing over it, so
    a pod would keep reporting healthy for up to a minute after the database went away.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    # Error rather than DatabaseError: InterfaceError sits beside DatabaseError rather
    # than beneath it, and it is what gets raised for a connection that has already been
    # closed — the state a dropped persistent connection leaves behind, which is the very
    # case this checks for.
    except Error:
        return JsonResponse({"status": "unhealthy"}, status=503)

    return JsonResponse({"status": "ok"})
