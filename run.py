import importlib.util
import os

# Load app.py directly to avoid conflict with the app/ package directory
_spec = importlib.util.spec_from_file_location(
    "app_main",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
init_db = _module.init_db

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
