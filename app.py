from flask import Flask, render_template

from config import Config
from extensions import db, login_manager
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.main import main_bp
from routes.owner import owner_bp
from seed import seed_data


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        from datetime import datetime

        return {"current_year": datetime.utcnow().year}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    with app.app_context():
        db.create_all()
        seed_data()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
