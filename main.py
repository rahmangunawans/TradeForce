import sys
import os
# Ensure current directory is in path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
