import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error


# Cayetano Fonseca Samadhi: Colores y nombre del equipo

AZUL = "#7C2D12"
AZUL_CLARO = "#FFEDD5"
VERDE = "#A16207"
NARANJA = "#F97316"
ROJO = "#B91C1C"
BLANCO = "#FFFBEB"
FONDO = "#FEF2F2"
TEXTO = "#450A0A"

estilo = ttk.Style()
estilo.theme_use("clam")

estilo.configure(
    "Treeview",
    background=BLANCO,
    foreground=TEXTO,
    fieldbackground=BLANCO,
    rowheight=30,
    font=("Arial", 10)
)

estilo.configure(
    "Treeview.Heading",
    background=AZUL,
    foreground=BLANCO,
    font=("Arial", 10, "bold")
)

estilo.map(
    "Treeview",
    background=[("selected", AZUL_CLARO)],
    foreground=[("selected", TEXTO)]
)

# Grande Fonseca Denise Geraldin: Proyecto inicial y estructura principal

def conectar():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ficha_alumnos"
    )

# Silva Velasco Leticia Alexa: Boton Limpiar

def limpiar():
    global id_seleccionado

    nombre.set("")
    grupo.set("")
    numero_lista.set("")

    id_seleccionado = None

    aviso.config(text="")

    resultado.config(state="normal")
    resultado.delete("1.0", tk.END)
    resultado.config(state="disabled")

    for elemento in tabla.selection():
        tabla.selection_remove(elemento)
# Tomas Martinez Zuri Naomi: Nombres del equipo

pie = tk.Frame(ventana, bg=AZUL, pady=10)
pie.pack(fill="x")

tk.Label(
    pie,
    text="FICHA DEL ALUMNO | EQUIPO 1",
    bg=AZUL,
    fg=NARANJA,
    font=("Arial", 11, "bold")
).pack()

tk.Label(
    pie,
    text="Grande Fonseca Denise Geraldin | Cayetano Fonseca Samadhi | Espino Chavez Leonardo Franco | Silva Velasco Leticia Alexa | Tomas Martinez Zuri Naomi",
    bg=AZUL,
    fg=BLANCO,
    font=("Arial", 8),
    wraplength=950
).pack(pady=4)
ventana = tk.Tk()
ventana.title("Ficha de alumnos")
ventana.geometry("1000x720")
ventana.minsize(800, 600)
ventana.configure(bg="#EEF3F8")

ventana.mainloop()