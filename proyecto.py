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


ventana = tk.Tk()
ventana.title("Ficha del alumno")
ventana.geometry("1000x720")
ventana.minsize(800, 600)
ventana.configure(bg="#EEF3F8")

ventana.mainloop()