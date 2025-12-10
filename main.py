#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

UPSTREAM = "https://127.0.0.1:2999"  # LoL liveclientdata
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8081


class ProxyHandler(BaseHTTPRequestHandler):
	def _set_cors_headers(self):
		# CORS: ты просил именно "*"
		self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		self.send_header("Access-Control-Allow-Headers", "*")

	def do_OPTIONS(self):
		self.send_response(204)
		self._set_cors_headers()
		self.end_headers()

	def _proxy(self):
		url = UPSTREAM + self.path

		# тело запроса (если есть)
		length = int(self.headers.get("Content-Length", 0))
		body = self.rfile.read(length) if length > 0 else None

		# прокидываем заголовки
		headers = {k: v for k, v in self.headers.items()}
		headers["Host"] = "127.0.0.1:2999"
		# убираем сжатие, чтобы не ловить ошибки декодирования
		headers.pop("Accept-Encoding", None)

		try:
			resp = requests.request(
				self.command,
				url,
				headers=headers,
				data=body,
				verify=False,                     # левый сертификат LoL клиента
				proxies={"http": None, "https": None},
				timeout=5,
			)

			self.send_response(resp.status_code)

			for k, v in resp.headers.items():
				lk = k.lower()
				# эти заголовки не пробрасываем
				if lk in (
					"content-length",
					"connection",
					"keep-alive",
					"transfer-encoding",
					"content-encoding",   # важное: выкидываем, чтобы не было ошибок с компрессией
				):
					continue

				if lk.startswith("access-control-"):
					continue

				self.send_header(k, v)

			# свои CORS-заголовки
			self._set_cors_headers()

			self.end_headers()
			self.wfile.write(resp.content)

		except Exception as e:
			err = f"Proxy error: {e}"
			self.send_response(502)
			self.send_header("Content-Type", "application/json")
			self._set_cors_headers()
			self.end_headers()
			self.wfile.write(('{ "error": "%s" }' % err).encode("utf-8"))

	def do_GET(self):
		self._proxy()

	def do_POST(self):
		self._proxy()

	def do_PUT(self):
		self._proxy()

	def do_DELETE(self):
		self._proxy()


if __name__ == "__main__":
	httpd = HTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
	print(f"Proxy listening on http://{LISTEN_HOST}:{LISTEN_PORT} -> {UPSTREAM}")
	httpd.serve_forever()
