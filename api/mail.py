from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import ssl
import re

MAILTM_API = "https://api.mail.tm"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/api/domains':
                self.handle_get_domains()
            elif self.path == '/api/messages':
                self.handle_get_messages()
            elif re.match(r'^/api/message/', self.path):
                message_id = self.path.replace('/api/message/', '')
                self.handle_get_message(message_id)
            else:
                self.send_json_response({"error": "Route non trouvée"}, 404)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def do_POST(self):
        try:
            if self.path == '/api/accounts':
                self.handle_create_account()
            elif self.path == '/api/token':
                self.handle_get_token()
            else:
                self.send_json_response({"error": "Route non trouvée"}, 404)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def forward_request(self, method, path, data=None, headers=None):
        url = f"{MAILTM_API}{path}"
        
        req_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'TempMail-App/1.0'
        }
        
        if headers:
            req_headers.update(headers)
        
        request = urllib.request.Request(url, method=method, headers=req_headers)
        
        if data:
            request.data = json.dumps(data).encode('utf-8')
        
        context = ssl._create_unverified_context()
        
        try:
            with urllib.request.urlopen(request, context=context) as response:
                response_data = response.read()
                if response_data:
                    return json.loads(response_data), response.getcode()
                return {}, response.getcode()
        except urllib.error.HTTPError as e:
            error_data = e.read()
            if error_data:
                return json.loads(error_data), e.code
            return {"error": str(e)}, e.code
        except Exception as e:
            return {"error": str(e)}, 500

    def handle_get_domains(self):
        data, status = self.forward_request('GET', '/domains')
        
        if status == 200 and isinstance(data, list):
            domains = [d['domain'] for d in data if d.get('domain')]
            self.send_json_response(domains, status)
        else:
            # Domaines de secours si l'API est down
            fallback = ["mail.tm", "cliptik.net", "viperace.com"]
            self.send_json_response(fallback, 200)

    def handle_create_account(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            response_data, status = self.forward_request('POST', '/accounts', data)
            self.send_json_response(response_data, status)
        except:
            self.send_json_response({"error": "Données invalides"}, 400)

    def handle_get_token(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            response_data, status = self.forward_request('POST', '/token', data)
            self.send_json_response(response_data, status)
        except:
            self.send_json_response({"error": "Données invalides"}, 400)

    def handle_get_messages(self):
        auth_header = self.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_json_response({"error": "Token manquant"}, 401)
            return
        
        token = auth_header.replace('Bearer ', '')
        headers = {'Authorization': f'Bearer {token}'}
        
        response_data, status = self.forward_request('GET', '/messages', headers=headers)
        self.send_json_response(response_data, status)

    def handle_get_message(self, message_id):
        auth_header = self.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_json_response({"error": "Token manquant"}, 401)
            return
        
        token = auth_header.replace('Bearer ', '')
        headers = {'Authorization': f'Bearer {token}'}
        
        response_data, status = self.forward_request('GET', f'/messages/{message_id}', headers=headers)
        self.send_json_response(response_data, status)
