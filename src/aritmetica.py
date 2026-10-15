
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
    # Esta condición intenta dividir entre cero cuando b == 0 y causaría
    # ZeroDivisionError; la condición está invertida respecto al mensaje.
    if b == 0:
        return a/b
    else:
        # Para divisores distintos de cero, devuelve este mensaje en vez
        # de calcular la división.
        return "Error: Division por cero no permitida"
    