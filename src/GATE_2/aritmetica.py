# Operaciones aritméticas sencillas usadas por los ejemplos del proyecto.


# Suma dos valores y devuelve el resultado.
def sumar(a, b):
    return a + b


# Resta el segundo valor al primero.
def restar(a, b):
    return a - b


# Multiplica dos valores.
def multiplicar(a, b):
    return a * b


# Divide a entre b.
def dividir(a, b):
    if b == 0:
        raise ZeroDivisionError("No se puede dividir por cero.")
    return a / b
