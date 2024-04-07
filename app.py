from io import BytesIO
from flask import Flask, render_template, send_from_directory, url_for, redirect, session, request, Response, jsonify, flash
import bcrypt
import database as dbase
from routes import init_routes
db = dbase.dbConnection()
import base64
from bson import ObjectId
from flask import send_file
from bson import Binary
from logic import obtener_usuario_por_numero_social, obtener_historial_clinico, generar_captcha
app = Flask(__name__)
app.secret_key = 'M0i1Xc$GfPw3Yz@2SbQ9lKpA5rJhDtE7'
init_routes(app)
###############################################################


@app.route('/buscar_usuario', methods=['GET', 'POST'])
def buscar_usuario():
    if request.method == 'POST':
        numero_social = request.form['numero_social']

        # Buscar en la base de datos el usuario por número de seguro social
        usuario = obtener_usuario_por_numero_social(numero_social)

        if usuario:
            # Usuario encontrado, obtener su historial clínico
            historial_clinico = obtener_historial_clinico(usuario['_id'])
            return render_template('admin.html', usuario=usuario, historial_clinico=historial_clinico)
        else:
            flash('No se encontró información para el número de seguro social proporcionado.')

    # Si es GET o si no se encontró el usuario, mostrar el formulario de búsqueda
    return redirect(url_for('admin'))



@app.route('/descargar_documento/<string:usuario_id>')
def descargar_documento(usuario_id):
    # Buscar el historial clínico por su _id en la base de datos
    historial_clinico = db['historial_clinico'].find_one({'_id': ObjectId(usuario_id)})

    # Verificar si el historial clínico y los resultados de laboratorio existen
    if historial_clinico and 'examenes_pruebas_medicas' in historial_clinico and \
            'resultados_laboratorio' in historial_clinico['examenes_pruebas_medicas']:

        # Obtener el primer resultado de laboratorio que tenga un documento adjunto
        for resultado in historial_clinico['examenes_pruebas_medicas']['resultados_laboratorio']:
            if resultado.get('documento'):
                # Obtener el contenido binario del documento
                documento_bin = resultado['documento']
                # Crear un objeto BytesIO para almacenar el contenido binario
                documento_stream = BytesIO(documento_bin)
                # Enviar el contenido binario como un archivo adjunto
                documento_stream.seek(0)  # Asegurar que la posición del cursor esté al inicio del archivo
                return send_file(documento_stream, mimetype='application/pdf', as_attachment=True, download_name='documento.pdf')

        # Si no se encontró ningún documento adjunto en los resultados de laboratorio
        flash('Documento no encontrado')
    else:
        flash('Historial clínico o resultado de laboratorio no encontrado')

    # Redirigir a la página principal si hay un error o el documento no está disponible
    return redirect(url_for('mi_historial'))



@app.route('/descargar_imagen/<string:usuario_id>')
def descargar_imagen(usuario_id):
    # Buscar el historial clínico por su _id en la base de datos
    historial_clinico = db['historial_clinico'].find_one({'_id': ObjectId(usuario_id)})

    # Verificar si el historial clínico y las imagenes medicas existen
    if historial_clinico and 'examenes_pruebas_medicas' in historial_clinico and \
            'imagenes_medicas' in historial_clinico['examenes_pruebas_medicas']:

        # Obtener la primera imagen medica que tenga un documento adjunto
        for resultado in historial_clinico['examenes_pruebas_medicas']['imagenes_medicas']:
            if resultado.get('imagen'):
                # Decodificar los datos base64 de la imagen a binario
                imagen_base64 = resultado['imagen']
                try:
                    imagen_bin = base64.b64decode(imagen_base64)
                except Exception as e:
                    flash('Error al decodificar la imagen')
                    return redirect(url_for('mi_historial'))

                # Crear un objeto BytesIO para almacenar el contenido binario
                imagen_stream = BytesIO(imagen_bin)
                # Enviar el contenido binario como un archivo adjunto
                imagen_stream.seek(0)  # Asegurar que la posición del cursor esté al inicio del archivo
                return send_file(imagen_stream, mimetype='image/jpeg', as_attachment=True, download_name='resultado.jpg')

        # Si no se encontró ningún documento adjunto en los resultados de laboratorio
        flash('Imagen no encontrada')
    else:
        flash('Historial clínico o imagenes medicas no encontrado')

    # Redirigir a la página principal si hay un error o la imagen no está disponible
    return redirect(url_for('mi_historial'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')
        captcha_ingresado = request.form.get('captcha')

        # Verificar CAPTCHA
        captcha_real = session.get('captcha')
        if not captcha_real or captcha_ingresado.upper() != captcha_real:
            flash('CAPTCHA incorrecto. Inténtalo de nuevo.')
            # Generar y mostrar nuevo CAPTCHA en el formulario
            captcha_text = generar_captcha()
            return render_template('login.html', captcha=captcha_text, message='CAPTCHA incorrecto. Inténtalo de nuevo.')


        paciente = db['pacientes']
        doctor = db['doctor']

        # Buscar en la colección de pacientes
        login_paciente = paciente.find_one({'correo': correo})
        if login_paciente and bcrypt.checkpw(password.encode('utf-8'), login_paciente['password']):
            # Autenticación exitosa
            session['correo'] = correo
            flash('Inicio de sesión exitoso como paciente.')
            return redirect(url_for('paciente'))
            

        # Buscar en la colección de doctores
        login_doctor = doctor.find_one({'correo': correo})
        if login_doctor and bcrypt.checkpw(password.encode('utf-8'), login_doctor['password']):
            # Autenticación exitosa
            session['correo'] = correo
            flash('Inicio de sesión exitoso como doctor.')
            return redirect(url_for('admin'))

        # Si no se encuentra en ninguna colección o la contraseña es incorrecta
        flash('Correo o contraseña incorrectos.', 'error')

    # Generar y mostrar CAPTCHA en el formulario de login
    captcha_data = generar_captcha()
    return render_template('login.html', captcha=captcha_data)


@app.route('/logout')
def logout():
    session.clear()  # Elimina todas las variables de sesión
    return redirect(url_for('index'))  # Redirige al inicio de sesión


@app.route('/register/', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        correo = request.form['correo']
        existing_paciente = db['pacientes'].find_one({'correo': correo})

        if existing_paciente is None:
            hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            paciente_data = {
                'nombre': request.form['nombre'],
                'numeroSocial': request.form['numeroSocial'],
                'correo': correo,
                'fecha_nacimiento': request.form['fecha'],
                'telefono': request.form['telefono'],
                'genero': request.form['genero'],
                'estado': request.form['estado'],
                'municipio': request.form['municipio'],
                'ciudad': request.form['ciudad'],
                'cp': request.form['cp'],
                'password': hashpass
            }

            paciente_id = db['pacientes'].insert_one(paciente_data).inserted_id

            historial_clinico_data = {
                "tipo": "historial_clinico",
                "usuario_id": paciente_id,
                "antecedentes_medicos": {},
                "medicaciones": {},
                "examenes_pruebas_medicas": {},
                "registro_consultas_medicas": [],
                "registro_vacunas": [],
                "estilo_vida": {},
                "contacto_emergencia": {}
            }

            db['historial_clinico'].insert_one(historial_clinico_data)

            session['correo'] = correo
            flash('Usuario registrado exitosamente')
            return redirect(url_for('login'))
        else:
            flash('El correo ya está en uso')
            return redirect(url_for('register'))

    return render_template('registro.html')

#######################################################
#GUARDAR DATOS
@app.route('/Añadir_medicaciones', methods=['POST'])
def Añadir_medicaciones():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')
        nombre = request.form['nombre_medicamento']
        dosis = request.form['dosis']
        frecuencia = request.form['frecuencia']

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('index'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db['historial_clinico'].find_one({'_id': id_historial})

        # Verificar si el historial clínico existe en la base de datos
        if historial_clinico is not None:
            print("historial_clinico encontrado:")
            print(historial_clinico)  # Historial clínico obtenido de la base de datos

            # Verificar si el campo de medicaciones existe y es una lista
            if 'medicaciones' in historial_clinico and isinstance(historial_clinico['medicaciones'], list):
                # Obtener la lista actual de medicaciones
                lista_medicaciones = historial_clinico['medicaciones']
                
                # Agregar el nuevo medicamento a la lista
                lista_medicaciones.append({
                    'nombre_del_medicamento': nombre,
                    'dosis': dosis,
                    'frecuencia': frecuencia,
                })
                
                # Actualizar el campo 'medicaciones' con la lista actualizada
                db['historial_clinico'].update_one(
                    {'_id': id_historial},
                    {'$set': {'medicaciones': lista_medicaciones}}
                )
            else:
                # Si no existen medicaciones o no es una lista, crear el campo como una lista con el nuevo medicamento
                db['historial_clinico'].update_one(
                    {'_id': id_historial},
                    {'$set': {'medicaciones': [{
                        'nombre_del_medicamento': nombre,
                        'dosis': dosis,
                        'frecuencia': frecuencia,
                    }]}}
                )

            flash('Datos de medicaciones actualizados exitosamente')
            return redirect(url_for('paciente'))
        else:
            flash('Historial clínico no encontrado en la base de datos')
    else:
        flash('Usuario no ha iniciado sesión')
    
    return redirect(url_for('login'))
@app.route('/Añadir_consulta', methods=['POST'])
def Añadir_consulta():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')
        fecha = request.form['fecha_consulta']
        motivo = request.form['motivo']
        diagnostico = request.form['diagnostico']
        tratamiento = request.form['tratamiento']

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db['historial_clinico'].find_one({'_id': id_historial})

        # Obtener la lista actual de consultas médicas
        consultas_medicas = historial_clinico['registro_consultas_medicas']
                
        # Agregar la nueva consulta médica a la lista
        consultas_medicas.append({
            'fecha': fecha,
            'motivo': motivo,
           'diagnostico': diagnostico,
            'tratamiento': tratamiento,
        })
                
        # Actualizar el campo 'registro_consultas_medicas' con la lista actualizada
        db['historial_clinico'].update_one(
            {'_id': id_historial},
            {'$set': {'registro_consultas_medicas': consultas_medicas}}
        )
        flash('Registro de consulta médica actualizado exitosamente')
        return redirect(url_for('paciente'))
    else:
        flash('Usuario no ha iniciado sesión')

    return redirect(url_for('login'))



@app.route('/Añadir_resultado_laboratorio', methods=['POST'])
def Añadir_resultado_laboratorio():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')
        tipo_laboratorio = request.form['tipo_laboratorio']
        resultado_laboratorio = request.form['resultado_laboratorio']

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))
        
        # Obtener el archivo PDF
        documento_laboratorio = request.files['documento_laboratorio']
        
        # Verificar si se cargó un archivo y si es PDF o JPG
        if documento_laboratorio:
            if documento_laboratorio.filename.endswith('.pdf') or documento_laboratorio.filename.endswith('.jpg'):
                documento_laboratorio_data = documento_laboratorio.read()
                documento_laboratorio_bin = Binary(documento_laboratorio_data)
            else:
                flash('El archivo debe ser PDF o JPG')
                return redirect(url_for('paciente'))
        else:
            documento_laboratorio_bin = None
        
        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db['historial_clinico'].find_one({'_id': id_historial}) 

        # Verificar si ya existe una lista de resultados de laboratorio
        if 'resultados_laboratorio' in historial_clinico['examenes_pruebas_medicas']:
        # Agregar el nuevo resultado de laboratorio
            historial_clinico['examenes_pruebas_medicas']['resultados_laboratorio'].append({
                'tipo': tipo_laboratorio,
                'resultado': resultado_laboratorio,
                'documento': documento_laboratorio_bin  # Guardar el archivo como binario
            })
        else:
        # Crear la lista de resultados de laboratorio y agregar el primer resultado
            historial_clinico['examenes_pruebas_medicas']['resultados_laboratorio'] = [{
                'tipo': tipo_laboratorio,
                'resultado': resultado_laboratorio,
                'documento': documento_laboratorio_bin  # Guardar el archivo como binario
            }]

        print("historial_clinico actualizado:")
        print(historial_clinico)  # Mostrar historial clínico actualizado

        # Guardar el historial clínico actualizado en la base de datos
        result = db['historial_clinico'].update_one(
            {'_id': id_historial},
            {'$set': historial_clinico}
        )
        print("Resultado de db.save():")
        print(result)  # Resultado de db.save()

        flash('Resultado de laboratorio añadido exitosamente')
        return redirect(url_for('paciente'))
    else:
        flash('Usuario no ha iniciado sesión')
    
    return redirect(url_for('login'))


@app.route('/Añadir_imagenes_medicas', methods=['POST'])
def Añadir_imagenes_medicas():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')
        tipo_imagen = request.form['tipo_imagen']
        resultado_imagen = request.form['resultado_imagen']

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Obtener el archivo JPG
        imagen_medica = request.files['imagen_medica']

        # Verificar si se cargó un archivo y si es un JPG
        if imagen_medica and imagen_medica.filename.endswith('.jpg'):
            imagen_medica_data = imagen_medica.read()
            imagen_medica_bin = Binary(imagen_medica_data)
        else:
            flash('El archivo debe ser JPG')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db['historial_clinico'].find_one({'_id': id_historial})

        if historial_clinico:
            print("historial_clinico encontrado:")
            print(historial_clinico)  # Historial clínico obtenido de la base de datos

            # Verificar si el campo de exámenes y pruebas médicas existe
            historial_clinico.setdefault('examenes_pruebas_medicas', {}).setdefault('imagenes_medicas', [])

            # Agregar la nueva imagen médica
            historial_clinico['examenes_pruebas_medicas']['imagenes_medicas'].append({
                'tipo': tipo_imagen,
                'resultado': resultado_imagen,
                'imagen': imagen_medica_bin  # Guardar el archivo como binario
            })

            print("historial_clinico actualizado:")
            print(historial_clinico)  # Mostrar historial clínico actualizado

            # Guardar el historial clínico actualizado en la base de datos
            result = db['historial_clinico'].update_one(
                {'_id': id_historial},
                {'$set': historial_clinico}
            )
            print("Resultado de db.save():")
            print(result)  # Resultado de db.save()

            flash('Imagen médica añadida exitosamente')
        else:
            flash('Historial clínico no encontrado en la base de datos')
    else:
        flash('Usuario no ha iniciado sesión')

    return redirect(url_for('mi_historial'))



@app.route('/Añadir_vacuna', methods=['POST'])
def Añadir_vacuna():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')     
        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db['historial_clinico'].find_one({'_id': id_historial})
   
        # Obtener la lista actual de consultas médicas
        registro_vacunas = historial_clinico['registro_vacunas']
                
        # Agregar la nueva registro_vacunas a la lista
        registro_vacunas.append({
            'nombre_vacuna' : request.form['nombre_vacuna'],
            'fecha_administracion' : request.form['fecha_administracion'],
            'fecha_primer_refuerzo' : request.form['fecha_primer_refuerzo'],
            'fecha_segundo_refuerzo' : request.form['fecha_segundo_refuerzo'],
            'fecha_tercer_refuerzo' : request.form['fecha_tercer_refuerzo']
        })
                
        # Actualizar el campo 'registro_vacunas' con la lista actualizada
        db['historial_clinico'].update_one(
            {'_id': id_historial},
            {'$set': {'registro_vacunas': registro_vacunas}}
        )
        
        flash('Registro de vacunas actualizado exitosamente')
        return redirect(url_for('paciente'))
    else:
        flash('Usuario no ha iniciado sesión')

    return redirect(url_for('login'))


    
###############################################################
#Seccion de actualizar datos
@app.route('/Actualizar_datos', methods=['POST'])
def Actualizar_datos():
    if 'correo' in session:
        id_usuario = request.form.get('id_usuario')
        telefono = request.form['N_telefono']
        correo = request.form['N_correo']
        estado = request.form['N_estado']
        ciudad = request.form['N_ciudad']
        municipio = request.form['N_municipio']
        cp = request.form['N_cp']
        
        # Verificar si el usuario existe en la base de datos
        usuario = db['pacientes'].find_one({'_id': ObjectId(id_usuario)})
        
        if usuario:
            # Actualizar los campos del usuario con los nuevos valores
            db['pacientes'].update_one(
                {'_id': ObjectId(id_usuario)},
                {
                    '$set': {
                        'telefono': telefono,
                        'correo': correo,
                        'estado': estado,
                        'municipio': municipio,
                        'ciudad': ciudad,
                        'cp': cp
                    }
                }
            )

            flash('Datos actualizados exitosamente')
        else:
            flash('Usuario no encontrado en la base de datos')
    else:
        flash('Usuario no ha iniciado sesión')
    
    return redirect(url_for('paciente'))

@app.route('/Actualizar_antecedentes', methods=['POST'])
def Actualizar_antecedentes():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')
        enfermedadesCronicas = request.form['N_enfermedad_cronica']
        alergias = request.form['N_alergia']
        cirugiasPrevias = request.form['N_cirugia_previa']
        traumatismosLesiones = request.form['N_traumatismo_lesion']

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db.get_collection('historial_clinico').find_one({'_id': id_historial})
        
        # Actualizar los campos de antecedentes médicos con los nuevos valores
        historial_clinico['antecedentes_medicos']['enfermedades_cronicas'] = enfermedadesCronicas
        historial_clinico['antecedentes_medicos']['alergias'] = alergias
        historial_clinico['antecedentes_medicos']['cirugias_previas'] = cirugiasPrevias
        historial_clinico['antecedentes_medicos']['traumatismos_o_lesiones'] = traumatismosLesiones

        # Guardar el historial clínico actualizado en la base de datos
        result = db.get_collection('historial_clinico').update_one(
            {'_id': id_historial},
            {'$set': historial_clinico}
        )
        print("Resultado de db.save():")
        print(result)  # Resultado de db.save()

        flash('Datos de antecedentes médicos actualizados exitosamente')
    else:
        flash('Usuario no ha iniciado sesión')
    
    return redirect(url_for('paciente'))


@app.route('/Estilo_vida', methods=['POST'])
def Estilo_vida():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db.get_collection('historial_clinico').find_one({'_id': id_historial})

        # Actualizar los campos de antecedentes médicos con los nuevos valores
        historial_clinico['estilo_vida']['hace_ejercicio'] = request.form['ejercicio']
        historial_clinico['estilo_vida']['frecuencia_hace_ejercicio'] = request.form['frecuencia_ejercicio']
        historial_clinico['estilo_vida']['consumo_alcohol'] = request.form['alcohol']
        historial_clinico['estilo_vida']['frecuencia_consumo_alcohol'] = request.form['frecuencia_alcohol']
        historial_clinico['estilo_vida']['consumo_tabaco'] = request.form['tabaco']
        historial_clinico['estilo_vida']['frecuencia_consumo_tabaco'] = request.form['frecuencia_tabaco']
        historial_clinico['estilo_vida']['nivel_estres'] = request.form['nivel_estres']

        print("historial_clinico actualizado:")
        print(historial_clinico)  # Mostrar historial clínico actualizado

            # Guardar el historial clínico actualizado en la base de datos
        result = db.get_collection('historial_clinico').update_one(
            {'_id': id_historial},
            {'$set': historial_clinico}
        )
        print("Resultado de db.save():")
        print(result)  # Resultado de db.save()
        flash('Datos de antecedentes médicos actualizados exitosamente')
    else:
        flash('Usuario no ha iniciado sesión')
    
    return redirect(url_for('paciente'))


@app.route('/Contacto_emergencia', methods=['POST'])
def Contacto_emergencia():
    if 'correo' in session:
        id_historial = request.form.get('id_historial')

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db.get_collection('historial_clinico').find_one({'_id': id_historial})
        # Verificar si el campo de antecedentes médicos existe
        if 'contacto_emergencia' in historial_clinico:
            # Actualizar los campos de antecedentes médicos con los nuevos valores
            historial_clinico['contacto_emergencia']['nombre_contacto'] = request.form['nombre_contacto']
            historial_clinico['contacto_emergencia']['telefono_contacto'] = request.form['telefono_contacto']
            historial_clinico['contacto_emergencia']['relacion_con_paciente'] = request.form['relacion_contacto']
        else:
            print("Contacto de emergencia no guardado")

        print("historial_clinico actualizado:")
        print(historial_clinico)  # Mostrar historial clínico actualizado

            # Guardar el historial clínico actualizado en la base de datos
        result = db.get_collection('historial_clinico').update_one(
            {'_id': id_historial},
            {'$set': historial_clinico}
        )
        print("Resultado de db.save():")
        print(result)  # Resultado de db.save()
        flash('Datos de antecedentes médicos actualizados exitosamente')
    else:
        flash('Usuario no ha iniciado sesión')
    
    return redirect(url_for('paciente'))  


###############################################################
#ELIMINAR
@app.route('/eliminar_resultado_laboratorio/<id_historial>', methods=['POST'])
def eliminar_resultado_laboratorio(id_historial):
    if 'correo' in session:
        indice = int(request.form.get('indice'))

        try:
            # Convertir id_historial a ObjectId
            id_historial = ObjectId(id_historial)
        except Exception as e:
            flash('Error al convertir el ID del historial clínico')
            return redirect(url_for('paciente'))

        # Buscar el historial clínico por su _id en la base de datos
        historial_clinico = db.get_collection('historial_clinico').find_one({'_id': id_historial})

        if historial_clinico:
            if 'examenes_pruebas_medicas' in historial_clinico and 'resultados_laboratorio' in historial_clinico['examenes_pruebas_medicas']:
                # Verificar si el índice está dentro de los límites de la lista
                if 0 <= indice < len(historial_clinico['examenes_pruebas_medicas']['resultados_laboratorio']):
                    # Eliminar el resultado de laboratorio en el índice especificado
                    historial_clinico['examenes_pruebas_medicas']['resultados_laboratorio'].pop(indice)

                    # Actualizar el historial clínico en la base de datos
                    result = db.get_collection('historial_clinico').update_one(
                        {'_id': id_historial},
                        {'$set': historial_clinico}
                    )
                    flash('Resultado de laboratorio eliminado exitosamente')
                else:
                    flash('Índice de resultado de laboratorio fuera de rango')
            else:
                flash('No hay resultados de laboratorio para eliminar')
        else:
            flash('Historial clínico no encontrado en la base de datos')
    else:
        flash('Usuario no ha iniciado sesión')

    return redirect(url_for('mi_historial'))


###############################################################
# Ruta para servir el archivo de validación estático
@app.route('/.well-known/pki-validation/58DD21D62A51640B766FA352B2819601.txt')
def serve_validation_file():
    return send_from_directory('static', '58DD21D62A51640B766FA352B2819601.txt')



if __name__ == "__main__":
    app.run(debug=True)
