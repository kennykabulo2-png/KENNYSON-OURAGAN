from flask import render_template

def init_routes(app):
    @app.route('/')
    def index():
        return "<h1>OYEBI OK</h1>"
