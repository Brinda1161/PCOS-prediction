import pytest
import importlib.util
import os

# Load app.py directly to avoid conflict with the app/ package directory
_spec = importlib.util.spec_from_file_location(
    "app_main",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
init_db = _module.init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = 'test_database.db'
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
    
    # Cleanup
    if os.path.exists('test_database.db'):
        os.remove('test_database.db')

def test_home_page(client):
    """Test that the home page loads."""
    rv = client.get('/')
    assert rv.status_code in [200, 302]

def test_login_page(client):
    """Test that the login page loads."""
    rv = client.get('/login')
    assert rv.status_code == 200

def test_register_page(client):
    """Test that the register page loads."""
    rv = client.get('/register')
    assert rv.status_code == 200

def test_blog_page(client):
    """Test that the blog page loads."""
    rv = client.get('/blog')
    assert rv.status_code == 200
