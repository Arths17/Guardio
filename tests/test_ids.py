import unittest
from backend.ids import score_packet, generate_alert


class TestIDS(unittest.TestCase):

    def test_score_packet(self):
        # Test with a benign packet
        benign_packet = {
            "source_ip": "192.168.1.50",
            "destination_ip": "10.0.0.1",
            "protocol": "HTTP",
            "payload": "GET /index.html HTTP/1.1",
        }
        score = score_packet(benign_packet)
        self.assertEqual(score, 0)

        # Test with a suspicious packet
        suspicious_packet = {
            "source_ip": "192.168.1.50",
            "destination_ip": "10.0.0.1",
            "protocol": "HTTP",
            "payload": "GET /admin HTTP/1.1",
        }
        score = score_packet(suspicious_packet)
        self.assertGreater(score, 0)

        # Test with a malicious packet
        malicious_packet = {
            "source_ip": "192.168.1.50",
            "destination_ip": "10.0.0.1",
            "protocol": "HTTP",
            "payload": "GET /etc/passwd HTTP/1.1",
        }
        score = score_packet(malicious_packet)
        self.assertGreater(score, 0)

    def test_generate_alert(self):
        # Test alert generation for a high score
        packet = {
            "source_ip": "192.168.1.50",
            "destination_ip": "10.0.0.1",
            "protocol": "HTTP",
            "payload": "GET /etc/passwd HTTP/1.1",
        }
        score = score_packet(packet)
        alert = generate_alert(packet, score)

        self.assertIn("alert_id", alert)
        self.assertIn("source_ip", alert)
        self.assertIn("destination_ip", alert)
        self.assertIn("protocol", alert)
        self.assertIn("payload", alert)
        self.assertIn("score", alert)
        self.assertIn("timestamp", alert)

        self.assertEqual(alert["source_ip"], packet["source_ip"])
        self.assertEqual(alert["destination_ip"], packet["destination_ip"])
        self.assertEqual(alert["protocol"], packet["protocol"])
        self.assertEqual(alert["payload"], packet["payload"])
        self.assertEqual(alert["score"], score)


if __name__ == "__main__":
    unittest.main()