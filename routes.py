from flask import Flask, render_template, url_for, redirect, session, request, Response, jsonify, flash
import database as dbase
from logic import obtener_usuario, obtener_doctor, obtener_historial_clinico

db = dbase.dbConnection()
def init_routes(app):
#REDIRECCIONES
    
    @app.route('/registro/')
    def registro():
    
     return render_template('registro.html')

    @app.route('/')
    def index():
     return render_template('inicio.html')

    @app.route('/paciente')
    def paciente():
        correo = session.get('correo')
        if correo:
            usuario = obtener_usuario(correo)
            if usuario:
                historial_clinico = obtener_historial_clinico(usuario['_id'])
                return render_template('usuario.html', usuario=usuario, historial_clinico=historial_clinico)
        return redirect(url_for('login'))

    @app.route('/admin')
    def admin():
        correo = session.get('correo')
        if correo:
            usuario = obtener_doctor(correo)
            if usuario:
                return render_template('admin.html')
        return redirect(url_for('login'))

    @app.route('/mi_historial/')
    def mi_historial():
        if 'correo' in session:
            correo = session['correo']
            usuario = obtener_usuario(correo)
            if usuario:
                historial_clinico = obtener_historial_clinico(usuario['_id'])
                return render_template('mi_historial.html', usuario=usuario, historial_clinico=historial_clinico)
            else:
                print("Historial no encontrado")
        return redirect(url_for('login'))

    @app.errorhandler(404)
    def notFound(error=None):
        message = {
            'message': 'No encontrado ' + request.url,
            'status': '404 Not Found'
        }
        response = jsonify(message)
        response.status_code = 404
        return response