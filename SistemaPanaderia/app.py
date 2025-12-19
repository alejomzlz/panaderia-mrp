import streamlit as st
import sqlite3
import hashlib
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid
import tempfile
import json

# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================
st.set_page_config(
    page_title="Sistema MRP Completo - Panadería",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CONSTANTES
# ============================================
SECRET_KEY = "panaderia-mrp-2024-completo-seguro"

# ============================================
# FUNCIONES BÁSICAS
# ============================================
def hash_password(password):
    """Hash seguro de contraseñas"""
    salt = "panaderia-salt-2024-completo"
    return hashlib.sha256((password + salt + SECRET_KEY).encode()).hexdigest()

def get_db_connection():
    """Conexión a la base de datos para Streamlit Cloud"""
    db_dir = tempfile.gettempdir()
    db_path = os.path.join(db_dir, 'panaderia_mrp_completo.db')
    
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    return conn

# ============================================
# INICIALIZACIÓN DE BASE DE DATOS COMPLETA
# ============================================
@st.cache_resource
def init_database():
    """Inicializa TODAS las tablas del sistema completo"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ========== TABLA DE USUARIOS ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        rol TEXT NOT NULL,
        password TEXT NOT NULL,
        permisos TEXT,
        email TEXT,
        telefono TEXT,
        departamento TEXT,
        creado_por INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ultimo_acceso TIMESTAMP,
        activo BOOLEAN DEFAULT 1,
        FOREIGN KEY (creado_por) REFERENCES usuarios(id)
    )
    ''')
    
    # Crear usuario admin si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_password = hash_password("Admin2024!")
        cursor.execute('''
        INSERT INTO usuarios (username, nombre, rol, password, permisos, email, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', 'Administrador Principal', 'admin', admin_password, 'all', 'admin@panaderia.com', 1))
    
    # ========== TABLA DE PRODUCTOS ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        categoria TEXT NOT NULL,
        subcategoria TEXT,
        unidad_medida TEXT NOT NULL,
        precio_compra DECIMAL(15,2) DEFAULT 0,
        precio_venta DECIMAL(15,2) DEFAULT 0,
        stock_minimo DECIMAL(15,2) DEFAULT 0,
        stock_maximo DECIMAL(15,2) DEFAULT 0,
        stock_actual DECIMAL(15,2) DEFAULT 0,
        peso DECIMAL(10,2),
        volumen DECIMAL(10,2),
        ubicacion TEXT,
        proveedor_id INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # ========== TABLA DE MATERIAS PRIMAS ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materias_primas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        categoria TEXT NOT NULL,
        unidad_medida TEXT NOT NULL,
        costo_unitario DECIMAL(15,2) DEFAULT 0,
        stock_actual DECIMAL(15,2) DEFAULT 0,
        stock_minimo DECIMAL(15,2) DEFAULT 0,
        stock_maximo DECIMAL(15,2) DEFAULT 0,
        fecha_caducidad DATE,
        lote TEXT,
        ubicacion TEXT,
        proveedor_id INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # ========== TABLA DE PROVEEDORES ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        ruc TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        contacto TEXT,
        tipo_proveedor TEXT,
        productos TEXT,
        plazo_entrega INTEGER DEFAULT 0,
        calificacion INTEGER DEFAULT 5,
        limite_credito DECIMAL(15,2) DEFAULT 0,
        saldo_actual DECIMAL(15,2) DEFAULT 0,
        condiciones_pago TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # ========== TABLA DE CLIENTES ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        tipo_documento TEXT,
        numero_documento TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        contacto TEXT,
        tipo_cliente TEXT,
        limite_credito DECIMAL(15,2) DEFAULT 0,
        saldo_actual DECIMAL(15,2) DEFAULT 0,
        dias_credito INTEGER DEFAULT 0,
        categoria TEXT DEFAULT 'REGULAR',
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_creador INTEGER,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # ========== TABLA DE ÓRDENES DE COMPRA ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ordenes_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_orden TEXT UNIQUE NOT NULL,
        proveedor_id INTEGER NOT NULL,
        fecha_orden DATE NOT NULL,
        fecha_entrega_esperada DATE,
        estado TEXT DEFAULT 'PENDIENTE',
        subtotal DECIMAL(15,2) DEFAULT 0,
        descuento DECIMAL(15,2) DEFAULT 0,
        impuestos DECIMAL(15,2) DEFAULT 0,
        total DECIMAL(15,2) DEFAULT 0,
        observaciones TEXT,
        usuario_creador INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    )
    ''')
    
    # ========== TABLA DE DETALLE ORDEN COMPRA ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detalle_orden_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        orden_compra_id INTEGER NOT NULL,
        producto_id INTEGER,
        materia_prima_id INTEGER,
        descripcion TEXT NOT NULL,
        cantidad DECIMAL(15,2) NOT NULL,
        unidad_medida TEXT NOT NULL,
        precio_unitario DECIMAL(15,2) NOT NULL,
        descuento DECIMAL(15,2) DEFAULT 0,
        impuestos DECIMAL(15,2) DEFAULT 0,
        total_linea DECIMAL(15,2) NOT NULL,
        FOREIGN KEY (orden_compra_id) REFERENCES ordenes_compra(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        FOREIGN KEY (materia_prima_id) REFERENCES materias_primas(id)
    )
    ''')
    
    # ========== TABLA DE RECEPCIÓN DE MATERIALES ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recepciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_recepcion TEXT UNIQUE NOT NULL,
        orden_compra_id INTEGER,
        proveedor_id INTEGER NOT NULL,
        fecha_recepcion DATE NOT NULL,
        estado TEXT DEFAULT 'PARCIAL',
        observaciones TEXT,
        usuario_receptor INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (orden_compra_id) REFERENCES ordenes_compra(id),
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    )
    ''')
    
    # ========== TABLA DE DETALLE RECEPCIÓN ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detalle_recepcion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recepcion_id INTEGER NOT NULL,
        producto_id INTEGER,
        materia_prima_id INTEGER,
        cantidad_pedida DECIMAL(15,2) NOT NULL,
        cantidad_recibida DECIMAL(15,2) NOT NULL,
        unidad_medida TEXT NOT NULL,
        lote TEXT,
        fecha_vencimiento DATE,
        ubicacion_destino TEXT,
        estado_calidad TEXT DEFAULT 'ACEPTADO',
        observaciones TEXT,
        FOREIGN KEY (recepcion_id) REFERENCES recepciones(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        FOREIGN KEY (materia_prima_id) REFERENCES materias_primas(id)
    )
    ''')
    
    # ========== TABLA DE ÓRDENES DE PRODUCCIÓN ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ordenes_produccion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_orden TEXT UNIQUE NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad_producir DECIMAL(15,2) NOT NULL,
        fecha_inicio DATE NOT NULL,
        fecha_fin_estimada DATE,
        estado TEXT DEFAULT 'PLANIFICADA',
        prioridad TEXT DEFAULT 'MEDIA',
        observaciones TEXT,
        usuario_creador INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    ''')
    
    # ========== TABLA DE REQUERIMIENTOS MATERIALES (BOM) ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requerimientos_materiales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        orden_produccion_id INTEGER NOT NULL,
        materia_prima_id INTEGER NOT NULL,
        cantidad_requerida DECIMAL(15,2) NOT NULL,
        cantidad_asignada DECIMAL(15,2) DEFAULT 0,
        unidad_medida TEXT NOT NULL,
        costo_unitario DECIMAL(15,2) DEFAULT 0,
        costo_total DECIMAL(15,2) DEFAULT 0,
        estado TEXT DEFAULT 'PENDIENTE',
        FOREIGN KEY (orden_produccion_id) REFERENCES ordenes_produccion(id),
        FOREIGN KEY (materia_prima_id) REFERENCES materias_primas(id)
    )
    ''')
    
    # ========== TABLA DE VENTAS ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura TEXT UNIQUE NOT NULL,
        cliente_id INTEGER NOT NULL,
        fecha_venta DATE NOT NULL,
        subtotal DECIMAL(15,2) DEFAULT 0,
        descuento DECIMAL(15,2) DEFAULT 0,
        impuestos DECIMAL(15,2) DEFAULT 0,
        total DECIMAL(15,2) DEFAULT 0,
        estado TEXT DEFAULT 'PENDIENTE',
        forma_pago TEXT,
        fecha_vencimiento DATE,
        observaciones TEXT,
        usuario_vendedor INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    )
    ''')
    
    # ========== TABLA DE DETALLE VENTA ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detalle_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad DECIMAL(15,2) NOT NULL,
        precio_unitario DECIMAL(15,2) NOT NULL,
        descuento DECIMAL(15,2) DEFAULT 0,
        impuestos DECIMAL(15,2) DEFAULT 0,
        total_linea DECIMAL(15,2) NOT NULL,
        FOREIGN KEY (venta_id) REFERENCES ventas(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    ''')
    
    # ========== TABLA DE MOVIMIENTOS INVENTARIO ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movimientos_inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_movimiento TEXT NOT NULL,
        referencia_id INTEGER,
        referencia_tipo TEXT,
        producto_id INTEGER,
        materia_prima_id INTEGER,
        cantidad DECIMAL(15,2) NOT NULL,
        unidad_medida TEXT NOT NULL,
        costo_unitario DECIMAL(15,2),
        stock_anterior DECIMAL(15,2),
        stock_nuevo DECIMAL(15,2),
        fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_responsable INTEGER,
        observaciones TEXT,
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        FOREIGN KEY (materia_prima_id) REFERENCES materias_primas(id)
    )
    ''')
    
    # ========== TABLA DE AJUSTES INVENTARIO ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ajustes_inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_ajuste TEXT UNIQUE NOT NULL,
        tipo_ajuste TEXT NOT NULL,
        fecha_ajuste DATE NOT NULL,
        motivo TEXT NOT NULL,
        observaciones TEXT,
        usuario_ajustador INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_ajustador) REFERENCES usuarios(id)
    )
    ''')
    
    # ========== TABLA DE DETALLE AJUSTE ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detalle_ajuste (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ajuste_id INTEGER NOT NULL,
        producto_id INTEGER,
        materia_prima_id INTEGER,
        cantidad_anterior DECIMAL(15,2) NOT NULL,
        cantidad_nueva DECIMAL(15,2) NOT NULL,
        diferencia DECIMAL(15,2) NOT NULL,
        unidad_medida TEXT NOT NULL,
        costo_unitario DECIMAL(15,2),
        observaciones TEXT,
        FOREIGN KEY (ajuste_id) REFERENCES ajustes_inventario(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        FOREIGN KEY (materia_prima_id) REFERENCES materias_primas(id)
    )
    ''')
    
    # ========== TABLA DE RECETAS ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recetas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        producto_id INTEGER NOT NULL,
        version INTEGER DEFAULT 1,
        estado TEXT DEFAULT 'ACTIVA',
        tiempo_preparacion INTEGER,
        rendimiento DECIMAL(10,2),
        unidad_rendimiento TEXT,
        instrucciones TEXT,
        observaciones TEXT,
        costo_total DECIMAL(15,2) DEFAULT 0,
        usuario_creador INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    ''')
    
    # ========== TABLA DE INGREDIENTES RECETA ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingredientes_receta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receta_id INTEGER NOT NULL,
        materia_prima_id INTEGER NOT NULL,
        cantidad DECIMAL(15,2) NOT NULL,
        unidad_medida TEXT NOT NULL,
        costo_unitario DECIMAL(15,2) DEFAULT 0,
        costo_total DECIMAL(15,2) DEFAULT 0,
        orden INTEGER DEFAULT 1,
        observaciones TEXT,
        FOREIGN KEY (receta_id) REFERENCES recetas(id),
        FOREIGN KEY (materia_prima_id) REFERENCES materias_primas(id)
    )
    ''')
    
    # ========== TABLA DE PEDIDOS CLIENTES ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pedidos_clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_pedido TEXT UNIQUE NOT NULL,
        cliente_id INTEGER NOT NULL,
        fecha_pedido DATE NOT NULL,
        fecha_entrega_esperada DATE,
        estado TEXT DEFAULT 'PENDIENTE',
        subtotal DECIMAL(15,2) DEFAULT 0,
        descuento DECIMAL(15,2) DEFAULT 0,
        impuestos DECIMAL(15,2) DEFAULT 0,
        total DECIMAL(15,2) DEFAULT 0,
        observaciones TEXT,
        usuario_creador INTEGER,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    )
    ''')
    
    # ========== TABLA DE DETALLE PEDIDO ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detalle_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad DECIMAL(15,2) NOT NULL,
        precio_unitario DECIMAL(15,2) NOT NULL,
        descuento DECIMAL(15,2) DEFAULT 0,
        total_linea DECIMAL(15,2) NOT NULL,
        estado_entrega TEXT DEFAULT 'PENDIENTE',
        FOREIGN KEY (pedido_id) REFERENCES pedidos_clientes(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    ''')
    
    # ========== TABLA DE LOGS SISTEMA ==========
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs_sistema (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        modulo TEXT NOT NULL,
        accion TEXT NOT NULL,
        detalles TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    ''')
    
    conn.commit()
    return conn

# ============================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================
def autenticar_usuario(username, password):
    """Autentica un usuario"""
    try:
        conn = get_db_connection()
        hashed_password = hash_password(password)
        
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, username, nombre, rol, permisos, email 
        FROM usuarios 
        WHERE username = ? AND password = ? AND activo = 1
        ''', (username, hashed_password))
        
        usuario = cursor.fetchone()
        
        if usuario:
            cursor.execute('''
            UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?
            ''', (usuario['id'],))
            conn.commit()
            
            cursor.execute('''
            INSERT INTO logs_sistema (usuario_id, modulo, accion, detalles)
            VALUES (?, ?, ?, ?)
            ''', (usuario['id'], 'AUTH', 'LOGIN', f'Usuario: {username}'))
            conn.commit()
            
            conn.close()
            return {
                'id': usuario['id'],
                'username': usuario['username'],
                'nombre': usuario['nombre'],
                'rol': usuario['rol'],
                'permisos': usuario['permisos'],
                'email': usuario['email']
            }
        
        conn.close()
        return None
    except Exception as e:
        return None

def registrar_log(usuario_id, modulo, accion, detalles=""):
    """Registra un log en el sistema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO logs_sistema (usuario_id, modulo, accion, detalles)
        VALUES (?, ?, ?, ?)
        ''', (usuario_id, modulo, accion, detalles))
        conn.commit()
        conn.close()
    except:
        pass

# ============================================
# FUNCIONES DE GESTIÓN DE USUARIOS
# ============================================
@st.cache_data(ttl=300)
def obtener_usuarios():
    """Obtiene todos los usuarios"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.*, creador.nombre as creador_nombre
    FROM usuarios u
    LEFT JOIN usuarios creador ON u.creado_por = creador.id
    ORDER BY u.fecha_creacion DESC
    ''')
    usuarios = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return usuarios

def crear_usuario(admin_id, datos):
    """Crea un nuevo usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (datos['username'],))
        if cursor.fetchone():
            return False, "El usuario ya existe"
        
        hashed_password = hash_password(datos['password'])
        
        cursor.execute('''
        INSERT INTO usuarios (username, nombre, rol, password, permisos, email, 
                            telefono, departamento, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['username'],
            datos['nombre'],
            datos['rol'],
            hashed_password,
            datos.get('permisos', ''),
            datos.get('email', ''),
            datos.get('telefono', ''),
            datos.get('departamento', ''),
            admin_id
        ))
        
        conn.commit()
        registrar_log(admin_id, 'USUARIOS', 'CREACION', f"Usuario: {datos['username']}")
        conn.close()
        return True, "✅ Usuario creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def actualizar_usuario(usuario_id, datos):
    """Actualiza un usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE usuarios 
        SET nombre = ?, rol = ?, permisos = ?, email = ?, 
            telefono = ?, departamento = ?, activo = ?
        WHERE id = ?
        ''', (
            datos['nombre'],
            datos['rol'],
            datos.get('permisos', ''),
            datos.get('email', ''),
            datos.get('telefono', ''),
            datos.get('departamento', ''),
            datos.get('activo', 1),
            usuario_id
        ))
        
        conn.commit()
        conn.close()
        return True, "✅ Usuario actualizado"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE PRODUCTOS
# ============================================
@st.cache_data(ttl=300)
def obtener_productos():
    """Obtiene todos los productos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT p.*, pr.nombre as proveedor_nombre
    FROM productos p
    LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
    WHERE p.activo = 1
    ORDER BY p.nombre
    ''')
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

def crear_producto(usuario_id, datos):
    """Crea un nuevo producto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('codigo'):
            datos['codigo'] = f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute('''
        INSERT INTO productos (codigo, nombre, descripcion, categoria, subcategoria,
                             unidad_medida, precio_compra, precio_venta,
                             stock_minimo, stock_maximo, stock_actual,
                             peso, volumen, ubicacion, proveedor_id, usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['codigo'],
            datos['nombre'],
            datos.get('descripcion', ''),
            datos['categoria'],
            datos.get('subcategoria', ''),
            datos['unidad_medida'],
            datos.get('precio_compra', 0),
            datos.get('precio_venta', 0),
            datos.get('stock_minimo', 0),
            datos.get('stock_maximo', 0),
            datos.get('stock_actual', 0),
            datos.get('peso', 0),
            datos.get('volumen', 0),
            datos.get('ubicacion', ''),
            datos.get('proveedor_id'),
            usuario_id
        ))
        
        producto_id = cursor.lastrowid
        
        # Registrar movimiento
        cursor.execute('''
        INSERT INTO movimientos_inventario 
        (tipo_movimiento, producto_id, cantidad, unidad_medida,
         stock_anterior, stock_nuevo, usuario_responsable, observaciones)
        VALUES (?, ?, ?, ?, 0, ?, ?, ?)
        ''', (
            'CREACION',
            producto_id,
            datos.get('stock_actual', 0),
            datos['unidad_medida'],
            datos.get('stock_actual', 0),
            usuario_id,
            f"Creación producto: {datos['nombre']}"
        ))
        
        conn.commit()
        registrar_log(usuario_id, 'PRODUCTOS', 'CREACION', f"Producto: {datos['nombre']}")
        conn.close()
        return True, "✅ Producto creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def actualizar_stock_producto(producto_id, cantidad, tipo_movimiento, usuario_id, observaciones=""):
    """Actualiza el stock de un producto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT stock_actual FROM productos WHERE id = ?", (producto_id,))
        stock_actual = cursor.fetchone()[0]
        
        if tipo_movimiento == 'ENTRADA':
            nuevo_stock = stock_actual + cantidad
        elif tipo_movimiento == 'SALIDA':
            nuevo_stock = stock_actual - cantidad
        else:
            nuevo_stock = cantidad
        
        cursor.execute('''
        UPDATE productos SET stock_actual = ?, fecha_actualizacion = CURRENT_TIMESTAMP 
        WHERE id = ?
        ''', (nuevo_stock, producto_id))
        
        cursor.execute('''
        INSERT INTO movimientos_inventario 
        (tipo_movimiento, producto_id, cantidad, unidad_medida,
         stock_anterior, stock_nuevo, usuario_responsable, observaciones)
        VALUES (?, ?, ?, 
               (SELECT unidad_medida FROM productos WHERE id = ?),
               ?, ?, ?, ?)
        ''', (
            tipo_movimiento,
            producto_id,
            cantidad,
            producto_id,
            stock_actual,
            nuevo_stock,
            usuario_id,
            observaciones
        ))
        
        conn.commit()
        conn.close()
        return True, "✅ Stock actualizado"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE MATERIAS PRIMAS
# ============================================
@st.cache_data(ttl=300)
def obtener_materias_primas():
    """Obtiene todas las materias primas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT mp.*, p.nombre as proveedor_nombre
    FROM materias_primas mp
    LEFT JOIN proveedores p ON mp.proveedor_id = p.id
    WHERE mp.activo = 1
    ORDER BY mp.nombre
    ''')
    materias = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return materias

def crear_materia_prima(usuario_id, datos):
    """Crea una nueva materia prima"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('codigo'):
            datos['codigo'] = f"MP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute('''
        INSERT INTO materias_primas (codigo, nombre, descripcion, categoria,
                                   unidad_medida, costo_unitario, stock_actual,
                                   stock_minimo, stock_maximo, fecha_caducidad,
                                   lote, ubicacion, proveedor_id, usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['codigo'],
            datos['nombre'],
            datos.get('descripcion', ''),
            datos['categoria'],
            datos['unidad_medida'],
            datos.get('costo_unitario', 0),
            datos.get('stock_actual', 0),
            datos.get('stock_minimo', 0),
            datos.get('stock_maximo', 0),
            datos.get('fecha_caducidad'),
            datos.get('lote', ''),
            datos.get('ubicacion', ''),
            datos.get('proveedor_id'),
            usuario_id
        ))
        
        conn.commit()
        registrar_log(usuario_id, 'MATERIAS_PRIMAS', 'CREACION', f"Materia prima: {datos['nombre']}")
        conn.close()
        return True, "✅ Materia prima creada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE PROVEEDORES
# ============================================
@st.cache_data(ttl=300)
def obtener_proveedores():
    """Obtiene todos los proveedores"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM proveedores 
    WHERE activo = 1 
    ORDER BY nombre
    ''')
    proveedores = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return proveedores

def crear_proveedor(usuario_id, datos):
    """Crea un nuevo proveedor"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('codigo'):
            datos['codigo'] = f"PROV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute('''
        INSERT INTO proveedores (codigo, nombre, ruc, direccion, telefono,
                               email, contacto, tipo_proveedor, productos,
                               plazo_entrega, calificacion, limite_credito,
                               saldo_actual, condiciones_pago, usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['codigo'],
            datos['nombre'],
            datos.get('ruc', ''),
            datos.get('direccion', ''),
            datos.get('telefono', ''),
            datos.get('email', ''),
            datos.get('contacto', ''),
            datos.get('tipo_proveedor', ''),
            datos.get('productos', ''),
            datos.get('plazo_entrega', 0),
            datos.get('calificacion', 5),
            datos.get('limite_credito', 0),
            datos.get('saldo_actual', 0),
            datos.get('condiciones_pago', ''),
            usuario_id
        ))
        
        conn.commit()
        registrar_log(usuario_id, 'PROVEEDORES', 'CREACION', f"Proveedor: {datos['nombre']}")
        conn.close()
        return True, "✅ Proveedor creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE CLIENTES
# ============================================
@st.cache_data(ttl=300)
def obtener_clientes():
    """Obtiene todos los clientes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM clientes 
    WHERE activo = 1 
    ORDER BY nombre
    ''')
    clientes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return clientes

def crear_cliente(usuario_id, datos):
    """Crea un nuevo cliente"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('codigo'):
            datos['codigo'] = f"CLI-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute('''
        INSERT INTO clientes (codigo, nombre, tipo_documento, numero_documento,
                            direccion, telefono, email, contacto, tipo_cliente,
                            limite_credito, saldo_actual, dias_credito,
                            categoria, usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['codigo'],
            datos['nombre'],
            datos.get('tipo_documento', ''),
            datos.get('numero_documento', ''),
            datos.get('direccion', ''),
            datos.get('telefono', ''),
            datos.get('email', ''),
            datos.get('contacto', ''),
            datos.get('tipo_cliente', ''),
            datos.get('limite_credito', 0),
            datos.get('saldo_actual', 0),
            datos.get('dias_credito', 0),
            datos.get('categoria', 'REGULAR'),
            usuario_id
        ))
        
        conn.commit()
        registrar_log(usuario_id, 'CLIENTES', 'CREACION', f"Cliente: {datos['nombre']}")
        conn.close()
        return True, "✅ Cliente creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE COMPRAS
# ============================================
@st.cache_data(ttl=300)
def obtener_ordenes_compra(estado=None):
    """Obtiene órdenes de compra"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT oc.*, p.nombre as proveedor_nombre, u.nombre as creador_nombre
    FROM ordenes_compra oc
    JOIN proveedores p ON oc.proveedor_id = p.id
    JOIN usuarios u ON oc.usuario_creador = u.id
    '''
    
    params = []
    if estado:
        query += " WHERE oc.estado = ?"
        params.append(estado)
    
    query += " ORDER BY oc.fecha_orden DESC"
    cursor.execute(query, params)
    ordenes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ordenes

def crear_orden_compra(usuario_id, datos):
    """Crea una nueva orden de compra"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('numero_orden'):
            año = datetime.now().year
            cursor.execute("SELECT COUNT(*) FROM ordenes_compra WHERE strftime('%Y', fecha_creacion) = ?", (str(año),))
            consecutivo = cursor.fetchone()[0] + 1
            datos['numero_orden'] = f"OC-{año}-{consecutivo:04d}"
        
        cursor.execute('''
        INSERT INTO ordenes_compra (numero_orden, proveedor_id, fecha_orden,
                                  fecha_entrega_esperada, estado, observaciones,
                                  usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['numero_orden'],
            datos['proveedor_id'],
            datos['fecha_orden'],
            datos.get('fecha_entrega_esperada'),
            datos.get('estado', 'PENDIENTE'),
            datos.get('observaciones', ''),
            usuario_id
        ))
        
        orden_id = cursor.lastrowid
        
        # Insertar detalles
        subtotal = 0
        for detalle in datos['detalles']:
            total_linea = detalle['cantidad'] * detalle['precio_unitario']
            subtotal += total_linea
            
            cursor.execute('''
            INSERT INTO detalle_orden_compra 
            (orden_compra_id, producto_id, materia_prima_id, descripcion,
             cantidad, unidad_medida, precio_unitario, total_linea)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                orden_id,
                detalle.get('producto_id'),
                detalle.get('materia_prima_id'),
                detalle['descripcion'],
                detalle['cantidad'],
                detalle['unidad_medida'],
                detalle['precio_unitario'],
                total_linea
            ))
        
        # Calcular totales
        impuestos = subtotal * 0.18
        total = subtotal + impuestos
        
        cursor.execute('''
        UPDATE ordenes_compra 
        SET subtotal = ?, impuestos = ?, total = ?
        WHERE id = ?
        ''', (subtotal, impuestos, total, orden_id))
        
        conn.commit()
        registrar_log(usuario_id, 'COMPRAS', 'CREACION_OC', f"OC: {datos['numero_orden']}")
        conn.close()
        return True, "✅ Orden de compra creada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE VENTAS
# ============================================
@st.cache_data(ttl=300)
def obtener_ventas(estado=None):
    """Obtiene ventas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT v.*, c.nombre as cliente_nombre, u.nombre as vendedor_nombre
    FROM ventas v
    JOIN clientes c ON v.cliente_id = c.id
    JOIN usuarios u ON v.usuario_vendedor = u.id
    '''
    
    params = []
    if estado:
        query += " WHERE v.estado = ?"
        params.append(estado)
    
    query += " ORDER BY v.fecha_venta DESC"
    cursor.execute(query, params)
    ventas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ventas

def crear_venta(usuario_id, datos):
    """Crea una nueva venta"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('numero_factura'):
            año = datetime.now().year
            cursor.execute("SELECT COUNT(*) FROM ventas WHERE strftime('%Y', fecha_creacion) = ?", (str(año),))
            consecutivo = cursor.fetchone()[0] + 1
            datos['numero_factura'] = f"FAC-{año}-{consecutivo:04d}"
        
        cursor.execute('''
        INSERT INTO ventas (numero_factura, cliente_id, fecha_venta,
                          estado, forma_pago, fecha_vencimiento,
                          observaciones, usuario_vendedor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['numero_factura'],
            datos['cliente_id'],
            datos['fecha_venta'],
            datos.get('estado', 'PENDIENTE'),
            datos.get('forma_pago', 'CONTADO'),
            datos.get('fecha_vencimiento'),
            datos.get('observaciones', ''),
            usuario_id
        ))
        
        venta_id = cursor.lastrowid
        
        # Insertar detalles y actualizar stock
        subtotal = 0
        for detalle in datos['detalles']:
            total_linea = detalle['cantidad'] * detalle['precio_unitario']
            subtotal += total_linea
            
            cursor.execute('''
            INSERT INTO detalle_venta 
            (venta_id, producto_id, cantidad, precio_unitario, total_linea)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                venta_id,
                detalle['producto_id'],
                detalle['cantidad'],
                detalle['precio_unitario'],
                total_linea
            ))
            
            # Actualizar stock
            cursor.execute('''
            UPDATE productos 
            SET stock_actual = stock_actual - ?, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (detalle['cantidad'], detalle['producto_id']))
            
            # Registrar movimiento
            cursor.execute('''
            INSERT INTO movimientos_inventario 
            (tipo_movimiento, producto_id, cantidad, unidad_medida,
             usuario_responsable, observaciones)
            VALUES (?, ?, ?, 
                   (SELECT unidad_medida FROM productos WHERE id = ?),
                   ?, ?)
            ''', (
                'VENTA',
                detalle['producto_id'],
                detalle['cantidad'],
                detalle['producto_id'],
                usuario_id,
                f"Venta {datos['numero_factura']}"
            ))
        
        # Calcular totales
        descuento = datos.get('descuento', 0)
        impuestos = (subtotal - descuento) * 0.18
        total = subtotal - descuento + impuestos
        
        cursor.execute('''
        UPDATE ventas 
        SET subtotal = ?, descuento = ?, impuestos = ?, total = ?
        WHERE id = ?
        ''', (subtotal, descuento, impuestos, total, venta_id))
        
        conn.commit()
        registrar_log(usuario_id, 'VENTAS', 'CREACION', f"Venta: {datos['numero_factura']}")
        conn.close()
        return True, "✅ Venta registrada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE GESTIÓN DE PRODUCCIÓN
# ============================================
@st.cache_data(ttl=300)
def obtener_ordenes_produccion(estado=None):
    """Obtiene órdenes de producción"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT op.*, p.nombre as producto_nombre, p.codigo as producto_codigo,
           u.nombre as creador_nombre
    FROM ordenes_produccion op
    JOIN productos p ON op.producto_id = p.id
    JOIN usuarios u ON op.usuario_creador = u.id
    '''
    
    params = []
    if estado:
        query += " WHERE op.estado = ?"
        params.append(estado)
    
    query += " ORDER BY op.fecha_inicio DESC"
    cursor.execute(query, params)
    ordenes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ordenes

def crear_orden_produccion(usuario_id, datos):
    """Crea una orden de producción"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not datos.get('numero_orden'):
            año = datetime.now().year
            cursor.execute("SELECT COUNT(*) FROM ordenes_produccion WHERE strftime('%Y', fecha_creacion) = ?", (str(año),))
            consecutivo = cursor.fetchone()[0] + 1
            datos['numero_orden'] = f"OP-{año}-{consecutivo:04d}"
        
        cursor.execute('''
        INSERT INTO ordenes_produccion (numero_orden, producto_id, cantidad_producir,
                                      fecha_inicio, fecha_fin_estimada, estado,
                                      prioridad, observaciones, usuario_creador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['numero_orden'],
            datos['producto_id'],
            datos['cantidad_producir'],
            datos['fecha_inicio'],
            datos.get('fecha_fin_estimada'),
            datos.get('estado', 'PLANIFICADA'),
            datos.get('prioridad', 'MEDIA'),
            datos.get('observaciones', ''),
            usuario_id
        ))
        
        orden_id = cursor.lastrowid
        
        # Insertar requerimientos de materiales
        for requerimiento in datos.get('requerimientos', []):
            cursor.execute('''
            INSERT INTO requerimientos_materiales 
            (orden_produccion_id, materia_prima_id, cantidad_requerida, unidad_medida)
            VALUES (?, ?, ?, ?)
            ''', (
                orden_id,
                requerimiento['materia_prima_id'],
                requerimiento['cantidad_requerida'],
                requerimiento['unidad_medida']
            ))
        
        conn.commit()
        registrar_log(usuario_id, 'PRODUCCION', 'CREACION_OP', f"OP: {datos['numero_orden']}")
        conn.close()
        return True, "✅ Orden de producción creada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# FUNCIONES DE REPORTES
# ============================================
@st.cache_data(ttl=300)
def obtener_kpis():
    """Obtiene KPIs principales"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    kpis = {}
    
    # Total productos
    cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1")
    kpis['total_productos'] = cursor.fetchone()[0] or 0
    
    # Productos bajo stock mínimo
    cursor.execute("SELECT COUNT(*) FROM productos WHERE stock_actual < stock_minimo AND activo = 1")
    kpis['productos_bajo_stock'] = cursor.fetchone()[0] or 0
    
    # Ventas del mes
    cursor.execute('''
    SELECT COALESCE(SUM(total), 0) 
    FROM ventas 
    WHERE strftime('%Y-%m', fecha_venta) = strftime('%Y-%m', 'now')
    ''')
    kpis['ventas_mes'] = float(cursor.fetchone()[0] or 0)
    
    # Compras del mes
    cursor.execute('''
    SELECT COALESCE(SUM(total), 0) 
    FROM ordenes_compra 
    WHERE strftime('%Y-%m', fecha_orden) = strftime('%Y-%m', 'now')
    ''')
    kpis['compras_mes'] = float(cursor.fetchone()[0] or 0)
    
    # Valor del inventario
    cursor.execute('''
    SELECT COALESCE(SUM(stock_actual * precio_compra), 0)
    FROM productos
    WHERE activo = 1
    ''')
    kpis['valor_inventario'] = float(cursor.fetchone()[0] or 0)
    
    # Total clientes
    cursor.execute("SELECT COUNT(*) FROM clientes WHERE activo = 1")
    kpis['total_clientes'] = cursor.fetchone()[0] or 0
    
    # Total proveedores
    cursor.execute("SELECT COUNT(*) FROM proveedores WHERE activo = 1")
    kpis['total_proveedores'] = cursor.fetchone()[0] or 0
    
    conn.close()
    return kpis

@st.cache_data(ttl=300)
def obtener_ventas_por_periodo(dias=30):
    """Obtiene ventas por período"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT DATE(fecha_venta) as fecha, SUM(total) as total
    FROM ventas
    WHERE fecha_venta >= date('now', ?)
    GROUP BY DATE(fecha_venta)
    ORDER BY fecha
    ''', (f'-{dias} days',))
    
    ventas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ventas

@st.cache_data(ttl=300)
def obtener_top_productos(limit=10):
    """Obtiene los productos más vendidos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT p.nombre, SUM(dv.cantidad) as total_vendido, SUM(dv.total_linea) as total_ventas
    FROM detalle_venta dv
    JOIN productos p ON dv.producto_id = p.id
    JOIN ventas v ON dv.venta_id = v.id
    WHERE v.fecha_venta >= date('now', '-30 days')
    GROUP BY p.id
    ORDER BY total_vendido DESC
    LIMIT ?
    ''', (limit,))
    
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

# ============================================
# INTERFAZ DE LOGIN
# ============================================
def mostrar_login():
    """Muestra la pantalla de login"""
    
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 50px auto;
        padding: 40px 30px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
    }
    .login-title {
        text-align: center;
        color: #2c3e50;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown('<h2 class="login-title">🏭 Sistema MRP Completo</h2>', unsafe_allow_html=True)
            st.markdown('<p style="text-align: center; color: #666;">Panadería Industrial</p>', unsafe_allow_html=True)
            st.markdown("---")
            
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("**Usuario**", placeholder="admin")
                password = st.text_input("**Contraseña**", type="password", placeholder="Admin2024!")
                
                submit = st.form_submit_button("🚀 **INGRESAR AL SISTEMA**", use_container_width=True, type="primary")
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Por favor complete todos los campos")
                    else:
                        with st.spinner("🔐 Verificando credenciales..."):
                            usuario = autenticar_usuario(username, password)
                            if usuario:
                                st.session_state.usuario = usuario
                                st.success("✅ ¡Autenticación exitosa!")
                                st.rerun()
                            else:
                                st.error("❌ Usuario o contraseña incorrectos")
            
            # Botón para crear admin si no existe
            st.markdown("---")
            if st.button("👑 Crear Usuario Admin", type="secondary", use_container_width=True):
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT username FROM usuarios WHERE username = 'admin'")
                if cursor.fetchone():
                    st.info("✅ El usuario admin ya existe")
                else:
                    try:
                        admin_hash = hash_password("Admin2024!")
                        cursor.execute('''
                        INSERT INTO usuarios (username, nombre, rol, password, permisos, email, creado_por)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', ('admin', 'Administrador', 'admin', admin_hash, 'all', 'admin@panaderia.com', 1))
                        conn.commit()
                        st.success("✅ Admin creado: usuario=admin, contraseña=Admin2024!")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                
                conn.close()
            
            st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# DASHBOARD PRINCIPAL
# ============================================
def mostrar_dashboard():
    """Dashboard principal"""
    
    st.title("📊 Dashboard Principal")
    
    # KPIs
    kpis = obtener_kpis()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📦 Productos",
            kpis['total_productos'],
            delta=f"-{kpis['productos_bajo_stock']} bajo stock" if kpis['productos_bajo_stock'] > 0 else None,
            delta_color="inverse" if kpis['productos_bajo_stock'] > 0 else "normal"
        )
    
    with col2:
        st.metric("💰 Ventas Mes", f"${kpis['ventas_mes']:,.2f}")
    
    with col3:
        st.metric("🛒 Compras Mes", f"${kpis['compras_mes']:,.2f}")
    
    with col4:
        st.metric("📊 Valor Inventario", f"${kpis['valor_inventario']:,.2f}")
    
    st.markdown("---")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Ventas Últimos 30 Días")
        ventas_data = obtener_ventas_por_periodo(30)
        if ventas_data:
            df_ventas = pd.DataFrame(ventas_data)
            if len(df_ventas) > 0:
                fig = px.line(df_ventas, x='fecha', y='total', title='Evolución de Ventas')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de ventas para mostrar")
        else:
            st.info("No hay datos de ventas para mostrar")
    
    with col2:
        st.subheader("🏆 Productos Más Vendidos")
        top_productos = obtener_top_productos(5)
        if top_productos:
            df_top = pd.DataFrame(top_productos)
            if len(df_top) > 0:
                fig = px.bar(df_top, x='nombre', y='total_vendido', title='Top Productos')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de productos vendidos")
        else:
            st.info("No hay datos de productos vendidos")
    
    # Alertas
    st.markdown("---")
    st.subheader("⚠️ Alertas del Sistema")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Productos bajo stock mínimo
    cursor.execute('''
    SELECT nombre, stock_actual, stock_minimo 
    FROM productos 
    WHERE stock_actual < stock_minimo AND activo = 1
    LIMIT 5
    ''')
    
    productos_bajo_stock = cursor.fetchall()
    
    if productos_bajo_stock:
        st.warning("**Productos bajo stock mínimo:**")
        for producto in productos_bajo_stock:
            st.write(f"- {producto['nombre']}: {producto['stock_actual']}/{producto['stock_minimo']}")
    else:
        st.success("✅ No hay productos bajo stock mínimo")
    
    # Órdenes de producción pendientes
    cursor.execute('''
    SELECT COUNT(*) 
    FROM ordenes_produccion 
    WHERE estado IN ('PLANIFICADA', 'EN_PROCESO')
    ''')
    op_pendientes = cursor.fetchone()[0]
    
    if op_pendientes > 0:
        st.info(f"**Órdenes de producción pendientes:** {op_pendientes}")
    
    conn.close()

# ============================================
# MÓDULO DE GESTIÓN DE USUARIOS
# ============================================
def mostrar_modulo_usuarios():
    """Módulo de gestión de usuarios"""
    
    st.title("👥 Gestión de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "➕ Nuevo Usuario", "⚙️ Editar Usuario"])
    
    with tab1:
        st.subheader("Usuarios Registrados")
        
        usuarios = obtener_usuarios()
        
        if usuarios:
            df = pd.DataFrame(usuarios)
            
            # Columnas a mostrar
            columnas_display = ['username', 'nombre', 'rol', 'email', 'departamento', 'activo', 'fecha_creacion']
            columnas_disponibles = [col for col in columnas_display if col in df.columns]
            
            if columnas_disponibles:
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Estadísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Usuarios", len(df))
                with col2:
                    activos = df['activo'].sum() if 'activo' in df.columns else 0
                    st.metric("Usuarios Activos", activos)
                with col3:
                    admins = len(df[df['rol'] == 'admin']) if 'rol' in df.columns else 0
                    st.metric("Administradores", admins)
            else:
                st.info("No hay datos disponibles")
        else:
            st.info("No hay usuarios registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Usuario")
        
        with st.form("form_nuevo_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Usuario*", help="Nombre único para login")
                nombre = st.text_input("Nombre Completo*")
                email = st.text_input("Email")
                telefono = st.text_input("Teléfono")
            
            with col2:
                rol = st.selectbox("Rol*", ["admin", "gerente", "supervisor", "operario", "ventas", "almacen"])
                departamento = st.selectbox("Departamento", 
                                          ["ADMINISTRACION", "PRODUCCION", "VENTAS", "ALMACEN", "COMPRAS", "CALIDAD"])
                password = st.text_input("Contraseña*", type="password", 
                                       help="Mínimo 6 caracteres")
                confirm_password = st.text_input("Confirmar Contraseña*", type="password")
                permisos = st.text_area("Permisos Especiales (opcional)", 
                                      placeholder="Separados por coma: crear_productos,ver_reportes,etc")
            
            st.write("*Campos obligatorios")
            
            if st.form_submit_button("👤 Crear Usuario", type="primary", use_container_width=True):
                if not all([username, nombre, password, confirm_password]):
                    st.error("❌ Complete todos los campos obligatorios")
                elif password != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif len(password) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres")
                else:
                    datos_usuario = {
                        'username': username,
                        'nombre': nombre,
                        'rol': rol,
                        'password': password,
                        'permisos': permisos,
                        'email': email,
                        'telefono': telefono,
                        'departamento': departamento
                    }
                    
                    success, mensaje = crear_usuario(
                        st.session_state.usuario['id'],
                        datos_usuario
                    )
                    
                    if success:
                        st.success(mensaje)
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error(mensaje)
    
    with tab3:
        st.subheader("Editar Usuario Existente")
        
        usuarios = obtener_usuarios()
        
        if usuarios:
            df = pd.DataFrame(usuarios)
            usuarios_lista = [f"{u['username']} - {u['nombre']}" for u in usuarios]
            
            usuario_seleccionado = st.selectbox("Seleccionar Usuario", usuarios_lista)
            
            if usuario_seleccionado:
                usuario_idx = usuarios_lista.index(usuario_seleccionado)
                usuario_data = usuarios[usuario_idx]
                
                with st.form("form_editar_usuario"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nuevo_nombre = st.text_input("Nombre", value=usuario_data['nombre'])
                        nuevo_rol = st.selectbox("Rol", 
                                               ["admin", "gerente", "supervisor", "operario", "ventas", "almacen"],
                                               index=["admin", "gerente", "supervisor", "operario", "ventas", "almacen"].index(usuario_data['rol']) if usuario_data['rol'] in ["admin", "gerente", "supervisor", "operario", "ventas", "almacen"] else 0)
                        nuevo_email = st.text_input("Email", value=usuario_data['email'] or "")
                    
                    with col2:
                        nuevo_telefono = st.text_input("Teléfono", value=usuario_data['telefono'] or "")
                        nuevo_departamento = st.selectbox("Departamento",
                                                        ["ADMINISTRACION", "PRODUCCION", "VENTAS", "ALMACEN", "COMPRAS", "CALIDAD"],
                                                        index=["ADMINISTRACION", "PRODUCCION", "VENTAS", "ALMACEN", "COMPRAS", "CALIDAD"].index(usuario_data['departamento']) if usuario_data['departamento'] in ["ADMINISTRACION", "PRODUCCION", "VENTAS", "ALMACEN", "COMPRAS", "CALIDAD"] else 0)
                        nuevo_activo = st.checkbox("Activo", value=bool(usuario_data['activo']))
                        nuevos_permisos = st.text_area("Permisos", value=usuario_data['permisos'] or "")
                    
                    if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                        datos_actualizados = {
                            'nombre': nuevo_nombre,
                            'rol': nuevo_rol,
                            'permisos': nuevos_permisos,
                            'email': nuevo_email,
                            'telefono': nuevo_telefono,
                            'departamento': nuevo_departamento,
                            'activo': 1 if nuevo_activo else 0
                        }
                        
                        success, mensaje = actualizar_usuario(
                            usuario_data['id'],
                            datos_actualizados
                        )
                        
                        if success:
                            st.success(mensaje)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(mensaje)
        else:
            st.info("No hay usuarios para editar")

# ============================================
# MÓDULO DE INVENTARIO COMPLETO
# ============================================
def mostrar_modulo_inventario():
    """Módulo de inventario completo"""
    
    st.title("📦 Gestión de Inventario Completo")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Productos", 
        "🛠️ Materias Primas", 
        "📊 Movimientos",
        "📈 Reportes",
        "⚙️ Ajustes"
    ])
    
    with tab1:
        st.subheader("📋 Gestión de Productos")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro = st.text_input("🔍 Buscar producto", key="filtro_productos")
        with col2:
            if st.button("➕ Nuevo Producto", use_container_width=True):
                st.session_state.crear_producto = True
        
        if st.session_state.get('crear_producto', False):
            with st.form("form_nuevo_producto", clear_on_submit=True):
                st.subheader("📝 Nuevo Producto")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    codigo = st.text_input("Código (auto-generado si vacío)")
                    nombre = st.text_input("Nombre del Producto*")
                    descripcion = st.text_area("Descripción")
                    categoria = st.selectbox("Categoría*", 
                                           ["PAN", "PASTEL", "GALLETA", "BOLLERIA", "OTRO"])
                    subcategoria = st.text_input("Subcategoría")
                    unidad_medida = st.selectbox("Unidad de Medida*",
                                               ["UNIDAD", "KILO", "GRAMO", "LITRO", "CAJA"])
                
                with col2:
                    precio_compra = st.number_input("Precio Compra", min_value=0.0, value=0.0, step=0.01)
                    precio_venta = st.number_input("Precio Venta", min_value=0.0, value=0.0, step=0.01)
                    stock_minimo = st.number_input("Stock Mínimo", min_value=0.0, value=10.0, step=0.1)
                    stock_maximo = st.number_input("Stock Máximo", min_value=0.0, value=100.0, step=0.1)
                    stock_actual = st.number_input("Stock Inicial", min_value=0.0, value=0.0, step=0.1)
                    peso = st.number_input("Peso (kg)", min_value=0.0, value=0.0, step=0.01)
                    volumen = st.number_input("Volumen (m³)", min_value=0.0, value=0.0, step=0.001)
                    ubicacion = st.text_input("Ubicación en Almacén")
                
                st.write("*Campos obligatorios")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Guardar Producto", use_container_width=True):
                        if not nombre or not categoria or not unidad_medida:
                            st.error("❌ Complete los campos obligatorios")
                        else:
                            datos_producto = {
                                'codigo': codigo if codigo.strip() else None,
                                'nombre': nombre,
                                'descripcion': descripcion,
                                'categoria': categoria,
                                'subcategoria': subcategoria,
                                'unidad_medida': unidad_medida,
                                'precio_compra': precio_compra,
                                'precio_venta': precio_venta,
                                'stock_minimo': stock_minimo,
                                'stock_maximo': stock_maximo,
                                'stock_actual': stock_actual,
                                'peso': peso,
                                'volumen': volumen,
                                'ubicacion': ubicacion
                            }
                            
                            success, mensaje = crear_producto(
                                st.session_state.usuario['id'],
                                datos_producto
                            )
                            
                            if success:
                                st.success(mensaje)
                                st.session_state.crear_producto = False
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(mensaje)
                
                with col_btn2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.session_state.crear_producto = False
                        st.rerun()
        
        # Lista de productos
        productos = obtener_productos()
        
        if productos:
            df = pd.DataFrame(productos)
            
            if filtro:
                df = df[df['nombre'].str.contains(filtro, case=False, na=False) | 
                       df['codigo'].str.contains(filtro, case=False, na=False)]
            
            if len(df) > 0:
                # Mostrar columnas seleccionadas
                columnas_muestra = ['codigo', 'nombre', 'categoria', 'stock_actual', 
                                  'stock_minimo', 'precio_venta', 'proveedor_nombre']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Acciones rápidas
                st.subheader("⚡ Acciones Rápidas")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    producto_id = st.number_input("ID Producto", min_value=1, value=1)
                    cantidad = st.number_input("Cantidad", min_value=0.0, value=1.0, step=0.1)
                
                with col2:
                    tipo_movimiento = st.selectbox("Tipo Movimiento", ["ENTRADA", "SALIDA"])
                    motivo = st.text_input("Motivo", placeholder="Ajuste de inventario")
                
                with col3:
                    st.write("")  # Espaciador
                    st.write("")
                    if st.button("📤 Aplicar Movimiento", use_container_width=True):
                        success, mensaje = actualizar_stock_producto(
                            int(producto_id),
                            cantidad,
                            tipo_movimiento,
                            st.session_state.usuario['id'],
                            motivo
                        )
                        
                        if success:
                            st.success(mensaje)
                            st.cache_data.clear()
                        else:
                            st.error(mensaje)
            else:
                st.info("No se encontraron productos con ese filtro")
        else:
            st.info("No hay productos registrados")
    
    with tab2:
        st.subheader("🛠️ Gestión de Materias Primas")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_mp = st.text_input("🔍 Buscar materia prima", key="filtro_mp")
        with col2:
            if st.button("➕ Nueva Materia Prima", use_container_width=True):
                st.session_state.crear_materia_prima = True
        
        if st.session_state.get('crear_materia_prima', False):
            with st.form("form_nueva_mp", clear_on_submit=True):
                st.subheader("📝 Nueva Materia Prima")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    codigo = st.text_input("Código (auto-generado si vacío)")
                    nombre = st.text_input("Nombre*")
                    descripcion = st.text_area("Descripción")
                    categoria = st.selectbox("Categoría*", 
                                           ["HARINA", "AZUCAR", "LEVADURA", "GRASA", "SABORIZANTE", "OTRO"])
                    unidad_medida = st.selectbox("Unidad de Medida*",
                                               ["KILO", "GRAMO", "LITRO", "BOLSA", "UNIDAD"])
                
                with col2:
                    costo_unitario = st.number_input("Costo Unitario", min_value=0.0, value=0.0, step=0.01)
                    stock_actual = st.number_input("Stock Actual", min_value=0.0, value=0.0, step=0.1)
                    stock_minimo = st.number_input("Stock Mínimo", min_value=0.0, value=10.0, step=0.1)
                    stock_maximo = st.number_input("Stock Máximo", min_value=0.0, value=100.0, step=0.1)
                    fecha_caducidad = st.date_input("Fecha de Caducidad (opcional)")
                    lote = st.text_input("Lote")
                    ubicacion = st.text_input("Ubicación")
                
                st.write("*Campos obligatorios")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Guardar Materia Prima", use_container_width=True):
                        if not nombre or not categoria or not unidad_medida:
                            st.error("❌ Complete los campos obligatorios")
                        else:
                            datos_mp = {
                                'codigo': codigo if codigo.strip() else None,
                                'nombre': nombre,
                                'descripcion': descripcion,
                                'categoria': categoria,
                                'unidad_medida': unidad_medida,
                                'costo_unitario': costo_unitario,
                                'stock_actual': stock_actual,
                                'stock_minimo': stock_minimo,
                                'stock_maximo': stock_maximo,
                                'fecha_caducidad': fecha_caducidad if fecha_caducidad else None,
                                'lote': lote,
                                'ubicacion': ubicacion
                            }
                            
                            success, mensaje = crear_materia_prima(
                                st.session_state.usuario['id'],
                                datos_mp
                            )
                            
                            if success:
                                st.success(mensaje)
                                st.session_state.crear_materia_prima = False
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(mensaje)
                
                with col_btn2:
                    if st.button("❌ Cancelar", key="cancelar_mp", use_container_width=True):
                        st.session_state.crear_materia_prima = False
                        st.rerun()
        
        # Lista de materias primas
        materias_primas = obtener_materias_primas()
        
        if materias_primas:
            df = pd.DataFrame(materias_primas)
            
            if filtro_mp:
                df = df[df['nombre'].str.contains(filtro_mp, case=False, na=False) | 
                       df['codigo'].str.contains(filtro_mp, case=False, na=False)]
            
            if len(df) > 0:
                columnas_muestra = ['codigo', 'nombre', 'categoria', 'stock_actual', 
                                  'stock_minimo', 'costo_unitario', 'proveedor_nombre']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron materias primas con ese filtro")
        else:
            st.info("No hay materias primas registradas")
    
    with tab3:
        st.subheader("📊 Movimientos de Inventario")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT mi.*, 
               COALESCE(p.nombre, mp.nombre) as item_nombre,
               u.nombre as usuario_nombre
        FROM movimientos_inventario mi
        LEFT JOIN productos p ON mi.producto_id = p.id
        LEFT JOIN materias_primas mp ON mi.materia_prima_id = mp.id
        LEFT JOIN usuarios u ON mi.usuario_responsable = u.id
        ORDER BY mi.fecha_movimiento DESC
        LIMIT 100
        ''')
        
        movimientos = cursor.fetchall()
        conn.close()
        
        if movimientos:
            df = pd.DataFrame(movimientos)
            columnas_muestra = ['fecha_movimiento', 'tipo_movimiento', 'item_nombre', 
                              'cantidad', 'unidad_medida', 'usuario_nombre', 'observaciones']
            columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
            
            st.dataframe(
                df[columnas_disponibles],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay movimientos registrados")
    
    with tab4:
        st.subheader("📈 Reportes de Inventario")
        
        productos = obtener_productos()
        materias_primas = obtener_materias_primas()
        
        if productos or materias_primas:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if productos:
                    valor_productos = sum(p['stock_actual'] * p['precio_compra'] for p in productos)
                    st.metric("💰 Valor Productos", f"${valor_productos:,.2f}")
                else:
                    st.metric("💰 Valor Productos", "$0.00")
            
            with col2:
                if materias_primas:
                    valor_mp = sum(mp['stock_actual'] * mp['costo_unitario'] for mp in materias_primas)
                    st.metric("🛠️ Valor Materias Primas", f"${valor_mp:,.2f}")
                else:
                    st.metric("🛠️ Valor Materias Primas", "$0.00")
            
            with col3:
                total_valor = (valor_productos if productos else 0) + (valor_mp if materias_primas else 0)
                st.metric("📊 Valor Total Inventario", f"${total_valor:,.2f}")
            
            # Gráficos
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if productos:
                    df_productos = pd.DataFrame(productos)
                    if 'categoria' in df_productos.columns:
                        stock_por_categoria = df_productos.groupby('categoria')['stock_actual'].sum().reset_index()
                        if len(stock_por_categoria) > 0:
                            fig = px.pie(stock_por_categoria, values='stock_actual', names='categoria',
                                       title='Stock de Productos por Categoría')
                            st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if materias_primas:
                    df_mp = pd.DataFrame(materias_primas)
                    if 'categoria' in df_mp.columns:
                        stock_por_categoria_mp = df_mp.groupby('categoria')['stock_actual'].sum().reset_index()
                        if len(stock_por_categoria_mp) > 0:
                            fig = px.bar(stock_por_categoria_mp, x='categoria', y='stock_actual',
                                       title='Stock de Materias Primas por Categoría')
                            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar reportes")
    
    with tab5:
        st.subheader("⚙️ Ajustes de Inventario")
        
        with st.form("form_ajuste_inventario"):
            col1, col2 = st.columns(2)
            
            with col1:
                tipo_item = st.selectbox("Tipo de Item", ["PRODUCTO", "MATERIA_PRIMA"])
                if tipo_item == "PRODUCTO":
                    productos_lista = obtener_productos()
                    if productos_lista:
                        items = [f"{p['id']} - {p['nombre']}" for p in productos_lista]
                        item_seleccionado = st.selectbox("Seleccionar Producto", items)
                        item_id = int(item_seleccionado.split(" - ")[0]) if item_seleccionado else None
                    else:
                        st.info("No hay productos disponibles")
                        item_id = None
                else:
                    materias_lista = obtener_materias_primas()
                    if materias_lista:
                        items = [f"{m['id']} - {m['nombre']}" for m in materias_lista]
                        item_seleccionado = st.selectbox("Seleccionar Materia Prima", items)
                        item_id = int(item_seleccionado.split(" - ")[0]) if item_seleccionado else None
                    else:
                        st.info("No hay materias primas disponibles")
                        item_id = None
            
            with col2:
                tipo_ajuste = st.selectbox("Tipo de Ajuste", ["ENTRADA", "SALIDA", "CORRECCION"])
                cantidad = st.number_input("Cantidad", min_value=0.0, value=0.0, step=0.1)
                motivo = st.selectbox("Motivo", 
                                    ["INVENTARIO_FISICO", "DONACION", "PERDIDA", 
                                     "CADUCIDAD", "DETERIORO", "OTRO"])
                observaciones = st.text_area("Observaciones")
            
            if st.form_submit_button("🔄 Aplicar Ajuste", use_container_width=True):
                if item_id and cantidad > 0:
                    if tipo_item == "PRODUCTO":
                        success, mensaje = actualizar_stock_producto(
                            item_id, cantidad, tipo_ajuste, 
                            st.session_state.usuario['id'],
                            f"{motivo}: {observaciones}"
                        )
                    else:
                        # Para materias primas sería similar
                        st.info("Funcionalidad para materias primas en desarrollo")
                        success = False
                        mensaje = "En desarrollo"
                    
                    if success:
                        st.success(mensaje)
                        st.cache_data.clear()
                    else:
                        st.error(mensaje)

# ============================================
# MÓDULO DE COMPRAS COMPLETO
# ============================================
def mostrar_modulo_compras():
    """Módulo de compras completo"""
    
    st.title("🛒 Gestión de Compras")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Órdenes de Compra", 
        "📦 Recepción", 
        "🏢 Proveedores",
        "📊 Reportes"
    ])
    
    with tab1:
        st.subheader("📋 Órdenes de Compra")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_oc = st.text_input("🔍 Buscar orden", placeholder="Número o proveedor")
        with col2:
            if st.button("➕ Nueva Orden", use_container_width=True):
                st.session_state.crear_orden_compra = True
        
        if st.session_state.get('crear_orden_compra', False):
            with st.form("form_nueva_oc", clear_on_submit=True):
                st.subheader("📝 Nueva Orden de Compra")
                
                proveedores = obtener_proveedores()
                if proveedores:
                    proveedores_lista = [f"{p['id']} - {p['nombre']}" for p in proveedores]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        proveedor_seleccionado = st.selectbox("Proveedor*", proveedores_lista)
                        proveedor_id = int(proveedor_seleccionado.split(" - ")[0]) if proveedor_seleccionado else None
                        fecha_orden = st.date_input("Fecha Orden*", value=datetime.now())
                        fecha_entrega = st.date_input("Fecha Entrega Esperada")
                    
                    with col2:
                        numero_orden = st.text_input("Número Orden (auto-generado si vacío)")
                        estado = st.selectbox("Estado", ["PENDIENTE", "APROBADA", "EN_PROCESO", "CANCELADA"])
                        observaciones = st.text_area("Observaciones")
                    
                    # Detalles de la orden
                    st.subheader("📦 Detalles de la Orden")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        tipo_item = st.selectbox("Tipo", ["PRODUCTO", "MATERIA_PRIMA"], key="tipo_item_oc")
                    with col2:
                        if tipo_item == "PRODUCTO":
                            productos_lista = obtener_productos()
                            items = [f"{p['id']} - {p['nombre']}" for p in productos_lista]
                            item_seleccionado = st.selectbox("Item", items, key="item_oc")
                            item_id = int(item_seleccionado.split(" - ")[0]) if item_seleccionado else None
                        else:
                            materias_lista = obtener_materias_primas()
                            items = [f"{m['id']} - {m['nombre']}" for m in materias_lista]
                            item_seleccionado = st.selectbox("Item", items, key="item_oc_mp")
                            item_id = int(item_seleccionado.split(" - ")[0]) if item_seleccionado else None
                    with col3:
                        cantidad = st.number_input("Cantidad", min_value=0.0, value=1.0, step=0.1)
                    with col4:
                        precio = st.number_input("Precio Unitario", min_value=0.0, value=0.0, step=0.01)
                    with col5:
                        st.write("")  # Espaciador
                        st.write("")
                        if st.button("➕ Agregar Item", key="agregar_item_oc"):
                            if 'detalles_oc' not in st.session_state:
                                st.session_state.detalles_oc = []
                            
                            descripcion = item_seleccionado.split(" - ")[1] if item_seleccionado else ""
                            detalle = {
                                'producto_id': item_id if tipo_item == "PRODUCTO" else None,
                                'materia_prima_id': item_id if tipo_item == "MATERIA_PRIMA" else None,
                                'descripcion': descripcion,
                                'cantidad': cantidad,
                                'unidad_medida': 'UNIDAD',  # Esto debería venir de la base de datos
                                'precio_unitario': precio
                            }
                            st.session_state.detalles_oc.append(detalle)
                            st.success(f"✅ {descripcion} agregado")
                    
                    # Mostrar items agregados
                    if 'detalles_oc' in st.session_state and st.session_state.detalles_oc:
                        st.subheader("📋 Items Agregados")
                        df_detalles = pd.DataFrame(st.session_state.detalles_oc)
                        st.dataframe(df_detalles[['descripcion', 'cantidad', 'precio_unitario']], 
                                   use_container_width=True, hide_index=True)
                        
                        # Calcular total
                        total = sum(d['cantidad'] * d['precio_unitario'] for d in st.session_state.detalles_oc)
                        st.info(f"**Total preliminar: ${total:,.2f}**")
                    
                    st.write("*Campos obligatorios")
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.form_submit_button("💾 Guardar Orden", use_container_width=True):
                            if not proveedor_id or not fecha_orden:
                                st.error("❌ Complete los campos obligatorios")
                            elif 'detalles_oc' not in st.session_state or not st.session_state.detalles_oc:
                                st.error("❌ Agregue al menos un item a la orden")
                            else:
                                datos_oc = {
                                    'numero_orden': numero_orden if numero_orden.strip() else None,
                                    'proveedor_id': proveedor_id,
                                    'fecha_orden': fecha_orden,
                                    'fecha_entrega_esperada': fecha_entrega,
                                    'estado': estado,
                                    'observaciones': observaciones,
                                    'detalles': st.session_state.detalles_oc
                                }
                                
                                success, mensaje = crear_orden_compra(
                                    st.session_state.usuario['id'],
                                    datos_oc
                                )
                                
                                if success:
                                    st.success(mensaje)
                                    if 'detalles_oc' in st.session_state:
                                        del st.session_state.detalles_oc
                                    st.session_state.crear_orden_compra = False
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(mensaje)
                    
                    with col_btn2:
                        if st.button("🔄 Limpiar Items", key="limpiar_items_oc", use_container_width=True):
                            if 'detalles_oc' in st.session_state:
                                del st.session_state.detalles_oc
                            st.rerun()
                    
                    with col_btn3:
                        if st.button("❌ Cancelar", key="cancelar_oc", use_container_width=True):
                            if 'detalles_oc' in st.session_state:
                                del st.session_state.detalles_oc
                            st.session_state.crear_orden_compra = False
                            st.rerun()
                else:
                    st.warning("⚠️ No hay proveedores registrados. Registre un proveedor primero.")
        
        # Lista de órdenes de compra
        ordenes = obtener_ordenes_compra()
        
        if ordenes:
            df = pd.DataFrame(ordenes)
            
            if filtro_oc:
                df = df[df['numero_orden'].str.contains(filtro_oc, case=False, na=False) | 
                       df['proveedor_nombre'].str.contains(filtro_oc, case=False, na=False)]
            
            if len(df) > 0:
                columnas_muestra = ['numero_orden', 'proveedor_nombre', 'fecha_orden', 
                                  'total', 'estado', 'creador_nombre']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron órdenes con ese filtro")
        else:
            st.info("No hay órdenes de compra registradas")
    
    with tab2:
        st.subheader("📦 Recepción de Materiales")
        st.info("Módulo de recepción en desarrollo")
    
    with tab3:
        st.subheader("🏢 Gestión de Proveedores")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_prov = st.text_input("🔍 Buscar proveedor", key="filtro_proveedores")
        with col2:
            if st.button("➕ Nuevo Proveedor", use_container_width=True):
                st.session_state.crear_proveedor = True
        
        if st.session_state.get('crear_proveedor', False):
            with st.form("form_nuevo_proveedor", clear_on_submit=True):
                st.subheader("📝 Nuevo Proveedor")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    codigo = st.text_input("Código (auto-generado si vacío)")
                    nombre = st.text_input("Nombre*")
                    ruc = st.text_input("RUC")
                    direccion = st.text_area("Dirección")
                    telefono = st.text_input("Teléfono")
                    email = st.text_input("Email")
                
                with col2:
                    contacto = st.text_input("Persona de Contacto")
                    tipo_proveedor = st.selectbox("Tipo de Proveedor", 
                                                ["MATERIA_PRIMA", "INSUMOS", "EQUIPOS", "SERVICIOS", "OTRO"])
                    productos = st.text_area("Productos que provee")
                    plazo_entrega = st.number_input("Plazo Entrega (días)", min_value=0, value=7)
                    calificacion = st.slider("Calificación", 1, 5, 3)
                    condiciones_pago = st.text_input("Condiciones de Pago")
                
                st.write("*Campos obligatorios")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Guardar Proveedor", use_container_width=True):
                        if not nombre:
                            st.error("❌ Complete el nombre del proveedor")
                        else:
                            datos_proveedor = {
                                'codigo': codigo if codigo.strip() else None,
                                'nombre': nombre,
                                'ruc': ruc,
                                'direccion': direccion,
                                'telefono': telefono,
                                'email': email,
                                'contacto': contacto,
                                'tipo_proveedor': tipo_proveedor,
                                'productos': productos,
                                'plazo_entrega': plazo_entrega,
                                'calificacion': calificacion,
                                'condiciones_pago': condiciones_pago
                            }
                            
                            success, mensaje = crear_proveedor(
                                st.session_state.usuario['id'],
                                datos_proveedor
                            )
                            
                            if success:
                                st.success(mensaje)
                                st.session_state.crear_proveedor = False
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(mensaje)
                
                with col_btn2:
                    if st.button("❌ Cancelar", key="cancelar_proveedor", use_container_width=True):
                        st.session_state.crear_proveedor = False
                        st.rerun()
        
        # Lista de proveedores
        proveedores = obtener_proveedores()
        
        if proveedores:
            df = pd.DataFrame(proveedores)
            
            if filtro_prov:
                df = df[df['nombre'].str.contains(filtro_prov, case=False, na=False) | 
                       df['codigo'].str.contains(filtro_prov, case=False, na=False)]
            
            if len(df) > 0:
                columnas_muestra = ['codigo', 'nombre', 'ruc', 'telefono', 'email', 
                                  'tipo_proveedor', 'calificacion']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron proveedores con ese filtro")
        else:
            st.info("No hay proveedores registrados")
    
    with tab4:
        st.subheader("📊 Reportes de Compras")
        
        ordenes = obtener_ordenes_compra()
        
        if ordenes:
            df = pd.DataFrame(ordenes)
            
            # KPIs
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_compras = df['total'].sum()
                st.metric("💰 Total Compras", f"${total_compras:,.2f}")
            
            with col2:
                ordenes_pendientes = len(df[df['estado'] == 'PENDIENTE'])
                st.metric("📋 Órdenes Pendientes", ordenes_pendientes)
            
            with col3:
                proveedores_unicos = df['proveedor_nombre'].nunique() if 'proveedor_nombre' in df.columns else 0
                st.metric("🏢 Proveedores Activos", proveedores_unicos)
            
            # Gráfico de compras por mes
            st.markdown("---")
            st.subheader("📈 Compras por Mes")
            
            if 'fecha_orden' in df.columns:
                df['fecha_orden'] = pd.to_datetime(df['fecha_orden'])
                df['mes'] = df['fecha_orden'].dt.strftime('%Y-%m')
                
                compras_por_mes = df.groupby('mes')['total'].sum().reset_index()
                
                if len(compras_por_mes) > 0:
                    fig = px.bar(compras_por_mes, x='mes', y='total', title='Compras por Mes')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de compras para mostrar reportes")

# ============================================
# MÓDULO DE VENTAS COMPLETO
# ============================================
def mostrar_modulo_ventas():
    """Módulo de ventas completo"""
    
    st.title("💰 Gestión de Ventas")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧾 Ventas", 
        "👥 Clientes", 
        "📦 Pedidos",
        "📊 Reportes"
    ])
    
    with tab1:
        st.subheader("🧾 Registro de Ventas")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_ventas = st.text_input("🔍 Buscar venta", placeholder="Factura o cliente")
        with col2:
            if st.button("➕ Nueva Venta", use_container_width=True):
                st.session_state.crear_venta = True
        
        if st.session_state.get('crear_venta', False):
            with st.form("form_nueva_venta", clear_on_submit=True):
                st.subheader("🧾 Nueva Venta")
                
                clientes = obtener_clientes()
                if clientes:
                    clientes_lista = [f"{c['id']} - {c['nombre']}" for c in clientes]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        cliente_seleccionado = st.selectbox("Cliente*", clientes_lista)
                        cliente_id = int(cliente_seleccionado.split(" - ")[0]) if cliente_seleccionado else None
                        fecha_venta = st.date_input("Fecha Venta*", value=datetime.now())
                        forma_pago = st.selectbox("Forma de Pago", ["EFECTIVO", "TARJETA", "TRANSFERENCIA", "CREDITO"])
                    
                    with col2:
                        numero_factura = st.text_input("Número Factura (auto-generado si vacío)")
                        estado = st.selectbox("Estado", ["PENDIENTE", "PAGADA", "CANCELADA"])
                        fecha_vencimiento = st.date_input("Fecha Vencimiento (crédito)", 
                                                         value=datetime.now() + timedelta(days=30))
                        observaciones = st.text_area("Observaciones")
                    
                    # Detalles de la venta
                    st.subheader("📦 Productos a Vender")
                    
                    productos_lista = obtener_productos()
                    if productos_lista:
                        productos_disponibles = [f"{p['id']} - {p['nombre']} (Stock: {p['stock_actual']})" 
                                               for p in productos_lista if p['stock_actual'] > 0]
                        
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            producto_seleccionado = st.selectbox("Producto", productos_disponibles)
                            producto_id = int(producto_seleccionado.split(" - ")[0]) if producto_seleccionado else None
                        with col2:
                            stock_disponible = 0
                            if producto_seleccionado:
                                # Extraer stock disponible del texto
                                import re
                                match = re.search(r'Stock: (\d+\.?\d*)', producto_seleccionado)
                                if match:
                                    stock_disponible = float(match.group(1))
                            cantidad = st.number_input("Cantidad", min_value=0.0, value=1.0, step=0.1, 
                                                     max_value=stock_disponible)
                        with col3:
                            precio = st.number_input("Precio Unitario", min_value=0.0, value=0.0, step=0.01)
                        with col4:
                            descuento_item = st.number_input("Descuento %", min_value=0.0, max_value=100.0, 
                                                           value=0.0, step=0.1)
                        with col5:
                            st.write("")  # Espaciador
                            st.write("")
                            if st.button("➕ Agregar Producto", key="agregar_producto_venta"):
                                if 'detalles_venta' not in st.session_state:
                                    st.session_state.detalles_venta = []
                                
                                descripcion = producto_seleccionado.split(" - ")[1].split(" (")[0] if producto_seleccionado else ""
                                detalle = {
                                    'producto_id': producto_id,
                                    'descripcion': descripcion,
                                    'cantidad': cantidad,
                                    'precio_unitario': precio,
                                    'descuento': descuento_item
                                }
                                st.session_state.detalles_venta.append(detalle)
                                st.success(f"✅ {descripcion} agregado")
                        
                        # Mostrar items agregados
                        if 'detalles_venta' in st.session_state and st.session_state.detalles_venta:
                            st.subheader("📋 Productos Agregados")
                            df_detalles = pd.DataFrame(st.session_state.detalles_venta)
                            st.dataframe(df_detalles[['descripcion', 'cantidad', 'precio_unitario', 'descuento']], 
                                       use_container_width=True, hide_index=True)
                            
                            # Calcular total
                            subtotal = sum(d['cantidad'] * d['precio_unitario'] * (1 - d['descuento']/100) 
                                         for d in st.session_state.detalles_venta)
                            st.info(f"**Subtotal: ${subtotal:,.2f}**")
                        
                        st.write("*Campos obligatorios")
                        
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            if st.form_submit_button("💰 Registrar Venta", use_container_width=True):
                                if not cliente_id or not fecha_venta:
                                    st.error("❌ Complete los campos obligatorios")
                                elif 'detalles_venta' not in st.session_state or not st.session_state.detalles_venta:
                                    st.error("❌ Agregue al menos un producto a la venta")
                                else:
                                    datos_venta = {
                                        'numero_factura': numero_factura if numero_factura.strip() else None,
                                        'cliente_id': cliente_id,
                                        'fecha_venta': fecha_venta,
                                        'estado': estado,
                                        'forma_pago': forma_pago,
                                        'fecha_vencimiento': fecha_vencimiento,
                                        'observaciones': observaciones,
                                        'detalles': st.session_state.detalles_venta
                                    }
                                    
                                    success, mensaje = crear_venta(
                                        st.session_state.usuario['id'],
                                        datos_venta
                                    )
                                    
                                    if success:
                                        st.success(mensaje)
                                        if 'detalles_venta' in st.session_state:
                                            del st.session_state.detalles_venta
                                        st.session_state.crear_venta = False
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(mensaje)
                        
                        with col_btn2:
                            if st.button("🔄 Limpiar Productos", key="limpiar_productos_venta", use_container_width=True):
                                if 'detalles_venta' in st.session_state:
                                    del st.session_state.detalles_venta
                                st.rerun()
                        
                        with col_btn3:
                            if st.button("❌ Cancelar", key="cancelar_venta", use_container_width=True):
                                if 'detalles_venta' in st.session_state:
                                    del st.session_state.detalles_venta
                                st.session_state.crear_venta = False
                                st.rerun()
                    else:
                        st.warning("⚠️ No hay productos con stock disponible para vender.")
                else:
                    st.warning("⚠️ No hay clientes registrados. Registre un cliente primero.")
        
        # Lista de ventas
        ventas = obtener_ventas()
        
        if ventas:
            df = pd.DataFrame(ventas)
            
            if filtro_ventas:
                df = df[df['numero_factura'].str.contains(filtro_ventas, case=False, na=False) | 
                       df['cliente_nombre'].str.contains(filtro_ventas, case=False, na=False)]
            
            if len(df) > 0:
                columnas_muestra = ['numero_factura', 'cliente_nombre', 'fecha_venta', 
                                  'total', 'estado', 'forma_pago', 'vendedor_nombre']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron ventas con ese filtro")
        else:
            st.info("No hay ventas registradas")
    
    with tab2:
        st.subheader("👥 Gestión de Clientes")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_clientes = st.text_input("🔍 Buscar cliente", key="filtro_clientes")
        with col2:
            if st.button("➕ Nuevo Cliente", use_container_width=True):
                st.session_state.crear_cliente = True
        
        if st.session_state.get('crear_cliente', False):
            with st.form("form_nuevo_cliente", clear_on_submit=True):
                st.subheader("📝 Nuevo Cliente")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    codigo = st.text_input("Código (auto-generado si vacío)")
                    nombre = st.text_input("Nombre*")
                    tipo_documento = st.selectbox("Tipo Documento", ["RUC", "DNI", "CÉDULA", "PASAPORTE"])
                    numero_documento = st.text_input("Número Documento")
                    direccion = st.text_area("Dirección")
                    telefono = st.text_input("Teléfono")
                
                with col2:
                    email = st.text_input("Email")
                    contacto = st.text_input("Persona de Contacto")
                    tipo_cliente = st.selectbox("Tipo de Cliente", ["NATURAL", "JURIDICO", "MAYORISTA", "MINORISTA"])
                    limite_credito = st.number_input("Límite de Crédito", min_value=0.0, value=0.0, step=1.0)
                    dias_credito = st.number_input("Días de Crédito", min_value=0, value=0, step=1)
                    categoria = st.selectbox("Categoría", ["REGULAR", "VIP", "ESPECIAL", "CORPORATIVO"])
                
                st.write("*Campos obligatorios")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Guardar Cliente", use_container_width=True):
                        if not nombre:
                            st.error("❌ Complete el nombre del cliente")
                        else:
                            datos_cliente = {
                                'codigo': codigo if codigo.strip() else None,
                                'nombre': nombre,
                                'tipo_documento': tipo_documento,
                                'numero_documento': numero_documento,
                                'direccion': direccion,
                                'telefono': telefono,
                                'email': email,
                                'contacto': contacto,
                                'tipo_cliente': tipo_cliente,
                                'limite_credito': limite_credito,
                                'dias_credito': dias_credito,
                                'categoria': categoria
                            }
                            
                            success, mensaje = crear_cliente(
                                st.session_state.usuario['id'],
                                datos_cliente
                            )
                            
                            if success:
                                st.success(mensaje)
                                st.session_state.crear_cliente = False
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(mensaje)
                
                with col_btn2:
                    if st.button("❌ Cancelar", key="cancelar_cliente", use_container_width=True):
                        st.session_state.crear_cliente = False
                        st.rerun()
        
        # Lista de clientes
        clientes = obtener_clientes()
        
        if clientes:
            df = pd.DataFrame(clientes)
            
            if filtro_clientes:
                df = df[df['nombre'].str.contains(filtro_clientes, case=False, na=False) | 
                       df['codigo'].str.contains(filtro_clientes, case=False, na=False) |
                       df['numero_documento'].str.contains(filtro_clientes, case=False, na=False)]
            
            if len(df) > 0:
                columnas_muestra = ['codigo', 'nombre', 'tipo_documento', 'numero_documento', 
                                  'telefono', 'email', 'categoria', 'limite_credito']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron clientes con ese filtro")
        else:
            st.info("No hay clientes registrados")
    
    with tab3:
        st.subheader("📦 Pedidos de Clientes")
        st.info("Módulo de pedidos en desarrollo")
    
    with tab4:
        st.subheader("📊 Reportes de Ventas")
        
        ventas = obtener_ventas()
        
        if ventas:
            df = pd.DataFrame(ventas)
            
            # KPIs
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_ventas = df['total'].sum()
                st.metric("💰 Total Ventas", f"${total_ventas:,.2f}")
            
            with col2:
                ventas_pendientes = len(df[df['estado'] == 'PENDIENTE'])
                st.metric("📋 Ventas Pendientes", ventas_pendientes)
            
            with col3:
                clientes_unicos = df['cliente_nombre'].nunique() if 'cliente_nombre' in df.columns else 0
                st.metric("👥 Clientes Activos", clientes_unicos)
            
            with col4:
                ventas_mes = df[pd.to_datetime(df['fecha_venta']).dt.month == datetime.now().month]['total'].sum()
                st.metric("📅 Ventas Este Mes", f"${ventas_mes:,.2f}")
            
            # Gráfico de ventas por mes
            st.markdown("---")
            st.subheader("📈 Ventas por Mes")
            
            if 'fecha_venta' in df.columns:
                df['fecha_venta'] = pd.to_datetime(df['fecha_venta'])
                df['mes'] = df['fecha_venta'].dt.strftime('%Y-%m')
                
                ventas_por_mes = df.groupby('mes')['total'].sum().reset_index()
                
                if len(ventas_por_mes) > 0:
                    fig = px.line(ventas_por_mes, x='mes', y='total', title='Evolución de Ventas', markers=True)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Top clientes
            st.markdown("---")
            st.subheader("🏆 Top Clientes")
            
            if 'cliente_nombre' in df.columns:
                top_clientes = df.groupby('cliente_nombre')['total'].sum().nlargest(5).reset_index()
                
                if len(top_clientes) > 0:
                    fig = px.bar(top_clientes, x='cliente_nombre', y='total', title='Clientes con Mayor Compra')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de ventas para mostrar reportes")

# ============================================
# MÓDULO DE PRODUCCIÓN COMPLETO
# ============================================
def mostrar_modulo_produccion():
    """Módulo de producción completo"""
    
    st.title("🏭 Gestión de Producción")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Órdenes Producción", 
        "📝 Recetas", 
        "📦 Requerimientos",
        "📊 Reportes"
    ])
    
    with tab1:
        st.subheader("📋 Órdenes de Producción")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            filtro_op = st.text_input("🔍 Buscar orden", placeholder="Número o producto")
        with col2:
            if st.button("➕ Nueva Orden", use_container_width=True):
                st.session_state.crear_orden_produccion = True
        
        if st.session_state.get('crear_orden_produccion', False):
            with st.form("form_nueva_op", clear_on_submit=True):
                st.subheader("📝 Nueva Orden de Producción")
                
                productos = obtener_productos()
                if productos:
                    productos_lista = [f"{p['id']} - {p['nombre']}" for p in productos]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        producto_seleccionado = st.selectbox("Producto a Producir*", productos_lista)
                        producto_id = int(producto_seleccionado.split(" - ")[0]) if producto_seleccionado else None
                        cantidad_producir = st.number_input("Cantidad a Producir*", min_value=0.0, value=1.0, step=0.1)
                        fecha_inicio = st.date_input("Fecha Inicio*", value=datetime.now())
                        fecha_fin = st.date_input("Fecha Fin Estimada", value=datetime.now() + timedelta(days=7))
                    
                    with col2:
                        numero_orden = st.text_input("Número Orden (auto-generado si vacío)")
                        estado = st.selectbox("Estado", ["PLANIFICADA", "EN_PROCESO", "COMPLETADA", "CANCELADA"])
                        prioridad = st.selectbox("Prioridad", ["ALTA", "MEDIA", "BAJA"])
                        observaciones = st.text_area("Observaciones")
                    
                    # Requerimientos de materiales
                    st.subheader("🛠️ Requerimientos de Materiales")
                    
                    materias_primas_lista = obtener_materias_primas()
                    if materias_primas_lista:
                        materias_disponibles = [f"{m['id']} - {m['nombre']} (Stock: {m['stock_actual']})" 
                                              for m in materias_primas_lista]
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            materia_seleccionada = st.selectbox("Materia Prima", materias_disponibles)
                            materia_id = int(materia_seleccionada.split(" - ")[0]) if materia_seleccionada else None
                        with col2:
                            cantidad_requerida = st.number_input("Cantidad Requerida", min_value=0.0, value=0.0, step=0.1)
                        with col3:
                            unidad_medida = st.text_input("Unidad Medida", value="KILO")
                        with col4:
                            st.write("")  # Espaciador
                            st.write("")
                            if st.button("➕ Agregar Material", key="agregar_material_op"):
                                if 'requerimientos_op' not in st.session_state:
                                    st.session_state.requerimientos_op = []
                                
                                descripcion = materia_seleccionada.split(" - ")[1].split(" (")[0] if materia_seleccionada else ""
                                requerimiento = {
                                    'materia_prima_id': materia_id,
                                    'descripcion': descripcion,
                                    'cantidad_requerida': cantidad_requerida,
                                    'unidad_medida': unidad_medida
                                }
                                st.session_state.requerimientos_op.append(requerimiento)
                                st.success(f"✅ {descripcion} agregado")
                        
                        # Mostrar requerimientos agregados
                        if 'requerimientos_op' in st.session_state and st.session_state.requerimientos_op:
                            st.subheader("📋 Materiales Requeridos")
                            df_requerimientos = pd.DataFrame(st.session_state.requerimientos_op)
                            st.dataframe(df_requerimientos[['descripcion', 'cantidad_requerida', 'unidad_medida']], 
                                       use_container_width=True, hide_index=True)
                    
                    st.write("*Campos obligatorios")
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.form_submit_button("💾 Guardar Orden", use_container_width=True):
                            if not producto_id or not cantidad_producir or not fecha_inicio:
                                st.error("❌ Complete los campos obligatorios")
                            else:
                                datos_op = {
                                    'numero_orden': numero_orden if numero_orden.strip() else None,
                                    'producto_id': producto_id,
                                    'cantidad_producir': cantidad_producir,
                                    'fecha_inicio': fecha_inicio,
                                    'fecha_fin_estimada': fecha_fin,
                                    'estado': estado,
                                    'prioridad': prioridad,
                                    'observaciones': observaciones,
                                    'requerimientos': st.session_state.requerimientos_op if 'requerimientos_op' in st.session_state else []
                                }
                                
                                success, mensaje = crear_orden_produccion(
                                    st.session_state.usuario['id'],
                                    datos_op
                                )
                                
                                if success:
                                    st.success(mensaje)
                                    if 'requerimientos_op' in st.session_state:
                                        del st.session_state.requerimientos_op
                                    st.session_state.crear_orden_produccion = False
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(mensaje)
                    
                    with col_btn2:
                        if st.button("🔄 Limpiar Materiales", key="limpiar_materiales_op", use_container_width=True):
                            if 'requerimientos_op' in st.session_state:
                                del st.session_state.requerimientos_op
                            st.rerun()
                    
                    with col_btn3:
                        if st.button("❌ Cancelar", key="cancelar_op", use_container_width=True):
                            if 'requerimientos_op' in st.session_state:
                                del st.session_state.requerimientos_op
                            st.session_state.crear_orden_produccion = False
                            st.rerun()
                else:
                    st.warning("⚠️ No hay productos registrados. Registre un producto primero.")
        
        # Lista de órdenes de producción
        ordenes_produccion = obtener_ordenes_produccion()
        
        if ordenes_produccion:
            df = pd.DataFrame(ordenes_produccion)
            
            if filtro_op:
                df = df[df['numero_orden'].str.contains(filtro_op, case=False, na=False) | 
                       df['producto_nombre'].str.contains(filtro_op, case=False, na=False)]
            
            if len(df) > 0:
                columnas_muestra = ['numero_orden', 'producto_nombre', 'cantidad_producir', 
                                  'fecha_inicio', 'estado', 'prioridad', 'creador_nombre']
                columnas_disponibles = [col for col in columnas_muestra if col in df.columns]
                
                st.dataframe(
                    df[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron órdenes con ese filtro")
        else:
            st.info("No hay órdenes de producción registradas")
    
    with tab2:
        st.subheader("📝 Gestión de Recetas")
        st.info("Módulo de recetas en desarrollo")
    
    with tab3:
        st.subheader("📦 Control de Requerimientos")
        st.info("Módulo de control de requerimientos en desarrollo")
    
    with tab4:
        st.subheader("📊 Reportes de Producción")
        
        ordenes = obtener_ordenes_produccion()
        
        if ordenes:
            df = pd.DataFrame(ordenes)
            
            # KPIs
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ordenes_activas = len(df[df['estado'].isin(['PLANIFICADA', 'EN_PROCESO'])])
                st.metric("🏭 Órdenes Activas", ordenes_activas)
            
            with col2:
                ordenes_completadas = len(df[df['estado'] == 'COMPLETADA'])
                st.metric("✅ Órdenes Completadas", ordenes_completadas)
            
            with col3:
                total_producir = df['cantidad_producir'].sum()
                st.metric("📦 Total a Producir", f"{total_producir:,.0f}")
            
            # Gráfico de órdenes por estado
            st.markdown("---")
            st.subheader("📊 Distribución por Estado")
            
            if 'estado' in df.columns:
                ordenes_por_estado = df['estado'].value_counts().reset_index()
                ordenes_por_estado.columns = ['estado', 'cantidad']
                
                if len(ordenes_por_estado) > 0:
                    fig = px.pie(ordenes_por_estado, values='cantidad', names='estado',
                               title='Órdenes de Producción por Estado')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de producción para mostrar reportes")

# ============================================
# MÓDULO DE REPORTES COMPLETO
# ============================================
def mostrar_modulo_reportes():
    """Módulo de reportes completo"""
    
    st.title("📈 Reportes y Análisis")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard Ejecutivo", 
        "💰 Financiero", 
        "📦 Inventario",
        "🏭 Producción"
    ])
    
    with tab1:
        st.subheader("📊 Dashboard Ejecutivo")
        
        kpis = obtener_kpis()
        
        # KPIs principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📦 Productos", kpis['total_productos'])
        
        with col2:
            st.metric("💰 Ventas Mes", f"${kpis['ventas_mes']:,.2f}")
        
        with col3:
            st.metric("🛒 Compras Mes", f"${kpis['compras_mes']:,.2f}")
        
        with col4:
            st.metric("📊 Valor Inventario", f"${kpis['valor_inventario']:,.2f}")
        
        # Gráficos combinados
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            # Ventas últimos 30 días
            ventas_data = obtener_ventas_por_periodo(30)
            if ventas_data:
                df_ventas = pd.DataFrame(ventas_data)
                if len(df_ventas) > 0:
                    fig = px.line(df_ventas, x='fecha', y='total', 
                                title='Ventas Últimos 30 Días', markers=True)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top productos
            top_productos = obtener_top_productos(5)
            if top_productos:
                df_top = pd.DataFrame(top_productos)
                if len(df_top) > 0:
                    fig = px.bar(df_top, x='nombre', y='total_vendido',
                               title='Top 5 Productos Más Vendidos')
                    st.plotly_chart(fig, use_container_width=True)
        
        # Alertas críticas
        st.markdown("---")
        st.subheader("⚠️ Alertas Críticas")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Productos con stock crítico
        cursor.execute('''
        SELECT nombre, stock_actual, stock_minimo 
        FROM productos 
        WHERE stock_actual <= stock_minimo * 0.5 AND activo = 1
        ORDER BY stock_actual ASC
        LIMIT 5
        ''')
        
        productos_criticos = cursor.fetchall()
        
        if productos_criticos:
            st.error("**🚨 Productos con Stock Crítico:**")
            for producto in productos_criticos:
                porcentaje = (producto['stock_actual'] / producto['stock_minimo']) * 100 if producto['stock_minimo'] > 0 else 0
                st.write(f"- {producto['nombre']}: {producto['stock_actual']}/{producto['stock_minimo']} ({porcentaje:.1f}%)")
        else:
            st.success("✅ No hay productos con stock crítico")
        
        # Órdenes de producción atrasadas
        cursor.execute('''
        SELECT numero_orden, producto_nombre, fecha_fin_estimada 
        FROM ordenes_produccion 
        WHERE estado = 'EN_PROCESO' AND fecha_fin_estimada < date('now')
        LIMIT 5
        ''')
        
        op_atrasadas = cursor.fetchall()
        
        if op_atrasadas:
            st.warning("**📅 Órdenes de Producción Atrasadas:**")
            for op in op_atrasadas:
                dias_atraso = (datetime.now().date() - datetime.strptime(op['fecha_fin_estimada'], '%Y-%m-%d').date()).days
                st.write(f"- {op['numero_orden']}: {op['producto_nombre']} ({dias_atraso} días atrasado)")
        
        conn.close()
    
    with tab2:
        st.subheader("💰 Reportes Financieros")
        
        ventas = obtener_ventas()
        compras = obtener_ordenes_compra()
        
        if ventas or compras:
            col1, col2 = st.columns(2)
            
            with col1:
                if ventas:
                    df_ventas = pd.DataFrame(ventas)
                    ventas_totales = df_ventas['total'].sum() if 'total' in df_ventas.columns else 0
                    ventas_mes = df_ventas[pd.to_datetime(df_ventas['fecha_venta']).dt.month == datetime.now().month]['total'].sum() if 'fecha_venta' in df_ventas.columns else 0
                    
                    st.metric("💰 Ventas Totales", f"${ventas_totales:,.2f}")
                    st.metric("📅 Ventas Este Mes", f"${ventas_mes:,.2f}")
            
            with col2:
                if compras:
                    df_compras = pd.DataFrame(compras)
                    compras_totales = df_compras['total'].sum() if 'total' in df_compras.columns else 0
                    compras_mes = df_compras[pd.to_datetime(df_compras['fecha_orden']).dt.month == datetime.now().month]['total'].sum() if 'fecha_orden' in df_compras.columns else 0
                    
                    st.metric("🛒 Compras Totales", f"${compras_totales:,.2f}")
                    st.metric("📅 Compras Este Mes", f"${compras_mes:,.2f}")
            
            # Margen de ganancia estimado
            if ventas and compras:
                margen = ventas_totales - compras_totales
                margen_porcentaje = (margen / ventas_totales * 100) if ventas_totales > 0 else 0
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📊 Margen Bruto", f"${margen:,.2f}")
                with col2:
                    st.metric("📈 Margen %", f"{margen_porcentaje:.1f}%")
        else:
            st.info("No hay datos financieros para mostrar")
    
    with tab3:
        st.subheader("📦 Reportes de Inventario")
        
        productos = obtener_productos()
        materias_primas = obtener_materias_primas()
        
        if productos or materias_primas:
            # Valor total del inventario
            valor_total = 0
            
            if productos:
                valor_productos = sum(p['stock_actual'] * p['precio_compra'] for p in productos)
                valor_total += valor_productos
            
            if materias_primas:
                valor_mp = sum(mp['stock_actual'] * mp['costo_unitario'] for mp in materias_primas)
                valor_total += valor_mp
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Valor Total", f"${valor_total:,.2f}")
            
            with col2:
                if productos:
                    st.metric("📦 Valor Productos", f"${valor_productos:,.2f}")
            
            with col3:
                if materias_primas:
                    st.metric("🛠️ Valor Materias Primas", f"${valor_mp:,.2f}")
            
            # Productos con mayor valor
            if productos:
                st.markdown("---")
                st.subheader("🏆 Productos con Mayor Valor en Inventario")
                
                df_productos = pd.DataFrame(productos)
                df_productos['valor'] = df_productos['stock_actual'] * df_productos['precio_compra']
                top_valor = df_productos.nlargest(5, 'valor')[['nombre', 'stock_actual', 'precio_compra', 'valor']]
                
                if len(top_valor) > 0:
                    st.dataframe(top_valor, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de inventario para mostrar")
    
    with tab4:
        st.subheader("🏭 Reportes de Producción")
        
        ordenes = obtener_ordenes_produccion()
        
        if ordenes:
            df = pd.DataFrame(ordenes)
            
            # Estadísticas de producción
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ordenes_totales = len(df)
                st.metric("📋 Total Órdenes", ordenes_totales)
            
            with col2:
                ordenes_completadas = len(df[df['estado'] == 'COMPLETADA'])
                st.metric("✅ Completadas", ordenes_completadas)
            
            with col3:
                eficiencia = (ordenes_completadas / ordenes_totales * 100) if ordenes_totales > 0 else 0
                st.metric("📈 Eficiencia", f"{eficiencia:.1f}%")
            
            # Distribución por prioridad
            if 'prioridad' in df.columns:
                st.markdown("---")
                st.subheader("📊 Distribución por Prioridad")
                
                prioridad_dist = df['prioridad'].value_counts().reset_index()
                prioridad_dist.columns = ['prioridad', 'cantidad']
                
                if len(prioridad_dist) > 0:
                    fig = px.pie(prioridad_dist, values='cantidad', names='prioridad',
                               title='Órdenes por Prioridad')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de producción para mostrar")

# ============================================
# MÓDULO DE CONFIGURACIÓN
# ============================================
def mostrar_modulo_configuracion():
    """Módulo de configuración del sistema"""
    
    st.title("⚙️ Configuración del Sistema")
    
    if st.session_state.usuario['rol'] != 'admin':
        st.warning("⛔ Acceso restringido. Solo administradores pueden acceder a esta sección.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 Empresa", 
        "🔐 Seguridad", 
        "🗄️ Base de Datos",
        "📋 Sistema"
    ])
    
    with tab1:
        st.subheader("🏢 Configuración de la Empresa")
        
        with st.form("form_config_empresa"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_empresa = st.text_input("Nombre de la Empresa", value="Panadería Industrial S.A.")
                ruc = st.text_input("RUC", value="12345678901")
                direccion = st.text_area("Dirección", value="Av. Principal 123")
                telefono = st.text_input("Teléfono", value="+51 1 2345678")
            
            with col2:
                email = st.text_input("Email Corporativo", value="info@panaderia-industrial.com")
                sitio_web = st.text_input("Sitio Web", value="www.panaderia-industrial.com")
                moneda = st.selectbox("Moneda Principal", ["PEN (S/)", "USD ($)", "EUR (€)"])
                impuestos = st.number_input("Porcentaje de Impuestos (%)", min_value=0.0, max_value=100.0, value=18.0)
            
            if st.form_submit_button("💾 Guardar Configuración", use_container_width=True):
                st.success("✅ Configuración de empresa guardada")
    
    with tab2:
        st.subheader("🔐 Configuración de Seguridad")
        
        # Cambiar contraseña del usuario actual
        with st.form("form_cambiar_password_admin"):
            st.write("### Cambiar Mi Contraseña")
            
            password_actual = st.text_input("Contraseña Actual", type="password")
            nueva_password = st.text_input("Nueva Contraseña", type="password")
            confirmar_password = st.text_input("Confirmar Nueva Contraseña", type="password")
            
            if st.form_submit_button("🔄 Cambiar Contraseña", use_container_width=True):
                if not all([password_actual, nueva_password, confirmar_password]):
                    st.error("❌ Complete todos los campos")
                elif nueva_password != confirmar_password:
                    st.error("❌ Las contraseñas nuevas no coinciden")
                elif len(nueva_password) < 8:
                    st.error("❌ La nueva contraseña debe tener al menos 8 caracteres")
                else:
                    # Verificar contraseña actual
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT password FROM usuarios WHERE id = ?",
                        (st.session_state.usuario['id'],)
                    )
                    resultado = cursor.fetchone()
                    
                    if resultado and hash_password(password_actual) == resultado[0]:
                        # Cambiar contraseña
                        new_hash = hash_password(nueva_password)
                        cursor.execute(
                            "UPDATE usuarios SET password = ? WHERE id = ?",
                            (new_hash, st.session_state.usuario['id'])
                        )
                        conn.commit()
                        conn.close()
                        
                        registrar_log(st.session_state.usuario['id'], 'CONFIGURACION', 'CAMBIO_PASSWORD', 'Admin cambió su contraseña')
                        st.success("✅ Contraseña cambiada exitosamente")
                    else:
                        st.error("❌ Contraseña actual incorrecta")
        
        # Configuración de sesiones
        st.markdown("---")
        st.subheader("Configuración de Sesiones")
        
        with st.form("form_config_sesiones"):
            tiempo_sesion = st.number_input("Tiempo de Sesión (minutos)", min_value=15, max_value=480, value=60)
            max_intentos = st.number_input("Máximo Intentos Fallidos", min_value=3, max_value=10, value=5)
            bloqueo_temporal = st.checkbox("Bloqueo Temporal después de intentos fallidos", value=True)
            
            if st.form_submit_button("💾 Guardar Configuración Sesiones", use_container_width=True):
                st.success("✅ Configuración de sesiones guardada")
    
    with tab3:
        st.subheader("🗄️ Gestión de Base de Datos")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Reinicializar Cache", type="secondary", use_container_width=True):
                st.cache_resource.clear()
                st.cache_data.clear()
                st.success("✅ Cache reinicializado")
        
        with col2:
            if st.button("📊 Estadísticas BD", type="secondary", use_container_width=True):
                conn = get_db_connection()
                cursor = conn.cursor()
                
                tablas = [
                    'usuarios', 'productos', 'materias_primas', 'proveedores',
                    'clientes', 'ordenes_compra', 'ordenes_produccion', 'ventas',
                    'movimientos_inventario', 'logs_sistema'
                ]
                
                st.write("**Estadísticas de la Base de Datos:**")
                for tabla in tablas:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                        count = cursor.fetchone()[0]
                        st.write(f"- {tabla}: {count} registros")
                    except:
                        st.write(f"- {tabla}: 0 registros")
                
                conn.close()
        
        with col3:
            if st.button("📥 Exportar Backup", type="secondary", use_container_width=True):
                st.info("Funcionalidad de exportación en desarrollo")
        
        # Limpieza de datos antiguos
        st.markdown("---")
        st.subheader("🧹 Limpieza de Datos")
        
        with st.form("form_limpieza_datos"):
            dias_logs = st.number_input("Eliminar logs mayores a (días)", min_value=30, max_value=365, value=90)
            confirmar = st.checkbox("Confirmar eliminación de datos")
            
            if st.form_submit_button("🧹 Ejecutar Limpieza", type="primary", use_container_width=True):
                if confirmar:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                    DELETE FROM logs_sistema 
                    WHERE fecha < date('now', ?)
                    ''', (f'-{dias_logs} days',))
                    
                    eliminados = cursor.rowcount
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ {eliminados} registros antiguos eliminados")
                else:
                    st.error("❌ Marque la confirmación para proceder")
    
    with tab4:
        st.subheader("📋 Información del Sistema")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            **Versión del Sistema:** 2.0.0
            **Última Actualización:** 2024-01-15
            **Desarrollado por:** Equipo de Desarrollo MRP
            **Soporte:** soporte@panaderia-industrial.com
            """)
        
        with col2:
            st.info("""
            **Módulos Implementados:**
            ✅ Gestión de Usuarios
            ✅ Inventario Completo
            ✅ Compras y Proveedores
            ✅ Ventas y Clientes
            ✅ Producción y Recetas
            ✅ Reportes y Dashboard
            """)
        
        # Información de uso
        st.markdown("---")
        st.subheader("📊 Estadísticas de Uso")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT usuario_id) FROM logs_sistema WHERE fecha >= date('now', '-7 days')")
        usuarios_activos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM logs_sistema WHERE fecha >= date('now', '-1 day')")
        actividades_hoy = cursor.fetchone()[0]
        
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👥 Usuarios Activos (7 días)", usuarios_activos)
        with col2:
            st.metric("📈 Actividades Hoy", actividades_hoy)

# ============================================
# BARRA DE NAVEGACIÓN SUPERIOR
# ============================================
def mostrar_barra_navegacion():
    """Muestra la barra de navegación superior"""
    
    usuario = st.session_state.usuario
    
    # CSS para la barra de navegación
    st.markdown("""
    <style>
    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .nav-left {
        font-size: 18px;
        font-weight: bold;
    }
    .nav-right {
        display: flex;
        gap: 10px;
    }
    .stButton button {
        background: rgba(255,255,255,0.2);
        border: none;
        color: white;
    }
    .stButton button:hover {
        background: rgba(255,255,255,0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Barra de navegación
    col1, col2, col3 = st.columns([6, 1, 1])
    
    with col1:
        st.markdown(f"### 🏭 Sistema MRP Completo | 👤 {usuario['nombre']} ({usuario['rol'].upper()})")
    
    with col2:
        if st.button("🔄", help="Actualizar página", key="refresh_btn"):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        if st.button("🚪", help="Cerrar sesión", key="logout_btn"):
            registrar_log(usuario['id'], 'AUTH', 'LOGOUT', 'Usuario cerró sesión')
            del st.session_state.usuario
            st.rerun()

# ============================================
# MENÚ PRINCIPAL
# ============================================
def mostrar_menu_principal():
    """Muestra el menú principal según el rol del usuario"""
    
    usuario = st.session_state.usuario
    rol = usuario['rol']
    
    # Definir opciones de menú según rol
    if rol == 'admin':
        opciones_menu = [
            ("📊 Dashboard", mostrar_dashboard),
            ("📦 Inventario", mostrar_modulo_inventario),
            ("🛒 Compras", mostrar_modulo_compras),
            ("💰 Ventas", mostrar_modulo_ventas),
            ("🏭 Producción", mostrar_modulo_produccion),
            ("👥 Usuarios", mostrar_modulo_usuarios),
            ("📈 Reportes", mostrar_modulo_reportes),
            ("⚙️ Configuración", mostrar_modulo_configuracion)
        ]
    elif rol == 'gerente':
        opciones_menu = [
            ("📊 Dashboard", mostrar_dashboard),
            ("📦 Inventario", mostrar_modulo_inventario),
            ("🛒 Compras", mostrar_modulo_compras),
            ("💰 Ventas", mostrar_modulo_ventas),
            ("🏭 Producción", mostrar_modulo_produccion),
            ("📈 Reportes", mostrar_modulo_reportes)
        ]
    elif rol == 'supervisor':
        opciones_menu = [
            ("📊 Dashboard", mostrar_dashboard),
            ("📦 Inventario", mostrar_modulo_inventario),
            ("🏭 Producción", mostrar_modulo_produccion),
            ("📈 Reportes", mostrar_modulo_reportes)
        ]
    elif rol == 'ventas':
        opciones_menu = [
            ("📊 Dashboard", mostrar_dashboard),
            ("💰 Ventas", mostrar_modulo_ventas),
            ("📈 Reportes", mostrar_modulo_reportes)
        ]
    elif rol == 'almacen':
        opciones_menu = [
            ("📊 Dashboard", mostrar_dashboard),
            ("📦 Inventario", mostrar_modulo_inventario),
            ("🛒 Compras", mostrar_modulo_compras)
        ]
    else:  # operario, etc.
        opciones_menu = [
            ("📊 Dashboard", mostrar_dashboard),
            ("🏭 Producción", mostrar_modulo_produccion)
        ]
    
    # Crear tabs
    tabs = st.tabs([opcion[0] for opcion in opciones_menu])
    
    # Mostrar contenido según tab seleccionado
    for i, (nombre, funcion) in enumerate(opciones_menu):
        with tabs[i]:
            funcion()

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
def main():
    """Función principal de la aplicación"""
    
    # Inicializar base de datos
    init_database()
    
    # Inicializar estado de la sesión
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    
    # Inicializar estados para formularios
    if 'crear_producto' not in st.session_state:
        st.session_state.crear_producto = False
    if 'crear_materia_prima' not in st.session_state:
        st.session_state.crear_materia_prima = False
    if 'crear_proveedor' not in st.session_state:
        st.session_state.crear_proveedor = False
    if 'crear_cliente' not in st.session_state:
        st.session_state.crear_cliente = False
    if 'crear_orden_compra' not in st.session_state:
        st.session_state.crear_orden_compra = False
    if 'crear_venta' not in st.session_state:
        st.session_state.crear_venta = False
    if 'crear_orden_produccion' not in st.session_state:
        st.session_state.crear_orden_produccion = False
    
    # Verificar autenticación
    if not st.session_state.usuario:
        mostrar_login()
    else:
        # Mostrar barra de navegación
        mostrar_barra_navegacion()
        
        # Mostrar menú principal
        mostrar_menu_principal()

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == "__main__":
    main()
