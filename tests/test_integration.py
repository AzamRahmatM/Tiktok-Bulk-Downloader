import subprocess
import threading
import http.server
import socketserver
import time
import shutil
from pathlib import Path
import sys
import os

def test_downloader_fetches_mock(tmp_path):
    # temporary copy the whole repo into tmp_path/project
    project_root = Path(__file__).parents[1]
    test_root = tmp_path / "project"
    shutil.copytree(project_root, test_root)

    #change cwd so both server and downloader see the project files
    os.chdir(test_root)

    # first start a simple HTTP server on port 8001
    port = 8001
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("localhost", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # give it a moment to spin up
    time.sleep(0.1)

    # 2) write the URL file pointing at our fixture
    url_file = test_root / "urls.txt"
    url_file.write_text(f"http://localhost:{port}/tests/fixture.html\n")

    # run the downloader CLI against tmp_path/out inside test_root
    out_dir = test_root / "out"
    cmd = [
        sys.executable, "src/download_tiktok_videos.py",
        "--url-file", str(url_file),
        "--download-dir", str(out_dir),
        "--batch-size", "1",
        "--concurrency", "1",
        "--min-delay", "0",
        "--max-delay", "0",
    ]
    subprocess.run(cmd, check=True)

    #need to asseert that our mock video got “downloaded”
    expected = out_dir / "fixture.html.mp4"
    assert expected.exists(), f"Expected {expected} to exist"

    # 5) tear down server
    httpd.shutdown()
    thread.join()