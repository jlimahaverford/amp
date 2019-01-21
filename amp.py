from app import app, db
from app.models import User, TwitterUser, Tweet, Amp

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'TwitterUser': TwitterUser, 
        'Tweet': Tweet,
        'Amp': Amp}

