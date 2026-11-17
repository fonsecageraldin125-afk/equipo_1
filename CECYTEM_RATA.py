
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import mysql.connector
import hashlib
import hmac
from datetime import date, datetime

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    GRAFICAS_DISPONIBLES = True
except ImportError:
    GRAFICAS_DISPONIBLES = False




DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cecytem"
}

AZUL = "#0D3B66"
AZUL_BOTON = "#1565C0"
AZUL_CLARO = "#E3F2FD"

AZUL_MEDIO = "#2563EB"
AZUL_SUAVE = "#DBEAFE"

FONDO = "#F1F5F9"
BLANCO = "#FFFFFF"
TEXTO = "#1E293B"
GRIS = "#64748B"
ROJO = "#B91C1C"
NARANJA = "#EA580C"

GRUPOS_BASE = [
    "1A", "1B", "1C",
    "2A", "2B", "2C",
    "3A", "3B", "3C"
]

ESTADOS_ASISTENCIA = [
    "Presente", "Falta", "Retardo", "Justificante"
]


def conectar():
    return mysql.connector.connect(**DB_CONFIG)


def verificar_password(password, guardada):
    if guardada is None:
        return False

    guardada = str(guardada)

    if hmac.compare_digest(password, guardada):
        return True

    sha = hashlib.sha256(password.encode("utf-8")).hexdigest()

    if hmac.compare_digest(sha, guardada.lower()):
        return True

    if ":" in guardada:
        sal, hash_guardado = guardada.split(":", 1)

        candidatos = [
            hashlib.sha256((password + sal).encode()).hexdigest(),
            hashlib.sha256((sal + password).encode()).hexdigest()
        ]

        if any(
            hmac.compare_digest(x, hash_guardado.lower())
            for x in candidatos
        ):
            return True

    return False


def crear_tablas():
    """Crea tablas auxiliares sin borrar tablas existentes."""
    conexion = conectar()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grupos_escolares (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(30) NOT NULL UNIQUE,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS docente_grupos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                docente VARCHAR(100) NOT NULL,
                grupo_id INT NOT NULL,
                UNIQUE KEY asignacion_unica (docente, grupo_id),
                FOREIGN KEY (grupo_id)
                    REFERENCES grupos_escolares(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alumnos_escolares (
                id INT AUTO_INCREMENT PRIMARY KEY,
                grupo_id INT NOT NULL,
                numero_lista INT NOT NULL,
                nombre VARCHAR(150) NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                UNIQUE KEY alumno_lista (grupo_id, numero_lista),
                FOREIGN KEY (grupo_id)
                    REFERENCES grupos_escolares(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asistencias_escolares (
                id INT AUTO_INCREMENT PRIMARY KEY,
                alumno_id INT NOT NULL,
                grupo_id INT NOT NULL,
                fecha DATE NOT NULL,
                estado VARCHAR(30) NOT NULL,
                docente VARCHAR(100) NOT NULL,
                observaciones TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY asistencia_diaria (alumno_id, fecha),
                FOREIGN KEY (alumno_id)
                    REFERENCES alumnos_escolares(id),
                FOREIGN KEY (grupo_id)
                    REFERENCES grupos_escolares(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_escolares (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                alumno VARCHAR(150) NOT NULL,
                grupo VARCHAR(50),
                fecha DATE NOT NULL,
                hora TIME NULL,
                detalle TEXT,
                accion VARCHAR(150),
                evidencia VARCHAR(500),
                seguimiento BOOLEAN DEFAULT FALSE,
                estado VARCHAR(40) DEFAULT 'Pendiente',
                registrado_por VARCHAR(100) NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisiones_directivas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                registro_id INT NULL,
                alumno VARCHAR(150) NOT NULL,
                accion VARCHAR(100) NOT NULL,
                justificacion TEXT,
                estado VARCHAR(40) DEFAULT 'Pendiente',
                director VARCHAR(100) NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cartas_compromiso (
                id INT AUTO_INCREMENT PRIMARY KEY,
                alumno VARCHAR(150) NOT NULL,
                tutor VARCHAR(150),
                motivo TEXT,
                compromisos TEXT,
                fecha DATE,
                director VARCHAR(100) NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        for grupo in GRUPOS_BASE:
            cursor.execute("""
                INSERT IGNORE INTO grupos_escolares (nombre)
                VALUES (%s)
            """, (grupo,))

        conexion.commit()

    finally:
        conexion.close()


class SistemaNezahualcoyotl:

    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Escolar Nezahualcóyotl")
        self.root.configure(bg=FONDO)
        self.root.minsize(320, 480)
        self._configurando_ventana = False
        self._modo_movil = None
        self._ventana_menu_movil = None
        self._programar_ajuste = None

        try:
            self.root.state("zoomed")
        except tk.TclError:
            ancho = self.root.winfo_screenwidth()
            alto = self.root.winfo_screenheight()
            self.root.geometry(f"{ancho}x{alto}+0+0")

        self.usuario = ""
        self.nombre = ""
        self.rol = ""

        self.color = AZUL_BOTON
        self.oscuro = AZUL
        self.claro = AZUL_CLARO

        self.contenido = None
        self.campos = {}
        self.vista_actual = "Inicio"
        self.grupo_seleccionado = None
        self.alumnos_lista = []
        self.variables_asistencia = {}
        self.variables_observaciones = {}
        self.canvas_grafica = None

        self.configurar_estilos()
        self.mostrar_login()

   

    def configurar_estilos(self):
        estilo = ttk.Style()

        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        estilo.configure(
            "Treeview",
            rowheight=29,
            font=("Segoe UI", 10),
            background=BLANCO,
            fieldbackground=BLANCO,
            foreground=TEXTO
        )

        estilo.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold")
        )

        estilo.configure("TEntry", padding=6)
        estilo.configure("TCombobox", padding=6)

    def limpiar_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def limpiar_contenido(self):
        if self.contenido:
            for widget in self.contenido.winfo_children():
                widget.destroy()

    def boton(self, padre, texto, comando, color=None):
        return tk.Button(
            padre,
            text=texto,
            command=comando,
            bg=color or self.color,
            fg=BLANCO,
            activebackground=self.oscuro,
            activeforeground=BLANCO,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=8
        )

    def titulo(self, texto, descripcion=""):
        tk.Label(
            self.contenido,
            text=texto,
            bg=FONDO,
            fg=self.oscuro,
            font=("Segoe UI", 21, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        if descripcion:
            tk.Label(
                self.contenido,
                text=descripcion,
                bg=FONDO,
                fg=GRIS,
                font=("Segoe UI", 10),
                anchor="w",
                justify="left",
                wraplength=1000
            ).pack(fill="x", pady=(0, 14))

    def leer_campo(self, nombre):
        widget = self.campos.get(nombre)

        if widget is None:
            return ""

        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()

        return widget.get().strip()

    def crear_scroll(self, padre):
        """Area desplazable para pantallas con muchos elementos."""
        marco = tk.Frame(padre, bg=FONDO)
        marco.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            marco, bg=FONDO, highlightthickness=0
        )
        scroll = ttk.Scrollbar(
            marco, orient="vertical", command=canvas.yview
        )

        interior = tk.Frame(canvas, bg=FONDO)
        ventana = canvas.create_window(
            (0, 0), window=interior, anchor="nw"
        )

        interior.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(
                ventana, width=e.width
            )
        )

        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        return interior

   

    def mostrar_login(self):
        self.limpiar_root()
        self.root.configure(bg=FONDO)

        marco = tk.Frame(
            self.root,
            bg=BLANCO,
            padx=22,
            pady=22,
            highlightbackground="#CBD5E1",
            highlightthickness=1
        )
        marco.place(
            relx=0.5, rely=0.5, anchor="center",
            relwidth=0.90, width=-24, height=380
        )
        marco.configure(width=390)
        marco.bind("<Configure>", self._ajustar_login)

        tk.Label(
            marco, text="NEZAHUALCÓYOTL",
            bg=BLANCO, fg=AZUL,
            font=("Segoe UI", 28, "bold")
        ).pack(pady=(5, 0))

        tk.Label(
            marco, text="Sistema Escolar Nezahualcóyotl",
            bg=BLANCO, fg=GRIS
        ).pack(pady=(0, 22))

        tk.Label(
            marco, text="Usuario",
            bg=BLANCO, fg=TEXTO, anchor="w"
        ).pack(fill="x")

        self.entrada_usuario = ttk.Entry(marco)
        self.entrada_usuario.pack(fill="x", pady=(5, 12))

        tk.Label(
            marco, text="Contraseña",
            bg=BLANCO, fg=TEXTO, anchor="w"
        ).pack(fill="x")

        self.entrada_password = ttk.Entry(marco, show="*")
        self.entrada_password.pack(fill="x", pady=(5, 18))
        self.entrada_password.bind(
            "<Return>", lambda e: self.validar_login()
        )

        self.boton(
            marco, "Iniciar sesión",
            self.validar_login, AZUL_BOTON
        ).pack(fill="x")

        tk.Label(
            marco,
            text="Acceso para docentes y dirección",
            bg=BLANCO, fg=GRIS,
            font=("Segoe UI", 9)
        ).pack(pady=17)

        self.entrada_usuario.focus_set()

    def _ajustar_login(self, evento=None):
        """Reduce tipografías y espacios cuando la ventana es estrecha."""
        if not hasattr(self, "entrada_usuario"):
            return
        ancho = self.root.winfo_width()
        compacto = ancho < 520
        tam_titulo = 19 if compacto else 25
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                for hijo in widget.winfo_children():
                    if isinstance(hijo, tk.Label) and hijo.cget("text") == "NEZAHUALCÓYOTL":
                        hijo.configure(font=("Segoe UI", tam_titulo, "bold"))

    def _programar_ajuste_responsivo(self, evento=None):
        """Evita ejecutar el ajuste muchas veces durante un redimensionamiento."""
        if evento is not None and evento.widget is not self.root:
            return
        if self._programar_ajuste is not None:
            try:
                self.root.after_cancel(self._programar_ajuste)
            except tk.TclError:
                pass
        self._programar_ajuste = self.root.after(120, self._ajustar_distribucion)

    def _ajustar_distribucion(self):
        self._programar_ajuste = None
        if not hasattr(self, "menu_lateral") or not self.menu_lateral.winfo_exists():
            return
        ancho = self.root.winfo_width()
        modo_movil = ancho < 760
        if hasattr(self, "etiqueta_usuario_barra") and self.etiqueta_usuario_barra.winfo_exists():
            if ancho < 520:
                self.etiqueta_usuario_barra.pack_forget()
            elif not self.etiqueta_usuario_barra.winfo_manager():
                self.etiqueta_usuario_barra.pack(side="left", padx=10)
        if hasattr(self, "etiqueta_marca") and self.etiqueta_marca.winfo_exists():
            self.etiqueta_marca.configure(font=("Segoe UI", 12 if ancho < 520 else 17, "bold"))
        if modo_movil == self._modo_movil:
            return
        self._modo_movil = modo_movil
        if modo_movil:
            self.menu_lateral.pack_forget()
            if hasattr(self, "boton_menu_movil") and self.boton_menu_movil.winfo_exists():
                self.boton_menu_movil.pack(side="left", padx=4, pady=8)
            if hasattr(self, "contenido") and self.contenido.winfo_exists():
                self.contenido.configure(padx=8, pady=10)
        else:
            if hasattr(self, "boton_menu_movil") and self.boton_menu_movil.winfo_exists():
                self.boton_menu_movil.pack_forget()
            self.menu_lateral.pack(side="left", fill="y", before=self.area_principal)
            if hasattr(self, "contenido") and self.contenido.winfo_exists():
                self.contenido.configure(padx=16, pady=16)
            if self._ventana_menu_movil is not None:
                try:
                    self._ventana_menu_movil.destroy()
                except tk.TclError:
                    pass
                self._ventana_menu_movil = None

    def _abrir_menu_movil(self):
        """Muestra las secciones en una ventana compacta para pantallas pequeñas."""
        if self._ventana_menu_movil is not None:
            try:
                if self._ventana_menu_movil.winfo_exists():
                    self._ventana_menu_movil.lift()
                    return
            except tk.TclError:
                pass
        ventana = tk.Toplevel(self.root)
        self._ventana_menu_movil = ventana
        ventana.title("Menú principal")
        ventana.configure(bg=self.oscuro)
        ancho = max(250, min(320, self.root.winfo_width() - 30))
        alto = min(max(360, ventana.winfo_screenheight() - 140), 620)
        ventana.geometry(f"{ancho}x{alto}")
        ventana.transient(self.root)
        encabezado = tk.Label(
            ventana, text="MENÚ PRINCIPAL", bg=self.oscuro,
            fg=BLANCO, font=("Segoe UI", 12, "bold")
        )
        encabezado.pack(fill="x", padx=12, pady=12)
        lienzo = tk.Canvas(ventana, bg=self.oscuro, highlightthickness=0)
        barra = ttk.Scrollbar(ventana, orient="vertical", command=lienzo.yview)
        interior = tk.Frame(lienzo, bg=self.oscuro)
        interior.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.create_window((0, 0), window=interior, anchor="nw", width=ancho - 25)
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        for opcion in self.obtener_menu():
            tk.Button(
                interior, text=opcion, command=lambda n=opcion: self._seleccionar_menu_movil(n),
                bg=AZUL_CLARO if opcion == self.vista_actual else self.oscuro,
                fg=AZUL if opcion == self.vista_actual else BLANCO,
                activebackground=AZUL_CLARO, activeforeground=AZUL,
                font=("Segoe UI", 10), relief="flat", anchor="w",
                padx=14, pady=12, bd=0
            ).pack(fill="x", padx=5, pady=2)
        ventana.protocol("WM_DELETE_WINDOW", self._cerrar_menu_movil)

    def _seleccionar_menu_movil(self, opcion):
        self._cerrar_menu_movil()
        self.ir(opcion)

    def _cerrar_menu_movil(self):
        if self._ventana_menu_movil is not None:
            try:
                self._ventana_menu_movil.destroy()
            except tk.TclError:
                pass
            self._ventana_menu_movil = None

    def validar_login(self):
        usuario = self.entrada_usuario.get().strip()
        password = self.entrada_password.get()

        if not usuario or not password:
            messagebox.showwarning(
                "Datos incompletos",
                "Escribe tu usuario y contraseña."
            )
            return

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT nombre, usuario, password_hash, rol
                FROM usuarios
                WHERE usuario = %s
                LIMIT 1
            """, (usuario,))

            fila = cursor.fetchone()

            if not fila or not verificar_password(
                password, fila.get("password_hash")
            ):
                messagebox.showerror(
                    "Acceso denegado",
                    "Usuario o contraseña incorrectos."
                )
                return

            rol = str(fila.get("rol") or "").strip().lower()

            if rol not in ("docente", "director"):
                messagebox.showerror(
                    "Rol inválido",
                    "La cuenta debe tener rol docente o director."
                )
                return

            self.usuario = str(fila["usuario"])
            self.nombre = str(fila.get("nombre") or usuario)
            self.rol = rol

            if rol == "docente":
                self.color, self.oscuro, self.claro = (
                    AZUL_BOTON, AZUL, AZUL_CLARO
                )
            else:
                self.color, self.oscuro, self.claro = (
                    AZUL_MEDIO, AZUL, AZUL_SUAVE
                )

        except mysql.connector.Error as error:
            messagebox.showerror(
                "Error de MySQL",
                f"No se pudo iniciar sesión:\n\n{error}\n\n"
                "Verifica DB_CONFIG y la estructura de usuarios."
            )
            return

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

        try:
            crear_tablas()
        except mysql.connector.Error as error:
            messagebox.showerror(
                "Error al preparar tablas", str(error)
            )
            return

        self.mostrar_sistema()

    
    def pantalla_personalizado(self):
        self.limpiar_contenido()
        self.titulo(
            "Personalizado",
            "Cambia los colores de la aplicación. Los cambios se aplican "
            "a menús, encabezados, fondos, botones y elementos seleccionados."
        )

        paletas = {
            "Azul institucional": ("#F1F5F9", "#0D3B66", "#1565C0", "#E3F2FD", "#1E293B", "#FFFFFF"),
            "Verde": ("#F0FDF4", "#14532D", "#16A34A", "#DCFCE7", "#14532D", "#FFFFFF"),
            "Morado": ("#F5F3FF", "#4C1D95", "#7C3AED", "#EDE9FE", "#2E1065", "#FFFFFF"),
            "Rojo": ("#FEF2F2", "#7F1D1D", "#DC2626", "#FEE2E2", "#450A0A", "#FFFFFF"),
            "Oscuro": ("#111827", "#030712", "#2563EB", "#1F2937", "#F9FAFB", "#1F2937")
        }

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel.pack(fill="x", pady=8)
        tk.Label(panel, text="Temas prediseñados", bg=BLANCO, fg=TEXTO,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        selector = ttk.Combobox(panel, values=list(paletas), state="readonly")
        selector.set("Azul institucional")
        selector.pack(fill="x", pady=5)

        def aplicar_preset():
            self.aplicar_colores(paletas[selector.get()])

        self.boton(panel, "Aplicar tema", aplicar_preset).pack(anchor="e", pady=8)

        panel_custom = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel_custom.pack(fill="x", pady=8)
        tk.Label(panel_custom, text="Colores personalizados", bg=BLANCO, fg=TEXTO,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        definiciones = [
            ("Fondo general", "fondo"),
            ("Barra superior y menú", "oscuro"),
            ("Botones y acentos", "acento"),
            ("Opción seleccionada", "seleccion"),
            ("Texto principal", "texto"),
            ("Tarjetas y paneles", "blanco")
        ]
        self.colores_personalizados = {}
        valores_actuales = {
            "fondo": FONDO, "oscuro": self.oscuro, "acento": self.color,
            "seleccion": self.claro, "texto": TEXTO, "blanco": BLANCO
        }

        for etiqueta, clave in definiciones:
            fila = tk.Frame(panel_custom, bg=BLANCO)
            fila.pack(fill="x", pady=5)
            tk.Label(fila, text=etiqueta, bg=BLANCO, fg=TEXTO).pack(side="left")
            muestra = tk.Label(fila, text=valores_actuales[clave],
                               bg=valores_actuales[clave], fg=TEXTO,
                               width=12, relief="solid", bd=1)
            muestra.pack(side="right", padx=8)
            self.colores_personalizados[clave] = muestra

            def elegir(k=clave, widget=muestra):
                color = colorchooser.askcolor(color=widget.cget("bg"),
                                               title="Selecciona un color")
                if color and color[1]:
                    widget.configure(text=color[1], bg=color[1])

            self.boton(fila, "Elegir", elegir).pack(side="right")

        def aplicar_custom():
            colores = tuple(self.colores_personalizados[k].cget("bg")
                            for k in ("fondo", "oscuro", "acento", "seleccion", "texto", "blanco"))
            self.aplicar_colores(colores)

        self.boton(panel_custom, "Aplicar mis colores", aplicar_custom).pack(anchor="e", pady=10)

        self.boton(self.contenido, "Restablecer colores", lambda: self.aplicar_colores(paletas["Azul institucional"]), color=GRIS).pack(anchor="w", pady=8)

    def aplicar_colores(self, colores):
        global FONDO, AZUL, AZUL_BOTON, AZUL_CLARO, TEXTO, BLANCO
        FONDO, AZUL, AZUL_BOTON, AZUL_CLARO, TEXTO, BLANCO = colores
        self.oscuro = AZUL
        self.color = AZUL_BOTON
        self.claro = AZUL_CLARO
        try:
            self.root.configure(bg=FONDO)
            self.mostrar_sistema()
            self.ir("Personalizado")
            messagebox.showinfo("Personalización aplicada", "Los colores se aplicaron a la aplicación.")
        except tk.TclError as error:
            messagebox.showerror("Error de apariencia", str(error))

    

    def obtener_menu(self):
        if self.rol == "docente":
            return [
                "Inicio",
                "Mis grupos",
                "Pase de lista",
                "Registrar retardo/falta",
                "Conducta docente",
                "Autocontrol",
                "Registrar incidencia",
                "Justificantes docente",
                "Mis reportes",
                "Buscar",
                "Gráficos",
                "Personalizado"
            ]

        return [
            "Inicio",
            "Retardos y faltas",
            "Conducta",
            "Justificantes",
            "Reportes generales",
            "Carta compromiso",
            "Creación de usuarios",
            "Gráficos",
            "Personalizado"
        ]

    def mostrar_sistema(self):
        self.limpiar_root()

        principal = tk.Frame(self.root, bg=FONDO)
        principal.pack(fill="both", expand=True)

        barra = tk.Frame(
            principal, bg=self.oscuro, height=58
        )
        barra.pack(fill="x")
        barra.pack_propagate(False)

        self.boton_menu_movil = self.boton(
            barra, "Menú", self._abrir_menu_movil, color=self.oscuro
        )

        self.etiqueta_marca = tk.Label(
            barra, text="NEZAHUALCÓYOTL",
            bg=self.oscuro, fg=BLANCO,
            font=("Segoe UI", 17, "bold")
        )
        self.etiqueta_marca.pack(side="left", padx=18)

        self.etiqueta_usuario_barra = tk.Label(
            barra,
            text=f"{self.rol.capitalize()}: {self.nombre}",
            bg=self.oscuro, fg=BLANCO
        )
        self.etiqueta_usuario_barra.pack(side="left", padx=10)

        try:
            numero_avisos = self.consultar("""
                SELECT COUNT(*) AS total
                FROM registros_escolares
                WHERE estado='Pendiente'
                   OR creado_en >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)[0]["total"]
        except mysql.connector.Error:
            numero_avisos = 0

        texto_campana = f"🔔 {numero_avisos}" if numero_avisos else "🔔"
        self.boton_campana = self.boton(
            barra, texto_campana,
            lambda: self.ir("Avisos")
        )
        self.boton_campana.pack(side="right", padx=5, pady=9)
        self.root.after(30000, self.actualizar_campana)

        self.boton(
            barra, "Salir", self.cerrar_sesion
        ).pack(side="right", padx=5, pady=9)

        cuerpo = tk.Frame(principal, bg=FONDO)
        cuerpo.pack(fill="both", expand=True)

        menu = tk.Frame(
            cuerpo, bg=self.oscuro, width=210
        )
        menu.pack(side="left", fill="y")
        menu.pack_propagate(False)
        self.menu_lateral = menu

        tk.Label(
            menu, text="MENÚ PRINCIPAL",
            bg=self.oscuro, fg=BLANCO,
            font=("Segoe UI", 10, "bold")
        ).pack(fill="x", padx=12, pady=15)

        menu_canvas = tk.Canvas(
            menu, bg=self.oscuro, highlightthickness=0
        )
        menu_scroll = ttk.Scrollbar(
            menu, orient="vertical",
            command=menu_canvas.yview
        )
        menu_interior = tk.Frame(menu_canvas, bg=self.oscuro)

        menu_interior.bind(
            "<Configure>",
            lambda e: menu_canvas.configure(
                scrollregion=menu_canvas.bbox("all")
            )
        )

        menu_canvas.create_window(
            (0, 0), window=menu_interior, anchor="nw", width=190
        )
        menu_canvas.configure(yscrollcommand=menu_scroll.set)

        menu_canvas.pack(side="left", fill="both", expand=True)
        menu_scroll.pack(side="right", fill="y")

        self.botones_menu = {}
        for opcion in self.obtener_menu():
            boton_menu = tk.Button(
                menu_interior,
                text=opcion,
                command=lambda n=opcion: self.ir(n),
                bg=AZUL_CLARO if opcion == self.vista_actual else self.oscuro,
                fg=AZUL if opcion == self.vista_actual else BLANCO,
                activebackground=AZUL_CLARO,
                activeforeground=AZUL,
                font=("Segoe UI", 10, "bold" if opcion == self.vista_actual else "normal"),
                relief="flat", anchor="w",
                cursor="hand2", padx=12, pady=10, bd=0
            )
            boton_menu.pack(fill="x", padx=5, pady=2)
            self.botones_menu[opcion] = boton_menu

        area = tk.Frame(cuerpo, bg=FONDO)
        area.pack(side="left", fill="both", expand=True)
        self.area_principal = area

        self.area_canvas = tk.Canvas(
            area, bg=FONDO, highlightthickness=0
        )
        barra_scroll = ttk.Scrollbar(
            area, orient="vertical",
            command=self.area_canvas.yview
        )

        self.area_canvas.configure(
            yscrollcommand=barra_scroll.set
        )

        barra_scroll.pack(side="right", fill="y")
        self.area_canvas.pack(side="left", fill="both", expand=True)

        self.contenido = tk.Frame(
            self.area_canvas, bg=FONDO, padx=16, pady=16
        )

        self.ventana_contenido = self.area_canvas.create_window(
            (0, 0), window=self.contenido, anchor="nw"
        )

        self.contenido.bind(
            "<Configure>",
            lambda e: self.area_canvas.configure(
                scrollregion=self.area_canvas.bbox("all")
            )
        )

        self.area_canvas.bind(
            "<Configure>",
            lambda e: self.area_canvas.itemconfigure(
                self.ventana_contenido, width=e.width
            )
        )

        self.ir("Inicio")
        self._modo_movil = None
        self._programar_ajuste_responsivo()
        self.root.bind("<Configure>", self._programar_ajuste_responsivo, add="+")

    def actualizar_campana(self):
        """Actualiza el contador de novedades mientras la sesión está abierta."""
        boton = getattr(self, "boton_campana", None)
        if boton is None or not boton.winfo_exists():
            return
        try:
            total = self.consultar("""
                SELECT COUNT(*) AS total
                FROM registros_escolares
                WHERE estado='Pendiente'
                   OR creado_en >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)[0]["total"]
            boton.configure(text=f"🔔 {total}" if total else "🔔")
        except (mysql.connector.Error, tk.TclError):
            pass
        if boton.winfo_exists():
            self.root.after(30000, self.actualizar_campana)

    def cerrar_sesion(self):
        if messagebox.askyesno(
            "Cerrar sesión", "¿Quieres salir de tu cuenta?"
        ):
            self.usuario = ""
            self.nombre = ""
            self.rol = ""
            self.mostrar_login()

    def ir(self, nombre):
        solo_director = {
            "Retardos y faltas", "Conducta", "Justificantes",
            "Reportes generales", "Carta compromiso", "Creación de usuarios",
            "Panel directivo", "Administrar usuarios", "Administrar grupos",
            "Asignar docentes", "Consultar alumnos", "Consultar reportes",
            "Monitoreo docente", "Toma de decisiones"
        }
        solo_docente = {
            "Mis grupos", "Pase de lista", "Registrar retardo/falta",
            "Conducta docente", "Autocontrol", "Registrar incidencia",
            "Justificantes docente", "Mis reportes"
        }

        if nombre in solo_director and self.rol != "director":
            messagebox.showwarning("Acceso restringido", "Esta pantalla es exclusiva de dirección.")
            return
        if nombre in solo_docente and self.rol != "docente":
            messagebox.showwarning("Acceso restringido", "Esta pantalla es exclusiva de docentes.")
            return

        self.vista_actual = nombre
        for opcion, boton_menu in getattr(self, "botones_menu", {}).items():
            seleccionado = opcion == nombre
            boton_menu.configure(
                bg=AZUL_CLARO if seleccionado else self.oscuro,
                fg=AZUL if seleccionado else BLANCO,
                font=("Segoe UI", 10, "bold" if seleccionado else "normal")
            )

        self.limpiar_contenido()
        vistas = {
            "Inicio": self.pantalla_inicio,
            "Mis grupos": self.pantalla_grupos,
            "Pase de lista": self.pantalla_pase_lista,
            "Registrar retardo/falta": self.pantalla_retardos,
            "Conducta docente": self.pantalla_conducta,
            "Autocontrol": self.pantalla_autocontrol,
            "Registrar incidencia": self.pantalla_incidencia,
            "Justificantes docente": self.pantalla_justificantes,
            "Mis reportes": self.pantalla_reportes,
            "Retardos y faltas": self.pantalla_director_retardos_faltas,
            "Conducta": self.pantalla_director_conducta,
            "Justificantes": self.pantalla_director_justificantes,
            "Reportes generales": self.pantalla_reportes_generales,
            "Carta compromiso": self.pantalla_carta,
            "Creación de usuarios": self.pantalla_usuarios,
            "Consultar reportes": self.pantalla_reportes,
            "Panel directivo": self.pantalla_directivo,
            "Administrar usuarios": self.pantalla_usuarios,
            "Administrar grupos": self.pantalla_grupos_admin,
            "Asignar docentes": self.pantalla_asignar,
            "Consultar alumnos": self.pantalla_alumnos_admin,
            "Monitoreo docente": self.pantalla_monitoreo,
            "Toma de decisiones": self.pantalla_decisiones,
            "Gráficos": self.pantalla_graficas,
            "Gráficas": self.pantalla_graficas,
            "Personalizado": self.pantalla_personalizado,
            "Buscar": self.pantalla_buscar,
            "Avisos": self.pantalla_avisos
        }
        vistas.get(nombre, self.pantalla_inicio)()

    def consultar(self, sql, parametros=(), diccionario=True):
        conexion = conectar()
        try:
            cursor = conexion.cursor(dictionary=diccionario)
            cursor.execute(sql, parametros)
            return cursor.fetchall()
        finally:
            conexion.close()

    def contar(self, tipo=None, estado=None):
        sql = "SELECT COUNT(*) AS total FROM registros_escolares"
        condiciones = []
        parametros = []

        if tipo:
            condiciones.append("tipo=%s")
            parametros.append(tipo)

        if estado:
            condiciones.append("estado=%s")
            parametros.append(estado)

        if self.rol == "docente":
            condiciones.append("registrado_por=%s")
            parametros.append(self.usuario)

        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)

        filas = self.consultar(sql, parametros)
        return filas[0]["total"]

    def tarjeta(self, padre, encabezado, valor, detalle=""):
        tarjeta = tk.Frame(
            padre, bg=BLANCO, padx=13, pady=12,
            highlightbackground="#CBD5E1",
            highlightthickness=1
        )
        tarjeta.pack(
            side="left", fill="both", expand=True, padx=5
        )

        tk.Label(
            tarjeta, text=encabezado,
            bg=BLANCO, fg=GRIS
        ).pack(anchor="w")

        tk.Label(
            tarjeta, text=str(valor),
            bg=BLANCO, fg=self.oscuro,
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w", pady=5)

        if detalle:
            tk.Label(
                tarjeta, text=detalle,
                bg=BLANCO, fg=GRIS,
                wraplength=220, justify="left"
            ).pack(anchor="w")

    def pantalla_inicio(self):
        self.titulo(
            "Panel de inicio",
            f"Bienvenido/a, {self.nombre}. "
            "Selecciona una sección para continuar."
        )

        fila = tk.Frame(self.contenido, bg=FONDO)
        fila.pack(fill="x", pady=8)

        try:
            total = self.contar()
            incidencias = self.contar("Incidencia")
            pendientes = self.contar(estado="Pendiente")
        except mysql.connector.Error:
            total = incidencias = pendientes = "—"

        for titulo, valor, detalle in [
            ("Registros", total, "Registros guardados"),
            ("Incidencias", incidencias, "Incidencias registradas"),
            ("Pendientes", pendientes, "Por revisar")
        ]:
            self.tarjeta(fila, titulo, valor, detalle)

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel.pack(fill="x", pady=15)

        tk.Label(
            panel, text="Accesos rápidos",
            bg=BLANCO, fg=self.oscuro,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", pady=(0, 10))

        accesos = (
            ["Pase de lista", "Registrar incidencia",
             "Mis reportes", "Gráficos"]
            if self.rol == "docente"
            else ["Retardos y faltas", "Conducta",
                  "Reportes generales", "Creación de usuarios"]
        )

       
        rejilla = tk.Frame(panel, bg=BLANCO)
        rejilla.pack(anchor="center", pady=4)

        for indice, acceso in enumerate(accesos):
            boton_acceso = self.boton(
                rejilla, acceso,
                lambda a=acceso: self.ir(a)
            )
            boton_acceso.configure(width=22, pady=12)
            boton_acceso.grid(
                row=indice // 2, column=indice % 2,
                padx=8, pady=7, sticky="ew"
            )

        for columna in range(2):
            rejilla.grid_columnconfigure(columna, weight=1, uniform="accesos")

        tk.Label(
            self.contenido,
            text=f"Fecha actual: {date.today().strftime('%d/%m/%Y')}  |  "
                 "Usa el menú lateral para acceder a todas las funciones.",
            bg=FONDO, fg=GRIS
        ).pack(anchor="w", pady=(4, 0))

    

    def pantalla_usuarios(self):
        self.limpiar_contenido()
        self.titulo(
            "Administrar usuarios",
            "Crea cuentas de docentes y directores."
        )

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=20, pady=18)
        panel.pack(fill="x")
        panel.columnconfigure(1, weight=1)

        self.campos = {}

        for i, campo in enumerate(
            ["Nombre completo", "Usuario", "Contraseña", "Rol"]
        ):
            tk.Label(
                panel, text=campo,
                bg=BLANCO, fg=TEXTO,
                font=("Segoe UI", 10, "bold")
            ).grid(row=i, column=0, sticky="w", padx=8, pady=8)

            if campo == "Rol":
                widget = ttk.Combobox(
                    panel, values=["docente", "director"],
                    state="readonly"
                )
                widget.set("docente")
            elif campo == "Contraseña":
                widget = ttk.Entry(panel, show="*")
            else:
                widget = ttk.Entry(panel)

            widget.grid(row=i, column=1, sticky="ew", padx=8, pady=8)
            self.campos[campo] = widget

        self.boton(
            panel, "Crear cuenta", self.crear_usuario
        ).grid(row=4, column=1, sticky="e", padx=8, pady=12)

        self.boton(
            self.contenido, "Ver usuarios",
            lambda: self.mostrar_tabla(
                "Usuarios",
                """SELECT nombre, usuario, rol
                   FROM usuarios ORDER BY nombre"""
            )
        ).pack(anchor="w", pady=12)

    def crear_usuario(self):
        nombre = self.leer_campo("Nombre completo")
        usuario = self.leer_campo("Usuario")
        password = self.leer_campo("Contraseña")
        rol = self.leer_campo("Rol").lower()

        if not nombre or not usuario or not password or rol not in (
            "docente", "director"
        ):
            messagebox.showwarning(
                "Datos incompletos",
                "Completa todos los campos y selecciona un rol válido."
            )
            return


        hash_password = hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor()

            cursor.execute(
                "SELECT usuario FROM usuarios WHERE usuario=%s",
                (usuario,)
            )

            if cursor.fetchone():
                messagebox.showwarning(
                    "Usuario existente",
                    "Ya existe una cuenta con ese nombre de usuario."
                )
                return

            cursor.execute("""
                INSERT INTO usuarios (nombre, usuario, password_hash, rol)
                VALUES (%s, %s, %s, %s)
            """, (nombre, usuario, hash_password, rol))

            conexion.commit()

            messagebox.showinfo(
                "Cuenta creada",
                f"Se creó la cuenta de {nombre} con rol {rol}."
            )

            for campo in ("Nombre completo", "Usuario", "Contraseña"):
                self.campos[campo].delete(0, "end")

        except mysql.connector.Error as error:
            messagebox.showerror(
                "Error al crear cuenta",
                f"{error}\n\n"
                "Comprueba las columnas de tu tabla usuarios."
            )

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

    
    def obtener_grupos(self):
        return self.consultar("""
            SELECT id, nombre
            FROM grupos_escolares
            ORDER BY nombre
        """)

    def obtener_mis_grupos(self):
        if self.rol == "director":
            return self.obtener_grupos()

        return self.consultar("""
            SELECT g.id, g.nombre
            FROM grupos_escolares g
            INNER JOIN docente_grupos dg ON dg.grupo_id=g.id
            WHERE dg.docente=%s
            ORDER BY g.nombre
        """, (self.usuario,))

    def pantalla_grupos_admin(self):
        self.limpiar_contenido()
        self.titulo(
            "Administrar grupos",
            "Crea grupos escolares. Cada grupo admite hasta 30 alumnos."
        )

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel.pack(fill="x")

        tk.Label(
            panel, text="Nombre del nuevo grupo",
            bg=BLANCO, fg=TEXTO
        ).pack(anchor="w")

        entrada = ttk.Entry(panel)
        entrada.pack(fill="x", pady=8)

        def crear_grupo():
            nombre = entrada.get().strip().upper()

            if not nombre:
                messagebox.showwarning(
                    "Grupo vacío", "Escribe un nombre de grupo."
                )
                return

            conexion = None
            try:
                conexion = conectar()
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO grupos_escolares (nombre)
                    VALUES (%s)
                """, (nombre,))
                conexion.commit()
                messagebox.showinfo(
                    "Grupo creado",
                    f"El grupo {nombre} ya está disponible."
                )
                entrada.delete(0, "end")
            except mysql.connector.IntegrityError:
                messagebox.showwarning(
                    "Grupo existente",
                    "Ese grupo ya está registrado."
                )
            except mysql.connector.Error as error:
                messagebox.showerror("Error MySQL", str(error))
            finally:
                if conexion is not None and conexion.is_connected():
                    conexion.close()

        self.boton(panel, "Crear grupo", crear_grupo).pack(anchor="e")

        self.boton(
            self.contenido, "Asignar docentes",
            lambda: self.ir("Asignar docentes")
        ).pack(anchor="w", pady=10)

        self.mostrar_tabla(
            "Grupos disponibles",
            """SELECT g.nombre AS grupo,
                      COUNT(a.id) AS alumnos
               FROM grupos_escolares g
               LEFT JOIN alumnos_escolares a
                 ON a.grupo_id=g.id AND a.activo=TRUE
               GROUP BY g.id, g.nombre
               ORDER BY g.nombre"""
        )

    def pantalla_asignar(self):
        self.limpiar_contenido()
        self.titulo(
            "Asignar docentes",
            "Relaciona un docente con uno o varios grupos."
        )

        try:
            docentes = self.consultar("""
                SELECT usuario, nombre
                FROM usuarios
                WHERE LOWER(rol)='docente'
                ORDER BY nombre
            """)

            grupos = self.obtener_grupos()

        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))
            return

        if not docentes or not grupos:
            tk.Label(
                self.contenido,
                text="Primero crea al menos un docente y un grupo.",
                bg=FONDO, fg=GRIS
            ).pack(anchor="w")
            return

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel.pack(fill="x")

        tk.Label(
            panel, text="Docente",
            bg=BLANCO, fg=TEXTO
        ).pack(anchor="w")

        mapa_docentes = {
            f"{d['nombre']} ({d['usuario']})": d["usuario"]
            for d in docentes
        }

        docente = ttk.Combobox(
            panel, values=list(mapa_docentes), state="readonly"
        )
        docente.pack(fill="x", pady=6)

        tk.Label(
            panel, text="Grupo",
            bg=BLANCO, fg=TEXTO
        ).pack(anchor="w")

        mapa_grupos = {
            g["nombre"]: g["id"] for g in grupos
        }

        grupo = ttk.Combobox(
            panel, values=list(mapa_grupos), state="readonly"
        )
        grupo.pack(fill="x", pady=6)

        def asignar():
            if not docente.get() or not grupo.get():
                messagebox.showwarning(
                    "Datos incompletos",
                    "Selecciona un docente y un grupo."
                )
                return

            conexion = None
            try:
                conexion = conectar()
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT IGNORE INTO docente_grupos
                    (docente, grupo_id)
                    VALUES (%s, %s)
                """, (
                    mapa_docentes[docente.get()],
                    mapa_grupos[grupo.get()]
                ))
                conexion.commit()

                messagebox.showinfo(
                    "Asignación guardada",
                    "El docente ya puede consultar la lista del grupo."
                )

            except mysql.connector.Error as error:
                messagebox.showerror("Error MySQL", str(error))

            finally:
                if conexion is not None and conexion.is_connected():
                    conexion.close()

        self.boton(panel, "Asignar grupo", asignar).pack(anchor="e")

        self.mostrar_tabla(
            "Asignaciones actuales",
            """SELECT u.nombre AS docente, g.nombre AS grupo
               FROM docente_grupos dg
               INNER JOIN usuarios u ON u.usuario=dg.docente
               INNER JOIN grupos_escolares g ON g.id=dg.grupo_id
               ORDER BY u.nombre, g.nombre"""
        )

    def pantalla_grupos(self):
        self.limpiar_contenido()
        self.titulo(
            "Mis grupos",
            "Selecciona un grupo para consultar y administrar sus alumnos."
        )

        try:
            grupos = self.obtener_mis_grupos()
        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))
            return

        if not grupos:
            tk.Label(
                self.contenido,
                text="Todavía no tienes grupos asignados. "
                     "Solicita a dirección que te asigne uno.",
                bg=FONDO, fg=GRIS, wraplength=750
            ).pack(anchor="w")
            return

        for grupo in grupos:
            panel = tk.Frame(
                self.contenido, bg=BLANCO, padx=18, pady=15
            )
            panel.pack(fill="x", pady=6)

            try:
                cantidad = self.consultar("""
                    SELECT COUNT(*) AS total
                    FROM alumnos_escolares
                    WHERE grupo_id=%s AND activo=TRUE
                """, (grupo["id"],))[0]["total"]
            except mysql.connector.Error:
                cantidad = 0

            tk.Label(
                panel,
                text=f"Grupo {grupo['nombre']}  ·  {cantidad}/30 alumnos",
                bg=BLANCO, fg=self.oscuro,
                font=("Segoe UI", 13, "bold")
            ).pack(side="left")

            self.boton(
                panel, "Abrir lista",
                lambda g=grupo: self.abrir_alumnos(g)
            ).pack(side="right")

    def abrir_alumnos(self, grupo):
        self.grupo_seleccionado = grupo

        self.limpiar_contenido()
        self.titulo(
            f"Lista del grupo {grupo['nombre']}",
            "Puedes registrar hasta 30 alumnos. "
            "Guarda los cambios al terminar."
        )

        try:
            alumnos = self.consultar("""
                SELECT id, numero_lista, nombre
                FROM alumnos_escolares
                WHERE grupo_id=%s AND activo=TRUE
                ORDER BY numero_lista
            """, (grupo["id"],))
        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))
            return

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=14, pady=14)
        panel.pack(fill="x")

        self.alumnos_lista = []

        for numero in range(1, 31):
            existente = next(
                (a for a in alumnos if a["numero_lista"] == numero),
                None
            )

            fila = tk.Frame(panel, bg=BLANCO)
            fila.pack(fill="x", pady=3)

            tk.Label(
                fila, text=f"{numero:02d}.",
                bg=BLANCO, fg=GRIS, width=5, anchor="w"
            ).pack(side="left")

            entrada = ttk.Entry(fila)
            entrada.pack(side="left", fill="x", expand=True)

            if existente:
                entrada.insert(0, existente["nombre"])

            self.alumnos_lista.append((numero, entrada))

        self.boton(
            self.contenido, "Guardar lista de alumnos",
            self.guardar_lista_alumnos
        ).pack(anchor="e", pady=12)

        self.boton(
            self.contenido, "Pasar lista",
            lambda: self.ir("Pase de lista")
        ).pack(anchor="e", pady=4)

    def guardar_lista_alumnos(self):
        grupo = self.grupo_seleccionado

        if not grupo:
            return

        nombres = [
            (numero, entrada.get().strip())
            for numero, entrada in self.alumnos_lista
        ]

        nombres_ocupados = [n for _, n in nombres if n]

        if len(nombres_ocupados) != len(set(
            n.casefold() for n in nombres_ocupados
        )):
            messagebox.showwarning(
                "Nombres repetidos",
                "Revisa los nombres duplicados de la lista."
            )
            return

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor()

            for numero, nombre in nombres:
                cursor.execute("""
                    SELECT id
                    FROM alumnos_escolares
                    WHERE grupo_id=%s AND numero_lista=%s
                """, (grupo["id"], numero))

                existente = cursor.fetchone()

                if nombre and existente:
                    cursor.execute("""
                        UPDATE alumnos_escolares
                        SET nombre=%s, activo=TRUE
                        WHERE id=%s
                    """, (nombre, existente[0]))

                elif nombre:
                    cursor.execute("""
                        INSERT INTO alumnos_escolares
                        (grupo_id, numero_lista, nombre)
                        VALUES (%s, %s, %s)
                    """, (grupo["id"], numero, nombre))

                elif existente:
                    cursor.execute("""
                        UPDATE alumnos_escolares
                        SET activo=FALSE
                        WHERE id=%s
                    """, (existente[0],))

            conexion.commit()

            messagebox.showinfo(
                "Lista guardada",
                "Se guardaron los cambios de la lista."
            )

        except mysql.connector.Error as error:
            if conexion is not None:
                conexion.rollback()
            messagebox.showerror("Error al guardar", str(error))

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

    def pantalla_alumnos_admin(self):
        self.mostrar_tabla(
            "Alumnos registrados",
            """SELECT g.nombre AS grupo, a.numero_lista,
                      a.nombre AS alumno
               FROM alumnos_escolares a
               INNER JOIN grupos_escolares g ON g.id=a.grupo_id
               WHERE a.activo=TRUE
               ORDER BY g.nombre, a.numero_lista"""
        )

    
    def pantalla_pase_lista(self):
        self.limpiar_contenido()
        self.titulo(
            "Pase de lista",
            "Edita los nombres directamente, selecciona una opción por alumno "
            "y guarda todo al terminar. Cada grupo dispone de 30 lugares."
        )

        try:
            grupos = self.obtener_mis_grupos()
        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))
            return

        if not grupos:
            tk.Label(
                self.contenido,
                text="No tienes grupos asignados. Solicita a dirección una asignación.",
                bg=FONDO, fg=GRIS
            ).pack(anchor="w")
            return

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=14, pady=12)
        panel.pack(fill="x", pady=(0, 10))
        tk.Label(panel, text="Grupo", bg=BLANCO, fg=TEXTO).pack(side="left", padx=(0, 8))
        mapa = {g["nombre"]: g for g in grupos}
        seleccion = ttk.Combobox(panel, values=list(mapa), state="readonly", width=13)
        seleccion.pack(side="left")
        seleccion.set(grupos[0]["nombre"])
        tk.Label(panel, text="Fecha", bg=BLANCO, fg=TEXTO).pack(side="left", padx=(15, 5))
        fecha = ttk.Entry(panel, width=12)
        fecha.insert(0, date.today().isoformat())
        fecha.pack(side="left")

        contenedor = tk.Frame(self.contenido, bg=FONDO)
        contenedor.pack(fill="both", expand=True)
        filas = {}

        encabezado = tk.Frame(contenedor, bg=self.oscuro, padx=8, pady=8)
        encabezado.pack(fill="x")
        for texto, ancho in [("N.º", 5), ("Alumno (editable)", 30), ("Acción / asistencia", 23), ("Detalle", 25)]:
            tk.Label(encabezado, text=texto, bg=self.oscuro, fg=BLANCO,
                     font=("Segoe UI", 9, "bold"), width=ancho, anchor="w").pack(side="left", padx=3)

        lista = tk.Frame(contenedor, bg=FONDO)
        lista.pack(fill="x")

        def cargar():
            for widget in lista.winfo_children():
                widget.destroy()
            filas.clear()
            try:
                datetime.strptime(fecha.get().strip(), "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Fecha inválida", "Usa el formato AAAA-MM-DD.")
                return

            grupo = mapa[seleccion.get()]
            try:
                alumnos = self.consultar("""
                    SELECT id, numero_lista, nombre
                    FROM alumnos_escolares
                    WHERE grupo_id=%s AND activo=TRUE
                    ORDER BY numero_lista
                """, (grupo["id"],))
                anteriores = self.consultar("""
                    SELECT alumno_id, estado, observaciones
                    FROM asistencias_escolares
                    WHERE grupo_id=%s AND fecha=%s
                """, (grupo["id"], fecha.get().strip()))
            except mysql.connector.Error as error:
                messagebox.showerror("Error MySQL", str(error))
                return

            por_numero = {a["numero_lista"]: a for a in alumnos}
            previos = {a["alumno_id"]: a for a in anteriores}
            opciones = ["Asistencia", "Falta", "Retardo", "Justificante", "Conducta", "Reporte", "Incidencia", "Autocontrol"]

            for numero in range(1, 31):
                alumno = por_numero.get(numero)
                fila = tk.Frame(lista, bg=BLANCO, padx=7, pady=4,
                                highlightbackground="#BFDBFE", highlightthickness=1)
                fila.pack(fill="x", pady=1)
                tk.Label(fila, text=f"{numero:02d}", bg=BLANCO, fg=self.oscuro,
                         width=5, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left", padx=3)
                entrada_nombre = ttk.Entry(fila)
                entrada_nombre.pack(side="left", fill="x", expand=True, padx=3)
                if alumno:
                    entrada_nombre.insert(0, alumno["nombre"])

                anterior = previos.get(alumno["id"]) if alumno else None
                estado_previo = anterior["estado"] if anterior else "Presente"
                estado_inicial = "Asistencia" if estado_previo == "Presente" else estado_previo
                accion = tk.StringVar(value=estado_inicial if estado_inicial in opciones else "Asistencia")
                combo = ttk.Combobox(fila, textvariable=accion, values=opciones,
                                     state="readonly", width=21)
                combo.pack(side="left", padx=3)
                detalle = ttk.Entry(fila)
                detalle.pack(side="left", fill="x", expand=True, padx=3)
                if anterior and anterior.get("observaciones"):
                    detalle.insert(0, anterior["observaciones"])
                filas[numero] = {"nombre": entrada_nombre, "accion": accion,
                                 "detalle": detalle, "alumno": alumno}

            tk.Label(lista, text="Consejo: usa Conducta, Reporte, Incidencia o Autocontrol para registrar una novedad del alumno.",
                     bg=FONDO, fg=GRIS, wraplength=850, justify="left").pack(anchor="w", pady=8)

        def guardar():
            grupo = mapa[seleccion.get()]
            fecha_texto = fecha.get().strip()
            try:
                datetime.strptime(fecha_texto, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Fecha inválida", "Usa el formato AAAA-MM-DD.")
                return

            conexion = None
            try:
                conexion = conectar()
                cursor = conexion.cursor()
                for numero, datos in filas.items():
                    nombre = datos["nombre"].get().strip()
                    if not nombre:
                        continue
                    cursor.execute("""SELECT id FROM alumnos_escolares
                                      WHERE grupo_id=%s AND numero_lista=%s""",
                                   (grupo["id"], numero))
                    existente = cursor.fetchone()
                    if existente:
                        alumno_id = existente[0]
                        cursor.execute("UPDATE alumnos_escolares SET nombre=%s, activo=TRUE WHERE id=%s",
                                       (nombre, alumno_id))
                    else:
                        cursor.execute("""INSERT INTO alumnos_escolares
                                          (grupo_id, numero_lista, nombre) VALUES (%s,%s,%s)""",
                                       (grupo["id"], numero, nombre))
                        alumno_id = cursor.lastrowid

                    accion = datos["accion"].get()
                    detalle = datos["detalle"].get().strip()
                    if accion in ("Asistencia", "Falta", "Retardo", "Justificante"):
                        estado = {"Asistencia": "Presente"}.get(accion, accion)
                        cursor.execute("""INSERT INTO asistencias_escolares
                            (alumno_id, grupo_id, fecha, estado, docente, observaciones)
                            VALUES (%s,%s,%s,%s,%s,%s)
                            ON DUPLICATE KEY UPDATE estado=VALUES(estado), docente=VALUES(docente), observaciones=VALUES(observaciones)""",
                            (alumno_id, grupo["id"], fecha_texto, estado, self.usuario, detalle or None))
                        if estado in ("Falta", "Retardo"):
                            cursor.execute("""INSERT INTO registros_escolares
                                (tipo, alumno, grupo, fecha, detalle, registrado_por)
                                VALUES (%s,%s,%s,%s,%s,%s)""",
                                (estado, nombre, grupo["nombre"], fecha_texto,
                                 detalle or f"Estado de asistencia: {estado}", self.usuario))
                    else:
                        cursor.execute("""INSERT INTO registros_escolares
                            (tipo, alumno, grupo, fecha, detalle, registrado_por)
                            VALUES (%s,%s,%s,%s,%s,%s)""",
                            (accion, nombre, grupo["nombre"], fecha_texto,
                             detalle or f"Registro de {accion.lower()} realizado desde el pase de lista.", self.usuario))

                conexion.commit()
                messagebox.showinfo("Lista guardada", f"Se guardó la lista de {grupo['nombre']} para el {fecha_texto}.")
                self.ir("Inicio")
            except (mysql.connector.Error, ValueError) as error:
                if conexion:
                    conexion.rollback()
                messagebox.showerror("Error al guardar", str(error))
            finally:
                if conexion is not None and conexion.is_connected():
                    conexion.close()

        self.boton(panel, "Cargar lista", cargar).pack(side="left", padx=12)
        self.boton(self.contenido, "Guardar lista", guardar).pack(anchor="e", pady=12)
        self.boton(self.contenido, "Registrar incidencia detallada", lambda: self.ir("Registrar incidencia")).pack(anchor="e", pady=(0, 10))
        cargar()



    def formulario(self, campos, tipo, boton_texto="Guardar"):
        self.limpiar_contenido()
        self.titulo(
            self.vista_actual,
            "Completa los datos y guarda el registro."
        )

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=20, pady=18)
        panel.pack(fill="x")
        panel.columnconfigure(1, weight=1)

        self.campos = {}

        campos_texto = {
            "Motivo detallado", "Descripción",
            "Acción tomada", "Observaciones",
            "Decisión / justificación", "Compromisos del alumno",
            "Motivo"
        }

        opciones = {
            "Grupo": self.nombres_mis_grupos(),
            "Tipo de problema": [
                "Autocontrol", "Conducta", "Conflicto", "Otro"
            ],
            "Tipo de acción": [
                "Amonestación", "Citatorio Tutor",
                "Suspensión Temporal", "Seguimiento Psicológico"
            ],
            "Estado": [
                "Pendiente", "Revisado", "Resuelto", "Justificado"
            ],
            "Tipo de justificante": [
                "Médico", "Familiar", "Académico", "Otro"
            ]
        }

        for i, campo in enumerate(campos):
            tk.Label(
                panel, text=campo,
                bg=BLANCO, fg=TEXTO,
                font=("Segoe UI", 10, "bold"),
                anchor="w"
            ).grid(
                row=i, column=0, sticky="nw",
                padx=(0, 15), pady=8
            )

            if campo in campos_texto:
                widget = tk.Text(
                    panel, height=4, wrap="word",
                    bg=self.claro, fg=TEXTO,
                    font=("Segoe UI", 10), relief="flat"
                )

            elif campo in opciones:
                valores = opciones[campo]

                if campo == "Grupo" and not valores:
                    valores = GRUPOS_BASE

                widget = ttk.Combobox(
                    panel, values=valores, state="readonly"
                )

                if campo == "Grupo" and valores:
                    widget.set(valores[0])

            else:
                widget = ttk.Entry(panel)

                if campo == "Fecha":
                    widget.insert(0, date.today().isoformat())

                if campo == "Hora":
                    widget.insert(
                        0, datetime.now().strftime("%H:%M")
                    )

            widget.grid(
                row=i, column=1, sticky="ew", pady=6
            )
            self.campos[campo] = widget

        self.boton(
            panel, boton_texto,
            lambda: self.guardar_registro(tipo)
        ).grid(
            row=len(campos), column=1,
            sticky="e", pady=(18, 0)
        )

    def nombres_mis_grupos(self):
        try:
            return [g["nombre"] for g in self.obtener_mis_grupos()]
        except mysql.connector.Error:
            return []

    def guardar_registro(self, tipo):
        alumno = self.leer_campo("Alumno")

        if not alumno:
            messagebox.showwarning(
                "Campo obligatorio", "Escribe el nombre del alumno."
            )
            return

        fecha = self.leer_campo("Fecha") or date.today().isoformat()
        hora = self.leer_campo("Hora") or None

        try:
            datetime.strptime(fecha, "%Y-%m-%d")

            if hora:
                formato = "%H:%M:%S" if len(hora) == 8 else "%H:%M"
                datetime.strptime(hora, formato)
                if len(hora) == 5:
                    hora += ":00"

        except ValueError:
            messagebox.showwarning(
                "Fecha u hora incorrecta",
                "Usa fecha AAAA-MM-DD y hora HH:MM."
            )
            return

        grupo = self.leer_campo("Grupo")

        detalle = next(
            (
                self.leer_campo(c) for c in (
                    "Motivo detallado", "Descripción",
                    "Observaciones", "Motivo",
                    "Decisión / justificación"
                ) if self.leer_campo(c)
            ),
            ""
        )

        accion = next(
            (
                self.leer_campo(c) for c in (
                    "Tipo de acción", "Acción tomada",
                    "Tipo de problema", "Tipo de justificante"
                ) if self.leer_campo(c)
            ),
            ""
        )

        evidencia = (
            self.leer_campo("Evidencia (ruta)")
            or self.leer_campo("Archivo de evidencia")
        )

        seguimiento = (
            self.leer_campo("Necesita seguimiento con tutor")
            .lower() in ("si", "sí", "1", "true")
        )

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor()

            cursor.execute("""
                INSERT INTO registros_escolares
                (tipo, alumno, grupo, fecha, hora, detalle,
                 accion, evidencia, seguimiento, registrado_por)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                tipo, alumno, grupo or None, fecha, hora,
                detalle or None, accion or None,
                evidencia or None, seguimiento, self.usuario
            ))

            conexion.commit()

            messagebox.showinfo(
                "Registro guardado",
                f"Se guardó correctamente. Folio: {cursor.lastrowid}"
            )
            self.ir("Inicio")

        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

    def pantalla_retardos(self):
        self.formulario(
            ["Alumno", "Grupo", "Fecha", "Hora", "Observaciones"],
            "Retardo/Falta", "Guardar registro"
        )

    def pantalla_conducta(self):
        self.formulario(
            ["Alumno", "Grupo", "Fecha",
             "Tipo de problema", "Motivo detallado",
             "Acción tomada"],
            "Conducta", "Guardar reporte"
        )

    def pantalla_autocontrol(self):
        self.formulario(
            ["Alumno", "Grupo", "Fecha", "Tipo de problema",
             "Descripción", "Acción tomada"],
            "Autocontrol", "Guardar reporte"
        )

    def pantalla_incidencia(self):
        self.formulario(
            ["Alumno", "Grupo", "Fecha", "Hora",
             "Motivo detallado", "Evidencia (ruta)",
             "Acción tomada"],
            "Incidencia", "Guardar incidencia"
        )

    def pantalla_justificantes(self):
        self.formulario(
            ["Alumno", "Grupo", "Fecha",
             "Tipo de justificante",
             "Archivo de evidencia", "Observaciones"],
            "Justificante", "Guardar justificante"
        )


    def mostrar_tabla(self, titulo, sql, parametros=()):
        self.limpiar_contenido()
        self.titulo(titulo, "Información consultada en MySQL.")

        marco = tk.Frame(self.contenido, bg=BLANCO)
        marco.pack(fill="both", expand=True)

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, parametros)
            filas = cursor.fetchall()

            if not filas:
                tk.Label(
                    marco, text="No hay registros para mostrar.",
                    bg=BLANCO, fg=GRIS, padx=15, pady=20
                ).pack(anchor="w")
                return

            columnas = list(filas[0].keys())

            tabla_marco = tk.Frame(marco, bg=BLANCO)
            tabla_marco.pack(fill="both", expand=True)

            tabla = ttk.Treeview(
                tabla_marco, columns=columnas,
                show="headings"
            )

            sy = ttk.Scrollbar(
                tabla_marco, orient="vertical",
                command=tabla.yview
            )
            sx = ttk.Scrollbar(
                tabla_marco, orient="horizontal",
                command=tabla.xview
            )

            tabla.configure(
                yscrollcommand=sy.set,
                xscrollcommand=sx.set
            )

            sy.pack(side="right", fill="y")
            sx.pack(side="bottom", fill="x")
            tabla.pack(fill="both", expand=True)

            for columna in columnas:
                tabla.heading(
                    columna,
                    text=columna.replace("_", " ").title()
                )
                tabla.column(
                    columna, width=150,
                    minwidth=90, stretch=True
                )

            for fila in filas:
                tabla.insert(
                    "", "end",
                    values=[
                        "" if v is None else str(v)
                        for v in fila.values()
                    ]
                )

        except mysql.connector.Error as error:
            messagebox.showerror("Error de consulta", str(error))

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

    def pantalla_reportes(self):
        if self.rol == "docente":
            self.mostrar_tabla(
                "Mis reportes",
                """SELECT id, tipo, alumno, grupo, fecha,
                          estado, creado_en
                   FROM registros_escolares
                   WHERE registrado_por=%s
                   ORDER BY creado_en DESC""",
                (self.usuario,)
            )
        else:
            self.mostrar_tabla(
                "Consultar reportes",
                """SELECT id, tipo, alumno, grupo, fecha,
                          estado, registrado_por, creado_en
                   FROM registros_escolares
                   ORDER BY creado_en DESC"""
            )

    def pantalla_directivo(self):
        self.limpiar_contenido()
        self.titulo(
            "Panel directivo",
            "Resumen general de la actividad escolar."
        )

        fila = tk.Frame(self.contenido, bg=FONDO)
        fila.pack(fill="x", pady=8)

        try:
            total = self.contar()
            incidencias = self.contar("Incidencia")
            pendientes = self.contar(estado="Pendiente")
        except mysql.connector.Error:
            total = incidencias = pendientes = "—"

        for t, v, d in [
            ("Registros", total, "Actividad acumulada"),
            ("Incidencias", incidencias, "Incidencias registradas"),
            ("Pendientes", pendientes, "Requieren revisión")
        ]:
            self.tarjeta(fila, t, v, d)

        self.boton(
            self.contenido, "Consultar reportes",
            lambda: self.ir("Consultar reportes")
        ).pack(anchor="w", pady=12)

        self.grafica_tipo("Registros por tipo")

    def tabla_directiva_con_detalle(self, encabezado, sql, parametros=()):
        self.limpiar_contenido()
        self.titulo(encabezado, "Selecciona un registro para consultar el estatus y los detalles del alumno.")
        marco = tk.Frame(self.contenido, bg=BLANCO, padx=10, pady=10)
        marco.pack(fill="both", expand=True)

        try:
            filas = self.consultar(sql, parametros)
        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))
            return

        if not filas:
            tk.Label(marco, text="No hay registros para mostrar.", bg=BLANCO,
                     fg=GRIS, font=("Segoe UI", 11)).pack(anchor="w", padx=8, pady=12)
            return

        columnas = list(filas[0].keys())
        tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=12)
        sy = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        sx = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        tabla.pack(fill="both", expand=True)

        for columna in columnas:
            tabla.heading(columna, text=columna.replace("_", " ").title())
            tabla.column(columna, width=145, minwidth=90, stretch=True)

        por_id = {}
        for fila in filas:
            iid = str(fila["id"])
            tabla.insert("", "end", iid=iid,
                         values=["" if v is None else str(v) for v in fila.values()])
            por_id[iid] = fila

        detalle = tk.Frame(marco, bg=self.claro, padx=14, pady=12)
        detalle.pack(fill="x", pady=(10, 0))
        etiqueta = tk.Label(detalle, text="Selecciona un alumno de la tabla para ver su información.",
                            bg=self.claro, fg=self.oscuro, justify="left",
                            anchor="w", wraplength=900, font=("Segoe UI", 10))
        etiqueta.pack(fill="x")

        def mostrar_detalle(event=None):
            seleccion = tabla.selection()
            if not seleccion:
                return
            fila = por_id.get(seleccion[0])
            if fila:
                campos = [
                    f"{clave.replace('_', ' ').title()}: {valor if valor not in (None, '') else 'Sin información'}"
                    for clave, valor in fila.items() if clave != "id"
                ]
                etiqueta.configure(text="\\n".join(campos))

        tabla.bind("<<TreeviewSelect>>", mostrar_detalle)

    def pantalla_director_retardos_faltas(self):
        self.tabla_directiva_con_detalle(
            "Retardos y faltas",
            """SELECT id, alumno, grupo, tipo, fecha, hora, estado, detalle,
                      registrado_por
               FROM registros_escolares
               WHERE LOWER(tipo) IN ('retardo', 'falta', 'retardo/falta')
               ORDER BY fecha DESC, creado_en DESC"""
        )

    def pantalla_director_conducta(self):
        self.tabla_directiva_con_detalle(
            "Conducta",
            """SELECT id, alumno, grupo, tipo, fecha, detalle, accion,
                      seguimiento, estado, registrado_por
               FROM registros_escolares
               WHERE LOWER(tipo) IN ('conducta', 'incidencia', 'autocontrol')
               ORDER BY fecha DESC, creado_en DESC"""
        )

    def pantalla_director_justificantes(self):
        self.tabla_directiva_con_detalle(
            "Justificantes",
            """SELECT id, alumno, grupo, fecha, accion, detalle, evidencia,
                      estado, registrado_por
               FROM registros_escolares
               WHERE LOWER(tipo)='justificante'
               ORDER BY fecha DESC, creado_en DESC"""
        )

    def pantalla_reportes_generales(self):
        self.mostrar_tabla(
            "Reportes generales",
            """SELECT id, tipo, alumno, grupo, fecha, hora, estado, detalle,
                      accion, registrado_por, creado_en
               FROM registros_escolares
               ORDER BY creado_en DESC"""
        )

    def pantalla_monitoreo(self):
        self.mostrar_tabla(
            "Monitoreo docente",
            """SELECT registrado_por AS docente,
                      COUNT(*) AS registros,
                      SUM(tipo='Incidencia') AS incidencias,
                      MAX(creado_en) AS ultimo_registro
               FROM registros_escolares
               GROUP BY registrado_por
               ORDER BY registros DESC"""
        )

    def pantalla_avisos(self):
        self.limpiar_contenido()
        self.titulo(
            "Notificaciones",
            "Novedades escolares recientes y asuntos pendientes. "
            "Se muestran registros de asistencia, retardos, faltas, conducta, reportes e incidencias."
        )
        try:
            if self.rol == "director":
                sql = """SELECT id, tipo, alumno, grupo, fecha, estado,
                                registrado_por, creado_en, detalle
                         FROM registros_escolares
                         WHERE estado='Pendiente'
                            OR creado_en >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                         ORDER BY creado_en DESC LIMIT 250"""
                filas = self.consultar(sql)
            else:
                sql = """SELECT id, tipo, alumno, grupo, fecha, estado,
                                registrado_por, creado_en, detalle
                         FROM registros_escolares
                         WHERE (registrado_por=%s)
                           AND (estado='Pendiente'
                            OR creado_en >= DATE_SUB(NOW(), INTERVAL 7 DAY))
                         ORDER BY creado_en DESC LIMIT 250"""
                filas = self.consultar(sql, (self.usuario,))
        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))
            return

        if not filas:
            tk.Label(self.contenido, text="No hay novedades recientes ni notificaciones pendientes.",
                     bg=FONDO, fg=GRIS, font=("Segoe UI", 11)).pack(anchor="w", pady=12)
            return

        for aviso in filas:
            tarjeta = tk.Frame(self.contenido, bg=BLANCO, padx=14, pady=11,
                               highlightbackground="#BFDBFE", highlightthickness=1)
            tarjeta.pack(fill="x", pady=5)
            titulo = f"{aviso['tipo']} · {aviso['alumno']}"
            tk.Label(tarjeta, text=titulo, bg=BLANCO, fg=self.oscuro,
                     font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
            meta = f"Grupo: {aviso.get('grupo') or 'Sin grupo'}   |   Fecha: {aviso['fecha']}   |   Estado: {aviso.get('estado') or 'Registrado'}"
            tk.Label(tarjeta, text=meta, bg=BLANCO, fg=AZUL_MEDIO,
                     font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(3, 0))
            detalle = aviso.get("detalle") or "Sin detalle adicional."
            tk.Label(tarjeta, text=detalle, bg=BLANCO, fg=TEXTO,
                     justify="left", anchor="w", wraplength=850).pack(fill="x", pady=(4, 0))
            tk.Label(tarjeta, text=f"Registrado por: {aviso.get('registrado_por') or 'Sistema'}",
                     bg=BLANCO, fg=GRIS, font=("Segoe UI", 8), anchor="w").pack(fill="x", pady=(4, 0))


    def pantalla_decisiones(self):
        self.limpiar_contenido()
        self.titulo(
            "Toma de decisiones",
            "Registra una acción directiva para un alumno."
        )

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel.pack(fill="x")
        panel.columnconfigure(1, weight=1)

        self.campos = {}

        campos = [
            "Folio del registro (opcional)",
            "Alumno",
            "Tipo de acción",
            "Decisión / justificación"
        ]

        for i, campo in enumerate(campos):
            tk.Label(
                panel, text=campo,
                bg=BLANCO, fg=TEXTO
            ).grid(row=i, column=0, sticky="nw", padx=8, pady=8)

            if campo == "Tipo de acción":
                widget = ttk.Combobox(
                    panel,
                    values=[
                        "Amonestación", "Citatorio Tutor",
                        "Suspensión Temporal",
                        "Seguimiento Psicológico"
                    ],
                    state="readonly"
                )
            elif campo == "Decisión / justificación":
                widget = tk.Text(panel, height=5, wrap="word")
            else:
                widget = ttk.Entry(panel)

            widget.grid(row=i, column=1, sticky="ew", padx=8, pady=8)
            self.campos[campo] = widget

        self.boton(
            panel, "Guardar decisión",
            self.guardar_decision
        ).grid(row=len(campos), column=1, sticky="e", pady=12)

    def guardar_decision(self):
        alumno = self.leer_campo("Alumno")
        accion = self.leer_campo("Tipo de acción")
        justificacion = self.leer_campo("Decisión / justificación")
        folio = self.leer_campo("Folio del registro (opcional)")

        if not alumno or not accion:
            messagebox.showwarning(
                "Datos incompletos",
                "Escribe el alumno y selecciona una acción."
            )
            return

        try:
            registro_id = int(folio) if folio else None
        except ValueError:
            messagebox.showwarning(
                "Folio inválido", "El folio debe ser numérico."
            )
            return

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor()

            cursor.execute("""
                INSERT INTO decisiones_directivas
                (registro_id, alumno, accion, justificacion, director)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                registro_id, alumno, accion,
                justificacion or None, self.usuario
            ))

            if registro_id:
                cursor.execute("""
                    UPDATE registros_escolares
                    SET estado='Revisado'
                    WHERE id=%s
                """, (registro_id,))

            conexion.commit()

            messagebox.showinfo(
                "Decisión guardada",
                "La decisión se guardó correctamente."
            )
            self.ir("Inicio")

        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

    def pantalla_carta(self):
        self.limpiar_contenido()
        self.titulo(
            "Carta compromiso",
            "Registra los compromisos acordados con el alumno."
        )

        panel = tk.Frame(self.contenido, bg=BLANCO, padx=18, pady=18)
        panel.pack(fill="x")
        panel.columnconfigure(1, weight=1)

        self.campos = {}

        for i, campo in enumerate([
            "Alumno", "Tutor", "Motivo",
            "Fecha", "Compromisos del alumno"
        ]):
            tk.Label(
                panel, text=campo,
                bg=BLANCO, fg=TEXTO
            ).grid(row=i, column=0, sticky="nw", padx=8, pady=8)

            if campo == "Compromisos del alumno" or campo == "Motivo":
                widget = tk.Text(panel, height=4, wrap="word")
            else:
                widget = ttk.Entry(panel)
                if campo == "Fecha":
                    widget.insert(0, date.today().isoformat())

            widget.grid(row=i, column=1, sticky="ew", padx=8, pady=8)
            self.campos[campo] = widget

        self.boton(
            panel, "Guardar carta", self.guardar_carta
        ).grid(row=5, column=1, sticky="e", pady=10)

    def guardar_carta(self):
        alumno = self.leer_campo("Alumno")
        fecha = self.leer_campo("Fecha")
        tutor = self.leer_campo("Tutor")
        motivo = self.leer_campo("Motivo")
        compromisos = self.leer_campo("Compromisos del alumno")

        if not alumno:
            messagebox.showwarning(
                "Dato obligatorio", "Escribe el nombre del alumno."
            )
            return

        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(
                "Fecha incorrecta", "Usa el formato AAAA-MM-DD."
            )
            return

        conexion = None

        try:
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO cartas_compromiso
                (alumno, tutor, motivo, compromisos, fecha, director)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                alumno, tutor or None, motivo or None,
                compromisos or None, fecha, self.usuario
            ))
            conexion.commit()

            messagebox.showinfo(
                "Carta guardada",
                "La carta compromiso se guardó en MySQL."
            )
            self.ir("Inicio")

        except mysql.connector.Error as error:
            messagebox.showerror("Error MySQL", str(error))

        finally:
            if conexion is not None and conexion.is_connected():
                conexion.close()

   
    def pantalla_graficas(self):
        self.limpiar_contenido()
        if self.rol == "docente":
            descripcion = "Estadísticas de los alumnos y grupos que tienes asignados."
            opciones = ["Alumnos por grupo", "Asistencia por estado", "Asistencia del día", "Registros por tipo"]
        else:
            descripcion = "Estadísticas generales de alumnos, grupos y actividad de toda la escuela."
            opciones = ["Alumnos por grupo", "Alumnos por grado", "Alumnos activos e inactivos", "Cantidad de grupos", "Resumen de la escuela", "Asistencia por estado", "Registros por tipo"]

        self.titulo("Gráficos", descripcion)
        controles = tk.Frame(self.contenido, bg=FONDO)
        controles.pack(fill="x", pady=8)
        tipo = ttk.Combobox(controles, values=opciones, state="readonly", width=32)
        tipo.set(opciones[0])
        tipo.pack(side="left", padx=(0, 8))

        def dibujar():
            self.limpiar_grafica()
            self.grafica_tipo(tipo.get())

        self.boton(controles, "Mostrar estadísticas", dibujar).pack(side="left")
        self.grafica_tipo(opciones[0])

    def limpiar_grafica(self):
        if self.canvas_grafica is not None:
            try:
                self.canvas_grafica.get_tk_widget().destroy()
            except tk.TclError:
                pass
            self.canvas_grafica = None

    def grafica_tipo(self, tipo):
        if not GRAFICAS_DISPONIBLES:
            tk.Label(
                self.contenido,
                text="Instala matplotlib con: "
                     "pip install matplotlib",
                bg=FONDO, fg=GRIS
            ).pack(anchor="w", pady=12)
            return

       
        if not hasattr(self, "marco_graficas"):
            self.marco_graficas = tk.Frame(
                self.contenido, bg=FONDO
            )
            self.marco_graficas.pack(fill="both", expand=True)
        else:
            for widget in self.marco_graficas.winfo_children():
                widget.destroy()

        try:
            if tipo == "Alumnos por grupo":
                if self.rol == "docente":
                    filas = self.consultar("""
                        SELECT g.nombre AS etiqueta, COUNT(a.id) AS cantidad
                        FROM docente_grupos dg
                        INNER JOIN grupos_escolares g ON g.id=dg.grupo_id
                        LEFT JOIN alumnos_escolares a ON a.grupo_id=g.id AND a.activo=TRUE
                        WHERE dg.docente=%s
                        GROUP BY g.id, g.nombre ORDER BY g.nombre
                    """, (self.usuario,))
                else:
                    filas = self.consultar("""
                        SELECT g.nombre AS etiqueta, COUNT(a.id) AS cantidad
                        FROM grupos_escolares g
                        LEFT JOIN alumnos_escolares a ON a.grupo_id=g.id AND a.activo=TRUE
                        GROUP BY g.id, g.nombre ORDER BY g.nombre
                    """)

            elif tipo == "Alumnos por grado":
                filas = self.consultar("""
                    SELECT CONCAT(LEFT(g.nombre, 1), '° grado') AS etiqueta,
                           COUNT(a.id) AS cantidad
                    FROM grupos_escolares g
                    LEFT JOIN alumnos_escolares a ON a.grupo_id=g.id AND a.activo=TRUE
                    GROUP BY LEFT(g.nombre, 1) ORDER BY etiqueta
                """)

            elif tipo == "Alumnos activos e inactivos":
                filas = self.consultar("""
                    SELECT IF(a.activo=TRUE, 'Activos', 'Inactivos') AS etiqueta,
                           COUNT(*) AS cantidad
                    FROM alumnos_escolares a
                    GROUP BY a.activo ORDER BY a.activo DESC
                """)

            elif tipo == "Cantidad de grupos":
                filas = self.consultar("""
                    SELECT 'Grupos registrados' AS etiqueta, COUNT(*) AS cantidad
                    FROM grupos_escolares
                """)

            elif tipo == "Resumen de la escuela":
                filas = self.consultar("""
                    SELECT 'Alumnos activos' AS etiqueta, COUNT(*) AS cantidad
                    FROM alumnos_escolares WHERE activo=TRUE
                    UNION ALL
                    SELECT 'Grupos' AS etiqueta, COUNT(*) AS cantidad
                    FROM grupos_escolares
                    UNION ALL
                    SELECT 'Docentes' AS etiqueta, COUNT(*) AS cantidad
                    FROM usuarios WHERE LOWER(rol)='docente'
                    UNION ALL
                    SELECT 'Registros escolares' AS etiqueta, COUNT(*) AS cantidad
                    FROM registros_escolares
                """)

            elif tipo == "Registros por tipo":
                if self.rol == "docente":
                    filas = self.consultar("""
                        SELECT tipo AS etiqueta, COUNT(*) AS cantidad
                        FROM registros_escolares WHERE registrado_por=%s
                        GROUP BY tipo ORDER BY cantidad DESC
                    """, (self.usuario,))
                else:
                    filas = self.consultar("""
                        SELECT tipo AS etiqueta, COUNT(*) AS cantidad
                        FROM registros_escolares
                        GROUP BY tipo ORDER BY cantidad DESC
                    """)

            elif tipo == "Asistencia del día":
                if self.rol == "docente":
                    filas = self.consultar("""
                        SELECT ae.estado AS etiqueta, COUNT(*) AS cantidad
                        FROM asistencias_escolares ae
                        INNER JOIN docente_grupos dg ON dg.grupo_id=ae.grupo_id
                        WHERE ae.fecha=%s AND dg.docente=%s
                        GROUP BY ae.estado ORDER BY cantidad DESC
                    """, (date.today().isoformat(), self.usuario))
                else:
                    filas = self.consultar("""
                        SELECT estado AS etiqueta, COUNT(*) AS cantidad
                        FROM asistencias_escolares WHERE fecha=%s
                        GROUP BY estado ORDER BY cantidad DESC
                    """, (date.today().isoformat(),))

            elif tipo == "Asistencia por estado":
                if self.rol == "docente":
                    filas = self.consultar("""
                        SELECT ae.estado AS etiqueta, COUNT(*) AS cantidad
                        FROM asistencias_escolares ae
                        INNER JOIN docente_grupos dg ON dg.grupo_id=ae.grupo_id
                        WHERE dg.docente=%s
                        GROUP BY ae.estado ORDER BY cantidad DESC
                    """, (self.usuario,))
                else:
                    filas = self.consultar("""
                        SELECT estado AS etiqueta, COUNT(*) AS cantidad
                        FROM asistencias_escolares
                        GROUP BY estado ORDER BY cantidad DESC
                    """)

            else:
                filas = self.consultar("""
                    SELECT registrado_por AS etiqueta,
                           COUNT(*) AS cantidad
                    FROM registros_escolares
                    GROUP BY registrado_por
                    ORDER BY cantidad DESC LIMIT 12
                """)

        except mysql.connector.Error as error:
            tk.Label(
                self.marco_graficas,
                text=f"Error al consultar datos: {error}",
                bg=FONDO, fg=ROJO
            ).pack(anchor="w")
            return

        if not filas:
            tk.Label(
                self.marco_graficas,
                text="Todavía no hay datos suficientes para esta gráfica.",
                bg=FONDO, fg=GRIS
            ).pack(anchor="w", pady=15)
            return

        etiquetas = [str(f["etiqueta"]) for f in filas]
        valores = [int(f["cantidad"] or 0) for f in filas]

        figura = Figure(figsize=(8, 4.5), dpi=100)
        eje = figura.add_subplot(111)

        if tipo in ("Asistencia del día", "Asistencia por estado"):
            colores = [
                "#16A34A", "#DC2626", "#F59E0B",
                "#2563EB", "#7C3AED", "#64748B"
            ]

            wedges, _, _ = eje.pie(
                valores,
                labels=etiquetas,
                autopct="%1.1f%%",
                startangle=90,
                colors=colores[:len(valores)],
                wedgeprops={"edgecolor": "white", "linewidth": 1}
            )

            eje.set_title(tipo)

            aviso = tk.Label(
                self.marco_graficas,
                text="Haz clic en una sección circular para ver su valor.",
                bg=FONDO, fg=GRIS
            )
            aviso.pack(anchor="w")

            def seleccionar_seccion(evento):
                if evento.artist in wedges:
                    i = list(wedges).index(evento.artist)
                    aviso.config(
                        text=f"{etiquetas[i]}: {valores[i]} registros"
                    )

            canvas = FigureCanvasTkAgg(
                figura, master=self.marco_graficas
            )
            canvas.draw()
            canvas.get_tk_widget().pack(
                fill="both", expand=True, pady=8
            )
            canvas.mpl_connect("pick_event", seleccionar_seccion)

            for wedge in wedges:
                wedge.set_picker(True)

            self.canvas_grafica = canvas
            return

        barras = eje.bar(
            etiquetas, valores,
            color=self.color, picker=True
        )

        eje.set_title(tipo)
        eje.set_ylabel("Cantidad")
        eje.tick_params(axis="x", labelrotation=25)
        figura.tight_layout()

        canvas = FigureCanvasTkAgg(
            figura, master=self.marco_graficas
        )
        canvas.draw()
        canvas.get_tk_widget().pack(
            fill="both", expand=True, pady=8
        )

        aviso = tk.Label(
            self.marco_graficas,
            text="Haz clic en una barra para consultar su cantidad.",
            bg=FONDO, fg=GRIS
        )
        aviso.pack(anchor="w")

        def seleccionar_barra(evento):
            if evento.artist in barras:
                i = list(barras).index(evento.artist)
                aviso.config(
                    text=f"{etiquetas[i]}: {valores[i]} registros"
                )

        canvas.mpl_connect("pick_event", seleccionar_barra)
        self.canvas_grafica = canvas

    
    def pantalla_buscar(self):
        self.limpiar_contenido()
        self.titulo(
            "Buscar registros",
            "Busca reportes por nombre de alumno."
        )

        fila = tk.Frame(self.contenido, bg=FONDO)
        fila.pack(fill="x", pady=8)

        entrada = ttk.Entry(fila)
        entrada.pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )

        def buscar():
            texto = entrada.get().strip()

            if not texto:
                messagebox.showwarning(
                    "Búsqueda vacía",
                    "Escribe el nombre de un alumno."
                )
                return

            if self.rol == "docente":
                sql = """
                    SELECT id, tipo, alumno, grupo, fecha, estado
                    FROM registros_escolares
                    WHERE alumno LIKE %s AND registrado_por=%s
                    ORDER BY creado_en DESC
                """
                params = (f"%{texto}%", self.usuario)
            else:
                sql = """
                    SELECT id, tipo, alumno, grupo, fecha,
                           estado, registrado_por
                    FROM registros_escolares
                    WHERE alumno LIKE %s
                    ORDER BY creado_en DESC
                """
                params = (f"%{texto}%",)

            self.mostrar_tabla(
                "Resultados de búsqueda", sql, params
            )

        self.boton(fila, "Buscar", buscar).pack(side="left")


if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaNezahualcoyotl(root)
    root.mainloop()