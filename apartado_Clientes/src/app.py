from flask import Flask, render_template, request, redirect, jsonify, url_for,session, flash, abort
import mysql.connector
from datetime import datetime, date
import hashlib
import secrets
from contextlib import closing
import os
from dotenv import load_dotenv
import logging
from datetime import time
import re
from mysql.connector import Error
from functools import wraps


###############################################################################
# Cargar variables de entorno
###############################################################################
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

###############################################################################
# Configuración de la base de datos (conexión a la base de datos)
###############################################################################
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME', 'clientes'),
    'pool_name': 'restaurante_pool',
    'pool_size': 5,
    'pool_reset_session': True
}

def get_db_connection():
    """Obtiene una conexión a la base de datos con manejo de errores"""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        app.logger.error(f"Database connection error: {err}")
        flash(f"Error de conexión a la base de datos: {err}", "error")
        raise


###############################################################################
# Inicio de la aplicación
###############################################################################

@app.route('/')
def index():
    # Permitir acceso sin login
    return redirect(url_for('pos'))


###############################################################################
#  verificar roles
###############################################################################
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user_role = session.get('user_role')
            if isinstance(allowed_roles, str):
                allowed_roles_list = [allowed_roles]
            else:
                allowed_roles_list = allowed_roles
                
            if user_role not in allowed_roles_list:
                flash('No tienes permisos para acceder a esta sección')
                return redirect(url_for('pos'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

###############################################################################
#  verificar si es dueño
###############################################################################
def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_role') != 'dueño':
            flash('Solo el dueño puede acceder a esta sección')
            return redirect(url_for('pos'))
        return f(*args, **kwargs)
    return decorated_function

###############################################################################
# verificar login 
###############################################################################

def login_optional(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # No requiere login, pero pasa información de si está logueado
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta función')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

###############################################################################
# función para formatear fechas
###############################################################################
@app.template_filter('datetime')
def datetime_filter(dt):
    return dt.strftime('%B %d, %Y %I:%M %p')


###############################################################################
# Agregar contexto global para templates
###############################################################################

@app.context_processor
def inject_now():
    return {
        'now': datetime.now(),
        'user_role': session.get('user_role', 'cliente'),
        'is_logged_in': 'user_id' in session,
        'user_name': session.get('user_name', 'Invitado')
    }

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_role(user_id):
    """Obtener el rol del usuario desde la base de datos"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.Nombre as rol_nombre 
            FROM Clientes c 
            JOIN Roles r ON c.Rol_ID = r.ID 
            WHERE c.ID = %s
        """, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result['rol_nombre'] if result else 'cliente'
    return 'cliente'

def validate_admin_code(codigo):
    """Validar código de administrador"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ca.*, r.Nombre as rol_nombre 
            FROM Codigos_Admin ca
            JOIN Roles r ON ca.Rol_ID = r.ID
            WHERE ca.Codigo = %s AND ca.Usado = FALSE
        """, (codigo,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result
    return None

def mark_admin_code_used(codigo, user_id):
    """Marcar código de administrador como usado"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE Codigos_Admin 
            SET Usado = TRUE, Fecha_Uso = NOW(), Usado_Por = %s 
            WHERE Codigo = %s
        """, (user_id, codigo))
        connection.commit()
        cursor.close()
        connection.close()



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.*, r.Nombre as rol_nombre 
                FROM Clientes c 
                JOIN Roles r ON c.Rol_ID = r.ID 
                WHERE c.Correo = %s AND c.Contrasena = %s
            """, (email, hash_password(password)))
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['ID']
                session['user_name'] = f"{user['Nombre']} {user['Apellido_P']}"
                session['user_role'] = user['rol_nombre']
                
                # Mensaje especial para el dueño
                if user['rol_nombre'] == 'dueño':
                    flash(f'¡Bienvenido de vuelta, {session["user_name"]}! (DUEÑO DEL RESTAURANTE)')
                else:
                    flash(f'Bienvenido, {session["user_name"]} ({session["user_role"]})')
                
                return redirect(url_for('pos'))
            else:
                flash('Credenciales inválidas')
            
            cursor.close()
            connection.close()
    else:
        # Si viene de otra página, limpiar la sesión automáticamente
        if 'user_id' in session:
            session.clear()
            flash('Sesión cerrada automáticamente')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        admin_code = data.get('admin_code', '').strip()
        
        # Determinar rol
        rol_id = 1  # Cliente por defecto
        
        # Si se proporciona código de admin, validarlo
        if admin_code:
            code_info = validate_admin_code(admin_code)
            if code_info:
                rol_id = code_info['Rol_ID']
            else:
                flash('Código de administrador inválido o ya usado')
                return render_template('register.html')
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                # Insertar usuario
                cursor.execute("""
                    INSERT INTO Clientes (Nombre, Apellido_P, Apellido_M, Correo, Contrasena, 
                                        Telefono, Fecha_Nacimiento, Genero, Rol_ID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    data['nombre'], data['apellido_p'], data.get('apellido_m', ''),
                    data['email'], hash_password(data['password']), data.get('telefono', ''),
                    data.get('fecha_nacimiento') or None, data.get('genero', 'Prefiero no decir'),
                    rol_id
                ))
                
                user_id = cursor.lastrowid
                connection.commit()
                
                # Si usó código de admin, marcarlo como usado
                if admin_code and code_info:
                    mark_admin_code_used(admin_code, user_id)
                
                role_name = 'administrador' if rol_id > 1 else 'cliente'
                flash(f'¡Registro exitoso como {role_name}! Por favor inicia sesión.')
                return redirect(url_for('login'))
                
            except Error as e:
                if "Duplicate entry" in str(e):
                    flash('Este correo electrónico ya está registrado')
                else:
                    flash(f'Error en el registro: {e}')
            finally:
                cursor.close()
                connection.close()
    
    return render_template('register.html')

@app.route('/placeholder.svg')
def placeholder():
    """Servir una imagen de placeholder cuando las imágenes reales no están disponibles"""
    height = request.args.get('height', 100)
    width = request.args.get('width', 100)
    query = request.args.get('query', 'Imagen')
    
    # Crear un SVG simple como placeholder
    svg = f'''
    <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#f8f9fa"/>
        <text x="50%" y="50%" font-family="Arial" font-size="14" fill="#6c757d" 
              text-anchor="middle" dominant-baseline="middle">
            {query}
        </text>
        <text x="50%" y="70%" font-family="Arial" font-size="12" fill="#6c757d" 
              text-anchor="middle" dominant-baseline="middle">
            (Sin imagen)
        </text>
    </svg>
    '''
    
    return svg, 200, {'Content-Type': 'image/svg+xml'}

@app.route('/pos')
@login_optional
def pos():
    connection = get_db_connection()
    menu_items = []
    categories = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get categories
        cursor.execute("SELECT * FROM Categorias_Menu WHERE Estatus = 'Activo'")
        categories = cursor.fetchall()
        
        # Get menu items with image URLs
        cursor.execute("""
            SELECT m.*, c.Nombre as Categoria_Nombre 
            FROM Menu m 
            JOIN Categorias_Menu c ON m.Categoria_ID = c.ID 
            WHERE m.Estatus = 'Disponible'
            ORDER BY c.Nombre, m.Nombre
        """)
        menu_items = cursor.fetchall()
        
        # Validar URLs de imágenes
        for item in menu_items:
            if item['Imagen_URL'] and not (item['Imagen_URL'].startswith('http://') or item['Imagen_URL'].startswith('https://')):
                # Si la URL no es válida, establecerla como None
                item['Imagen_URL'] = None
        
        cursor.close()
        connection.close()
    
    return render_template('pos.html', menu_items=menu_items, categories=categories)

###############################################################################
# RUTAS SOLO PARA DUEÑO
###############################################################################


@app.route('/owner/dashboard')
@owner_required
def owner_dashboard():
    connection = get_db_connection()
    stats = {}
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Estadísticas generales
        cursor.execute("SELECT COUNT(*) as total_clientes FROM Clientes WHERE Rol_ID = 1")
        stats['total_clientes'] = cursor.fetchone()['total_clientes']
        
        cursor.execute("SELECT COUNT(*) as total_pedidos FROM Pedidos")
        stats['total_pedidos'] = cursor.fetchone()['total_pedidos']
        
        cursor.execute("SELECT SUM(Total) as ingresos_totales FROM Pedidos WHERE Estatus = 'Entregado'")
        result = cursor.fetchone()
        stats['ingresos_totales'] = result['ingresos_totales'] or 0
        
        cursor.execute("SELECT COUNT(*) as total_admins FROM Clientes WHERE Rol_ID > 1")
        stats['total_admins'] = cursor.fetchone()['total_admins']
        
        cursor.close()
        connection.close()
    
    return render_template('owner/dashboard.html', stats=stats)

###############################################################################
# RUTAS PARA ADMINISTRADORES Y DUEÑO
###############################################################################

@app.route('/admin/menu')
@role_required(['admin', 'mesero', 'dueño'])
def menu_management():
    connection = get_db_connection()
    menu_items = []
    categories = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get categories
        cursor.execute("SELECT * FROM Categorias_Menu ORDER BY Nombre")
        categories = cursor.fetchall()
        
        # Get all menu items with image URLs
        cursor.execute("""
            SELECT m.*, c.Nombre as Categoria_Nombre 
            FROM Menu m 
            JOIN Categorias_Menu c ON m.Categoria_ID = c.ID 
            ORDER BY c.Nombre, m.Nombre
        """)
        menu_items = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('admin/menu.html', menu_items=menu_items, categories=categories)

@app.route('/admin/orders')
@role_required(['admin', 'mesero', 'cocinero', 'dueño'])
def admin_orders():
    connection = get_db_connection()
    orders = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get all orders for admin
        cursor.execute("""
            SELECT p.*, c.Nombre, c.Apellido_P, s.Nombre as Sucursal_Nombre
            FROM Pedidos p
            LEFT JOIN Clientes c ON p.Cliente_ID = c.ID
            LEFT JOIN Sucursales s ON p.Sucursal_ID = s.ID
            ORDER BY p.Fecha_Hora DESC
            LIMIT 100
        """)
        orders = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/tables')
@role_required(['admin', 'dueño'])
def admin_tables():
    connection = get_db_connection()
    mesas = []
    sucursales = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get tables
        cursor.execute("""
            SELECT m.*, s.Nombre as Sucursal_Nombre
            FROM Mesas m
            JOIN Sucursales s ON m.Sucursal_ID = s.ID
            ORDER BY s.Nombre, m.Numero_Mesa
        """)
        mesas = cursor.fetchall()
        
        # Get sucursales for adding new tables
        cursor.execute("SELECT * FROM Sucursales WHERE Estatus = 'Activa'")
        sucursales = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('admin/tables.html', mesas=mesas, sucursales=sucursales)

@app.route('/admin/settings')
@role_required(['admin', 'dueño'])
def admin_settings():
    connection = get_db_connection()
    user_data = {}
    sucursales = []
    clientes = []
    admin_codes = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get user data
        cursor.execute("SELECT * FROM Clientes WHERE ID = %s", (session['user_id'],))
        user_data = cursor.fetchone()
        
        # Get sucursales
        cursor.execute("SELECT * FROM Sucursales ORDER BY Nombre")
        sucursales = cursor.fetchall()
        
        # Get all clients for admin
        cursor.execute("""
            SELECT c.*, r.Nombre as rol_nombre 
            FROM Clientes c 
            JOIN Roles r ON c.Rol_ID = r.ID 
            ORDER BY c.Nombre, c.Apellido_P
        """)
        clientes = cursor.fetchall()
        
        # Get admin codes
        cursor.execute("""
            SELECT ca.*, r.Nombre as rol_nombre, 
                   c1.Nombre as creado_por_nombre,
                   c2.Nombre as usado_por_nombre
            FROM Codigos_Admin ca
            JOIN Roles r ON ca.Rol_ID = r.ID
            LEFT JOIN Clientes c1 ON ca.Creado_Por = c1.ID
            LEFT JOIN Clientes c2 ON ca.Usado_Por = c2.ID
            ORDER BY ca.Fecha_Creacion DESC
        """)
        admin_codes = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('admin/settings.html', 
                         user_data=user_data, 
                         sucursales=sucursales, 
                         clientes=clientes,
                         admin_codes=admin_codes)

###############################################################################
# RUTAS PARA CLIENTES
###############################################################################

@app.route('/orders')
@login_required
def client_orders():
    connection = get_db_connection()
    orders = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get only user's orders
        cursor.execute("""
            SELECT p.*, s.Nombre as Sucursal_Nombre
            FROM Pedidos p
            LEFT JOIN Sucursales s ON p.Sucursal_ID = s.ID
            WHERE p.Cliente_ID = %s
            ORDER BY p.Fecha_Hora DESC
            LIMIT 20
        """, (session['user_id'],))
        orders = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('client/orders.html', orders=orders)

@app.route('/payment')
@login_required
def payment():
    # Get current cart for payment
    cart = session.get('cart', [])
    if not cart:
        flash('No hay items en el carrito para procesar el pago')
        return redirect(url_for('pos'))
    
    total = sum(item['price'] * item['quantity'] for item in cart)
    tax = total * 0.10
    final_total = total + tax
    
    return render_template('payment.html', cart=cart, subtotal=total, tax=tax, total=final_total)

@app.route('/profile')
@login_required
def client_profile():
    connection = get_db_connection()
    user_data = {}
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get user data
        cursor.execute("""
            SELECT c.*, r.Nombre as rol_nombre 
            FROM Clientes c 
            JOIN Roles r ON c.Rol_ID = r.ID 
            WHERE c.ID = %s
        """, (session['user_id'],))
        user_data = cursor.fetchone()
        
        cursor.close()
        connection.close()
    
    return render_template('client/profile.html', user_data=user_data)

# API Routes 
@app.route('/api/add_to_order', methods=['POST'])
@login_required
def add_to_order():
    data = request.json
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    
    # Initialize cart in session if not exists
    if 'cart' not in session:
        session['cart'] = []
    
    # Check if item already in cart
    for item in session['cart']:
        if item['id'] == item_id:
            item['quantity'] += quantity
            session.modified = True
            return jsonify({'success': True})
    
    # Get item details from database
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Menu WHERE ID = %s", (item_id,))
        menu_item = cursor.fetchone()
        
        if menu_item:
            session['cart'].append({
                'id': item_id,
                'name': menu_item['Nombre'],
                'price': float(menu_item['Precio']),
                'quantity': quantity,
                'Imagen_URL': menu_item.get('Imagen_URL') # <--- ¡AQUÍ ESTÁ EL CAMBIO CLAVE!
            })
            session.modified = True
            
        cursor.close()
        connection.close()
    
    return jsonify({'success': True})

@app.route('/api/get_cart')
@login_required
def get_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    return jsonify({
        'cart': cart,
        'subtotal': total,
        'tax': total * 0.10,
        'total': total * 1.10
    })

@app.route('/api/update_cart_item', methods=['POST'])
@login_required
def update_cart_item():
    data = request.json
    item_id = data.get('item_id')
    quantity = data.get('quantity')
    
    if 'cart' in session:
        for item in session['cart']:
            if item['id'] == item_id:
                if quantity <= 0:
                    session['cart'].remove(item)
                else:
                    item['quantity'] = quantity
                session.modified = True
                break
    
    return jsonify({'success': True})

@app.route('/api/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session['cart'] = []
    session.modified = True
    return jsonify({'success': True})

@app.route('/api/place_order', methods=['POST'])
@login_required
def place_order():
    cart = session.get('cart', [])
    if not cart:
        return jsonify({'error': 'El carrito está vacío'}), 400
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            # Calculate totals
            subtotal = sum(item['price'] * item['quantity'] for item in cart)
            tax = subtotal * 0.10
            total = subtotal + tax
            
            # Generate order code
            order_code = f"ORD{secrets.randbelow(100000000):08d}"
            
            # Get first active sucursal
            cursor.execute("SELECT ID FROM Sucursales WHERE Estatus = 'Activa' LIMIT 1")
            sucursal_result = cursor.fetchone()
            sucursal_id = sucursal_result[0] if sucursal_result else 1
            
            # Insert order
            cursor.execute("""
                INSERT INTO Pedidos (Cliente_ID, Sucursal_ID, Subtotal, Impuestos, Total, 
                                   Codigo_Pedido, Tipo, Estatus, Fecha_Hora)
                VALUES (%s, %s, %s, %s, %s, %s, 'Presencial', 'Nuevo', NOW())
            """, (session['user_id'], sucursal_id, subtotal, tax, total, order_code))
            
            connection.commit()
            
            # Clear cart
            session['cart'] = []
            session.modified = True
            
            return jsonify({'success': True, 'order_code': order_code})
            
        except Error as e:
            connection.rollback()
            print(f"Error placing order: {e}")  # Para debug
            return jsonify({'error': f'Error al procesar pedido: {str(e)}'}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


# API Routes para administradores y dueño
@app.route('/api/add_table', methods=['POST'])
@role_required(['admin', 'dueño'])
def add_table():
    data = request.json
    connection = get_db_connection()
    
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO Mesas (Sucursal_ID, Numero_Mesa, Capacidad, Ubicacion)
                VALUES (%s, %s, %s, %s)
            """, (
                data['sucursal_id'],
                data['numero_mesa'],
                data['capacidad'],
                data['ubicacion']
            ))
            connection.commit()
            return jsonify({'success': True, 'message': 'Mesa agregada exitosamente'})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/update_order_status', methods=['POST'])
@role_required(['admin', 'mesero', 'cocinero', 'dueño'])
def update_order_status():
    data = request.json
    order_id = data.get('order_id')
    new_status = data.get('status')
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                UPDATE Pedidos SET Estatus = %s WHERE ID = %s
            """, (new_status, order_id))
            connection.commit()
            return jsonify({'success': True})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/add_menu_item', methods=['POST'])
@role_required(['admin', 'mesero', 'dueño'])
def add_menu_item():
    data = request.json
    connection = get_db_connection()
    
    if connection:
        cursor = connection.cursor()
        try:
            # Validar URL de imagen si se proporciona
            imagen_url = data.get('imagen_url', '').strip()
            if imagen_url and not imagen_url.startswith(('http://', 'https://')):
                return jsonify({'error': 'La URL de la imagen debe comenzar con http:// o https://'}), 400
            
            cursor.execute("""
                INSERT INTO Menu (Nombre, Descripcion, Precio, Categoria_ID, Imagen_URL, Estatus)
                VALUES (%s, %s, %s, %s, %s, 'Disponible')
            """, (
                data['nombre'],
                data.get('descripcion', ''),
                data['precio'],
                data['categoria_id'],
                imagen_url if imagen_url else None
            ))
            connection.commit()
            return jsonify({'success': True, 'message': 'Producto agregado exitosamente'})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/get_menu_item/<int:item_id>')
@role_required(['admin', 'mesero', 'dueño'])
def get_menu_item(item_id):
    connection = get_db_connection()
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM Menu WHERE ID = %s", (item_id,))
            item = cursor.fetchone()
            
            if item:
                # Convertir valores Decimal a float para JSON
                if 'Precio' in item:
                    item['Precio'] = float(item['Precio'])
                
                return jsonify({'success': True, 'item': item})
            else:
                return jsonify({'error': 'Producto no encontrado'}), 404
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/update_menu_item', methods=['POST'])
@role_required(['admin', 'mesero', 'dueño'])
def update_menu_item():
    data = request.json
    connection = get_db_connection()
    
    if connection:
        cursor = connection.cursor()
        try:
            # Validar URL de imagen si se proporciona
            imagen_url = data.get('imagen_url', '').strip()
            if imagen_url and not imagen_url.startswith(('http://', 'https://')):
                return jsonify({'error': 'La URL de la imagen debe comenzar con http:// o https://'}), 400
            
            cursor.execute("""
                UPDATE Menu 
                SET Nombre = %s, Descripcion = %s, Precio = %s, 
                    Categoria_ID = %s, Imagen_URL = %s, Estatus = %s
                WHERE ID = %s
            """, (
                data['nombre'],
                data.get('descripcion', ''),
                data['precio'],
                data['categoria_id'],
                imagen_url if imagen_url else None,
                data['estatus'],
                data['item_id']
            ))
            connection.commit()
            return jsonify({'success': True, 'message': 'Producto actualizado exitosamente'})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/delete_menu_item', methods=['POST'])
@role_required(['admin', 'dueño'])
def delete_menu_item():
    data = request.json
    item_id = data.get('item_id')
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM Menu WHERE ID = %s", (item_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Producto eliminado exitosamente'})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/generate_admin_code', methods=['POST'])
@role_required(['admin', 'dueño'])
def generate_admin_code():
    data = request.json
    rol_id = data.get('rol_id', 2)  # Admin por defecto
    
    # Generar código único
    codigo = f"ADMIN{secrets.randbelow(1000000):06d}"
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO Codigos_Admin (Codigo, Rol_ID, Creado_Por)
                VALUES (%s, %s, %s)
            """, (codigo, rol_id, session['user_id']))
            connection.commit()
            return jsonify({'success': True, 'codigo': codigo})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente')
    return redirect(url_for('login'))

@app.route('/api/add_category', methods=['POST'])
@role_required(['admin', 'dueño'])
def add_category():
    data = request.json
    connection = get_db_connection()
    
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO Categorias_Menu (Nombre, Descripcion, Estatus)
                VALUES (%s, %s, 'Activo')
            """, (
                data['nombre'],
                data.get('descripcion', '')
            ))
            connection.commit()
            return jsonify({'success': True, 'message': 'Categoría agregada exitosamente'})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

@app.route('/api/add_sucursal', methods=['POST'])
@role_required('dueño')  # Solo el dueño puede agregar sucursales
def add_sucursal():
    try:
        data = request.json
        
        # Validar que se recibieron los datos
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        nombre = data.get('nombre', '').strip()
        direccion = data.get('direccion', '').strip()
        telefono = data.get('telefono', '').strip()
        
        # Validar campos requeridos
        if not nombre:
            return jsonify({'error': 'El nombre de la sucursal es requerido'}), 400
        if not direccion:
            return jsonify({'error': 'La dirección es requerida'}), 400
        if not telefono:
            return jsonify({'error': 'El teléfono es requerido'}), 400
        
        # Validar longitud de campos
        if len(nombre) > 100:
            return jsonify({'error': 'El nombre es demasiado largo (máximo 100 caracteres)'}), 400
        if len(direccion) > 255:
            return jsonify({'error': 'La dirección es demasiado larga (máximo 255 caracteres)'}), 400
        if len(telefono) > 20:
            return jsonify({'error': 'El teléfono es demasiado largo (máximo 20 caracteres)'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cursor = connection.cursor()
        try:
            # Verificar si ya existe una sucursal con el mismo nombre
            cursor.execute("SELECT COUNT(*) FROM Sucursales WHERE Nombre = %s", (nombre,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'error': 'Ya existe una sucursal con ese nombre'}), 400
            
            # Insertar nueva sucursal
            cursor.execute("""
                INSERT INTO Sucursales (Nombre, Direccion, Telefono, Estatus)
                VALUES (%s, %s, %s, 'Activa')
            """, (nombre, direccion, telefono))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Sucursal agregada exitosamente'})
            
        except Error as e:
            connection.rollback()
            print(f"Database error: {e}")  # Para debug
            return jsonify({'error': f'Error de base de datos: {str(e)}'}), 500
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        print(f"General error: {e}")  # Para debug
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/delete_order', methods=['POST'])
@role_required('dueño')
def delete_order():
    data = request.json
    order_id = data.get('order_id')
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM Pedidos WHERE ID = %s", (order_id,))
            connection.commit()
            return jsonify({'success': True})
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    
    return jsonify({'error': 'Error de conexión'}), 500

if __name__ == '__main__':
    app.run(debug=True)
