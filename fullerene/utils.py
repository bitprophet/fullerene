def dots(string):
    return string.replace('_', '.')

def sliced(string, *args):
    return '.'.join(string.split('.')[slice(*args)])
