"""Loopback-only synthetic SSE fixture. No model, GPU or reasoning ability."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != '/v1/completions':
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        # Reserved fixture input used only in integration tests.
        mode = body['prompt'] if isinstance(body['prompt'], str) else 'valid'
        if mode == 'http_error':
            self.send_error(503)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Connection', 'close')
        self.end_headers()
        def send(value):
            text = value if isinstance(value, str) else json.dumps(value)
            self.wfile.write(('data: ' + text + '\r\n\r\n').encode())
            self.wfile.flush()
        try:
            time.sleep(0.01)
            send({'choices': [{'index': 0, 'text': 'Final answer: ', 'finish_reason': None}]})
            time.sleep(0.01)
            send({'choices': [{'index': 0, 'text': '42', 'finish_reason': None}]})
            send({'choices': [{'index': 0, 'text': '', 'finish_reason': 'length'}]})
            if mode != 'missing_usage':
                send({'choices': [], 'usage': {'prompt_tokens': 3, 'completion_tokens': 3, 'total_tokens': 6}})
            if mode != 'missing_done':
                send('[DONE]')
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    print('MOCK ONLY: http://127.0.0.1:' + str(args.port), flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
