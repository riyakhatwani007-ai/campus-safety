"""Run:  python -m unittest tests.test_app -v      (uses a temporary database)"""
import os, sys, tempfile, unittest
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import app as campus


def client():
    return campus.app.test_client()


def register_login(c, email, name="Test Student", role="student"):
    c.post("/register", data={"name": name, "email": email, "phone": "9999999999", "password": "password123", "role": role})
    return c.post("/login", data={"email": email, "password": "password123"}, follow_redirects=False)


class CampusSafetyTests(unittest.TestCase):
    def test_01_login_required(self):
        r = client().get("/sos")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_02_register_login_and_bad_password(self):
        c = client()
        self.assertEqual(register_login(c, "a@x.com").status_code, 302)
        self.assertEqual(c.get("/sos").status_code, 200)
        bad = client().post("/login", data={"email": "a@x.com", "password": "wrong"})
        self.assertIn(b"Wrong email or password", bad.data)

    def test_03_cannot_self_register_as_security(self):
        c = client()
        register_login(c, "sneaky@x.com", role="security")
        self.assertEqual(c.get("/dashboard").status_code, 403)

    def test_04_sos_flow_with_location(self):
        c = client(); register_login(c, "b@x.com")
        r = c.post("/api/sos", json={"text": "my friend fainted and is not responding", "lat": 25.18, "lng": 75.83, "accuracy": 12})
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual((j["category"], j["severity"]), ("medical", "high"))
        page = c.get(j["url"])
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"CPR", page.data)                       # unresponsive first-aid shown
        self.assertEqual(c.post(f"/api/location/{j['id']}", json={"lat": 25.19, "lng": 75.84}).status_code, 200)
        self.assertEqual(c.get(j["url"] + "?as=fire").status_code, 200)   # switch category view

    def test_05_sos_without_location_and_empty_text(self):
        c = client(); register_login(c, "c@x.com")
        self.assertEqual(c.post("/api/sos", json={"text": "  "}).status_code, 400)
        self.assertEqual(c.post("/api/sos", json={"text": "hostel me aag lag gayi hai"}).status_code, 200)
        self.assertEqual(c.post("/api/sos", json={"text": "help", "lat": 999, "lng": 5}).status_code, 200)  # bad GPS ignored

    def test_06_privacy_between_students(self):
        a, b = client(), client()
        register_login(a, "d@x.com"); register_login(b, "e@x.com")
        iid = a.post("/api/sos", json={"text": "someone is following me"}).get_json()["id"]
        self.assertEqual(b.get(f"/incident/{iid}").status_code, 403)
        self.assertEqual(b.post(f"/api/location/{iid}", json={"lat": 1, "lng": 1}).status_code, 404)

    def test_07_security_dashboard_and_status(self):
        s = client()
        self.assertEqual(s.post("/login", data={"email": "security@campus.local", "password": "ChangeMe123"}).status_code, 302)
        self.assertEqual(s.get("/dashboard").status_code, 200)
        rows = s.get("/api/incidents").get_json()
        self.assertTrue(len(rows) >= 1)
        self.assertEqual(rows[0]["severity"], "high")          # high severity sorted first
        iid = rows[0]["id"]
        self.assertEqual(s.post(f"/api/incident/{iid}/status", json={"status": "responding"}).status_code, 200)
        self.assertEqual(s.post(f"/api/incident/{iid}/status", json={"status": "bogus"}).status_code, 400)
        self.assertEqual(s.get(f"/incident/{iid}").status_code, 200)       # security can view any incident
        self.assertIn(b"incident_report", s.get("/export.csv").headers["Content-Disposition"].encode())
        self.assertEqual(s.get("/api/incidents?severity=high&status=responding").status_code, 200)

    def test_08_student_cannot_use_security_api(self):
        c = client(); register_login(c, "f@x.com")
        self.assertEqual(c.get("/api/incidents").status_code, 403)
        self.assertEqual(c.post("/api/incident/1/status", json={"status": "resolved"}).status_code, 403)

    def test_09_triage_safety_rules(self):
        from models.triage import predict
        self.assertEqual(predict("he is unconscious")["severity"], "high")
        self.assertEqual(predict("i want to kill myself")["subtopic"], "mental_health")
        self.assertEqual(predict("kuch ho gaya help")["category"], "unknown")


if __name__ == "__main__":
    unittest.main()
