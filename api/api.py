from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import ssl
import re

# Configuration
MAILTM_API = "https://api.mail.tm"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Gère les requêtes GET"""
        try:
            # Route: /api/domains
            if self.path == '/api/domains':
                self.handle_get_domains()
            
            # Route: /api/messages
            elif self.path == '/api/messages':
                self.handle_get_messages()
            
            # Route: /api/messages/{id}
            elif re.match(r'^/api/messages/[a-f0-9-]+$', self.path):
                message_id = self.path.split('/')[-1]
                self.handle_get_message(message_id)
            
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Route non trouvée"}).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_POST(self):
        """Gère les requêtes POST"""
        try:
            # Route: /api/accounts
            if self.path == '/api/accounts':
                self.handle_create_account()
            
            # Route: /api/token
            elif self.path == '/api/token':
                self.handle_get_token()
            
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Route non trouvée"}).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_OPTIONS(self):
        """Gère les requêtes OPTIONS (CORS)"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Ajoute les headers CORS nécessaires"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def send_json_response(self, data, status=200):
        """Envoie une réponse JSON avec les bons headers"""
        self.send_response(status)
        self.send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def forward_request(self, method, path, data=None, headers=None):
        """Fait une requête vers l'API mail.tm"""
        url = f"{MAILTM_API}{path}"
        
        req_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'TempMail-Proxy/1.0'
        }
        
        # Ajouter les headers personnalisés
        if headers:
            req_headers.update(headers)
        
        # Créer la requête
        request = urllib.request.Request(
            url,
            method=method,
            headers=req_headers
        )
        
        # Ajouter le body si présent
        if data:
            request.data = json.dumps(data).encode('utf-8')
        
        # Ignorer la vérification SSL (pour le développement)
        context = ssl._create_unverified_context()
        
        try:
            with urllib.request.urlopen(request, context=context) as response:
                response_data = response.read()
                if response_data:
                    return json.loads(response_data), response.getcode()
                return {}, response.getcode()
        except urllib.error.HTTPError as e:
            # Lire l'erreur si possible
            error_data = e.read()
            if error_data:
                return json.loads(error_data), e.code
            return {"error": str(e)}, e.code
        except Exception as e:
            return {"error": str(e)}, 500
    
    def handle_get_domains(self):
        """Récupère la liste des domaines disponibles"""
        data, status = self.forward_request('GET', '/domains')
        
        # Extraire juste les noms de domaines
        if status == 200 and isinstance(data, list):
            domains = [d['domain'] for d in data if d.get('domain')]
            self.send_json_response(domains, status)
        else:
            # Fallback en cas d'erreur
            fallback_domains = ["mail.tm", "cliptik.net", "viperace.com", "yopmail.com"]
            self.send_json_response(fallback_domains, 200)
    
    def handle_create_account(self):
        """Crée un nouveau compte email"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            response_data, status = self.forward_request('POST', '/accounts', data)
            self.send_json_response(response_data, status)
        except json.JSONDecodeError:
            self.send_json_response({"error": "Données JSON invalides"}, 400)
    
    def handle_get_token(self):
        """Obtient un token d'authentification"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            response_data, status = self.forward_request('POST', '/token', data)
            self.send_json_response(response_data, status)
        except json.JSONDecodeError:
            self.send_json_response({"error": "Données JSON invalides"}, 400)
    
    def handle_get_messages(self):
        """Récupère les messages de la boîte"""
        # Récupérer le token du header Authorization
        auth_header = self.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_json_response({"error": "Token manquant ou invalide"}, 401)
            return
        
        token = auth_header.replace('Bearer ', '')
        headers = {'Authorization': f'Bearer {token}'}
        
        response_data, status = self.forward_request('GET', '/messages', headers=headers)
        self.send_json_response(response_data, status)
    
    def handle_get_message(self, message_id):
        """Récupère un message spécifique"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_json_response({"error": "Token manquant ou invalide"}, 401)
            return
        
        token = auth_header.replace('Bearer ', '')
        headers = {'Authorization': f'Bearer {token}'}
        
        response_data, status = self.forward_request('GET', f'/messages/{message_id}', headers=headers)
        self.send_json_response(response_data, status)
