from flask import Flask, render_template, request, send_file, jsonify, Response
from docs_scraper import DocsRsScraper
import os
import re
import queue
import threading
from datetime import datetime
import hashlib

app = Flask(__name__)
progress_queues = {}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/progress/<session_id>')
def progress(session_id):
    def generate():
        q = progress_queues.get(session_id)
        if not q:
            return
            
        try:
            while True:
                try:
                    message = q.get(timeout=30)
                    if message == "DONE":
                        yield f"data: {message}\n\n"
                        break
                    yield f"data: {message}\n\n"
                except queue.Empty:
                    yield f"data: ...\n\n"
                    
        except GeneratorExit:
            pass
        finally:
            progress_queues.pop(session_id, None)
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    crate_path = data.get('cratePath', '').strip('/')
    base_filename = data.get('filename', '').strip()
    session_id = data.get('sessionId')
    
    if not crate_path:
        return jsonify({'error': 'Crate path is required'}), 400
    
    if not re.match(r'^[\w-]+/(?:latest|[\d.]+(?:-[\w.]+)?)/[\w-]+/?$', crate_path):
        return jsonify({'error': 'Invalid crate path format. Expected format: name/version/name (e.g., wgpu/latest/wgpu)'}), 400
        
    if not base_filename:
        return jsonify({'error': 'Filename is required'}), 400
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = hashlib.md5(session_id.encode()).hexdigest()[:8]
    
    base_filename = base_filename.replace('.md', '')
    filename = f"{base_filename}_{timestamp}_{unique_id}.md"
    
    downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    
    output_path = os.path.join(downloads_dir, filename)
    full_url = f"https://docs.rs/{crate_path}"
    
    progress_queue = queue.Queue()
    progress_queues[session_id] = progress_queue
    
    try:
        def progress_callback(message):
            progress_queue.put(message)
        
        scraper = DocsRsScraper(full_url, progress_callback)
        
        def scrape_thread():
            try:
                if scraper.scrape():
                    progress_queue.put("Scraping completed successfully")
                    if scraper.save_to_file(output_path):
                        progress_queue.put("Documentation saved successfully")
                        progress_queue.put("DONE")
                    else:
                        progress_queue.put("ERROR: Failed to save documentation")
                        progress_queue.put("DONE")
                else:
                    progress_queue.put("ERROR: Scraping failed")
                    progress_queue.put("DONE")
            except Exception as e:
                progress_queue.put(f"ERROR: {str(e)}")
                progress_queue.put("DONE")
        
        threading.Thread(target=scrape_thread).start()
        
        return jsonify({
            'success': True,
            'message': 'Started scraping documentation',
            'sessionId': session_id,
            'filename': filename
        })
        
    except Exception as e:
        progress_queues.pop(session_id, None)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        file_path = os.path.join(downloads_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True) 