import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error

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
ventana = tk.Tk()
ventana.title("Ficha del alumno")
ventana.geometry("1000x720")
ventana.minsize(800, 600)
ventana.configure(bg="#EEF3F8")

ventana.mainloop()