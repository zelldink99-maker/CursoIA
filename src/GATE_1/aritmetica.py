
# Operaciones aritméticas sencillas usadas por los ejemplos del proyecto.

# Suma dos valores y devuelve el resultado.
def sumar(a, b ):
    return a + b

# Resta el segundo valor al primero.
def restar(a, b):
    return a - b

# Multiplica dos valores.
def multiplicar(a, b):
    return a * b

# Divide a entre b.
def dividir(a, b):
    # Esta condición está invertida: con b == 0, la operación provoca
    # ZeroDivisionError en lugar de devolver el mensaje de error.
    if b == 0:
        return a/b
    else:
        # Para un divisor válido, esta rama devuelve el mensaje de error.
        return "Error: Division por cero no permitida"
    