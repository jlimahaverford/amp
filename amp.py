from app import create_app, db
from app.models import User, TwitterUser, Tweet, Amp


app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'TwitterUser': TwitterUser, 
        'Tweet': Tweet,
        'Amp': Amp}
