"""Admin routes: login, logout, and the visitors dashboard.

Login is a single password form (no usernames). On success the
session gets `admin=True`; the cookie is signed by SessionMiddleware.
The visitors page reads aggregations from the access_log table.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from pi.dashboard.security import (
    is_admin,
    require_admin,
    verify_password,
)

router = APIRouter()


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_form(request: Request) -> HTMLResponse:
    """Render the admin login form."""
    if is_admin(request):
        return RedirectResponse(url="/", status_code=303)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {"error": None},
    )


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(
    request: Request,
    password: str = Form(...),
) -> HTMLResponse:
    """Verify a submitted password; on success, set session and redirect."""
    security = getattr(request.app.state, "security_config", None)
    expected = security.admin_password_sha256 if security else ""

    if not expected:
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {"error": "Auth is not configured on this instance."},
            status_code=503,
        )

    if not verify_password(password, expected):
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {"error": "Incorrect password."},
            status_code=401,
        )

    request.session["admin"] = True
    return RedirectResponse(url="/", status_code=303)


@router.get("/admin/logout")
async def admin_logout(request: Request) -> RedirectResponse:
    """Clear the session and redirect home."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get(
    "/admin/visitors",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_visitors(request: Request) -> HTMLResponse:
    """Render aggregated access_log stats for the operator."""
    repo = request.app.state.repo
    now = datetime.now(timezone.utc)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = now - timedelta(days=7)

    today_iso = start_today.isoformat()
    week_iso = start_week.isoformat()

    total_today = await repo.access_count_since(today_iso)
    total_week = await repo.access_count_since(week_iso)
    distinct_ips_today = await repo.access_distinct_ips_since(today_iso)
    distinct_uas_today = await repo.access_distinct_uas_since(today_iso)
    top_paths = await repo.access_top_paths_since(today_iso, limit=10)
    recent = await repo.access_recent(limit=50)
    # 24-hour hourly bucket series for the traffic chart.
    chart_start = (now - timedelta(hours=24)).isoformat()
    hourly = await repo.access_hourly_buckets(chart_start, hours=24)

    # Peak hour today: bucket recent-today rows by hour of timestamp.
    hour_counts: Counter[int] = Counter()
    for row in recent:
        ts = row["timestamp"]
        if ts >= today_iso:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hour_counts[dt.hour] += 1
            except ValueError:
                continue
    peak_hour = (
        f"{hour_counts.most_common(1)[0][0]:02d}:00"
        if hour_counts
        else "—"
    )

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "admin_visitors.html",
        {
            "total_today": total_today,
            "total_week": total_week,
            "distinct_ips_today": distinct_ips_today,
            "distinct_uas_today": distinct_uas_today,
            "peak_hour": peak_hour,
            "top_paths": top_paths,
            "recent": recent,
            "hourly": hourly,
        },
    )
