"""UTP MCP Server — API Clients for Portal (GraphQL) and Class (REST)."""

import os
import time

import httpx

from .auth import AuthManager


# ─── Constants ───────────────────────────────────────────────────────────────
PORTAL_GRAPHQL = "https://api-portal.utpxpedition.com/graphql"
CLASS_API = "https://api-pao.utpxpedition.com"

DAYS_MAP = {"1": "Lunes", "2": "Martes", "3": "Miércoles", "4": "Jueves", "5": "Viernes", "6": "Sábado", "7": "Domingo"}


class PortalClient:
    """Client for UTP Portal GraphQL API (grades, periods, schedule, courses)."""

    def __init__(self, auth: AuthManager):
        self._auth = auth
        self._http = httpx.Client(timeout=20)
        self._user_id = os.getenv("UTP_USERNAME", "").lower()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._auth.get_token('portal')}",
            "Content-Type": "application/json",
            "applicationid": "APP00002",
            "user-id": self._user_id,
            "user-role": "student",
            "Origin": "https://portal.utp.edu.pe",
            "Referer": "https://portal.utp.edu.pe/",
        }

    def _query(self, gql: str, variables: dict | None = None) -> dict:
        body: dict = {"query": gql}
        if variables:
            body["variables"] = variables
        resp = self._http.post(PORTAL_GRAPHQL, json=body, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise Exception(f"GraphQL error: {data['errors'][0]['message']}")
        return data.get("data", {})

    # ─── Periods ─────────────────────────────────────────────────────────────

    def get_periods(self) -> list:
        """All academic periods with id and name."""
        return self._query("{ getPeriodsByStudent { id name } }").get("getPeriodsByStudent", [])

    # ─── Course Summary (courses + schedule + evaluations) ───────────────────

    def get_course_summary(self, period_id: str) -> dict:
        """Get full course summary for a period: courses, schedule, evaluations."""
        q = """
        query GetCourseSummary($periodId: String!) {
            getCourseSummary(periodId: $periodId) {
                summary {
                    enrolledCourses
                    campus
                    average
                    weeklyHours
                    meritOrder
                }
                courses {
                    courseId
                    title
                    teacher
                    weeklyHours
                    average
                    courseMode
                    credits
                    section
                    schedule { day startDate endDate }
                    evaluations { name value shortName }
                }
            }
        }
        """
        data = self._query(q, {"periodId": period_id}).get("getCourseSummary", {})

        # Enrich schedule with day names
        for course in data.get("courses", []):
            for sched in course.get("schedule", []):
                sched["dayName"] = DAYS_MAP.get(sched.get("day"), sched.get("day"))

        return data

    # ─── Grade Record (historical) ──────────────────────────────────────────

    def get_grade_record(self) -> list:
        """Get full historical grade record across all periods."""
        q = """
        {
            getCoursesGradeRecord {
                name
                items {
                    cycle
                    courseName
                    grade
                    credits
                    approvalStatus
                }
            }
        }
        """
        return self._query(q).get("getCoursesGradeRecord", [])

    # ─── Schedule by Date ────────────────────────────────────────────────────

    def get_schedule_by_date(self, timestamp_ms: float | None = None, periods: list[str] | None = None) -> dict:
        """Get weekly schedule for a given date (epoch ms)."""
        if timestamp_ms is None:
            timestamp_ms = float(int(time.time() * 1000))
        if periods is None:
            periods = []

        q = """
        query GetSchedules($date: Float!, $periods: [String!]) {
            scheduleByDate(
                filters: {
                    date: $date
                    classTypes: [1, 2, 3, 4, 5, 6]
                    periods: $periods
                }
            ) {
                dates {
                    date
                    items {
                        name
                        startTime
                        endTime
                        modality { id name }
                        class { id classType }
                    }
                }
            }
        }
        """
        return self._query(q, {"date": timestamp_ms, "periods": periods}).get("scheduleByDate", {})

    # ─── Payments ────────────────────────────────────────────────────────────

    def get_pending_payments(self) -> list:
        """Get pending payments and debts."""
        q = """
        {
            pendingPayments {
                items {
                    amount
                    amountToPay
                    dueDate
                    name
                    status
                }
            }
        }
        """
        data = self._query(q).get("pendingPayments", {})
        return data.get("items", [])

    def get_payment_history(self, period: str) -> list:
        """Get history of paid payments for a given period."""
        q = """
        query GetPaidPayments($period: String!) {
            paidPayments(period: $period) {
                items {
                    amount
                    name
                    status
                }
            }
        }
        """
        data = self._query(q, {"period": period}).get("paidPayments", {})
        return data.get("items", [])

    # ─── Procedures & Academic Plan ──────────────────────────────────────────

    def get_procedures(self) -> list:
        """Get requested procedures and their status."""
        q = """
        {
            procedures {
                requests {
                    name
                    status {
                        name
                        description
                    }
                    createdDate
                }
            }
        }
        """
        data = self._query(q).get("procedures", {})
        return data.get("requests", [])

    def close(self):
        self._http.close()


class ClassClient:
    """Client for UTP Class REST API (courses, assignments, messages, calendar)."""

    def __init__(self, auth: AuthManager):
        self._auth = auth
        self._http = httpx.Client(timeout=20, base_url=CLASS_API)
        self._uuid = os.getenv("CLASS_USER_UUID", "")
        self._tenant = os.getenv("CLASS_TENANT_ID", "")

    def _headers(self) -> dict:
        h = {
            "Authorization": f"Bearer {self._auth.get_token('class')}",
            "Content-Type": "application/json",
            "User-Id": self._uuid,
            "User-Role": "STUDENT",
            "Origin": "https://class.utp.edu.pe",
            "Referer": "https://class.utp.edu.pe/",
        }
        if self._tenant:
            h["X-Tenant-Id"] = self._tenant
        return h

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self._http.get(path, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: dict) -> dict:
        resp = self._http.post(path, headers=self._headers(), json=json_data)
        resp.raise_for_status()
        return resp.json()

    # ─── Courses ─────────────────────────────────────────────────────────────
    def get_dashboard_courses(self) -> list:
        data = self._get(f"/learning/student/{self._uuid}/dashboard-courses")
        return data.get("data", [])

    # ─── Assignments / Activities ────────────────────────────────────────────
    def get_pending_activities(self) -> list:
        data = self._get("/course/student/activities/pending/resume")
        return data.get("data", [])

    def get_course_content(self, course_id: str, section_id: str) -> dict:
        try:
            data = self._get(f"/course/student/courses/{course_id}/sections/{section_id}/full")
            return data.get("data", {})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise e

    def get_activity_detail(self, section_id: str, activity_id: str) -> dict:
        data = self._get(f"/learning/student/section/{section_id}/activity/{activity_id}")
        return data.get("data", {})

    # ─── Messages ────────────────────────────────────────────────────────────
    def get_messages(self, page: int = 1, filter_type: str = "all") -> list:
        data = self._get(
            f"/communication/student/message/from/{self._uuid}",
            params={"page": page, "filter": filter_type},
        )
        return data.get("data", [])

    def get_conversation(self, conversation_id: str, page: int = 1) -> list:
        data = self._get(
            f"/communication/student/message/{conversation_id}",
            params={"page": page},
        )
        return data.get("data", [])

    def send_message(self, to_user_id: str, message: str, section_id: str) -> dict:
        return self._post(
            "/communication/student/message/send",
            {
                "userIdFrom": self._uuid,
                "userIdTo": to_user_id,
                "message": message,
                "sectionId": section_id,
            },
        )

    def close(self):
        self._http.close()
